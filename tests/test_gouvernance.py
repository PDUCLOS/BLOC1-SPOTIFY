"""Tests du démonstrateur : chaque contrôle trouve les défauts injectés, la remédiation
corrige ce qu'elle doit corriger et laisse en échec ce qu'elle ne doit pas maquiller."""

from __future__ import annotations

import json

import pytest

from gouvernance import checks, remediate, report
from gouvernance.__main__ import main
from gouvernance.generate import generate, sha256


@pytest.fixture(scope="module")
def ds():
    return generate(n_users=2000, seed=7)


@pytest.fixture(scope="module")
def con(ds, tmp_path_factory):
    return checks.connect(ds.write_csv(tmp_path_factory.mktemp("csv")))


@pytest.fixture(scope="module")
def results(con):
    before = {r.id: r for r in checks.run_all(con, "raw")}
    stats = remediate.remediate(con)
    after = {r.id: r for r in checks.run_all(con, "clean")}
    return before, stats, after


def test_generation_est_deterministe():
    a, b = generate(n_users=200, seed=1), generate(n_users=200, seed=1)
    assert a.tables == b.tables
    assert generate(n_users=200, seed=2).tables != a.tables


def test_aucune_donnee_reelle():
    ds = generate(n_users=300, seed=3)
    emails = [u["email"] for u in ds.tables["users"]]
    assert all(e.endswith("example.com") for e in emails)


def test_chaque_controle_a_un_identifiant_unique():
    ids = [c.id for c in checks.CHECKS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("cid", ["Q01", "Q02", "Q04", "Q05", "Q06", "Q07", "Q08", "Q09", "Q10",
                                 "C01", "C02", "C03", "C04", "C05", "C06", "K02"])
def test_les_defauts_injectes_sont_detectes(results, cid):
    before, _, _ = results
    assert before[cid].failed > 0, f"{cid} n'a rien trouvé alors que des défauts sont injectés"


def test_controles_sans_defaut_injecte_passent(results):
    before, _, _ = results
    for cid in ("Q03", "Q11", "K01", "K03", "K04"):
        assert before[cid].failed == 0, cid


def test_orphelins_comptes_exactement(ds, results):
    before, _, _ = results
    users = {u["user_id"] for u in ds.tables["users"]}
    expected = sum(e["user_id"] not in users for e in ds.tables["events"])
    assert before["Q08"].failed == expected


def test_dsar_et_violations_attendues(results):
    before, _, _ = results
    assert before["C05"].failed == 4          # 3 clôturées en retard + 1 ouverte hors délai
    assert set(before["C06"].sample) == {"INC-003", "INC-006"}  # 90 h, et jamais notifiée
    assert before["C06"].checked == 5         # l'incident sans donnée personnelle est hors champ


def test_remediation_corrige_les_donnees(results):
    _, _, after = results
    for cid in ("Q05", "Q06", "Q07", "Q08", "Q09", "C01", "C02", "C03", "C04", "K02"):
        assert after[cid].failed == 0, cid


def test_remediation_n_invente_rien(results):
    before, _, after = results
    assert after["Q02"].failed == before["Q02"].failed   # année de naissance : à recollecter
    assert after["Q10"].failed > 0                        # lignage : à corriger à la source
    assert after["C05"].failed == before["C05"].failed    # défaut de processus
    assert after["C06"].failed == before["C06"].failed


def test_pseudonymisation_identique_au_generateur(con, results):
    raw = con.execute("SELECT email FROM raw.users WHERE user_id = 'U0000001'").fetchone()[0]
    sql = con.execute("SELECT sha256(LOWER(TRIM(?)))", [raw]).fetchone()[0]
    assert sql == sha256(raw)


def test_enrichissement_du_pays(results):
    before, stats, after = results
    assert stats["pays_enrichis_depuis_abonnements"] > 0
    assert after["Q01"].failed < before["Q01"].failed


def test_kpis_et_cibles(con, results):
    kb = checks.kpis(list(results[0].values()), con, "raw")
    ka = checks.kpis(list(results[2].values()), con, "clean")
    rows = {r["key"]: r for r in report.kpi_rows(kb, ka)}
    assert rows["consentements_traces"]["ok"]
    assert not rows["violations_notifiees_72h"]["ok"]
    assert ka["taux_donnees_manquantes"] < kb["taux_donnees_manquantes"]


def test_cli_produit_le_rapport(tmp_path, capsys):
    assert main(["--users", "300", "--out", str(tmp_path / "out"), "--data", str(tmp_path / "csv")]) == 0
    payload = json.loads((tmp_path / "out" / "rapport.json").read_text(encoding="utf-8"))
    assert payload["synthese"]["total"] == len(checks.CHECKS) + 4
    html = (tmp_path / "out" / "rapport.html").read_text(encoding="utf-8")
    assert "Données 100 % synthétiques" in html
    assert "Contrôles conformes" in capsys.readouterr().out
