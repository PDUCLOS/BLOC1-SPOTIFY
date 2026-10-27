"""Génère docs/architecture.drawio (4 pages) puis, si draw.io est installé, les exports PNG.

Les diagrammes reprennent le contenu des livrables (02a, 02c, 03, 04) ; les annotations
de relecture ajoutées ici sont signalées comme telles (cadre pointillé orange).

Usage :  python scripts/build_drawio.py
"""

from __future__ import annotations

import subprocess
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architecture.drawio"
IMG = ROOT / "docs" / "img"
DRAWIO = Path(r"C:\Users\Patrice DUCLOS\AppData\Local\Programs\draw.io\draw.io.exe")

GREEN, DARK, PURPLE, SLATE = "#1DB954", "#191414", "#7C4DFF", "#2E3B4E"
FONT = "fontFamily=Segoe UI;"


class Page:
    def __init__(self, name: str, w: int, h: int):
        self.name, self.w, self.h, self.cells, self.n = name, w, h, [], 0

    def _id(self) -> str:
        self.n += 1
        return f"{self.name[0]}-{self.n}"

    def box(self, label: str, x, y, w, h, fill="#ffffff", stroke="#9aa5a0", font="#151a17", size=13,
            bold=False, rounded=True, extra="", align="center") -> str:
        cid = self._id()
        style = (f"rounded={int(rounded)};whiteSpace=wrap;html=1;arcSize=8;fillColor={fill};strokeColor={stroke};"
                 f"fontColor={font};fontSize={size};{FONT}align={align};verticalAlign=middle;spacing=8;"
                 f"{'fontStyle=1;' if bold else ''}{extra}")
        self.cells.append(f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
                          f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return cid

    def text(self, label: str, x, y, w, h, size=13, color="#151a17", bold=False, align="left") -> str:
        return self.box(label, x, y, w, h, fill="none", stroke="none", font=color, size=size, bold=bold,
                        rounded=False, align=align)

    def edge(self, src: str, dst: str, label: str = "", dashed=False, color="#3d4642", exit=None, entry=None,
             arrow=True, both=False, points=None) -> str:
        cid = self._id()
        e = f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;" if exit else ""
        n = f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;" if entry else ""
        style = (f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;{e}{n}"
                 f"strokeColor={color};strokeWidth=1.6;fontSize=11;{FONT}fontColor=#3d4642;labelBackgroundColor=#ffffff;"
                 f"endArrow={'block' if arrow else 'none'};endFill=1;startArrow={'block' if both else 'none'};startFill=1;"
                 f"{'dashed=1;dashPattern=6 4;' if dashed else ''}")
        pts = ""
        if points:
            pts = '<Array as="points">' + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points) + "</Array>"
        self.cells.append(f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" edge="1" parent="1" '
                          f'source="{src}" target="{dst}"><mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>')
        return cid

    def xml(self, idx: int) -> str:
        body = "".join(self.cells)
        return (f'<diagram id="p{idx}" name="{escape(self.name)}"><mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" '
                f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{self.w}" '
                f'pageHeight="{self.h}" background="#ffffff" math="0" shadow="0"><root><mxCell id="0"/>'
                f'<mxCell id="1" parent="0"/>{body}</root></mxGraphModel></diagram>')


def lines(title: str, *items: str) -> str:
    return f"<b>{escape(title)}</b><br>" + "<br>".join(escape(i) for i in items)


