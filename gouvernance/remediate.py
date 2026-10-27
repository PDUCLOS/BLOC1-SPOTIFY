"""Remédiation du périmètre pilote : schéma ``raw`` -> schéma ``clean``.

Ce que l'on corrige, et ce que l'on refuse de corriger :
- on standardise, on enrichit depuis une source de référence, on déduplique, on pseudonymise ;
- on met en quarantaine ce qui est faux (orphelins, durées négatives, dates futures) ;
- on purge ce qui dépasse la durée de conservation ;
- un consentement sans preuve est traité comme absent (la charge de la preuve pèse sur
  le responsable de traitement, RGPD art. 7-1) ;
- on n'invente rien : un lignage manquant, une DSAR en retard ou une violation notifiée
  trop tard restent en échec. Ce sont des défauts de processus, à corriger à la source.
"""

from __future__ import annotations

import duckdb

from .checks import ISO, NOW, blank

COUNTRY_NAMES = "MAP {'FRANCE': 'FR', 'ALLEMAGNE': 'DE', 'ESPAGNE': 'ES'}"


def remediate(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    con.execute("CREATE SCHEMA IF NOT EXISTS clean")
    con.execute("CREATE SCHEMA IF NOT EXISTS quarantine")
    con.execute(f"""
        CREATE OR REPLACE TABLE clean.users AS
        WITH std AS (
            SELECT * EXCLUDE (country, phone_number),   -- colonne hors catalogue : supprimée
                   COALESCE({COUNTRY_NAMES}[UPPER(TRIM(country))], UPPER(TRIM(country))) AS country_std
            FROM raw.users)
        SELECT std.* EXCLUDE (country_std, consent_marketing),
               CASE WHEN country_std IN {ISO} THEN country_std ELSE s.billing_country END AS country,
               CASE WHEN consent_marketing = 'true' AND {blank('consent_ts')} THEN 'false'
                    ELSE consent_marketing END AS consent_marketing
        FROM std LEFT JOIN raw.subscriptions s USING (user_id)""")
    con.execute(f"""
        CREATE OR REPLACE TABLE quarantine.events AS
        SELECT *, CASE
            WHEN user_id NOT IN (SELECT user_id FROM raw.users) THEN 'utilisateur inconnu'
            WHEN TRY_CAST(ms_played AS BIGINT) < 0 THEN 'durée négative'
            WHEN TRY_CAST(event_ts AS TIMESTAMP) > {NOW} THEN 'date future' END AS motif
        FROM raw.events
        WHERE user_id NOT IN (SELECT user_id FROM raw.users)
           OR TRY_CAST(ms_played AS BIGINT) < 0 OR TRY_CAST(event_ts AS TIMESTAMP) > {NOW}""")
    con.execute(f"""
        CREATE OR REPLACE TABLE clean.events AS
        SELECT * FROM raw.events
        WHERE event_id NOT IN (SELECT event_id FROM quarantine.events)
          AND TRY_CAST(event_ts AS TIMESTAMP) >= {NOW} - INTERVAL 24 MONTH
        QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY ingested_at) = 1""")
    con.execute(f"""
        CREATE OR REPLACE TABLE clean.campaign_audience AS
        SELECT a.* EXCLUDE (email_sha256),
               CASE WHEN regexp_matches(email_sha256, '^[0-9a-f]{{64}}$') THEN email_sha256
                    ELSE sha256(LOWER(TRIM(email_sha256))) END AS email_sha256
        FROM raw.campaign_audience a
        WHERE user_id IN (SELECT user_id FROM clean.users WHERE consent_marketing = 'true')""")
    for t in ("subscriptions", "dsar_requests", "security_incidents"):
        con.execute(f"CREATE OR REPLACE TABLE clean.{t} AS SELECT * FROM raw.{t}")

    count = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    return {
        "pays_enrichis_depuis_abonnements": count(
            f"SELECT COUNT(*) FROM raw.users r JOIN clean.users c USING (user_id) "
            f"WHERE (r.country IS NULL OR UPPER(TRIM(r.country)) NOT IN {ISO}) AND c.country IS NOT NULL"),
        "consentements_sans_preuve_revoques": count(
            "SELECT COUNT(*) FROM raw.users r JOIN clean.users c USING (user_id) "
            "WHERE r.consent_marketing = 'true' AND c.consent_marketing = 'false'"),
        "evenements_en_quarantaine": count("SELECT COUNT(*) FROM quarantine.events"),
        "doublons_supprimes": count(
            "SELECT COUNT(*) - COUNT(DISTINCT event_id) FROM raw.events "
            "WHERE event_id NOT IN (SELECT event_id FROM quarantine.events)"),
        "evenements_purges_retention": count(
            f"SELECT COUNT(DISTINCT event_id) FROM raw.events WHERE TRY_CAST(event_ts AS TIMESTAMP) < {NOW} - INTERVAL 24 MONTH "
            "AND event_id NOT IN (SELECT event_id FROM quarantine.events)"),
        "audience_retiree_sans_consentement": count("SELECT COUNT(*) FROM raw.campaign_audience")
        - count("SELECT COUNT(*) FROM clean.campaign_audience"),
        "emails_en_clair_pseudonymises": count(
            "SELECT COUNT(*) FROM raw.campaign_audience WHERE NOT regexp_matches(email_sha256, '^[0-9a-f]{64}$') "
            "AND user_id IN (SELECT user_id FROM clean.campaign_audience)"),
        "colonnes_hors_catalogue_supprimees": count(
            "SELECT COUNT(*) FROM information_schema.columns r WHERE r.table_schema = 'raw' AND r.table_name = 'users' "
            "AND r.column_name NOT IN (SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'clean' AND table_name = 'users')"),
    }
