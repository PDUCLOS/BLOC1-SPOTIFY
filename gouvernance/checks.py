"""Contrôles de gouvernance exécutés dans DuckDB.

Convention reprise des tests dbt : chaque contrôle est une requête SQL qui compte les
lignes en échec et les lignes contrôlées. Taux de réussite = 1 − échecs / contrôlées.
Chaque contrôle est rattaché à un principe de la politique (02c) ou à un KPI du plan (03).
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb

from .generate import AS_OF

CATALOG = Path(__file__).with_name("catalog.toml")
LEVELS = ["public", "interne", "confidentiel", "restreint"]
ISO = "('FR','DE','ES','IT','SE','GB','US','BR','MX','JP','IN','SG')"
NOW = f"TIMESTAMP '{AS_OF:%Y-%m-%d %H:%M:%S}'"


def blank(col: str) -> str:
    return f"NULLIF(TRIM(CAST({col} AS VARCHAR)), '') IS NULL"


@dataclass(frozen=True)
class Check:
    id: str
    family: str      # qualite | conformite | catalogue
    dimension: str   # completude, exactitude, coherence, tracabilite, consentement, ...
    title: str
    reference: str   # principe / article / KPI d'origine
    table: str
    failing: str     # condition SQL vraie pour une ligne en échec
    scope: str = "TRUE"  # lignes concernées par le contrôle
    threshold: float = 0.95


# {s} est remplacé par le schéma contrôlé (raw ou clean).
CHECKS: list[Check] = [
    Check("Q01", "qualite", "completude", "Pays renseigné", "Politique, principe 4", "users", blank("country")),
    Check("Q02", "qualite", "completude", "Année de naissance renseignée", "Politique, principe 4", "users", blank("birth_year")),
    Check("Q03", "qualite", "completude", "Consentement marketing renseigné", "Politique, principe 4", "users",
          "consent_marketing NOT IN ('true', 'false') OR consent_marketing IS NULL"),
    Check("Q04", "qualite", "exactitude", "E-mail au bon format", "Politique, principe 4", "users",
          r"NOT regexp_matches(COALESCE(email, ''), '^[^@\s]+@[^@\s]+\.[a-z]{2,}$')"),
    Check("Q05", "qualite", "exactitude", "Pays dans le référentiel ISO", "Politique, principe 4", "users",
          f"country NOT IN {ISO}", scope=f"NOT ({blank('country')})"),
    Check("Q06", "qualite", "exactitude", "Durée d'écoute positive", "Politique, principe 4", "events",
          "TRY_CAST(ms_played AS BIGINT) < 0 OR TRY_CAST(ms_played AS BIGINT) IS NULL"),
    Check("Q07", "qualite", "exactitude", "Événement non daté dans le futur", "Politique, principe 4", "events",
          f"TRY_CAST(event_ts AS TIMESTAMP) > {NOW} OR TRY_CAST(event_ts AS TIMESTAMP) IS NULL"),
    Check("Q08", "qualite", "coherence", "Événement rattaché à un utilisateur connu", "Politique, principe 4", "events",
          "user_id NOT IN (SELECT user_id FROM {s}.users)"),
    Check("Q09", "qualite", "coherence", "Identifiant d'événement unique", "Politique, principe 4", "events",
          "event_id IN (SELECT event_id FROM {s}.events GROUP BY 1 HAVING COUNT(*) > 1)"),
    Check("Q10", "qualite", "tracabilite", "Lignage des événements (source, ingestion)", "Politique, principe 4", "events",
          f"{blank('source_system')} OR {blank('ingested_at')}"),
    Check("Q11", "qualite", "tracabilite", "Lignage des profils (source, ingestion)", "Politique, principe 4", "users",
          f"{blank('source_system')} OR {blank('ingested_at')}"),
    Check("C01", "conformite", "consentement", "Consentement tracé (horodatage + canal)", "Plan, KPI pilote « 100 % »",
          "users", f"{blank('consent_ts')} OR {blank('consent_source')}", scope="consent_marketing = 'true'", threshold=1.0),
    Check("C02", "conformite", "consentement", "Audience de campagne : consentement présent", "RGPD art. 6-1-a et 7",
          "campaign_audience",
          "user_id NOT IN (SELECT user_id FROM {s}.users WHERE consent_marketing = 'true' "
          f"AND NOT ({blank('consent_ts')}))", threshold=1.0),
    Check("C03", "conformite", "minimisation", "Audience pseudonymisée (SHA-256)", "Politique, principe 6",
          "campaign_audience", "NOT regexp_matches(COALESCE(email_sha256, ''), '^[0-9a-f]{64}$')", threshold=1.0),
    Check("C04", "conformite", "minimisation", "Événements dans la durée de conservation (24 mois)", "Politique, principe 6",
          "events", f"TRY_CAST(event_ts AS TIMESTAMP) < {NOW} - INTERVAL 24 MONTH", threshold=1.0),
    Check("C05", "conformite", "droits", "Demandes DSAR dans les délais (RGPD 30 j, CCPA 45 j)", "Politique, principe 7",
          "dsar_requests",
          f"date_diff('day', CAST(received_at AS TIMESTAMP), COALESCE(TRY_CAST(closed_at AS TIMESTAMP), {NOW})) "
          "> CASE regime WHEN 'CCPA' THEN 45 ELSE 30 END",
          scope=f"NOT ({blank('closed_at')}) OR date_diff('day', CAST(received_at AS TIMESTAMP), {NOW}) "
                "> CASE regime WHEN 'CCPA' THEN 45 ELSE 30 END",
          threshold=1.0),
    Check("C06", "conformite", "violations", "Violation notifiée sous 72 h", "RGPD art. 33", "security_incidents",
          f"COALESCE(TRY_CAST(notified_at AS TIMESTAMP), {NOW}) > CAST(detected_at AS TIMESTAMP) + INTERVAL 72 HOUR",
          scope="personal_data = 'true'", threshold=1.0),
]


@dataclass
class Result:
    id: str
    family: str
    dimension: str
    title: str
    reference: str
    table: str
    checked: int
    failed: int
    rate: float
    threshold: float
    passed: bool
    sample: list[str]


def connect(csv_paths: dict[str, Path]) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("CREATE SCHEMA raw")
    for name, path in csv_paths.items():
        con.execute(f"CREATE TABLE raw.{name} AS SELECT * FROM read_csv(?, header = true, all_varchar = true)",
                    [str(path)])
    return con


def run_sql_checks(con: duckdb.DuckDBPyConnection, schema: str) -> list[Result]:
    out = []
    for c in CHECKS:
        t, failing, scope = f"{schema}.{c.table}", c.failing.replace("{s}", schema), c.scope.replace("{s}", schema)
        checked, failed = con.execute(
            f"SELECT COUNT(*), COUNT(*) FILTER (WHERE {failing}) FROM {t} WHERE {scope}").fetchone()
        key = con.execute(f"SELECT * FROM {t} LIMIT 0").description[0][0]
        sample = [r[0] for r in con.execute(f"SELECT DISTINCT {key} FROM {t} WHERE ({scope}) AND ({failing}) ORDER BY 1 LIMIT 3").fetchall()]
        rate = 1.0 if checked == 0 else 1 - failed / checked
        out.append(Result(c.id, c.family, c.dimension, c.title, c.reference, c.table, checked, failed,
                          rate, c.threshold, rate >= c.threshold, sample))
    return out


def load_catalog(path: Path = CATALOG) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)["datasets"]


def run_catalog_checks(con: duckdb.DuckDBPyConnection, schema: str, catalog: dict | None = None) -> list[Result]:
    """Contrôles du catalogue : responsabilité (principe 1), classification (§3), minimisation (principe 6)."""
    catalog = catalog or load_catalog()
    physical = {
        t: [r[0] for r in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = ? AND table_name = ?",
            [schema, t]).fetchall()]
        for (t,) in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = ?",
                                [schema]).fetchall()
    }

    def result(cid, dim, title, ref, items, failures, threshold=1.0):
        n, f = len(items), len(failures)
        rate = 1.0 if n == 0 else 1 - f / n
        return Result(cid, "catalogue", dim, title, ref, "catalogue", n, f, rate, threshold, rate >= threshold, failures[:3])

    required = ("steward", "classification", "legal_basis", "retention_months")
    k1 = [t for t in physical if t not in catalog or any(not catalog[t].get(k) for k in required)]
    cols = [(t, c) for t, cs in physical.items() for c in cs]
    k2 = [f"{t}.{c}" for t, c in cols if c not in catalog.get(t, {}).get("columns", {})]
    declared = [(t, c, m) for t, d in catalog.items() for c, m in d.get("columns", {}).items()]
    k3 = [f"{t}.{c}" for t, c, m in declared
          if m.get("pii") and LEVELS.index(m["classification"]) < LEVELS.index("confidentiel")]
    k4 = [f"{t}.{c}" for t, c, _ in declared if c not in physical.get(t, [])]
    return [
        result("K01", "responsabilite", "Chaque table a un responsable, une classification, une base légale et une rétention",
               "Politique, principe 1 et §3", list(physical), k1),
        result("K02", "minimisation", "Aucune colonne physique hors catalogue", "Politique, principe 6", cols, k2),
        result("K03", "classification", "Donnée personnelle classée au moins « confidentiel »", "Politique, §3",
               declared, k3),
        result("K04", "documentation", "Le catalogue ne décrit pas de colonne disparue", "Politique, principe 8",
               declared, k4),
    ]


def run_all(con: duckdb.DuckDBPyConnection, schema: str) -> list[Result]:
    return run_sql_checks(con, schema) + run_catalog_checks(con, schema)


def missing_rate(con: duckdb.DuckDBPyConnection, schema: str, catalog: dict | None = None) -> float:
    """Part de cellules vides sur les colonnes marquées ``critical`` dans le catalogue."""
    catalog = catalog or load_catalog()
    cells = empty = 0
    for t, d in catalog.items():
        for c, m in d.get("columns", {}).items():
            if not m.get("critical"):
                continue
            n, e = con.execute(f"SELECT COUNT(*), COUNT(*) FILTER (WHERE {blank(c)}) FROM {schema}.{t}").fetchone()
            cells, empty = cells + n, empty + e
    return empty / cells if cells else 0.0


def kpis(results: list[Result], con: duckdb.DuckDBPyConnection, schema: str) -> dict:
    by = {r.id: r for r in results}
    quality = [r for r in results if r.family == "qualite"]
    return {
        "score_qualite": sum(r.rate for r in quality) / len(quality),
        "taux_donnees_manquantes": missing_rate(con, schema),
        "consentements_traces": by["C01"].rate,
        "dsar_dans_les_delais": by["C05"].rate,
        "violations_notifiees_72h": by["C06"].rate,
        "controles_ok": sum(r.passed for r in results),
        "controles_total": len(results),
    }


def as_dicts(results: list[Result]) -> list[dict]:
    return [asdict(r) for r in results]