def html_box(p: Page, title: str, sub: str, items: list[str], x, y, w, h, fill, font="#ffffff") -> str:
    label = (f'<div style="font-size:16px;font-weight:bold">{escape(title)}</div>'
             f'<div style="font-size:12px;font-style:italic;margin:2px 0 6px">{escape(sub)}</div>'
             f'<div style="font-size:12px;text-align:left">' + "<br>".join("• " + escape(i) for i in items) + "</div>")
    cid = p._id()
    style = (f"rounded=1;whiteSpace=wrap;html=1;arcSize=6;fillColor={fill};strokeColor={fill};fontColor={font};"
             f"{FONT}verticalAlign=top;spacing=10;")
    p.cells.append(f'<mxCell id="{cid}" value="{escape(label)}" style="{style}" vertex="1" parent="1">'
                   f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    return cid


def note(p: Page, label: str, x, y, w, h) -> str:
    return p.box(label, x, y, w, h, fill="#fff6e5", stroke="#c98a12", font="#5a3d00", size=12, align="left",
                 extra="dashed=1;dashPattern=5 3;")


# ---------------------------------------------------------------- page 1 : organisation
def page_organisation() -> Page:
    p = Page("1 · Organisation", 1600, 1060)
    p.text("Organisation de la gouvernance — modèle Center of Excellence", 40, 20, 1100, 36, size=24, bold=True)
    p.text("Source : organigramme 02a et politique 02c §5. Traits pleins : rattachement ; pointillés : collaboration.",
           40, 56, 1100, 24, size=13, color="#5b645f")
    exe = html_box(p, "Direction exécutive", "Sponsor — CEO / COO", ["Mandat stratégique, validation de la politique",
                   "Allocation budgétaire"], 630, 100, 340, 110, DARK)
    cdo = html_box(p, "Chief Data Officer (CDO)", "Pilote de la gouvernance",
                   ["Définit politiques et stratégie data", "Aligne gouvernance et priorités business",
                    "Supervise conformité et usage approprié"], 360, 270, 340, 130, GREEN)
    com = html_box(p, "Comité de gouvernance", "Mensuel au démarrage, puis trimestriel",
                   ["Approuve politiques et processus", "Arbitre les enjeux interservices",
                    "Aligne légal, conformité, opérations"], 900, 270, 340, 130, PURPLE)
    p.edge(exe, cdo, exit=(0.5, 1), entry=(0.5, 0))
    p.edge(exe, com, exit=(0.5, 1), entry=(0.5, 0))
    p.edge(cdo, com, "collaboration", dashed=True, exit=(1, 0.5), entry=(0, 0.5), arrow=False)
    dpo = html_box(p, "Data Protection Officer", "Conformité RGPD / CCPA / DSAR",
                   ["Surveille la conformité vie privée", "Point de contact CNIL", "Pilote la réponse aux violations"],
                   170, 470, 340, 125, SLATE)
    rssi = html_box(p, "Engineering / RSSI", "Sécurité et infrastructure",
                    ["SIEM (Splunk), chiffrement (Vormetric)", "Conformité PCI-DSS", "Tests d'intrusion, accès"],
                    570, 470, 340, 125, SLATE)
    jur = html_box(p, "Juridique & Privacy", "Cadre légal et risque réglementaire",
                   ["Veille RGPD / CCPA / AI Act", "Contrats DPA et sous-traitance", "Avis juridique sur les traitements"],
                   970, 470, 340, 125, SLATE)
    for t in (dpo, rssi, jur):
        p.edge(cdo, t, exit=(0.3, 1), entry=(0.5, 0))
    stew = p.box("", 120, 680, 1260, 200, fill="#eefaf2", stroke=GREEN, extra="verticalAlign=top;")
    p.text("Data Stewards — un par domaine métier : qualité, accès, conformité de leur périmètre", 140, 688, 1000, 26,
           size=14, bold=True, color="#0d5c31")
    for i, (dom, items) in enumerate([("Marketing (pilote)", ["Engagement et audiences", "Campagnes et ciblage"]),
                                      ("Produit", ["Usage produit", "Recommandation"]),
                                      ("Finance", ["Revenus et abonnements", "Reporting financier"]),
                                      ("Paiement", ["Données titulaire (PCI-DSS)", "Transactions et fraude"])]):
        html_box(p, dom, "Data Steward", items, 145 + i * 305, 725, 285, 130, GREEN)
    # Le CDO descend vers les stewards par l'espace entre DPO et RSSI (x = 540).
    p.edge(cdo, stew, exit=(0.5294, 1), entry=(0.3333, 0))
    p.box("Tous les collaborateurs : appliquer la politique, formation annuelle, signaler les incidents (politique §5)",
          120, 905, 1260, 44, fill="#f3f4f3", stroke="#c9cfcb", size=13)
    note(p, "Relecture — point de vigilance : RGPD art. 38-3 demande que le DPO rende compte « au niveau le plus élevé "
            "de la direction ». La note 02b le rattache au CDO et assimile le CDO à ce niveau : à confirmer, ou "
            "ajouter une ligne directe DPO → direction exécutive.", 1330, 110, 250, 170)
    note(p, "Rôles volontairement hors organigramme (note 02b §4) : Data Owners, Data Managers, Data Engineers, "
            "Data Scientists — ils relèvent du Data Management, que la gouvernance audite.", 1330, 470, 250, 130)
    p.text("Légende : noir = sponsor · vert = gouvernance et stewardship · violet = comité transverse · ardoise = fonctions "
           "sous le CDO · cadre orange pointillé = annotation de relecture (hors livrables)", 40, 975, 1500, 40, size=12,
           color="#5b645f")
    return p


# ---------------------------------------------------------------- page 2 : flux et outillage
def page_flux() -> Page:
    p = Page("2 · Flux de données et outillage", 1600, 1000)
    p.text("Flux de données du pilote et outillage cible", 40, 20, 1100, 36, size=24, bold=True)
    p.text("Source : plan 03 §3 et annexe B, présentation slides 8-9. Sous chaque brique : le rôle responsable (plan 03, tableau 3.7).",
           40, 56, 1300, 24, size=13, color="#5b645f")
    band = p.box("Couche conformité et sécurité — transverse à toute la chaîne :  OneTrust (consentement, data mapping, "
                 "DSAR)  ·  Splunk (SIEM, détection des incidents)  ·  Vormetric (chiffrement, clés)", 40, 110, 1500, 56,
                 fill="#ecebff", stroke=PURPLE, font="#2d1a7a", size=14, bold=True)
    steps = [
        ("Sources", "User Engagement Data (sessions, écoutes, interactions) · audiences marketing", "Data Steward Marketing"),
        ("Databricks", "Lakehouse : ingestion, stockage, ML · Unity Catalog (lignage, accès)", "CDO + Data Engineering"),
        ("dbt + Talend", "Transformation, tests qualité (4 dimensions), dédoublonnage, lignage", "Data Stewards"),
        ("Collibra", "Catalogue : quoi, où, qui est responsable, qui peut y accéder", "CDO + Data Stewards"),
        ("Consommation", "BI, data science, activation marketing (audiences consenties)", "Métiers"),
    ]
    ids = []
    for i, (t, d, r) in enumerate(steps):
        x = 40 + i * 310
        ids.append(p.box(lines(t, d).replace(escape(t), t), x, 230, 260, 130, fill="#ffffff" if i else "#f3f4f3",
                         stroke=GREEN if i else "#9aa5a0", size=13))
        p.text(f"Responsable : {r}", x, 365, 260, 24, size=12, color="#5b645f", align="center")
    for a, b in zip(ids, ids[1:]):
        p.edge(a, b, exit=(1, 0.5), entry=(0, 0.5))
    p.box("Couche MLOps et gouvernance IA — usages ML (recommandation, personnalisation) :  MLflow (suivi des expériences, "
          "registre de modèles)  ·  Evidently (qualité et dérive en production) · Responsable : Data Science + CDO",
          350, 420, 1190, 56, fill="#e9f6ff", stroke="#2a7ab8", font="#103c5c", size=13, bold=True)
    p.text("Classification (politique §3) : le niveau d'une donnée fixe ses contrôles", 40, 520, 900, 28, size=16, bold=True)
    for i, (lvl, ex, ctl, fill) in enumerate([
            ("Public", "catalogue musical, pages artistes", "aucun contrôle spécifique", "#f3f4f3"),
            ("Interne", "métriques business, rapports", "RBAC, accès authentifié", "#e8f5ec"),
            ("Confidentiel", "profils, comportements, licences", "chiffrement, RBAC strict, audit trail", "#fff3d6"),
            ("Restreint", "paiement (PCI-DSS), credentials", "AES-256, MFA, ségrégation, audit temps réel", "#fde3e0")]):
        p.box(f"<b>{lvl}</b><br>{escape(ex)}<br><i>{escape(ctl)}</i>", 40 + i * 375, 560, 355, 90, fill=fill,
              stroke="#c9cfcb", size=13)
    p.box("<b>Périmètre du pilote (6 mois)</b><br>Dans le périmètre : User Engagement Data et audiences marketing · "
          "équipes Marketing, Product Analytics, IT, Légal/Privacy.<br>Hors périmètre : données de paiement (PCI-DSS) et "
          "catalogue Content/Artist, traités en vagues 2 et 3.", 40, 690, 900, 110, fill="#eefaf2", stroke=GREEN,
          size=13, align="left")
    note(p, "Démonstrateur du dépôt (python -m gouvernance) : DuckDB tient le rôle de Databricks, des requêtes SQL "
            "à la manière des tests dbt celui de dbt/Talend, catalog.toml celui de Collibra. Aucun de ces outils "
            "n'est déployé.", 980, 690, 560, 110)
    p.text("Le schéma ne montre pas l'infrastructure cloud sous Databricks, facturée à part (plan 03, annexe A).", 40, 830,
           1300, 24, size=12, color="#5b645f")
    return p


# ---------------------------------------------------------------- page 3 : feuille de route
def page_roadmap() -> Page:
    p = Page("3 · Feuille de route", 1600, 900)
    p.text("Feuille de route : pilote, vagues de déploiement, trajectoire d'organisation", 40, 20, 1300, 36, size=24, bold=True)
    p.text("Trois documents décrivent le calendrier ; ils sont alignés ligne à ligne ci-dessous (mois M0 à M24).", 40, 56,
           1300, 24, size=13, color="#5b645f")
    x0, k, top = 300, 50, 120
    for m in range(0, 25, 2):
        p.text(f"M{m}", x0 + m * k - 20, top, 40, 20, size=11, color="#5b645f", align="center")
        p.box("", x0 + m * k, top + 24, 1, 560, fill="#e3e7e4", stroke="none", rounded=False)
    rows = [
        ("Plan 03 — déploiement", [(0, 6, "Pilote Marketing", GREEN), (6, 10, "Vague 1 : Produit, DS", "#46c776"),
                                   (10, 14, "Vague 2 : Paiement, Finance", "#46c776"), (14, 18, "Vague 3 : Content, RH, Support", "#46c776")]),
        ("Politique 02c §6.1", [(0, 6, "Phase 1 : pilote", "#7d8a84"), (6, 12, "Phase 2 : Contenu, Paiement, bascule CoE", "#7d8a84"),
                                (12, 24, "Phase 3 : rollout global, ML/IA (MLflow + Evidently)", "#7d8a84")]),
        ("Slides 7-8 — organisation", [(0, 12, "Centralisé : le bureau du CDO porte le programme", SLATE),
                                       (12, 24, "Center of Excellence : noyau + équipes data métiers", PURPLE)]),
        ("Comité de gouvernance", [(0, 6, "Mensuel", "#9a7cff"), (6, 24, "Trimestriel (02a) · revues annuelles (02c)", "#b9a6ff")]),
    ]
    for i, (label, bars) in enumerate(rows):
        y = top + 50 + i * 95
        p.text(label, 40, y + 8, 250, 40, size=14, bold=True)
        for a, b, t, c in bars:
            p.box(escape(t), x0 + a * k + 2, y, (b - a) * k - 4, 56, fill=c, stroke=c, font="#ffffff", size=12, bold=True)
    y = top + 50 + 4 * 95
    p.text("Jalons du pilote (plan 03 §4.4)", 40, y + 8, 250, 40, size=14, bold=True)
    p.box("<b>M1</b> kick-off, cartographie, KPIs · <b>M1-M2</b> audit qualité (baseline) · <b>M2</b> audit RGPD/CCPA · "
          "<b>M2-M3</b> Collibra, Talend, OneTrust<br><b>M4</b> revue mi-parcours · <b>M5</b> formation Marketing · "
          "<b>M6</b> bilan des KPIs et plan de scaling", x0 + 2, y, 16 * k - 4, 56, fill="#ffffff", stroke=GREEN,
          size=12, align="left")
    note(p, "Relecture (audit D01) : le plan finit à M18, la politique à M24 ; la politique bascule vers le CoE en phase 2 "
            "(7 à 12 mois), les slides à M12. Compatible (outillage vs organisation), mais à formuler de la même façon.",
         40, 730, 760, 80)
    note(p, "KPIs du pilote mesurés à M6 : −10 % de données manquantes, 100 % de consentements tracés, +20 % de vitesse "
            "d'accès, 100 % des incidents détectés sous 24 h, 100 % des équipes Marketing formées (plan 03 §4.6).",
         830, 730, 730, 80)
    return p


# ---------------------------------------------------------------- page 4 : démonstrateur
def page_demo() -> Page:
    p = Page("4 · Démonstrateur", 1600, 820)
    p.text("Démonstrateur exécutable du dépôt — python -m gouvernance", 40, 20, 1300, 36, size=24, bold=True)
    p.text("Données 100 % synthétiques. Il rend vérifiables les règles de la politique, sans prétendre déployer la cible.",
           40, 56, 1300, 24, size=13, color="#5b645f")
    gen = p.box(lines("generate.py", "5 000 utilisateurs, ~50 000 événements", "13 types de défauts injectés"), 40, 130, 250, 100)
    raw = p.box(lines("DuckDB · schéma raw", "6 tables CSV chargées telles quelles"), 360, 130, 250, 100, stroke=GREEN)
    chk = p.box(lines("checks.py · 21 contrôles", "11 qualité (4 dimensions)", "6 conformité RGPD/CCPA · 4 catalogue"),
                700, 130, 280, 100, fill="#eefaf2", stroke=GREEN)
    cat = p.box(lines("catalog.toml", "responsable, classification,", "base légale, rétention"), 700, 290, 280, 90,
                fill="#ecebff", stroke=PURPLE)
    rem = p.box(lines("remediate.py", "standardise, enrichit, déduplique,", "pseudonymise, purge, met en quarantaine"),
                360, 290, 250, 100)
    cln = p.box(lines("DuckDB · clean + quarantine", "recontrôlé avec les mêmes 21 règles"), 360, 450, 250, 90, stroke=GREEN)
    rep = p.box(lines("report.py", "rapport.json + rapport.html", "KPIs avant / après vs cibles"), 1080, 130, 260, 100,
                fill="#e9f6ff", stroke="#2a7ab8")
    p.edge(gen, raw, "CSV", exit=(1, 0.5), entry=(0, 0.5))
    p.edge(raw, chk, "avant", exit=(1, 0.5), entry=(0, 0.5))
    p.edge(cat, chk, exit=(0.5, 0), entry=(0.5, 1))
    p.edge(raw, rem, exit=(0.5, 1), entry=(0.5, 0))
    p.edge(rem, cln, exit=(0.5, 1), entry=(0.5, 0))
    p.edge(cln, chk, "après", exit=(1, 0.5), entry=(1, 0.75), points=[(1030, 495), (1030, 205)])
    p.edge(chk, rep, exit=(1, 0.5), entry=(0, 0.5))
    liv = p.box(lines("Livrables du dépôt", "01 évaluation · 02c politique", "03 plan · 04 présentation"), 1080, 450, 260, 90)
    aud = p.box(lines("audit_livrables.py", "recalcule maturité, budget, décomptes", "12 points : 7 cohérents, 5 signalés"),
                1080, 290, 260, 100, fill="#fff3d6", stroke="#c98a12")
    p.edge(liv, aud, "lecture seule", exit=(0.5, 0), entry=(0.5, 1))
    p.edge(aud, rep, exit=(0.5, 0), entry=(0.5, 1))
    p.box("<b>Ce que la remédiation refuse de maquiller</b><br>année de naissance manquante (à recollecter) · lignage absent "
          "(à corriger à la source) · DSAR en retard et violations notifiées hors délai (défauts de processus) · un "
          "consentement sans preuve est traité comme absent (RGPD art. 7-1)", 40, 600, 940, 90, fill="#f3f4f3",
          stroke="#c9cfcb", size=13, align="left")
    p.box("<b>Tests</b> : 40 tests pytest (défauts détectés, remédiation, audit sur les vrais fichiers)", 1080, 600, 460, 90,
          fill="#f3f4f3", stroke="#c9cfcb", size=13, align="left")
    return p


def main() -> int:
    pages = [page_organisation(), page_flux(), page_roadmap(), page_demo()]
    xml = ('<mxfile host="Electron" type="device">' + "".join(pg.xml(i) for i, pg in enumerate(pages)) + "</mxfile>")
    OUT.write_text(xml, encoding="utf-8")
    print(f"{OUT} : {len(pages)} pages")
    if DRAWIO.exists():
        for i in range(len(pages)):
            png = IMG / f"architecture-{i + 1}.png"
            subprocess.run([str(DRAWIO), "-x", "-f", "png", "-p", str(i + 1), "-s", "1.5", "-b", "20", "-o", str(png), str(OUT)],
                           check=True, capture_output=True)
            print(f"  {png.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
