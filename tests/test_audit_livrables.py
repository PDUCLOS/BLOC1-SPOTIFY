"""Tests de l'audit de cohérence : sur les vrais livrables du dépôt, puis sur des cas construits."""

from __future__ import annotations

import pytest

from gouvernance import audit_livrables as al


@pytest.fixture(scope="module")
def findings():
    return {f.id: f for f in al.audit()}


def test_notes_du_document_d_evaluation():
    assert al.eval_scores() == [3, 2, 2, 3, 2, 2, 2, 3, 2]


def test_le_graphique_couvre_les_neuf_dimensions():
    assert list(al.chart_scores()) == al.DIMENSIONS


def test_ecart_de_maturite_detecte(findings):
    assert findings["A01"].statut == "ecart"
    assert findings["A02"].statut == "ecart"
    assert "2,33" in findings["A02"].constat and "2,44" in findings["A02"].constat


@pytest.mark.parametrize("text, expected", [
    ("40–70 K$", (40, 70)), ("0–5 K$", (0, 5)), ("0,5–1,5 M$", (500, 1500)), ("≈ 350–560 K$", (350, 560)),
])
def test_parse_range(text, expected):
    assert al.parse_range(text) == expected


def test_parse_range_refuse_l_illisible():
    with pytest.raises(ValueError):
        al.parse_range("sur devis")


def test_budget(findings):
    assert findings["B01"].statut == "ok"      # 270–430 K$
    assert findings["B02"].statut == "ok"      # 2,1–5,8 M$
    assert findings["B03"].statut == "ecart"   # « 30 à 50 % » appliqué à 30 %
    assert findings["B04"].statut == "ok"
    assert "351–645" in findings["B03"].constat


def test_decomptes_de_la_slide_5(findings):
    assert [findings[i].statut for i in ("C01", "C02", "C03", "C05")] == ["ok"] * 4
    assert findings["C04"].statut == "non_tracable"


def test_tous_les_statuts_sont_connus(findings):
    assert {f.statut for f in findings.values()} <= {"ok", "ecart", "non_tracable", "a_harmoniser"}


def test_l_audit_ne_modifie_pas_les_livrables(tmp_path):
    files = sorted(al.ROOT.glob("0*.*"))
    before = {f.name: f.stat().st_mtime_ns for f in files}
    al.audit()
    assert {f.name: f.stat().st_mtime_ns for f in files} == before
