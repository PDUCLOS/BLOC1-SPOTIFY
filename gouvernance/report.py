"""Rapport du démonstrateur : JSON (machine) + tableau de bord HTML autonome (humain)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

TARGETS = {  # cibles reprises de la politique (02c, §6.2) et du plan (03, §4.6)
    "score_qualite": ("Score qualité (moyenne des 11 contrôles qualité)", 0.95, "≥ 95 %", "Politique §6.2"),
    "taux_donnees_manquantes": ("Cellules vides sur colonnes critiques", None, "−10 % vs avant", "Plan §4.6"),
    "consentements_traces": ("Consentements tracés", 1.0, "100 %", "Plan §4.6"),
    "dsar_dans_les_delais": ("DSAR traitées dans les délais légaux", 1.0, "100 %", "Politique §6.2"),
    "violations_notifiees_72h": ("Violations notifiées sous 72 h", 1.0, "100 %", "RGPD art. 33"),
}
LABELS = {
    "pays_enrichis_depuis_abonnements": "Pays vides ou invalides complétés depuis les abonnements",
    "consentements_sans_preuve_revoques": "Consentements sans preuve traités comme absents",
    "evenements_en_quarantaine": "Événements mis en quarantaine (orphelins, durées négatives, dates futures)",
    "doublons_supprimes": "Doublons d'événements supprimés",
    "evenements_purges_retention": "Événements purgés (au-delà de 24 mois)",
    "audience_retiree_sans_consentement": "Lignes d'audience retirées faute de consentement",
    "emails_en_clair_pseudonymises": "E-mails en clair pseudonymisés (SHA-256)",
    "colonnes_hors_catalogue_supprimees": "Colonnes hors catalogue supprimées",
}
STATUS = {"ok": ("ok", "cohérent"), "ecart": ("bad", "écart"), "non_tracable": ("warn", "non traçable"),
          "a_harmoniser": ("warn", "à harmoniser")}


def num(x: int) -> str:
    return f"{x:,}".replace(",", " ")


def pct(x: float, nd: int = 1) -> str:
    return f"{100 * x:.{nd}f} %".replace(".", ",")


def kpi_rows(before: dict, after: dict) -> list[dict]:
    rows = []
    for key, (label, target, target_txt, ref) in TARGETS.items():
        b, a = before[key], after[key]
        if key == "taux_donnees_manquantes":
            change = (a - b) / b if b else 0.0
            ok = change <= -0.10
            rows.append(dict(key=key, label=label, before=pct(b, 2), after=pct(a, 2), target=target_txt,
                             ref=ref, ok=ok, note=f"{pct(change)} en relatif"))
        else:
            rows.append(dict(key=key, label=label, before=pct(b), after=pct(a), target=target_txt, ref=ref,
                             ok=a >= target, note=""))
    return rows


def write(out: Path, payload: dict) -> tuple[Path, Path]:
    out.mkdir(parents=True, exist_ok=True)
    js = out / "rapport.json"
    js.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    html = out / "rapport.html"
    html.write_text(render_html(payload), encoding="utf-8")
    return js, html


def _pill(ok: bool, yes: str = "conforme", no: str = "en échec") -> str:
    return f'<span class="pill {"ok" if ok else "bad"}">{yes if ok else no}</span>'


def render_html(p: dict) -> str:
    meta = p["meta"]
    kpis = "".join(
        f'<tr><td>{escape(r["label"])}</td><td class="num">{r["before"]}</td><td class="num"><b>{r["after"]}</b></td>'
        f'<td class="num">{escape(r["target"])}</td><td>{_pill(r["ok"], "atteint", "non atteint")}'
        f'{" <span class=muted>" + escape(r["note"]) + "</span>" if r["note"] else ""}</td>'
        f'<td class="muted">{escape(r["ref"])}</td></tr>'
        for r in p["kpis"])
    checks = "".join(
        f'<tr><td><code>{b["id"]}</code></td><td>{escape(b["title"])}<div class="muted small">{escape(b["reference"])}'
        f' · {escape(b["table"])}</div></td><td class="num">{num(b["failed"])} / {num(b["checked"])}</td>'
        f'<td>{_pill(b["passed"])}</td><td class="num">{num(a["failed"])} / {num(a["checked"])}</td><td>{_pill(a["passed"])}</td>'
        f'<td class="muted small">{escape(", ".join(map(str, a["sample"] or b["sample"])))}</td></tr>'
        for b, a in zip(p["controles_avant"], p["controles_apres"]))
    remed = "".join(f'<tr><td>{escape(LABELS.get(k, k))}</td><td class="num">{num(v)}</td></tr>'
                    for k, v in p["remediation"].items())
    audit = "".join(
        f'<tr><td><code>{f["id"]}</code></td><td><b>{escape(f["sujet"])}</b><div class="muted small">{escape(f["constat"])}</div></td>'
        f'<td><span class="pill {STATUS[f["statut"]][0]}">{STATUS[f["statut"]][1]}</span></td>'
        f'<td class="small">{escape(f["trouve"])}</td></tr>'
        for f in p["audit_livrables"])
    t = meta["durees_s"]
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Contrôles de gouvernance</title>
<style>
:root {{ --bg:#f5f6f4; --surface:#fff; --ink:#151a17; --muted:#5b645f; --line:#dde2de; --accent:#127a46;
  --good:#127a46; --good-soft:#dff2e7; --warn:#8f5d00; --warn-soft:#fbefd6; --bad:#b0261c; --bad-soft:#fbe2df; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.55 "Segoe UI",system-ui,sans-serif; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:28px 20px 48px; display:grid; gap:22px; }}
h1 {{ font-size:1.7rem; margin:0; }} h2 {{ font-size:1.15rem; margin:0 0 8px; }}
.eyebrow {{ font:600 .72rem Consolas,monospace; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); }}
.muted {{ color:var(--muted); }} .small {{ font-size:.82rem; }}
.card {{ background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:16px 18px; overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:.9rem; }}
th,td {{ padding:8px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
th {{ font-weight:600; font-size:.76rem; color:var(--muted); white-space:nowrap; }}
tr:last-child td {{ border-bottom:0; }} td.num {{ text-align:right; font-family:Consolas,monospace; white-space:nowrap; }}
code {{ font-family:Consolas,monospace; background:#eef1ee; padding:1px 5px; border-radius:3px; }}
.pill {{ font:600 .72rem Consolas,monospace; padding:2px 8px; border-radius:999px; white-space:nowrap; }}
.pill.ok {{ background:var(--good-soft); color:var(--good); }} .pill.bad {{ background:var(--bad-soft); color:var(--bad); }}
.pill.warn {{ background:var(--warn-soft); color:var(--warn); }}
.banner {{ border-left:4px solid var(--warn); }}
</style></head><body><div class="wrap">
<div><span class="eyebrow">Démonstrateur · pilote Marketing / User Engagement Data</span>
<h1>Contrôles de gouvernance : avant et après remédiation</h1>
<p class="muted">Généré par <code>python -m gouvernance</code> le {escape(meta["genere_le"])} ·
{num(meta["lignes"]["users"])} utilisateurs, {num(meta["lignes"]["events"])} événements · graine {meta["graine"]} ·
DuckDB {escape(meta["duckdb"])} · génération {t["generation"]:.2f} s, contrôles {t["controles_avant"]:.2f} s,
remédiation + recontrôle {t["remediation_et_controles_apres"]:.2f} s.</p></div>
<div class="card banner"><b>Données 100 % synthétiques.</b> <span class="muted">Défauts injectés à des taux connus
(<code>gouvernance/generate.py</code>). Les chiffres mesurent le démonstrateur, pas Spotify.</span></div>
<div class="card"><h2>KPIs de pilotage</h2><table><thead><tr><th>Indicateur</th><th class="num">Avant</th><th class="num">Après</th>
<th class="num">Cible</th><th>Statut</th><th>Source</th></tr></thead><tbody>{kpis}</tbody></table></div>
<div class="card"><h2>{p["synthese"]["ok_avant"]} → {p["synthese"]["ok_apres"]} contrôles conformes sur {p["synthese"]["total"]}</h2>
<table><thead><tr><th>Id</th><th>Contrôle</th><th class="num">Échecs avant</th><th></th><th class="num">Échecs après</th><th></th><th>Exemples</th></tr></thead>
<tbody>{checks}</tbody></table></div>
<div class="card"><h2>Ce que la remédiation a fait</h2><table><tbody>{remed}</tbody></table>
<p class="muted small">Non corrigé, volontairement : année de naissance manquante (à recollecter), lignage absent (à corriger dans le pipeline source),
DSAR en retard et violations notifiées hors délai (défauts de processus, pas de données).</p></div>
<div class="card"><h2>Audit de cohérence des livrables</h2><table><thead><tr><th>Id</th><th>Point contrôlé</th><th>Statut</th><th>Trouvé</th></tr></thead>
<tbody>{audit}</tbody></table></div>
</div></body></html>
"""
