"""Audit de cohérence des livrables Word / PowerPoint du dépôt.

Un comité exécutif lit les chiffres de la présentation ; un auditeur relit le document
source. Ce module recalcule ce qui peut l'être et compare les deux. Il lit les fichiers
en lecture seule et ne les modifie jamais.

Statuts : ``ok`` (cohérent), ``ecart`` (contradiction chiffrée), ``non_tracable``
(affirmation sans source dans le dépôt), ``a_harmoniser`` (formulations compatibles
mais différentes d'un document à l'autre).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

import docx
import pptx

ROOT = Path(__file__).resolve().parents[1]
EVAL = "01_Evaluation_Maturite_Data.docx"
POLICY = "02c_Politique_Gouvernance_Donnees.docx"
PLAN = "03_Plan_Implementation_Gouvernance.docx"
DECK = "04_Presentation_Comite_Executif.pptx"

# Ordre des sections 3.1 à 3.9 du document d'évaluation, et libellés du graphique de la slide 3.
DIMENSIONS = ["Data Governance", "Data Quality", "Data Architecture", "Compliance", "Data Usage",
              "Data Security", "Data Literacy", "Data Integration", "Analytics & BI"]


@dataclass
class Finding:
    id: str
    sujet: str
    statut: str
    constat: str
    attendu: str
    trouve: str
    source: str


def _paragraphs(path: Path) -> list[str]:
    return [p.text for p in docx.Document(path).paragraphs]


def _slides_text(path: Path) -> list[str]:
    out = []
    for s in pptx.Presentation(path).slides:
        out.append("\n".join(sh.text_frame.text for sh in s.shapes if sh.has_text_frame))
    return out


def _fr(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def eval_scores(root: Path = ROOT) -> list[int]:
    text = "\n".join(_paragraphs(root / EVAL))
    return [int(s) for s in re.findall(r"Score\s*:\s*(\d)", text)]


def chart_scores(root: Path = ROOT) -> dict[str, float]:
    for s in pptx.Presentation(root / DECK).slides:
        for sh in s.shapes:
            if sh.has_chart:
                plot = sh.chart.plots[0]
                return dict(zip(plot.categories, plot.series[0].values))
    return {}


def parse_range(text: str) -> tuple[float, float]:
    """« 40–70 K$ » -> (40, 70) ; « 0,5–1,5 M$ » -> (500, 1500). Montants en K$."""
    m = re.search(r"([\d,]+)\s*[–-]\s*([\d,]+)\s*([KM])\$", text)
    if not m:
        raise ValueError(f"fourchette illisible : {text!r}")
    k = 1000 if m.group(3) == "M" else 1
    return float(m.group(1).replace(",", ".")) * k, float(m.group(2).replace(",", ".")) * k


def budget_table(root: Path = ROOT) -> list[list[str]]:
    for t in docx.Document(root / PLAN).tables:
        rows = [[c.text.strip() for c in r.cells] for r in t.rows]
        if rows and rows[0][:2] == ["Poste", "Modèle de prix"]:
            return rows
    raise LookupError("tableau budgétaire introuvable dans le plan")


def audit_maturity(root: Path = ROOT) -> list[Finding]:
    doc = eval_scores(root)
    chart = chart_scores(root)
    deck = _slides_text(root / DECK)
    mean_doc = sum(doc) / len(doc)
    mean_chart = sum(chart.values()) / len(chart)
    diffs = [f"{d} {doc[i]}→{chart[d]:g}" for i, d in enumerate(DIMENSIONS) if chart.get(d) != doc[i]]
    announced = re.search(r"(\d,\d)\s*/\s*5", deck[2]).group(1)
    eval_text = "\n".join(_paragraphs(root / EVAL))
    written = re.search(r"environ\s+(\d,\d)", eval_text).group(1)
    return [
        Finding("A01", "Notes de maturité par dimension", "ecart" if diffs else "ok",
                f"{len(diffs)} dimension(s) sur 9 ont une note différente entre le document d'évaluation et le graphique de la slide 3."
                if diffs else "Les 9 notes du graphique reprennent celles du document.",
                "notes du document 01 (§3.1 à 3.9) : " + " ".join(map(str, doc)),
                "graphique slide 3 : " + " ".join(f"{v:g}" for v in chart.values()) + (" — " + " ; ".join(diffs) if diffs else ""),
                f"{EVAL} · {DECK} (slide 3)"),
        Finding("A02", "Moyenne de maturité", "ecart" if announced != _fr(mean_doc, 1) else "ok",
                f"Le document calcule {_fr(mean_doc)} (« environ {written} ») ; la présentation annonce {announced} / 5, "
                f"qui est la moyenne des notes du graphique ({_fr(mean_chart)}).",
                f"{_fr(mean_doc, 1)} / 5 (moyenne des notes du document)", f"{announced} / 5 (slides 2 et 3, README)",
                f"{EVAL} · {DECK}"),
    ]


def audit_budget(root: Path = ROOT) -> list[Finding]:
    rows = budget_table(root)
    lines = {r[0]: r for r in rows[1:]}
    posts = [r for r in rows[1:8]]
    lo = sum(parse_range(r[2])[0] for r in posts)
    hi = sum(parse_range(r[2])[1] for r in posts)
    tlo = sum(parse_range(r[3])[0] for r in posts)
    thi = sum(parse_range(r[3])[1] for r in posts)
    sub = lines["Sous-total licences"]
    slo, shi = parse_range(sub[2])
    integ = lines["Intégration & services (an 1)"]
    ilo, ihi = parse_range(integ[2])
    total_lo, total_hi = parse_range(lines["TOTAL indicatif"][2])
    target = parse_range(sub[3])
    f = [
        Finding("B01", "Sous-total licences du pilote", "ok" if (lo, hi) == (slo, shi) else "ecart",
                f"La somme des 7 postes donne {lo:.0f}–{hi:.0f} K$.", f"{lo:.0f}–{hi:.0f} K$", sub[2], f"{PLAN} (annexe A)"),
        Finding("B02", "Sous-total licences de la cible", "ok" if abs(tlo - target[0]) < 50 and abs(thi - target[1]) < 50 else "ecart",
                f"La somme des 7 postes donne {_fr(tlo / 1000, 3)}–{_fr(thi / 1000, 3)} M$, arrondie à {sub[3]}.",
                f"{_fr(tlo / 1000, 1)}–{_fr(thi / 1000, 1)} M$", sub[3], f"{PLAN} (annexe A)"),
    ]
    low30, high50 = 0.30 * lo, 0.50 * hi
    coherent = abs(ilo - low30) < 5 and abs(ihi - high50) < 5
    f.append(Finding(
        "B03", "Services d'intégration « +30 à 50 % »", "ok" if coherent else "ecart",
        f"{integ[2]} correspond à 30 % des deux bornes ({0.3 * lo:.0f}–{0.3 * hi:.0f} K$). "
        f"Appliquer réellement 30 à 50 % donne {low30:.0f}–{high50:.0f} K$, soit un total pilote de "
        f"{lo + low30:.0f}–{hi + high50:.0f} K$ au lieu de {total_lo:.0f}–{total_hi:.0f} K$.",
        f"{low30:.0f}–{high50:.0f} K$ (30 % de la borne basse, 50 % de la borne haute)", integ[2],
        f"{PLAN} (annexe A) · {DECK} (slides 12 à 14)"))
    f.append(Finding(
        "B04", "Total indicatif du pilote", "ok" if (total_lo, total_hi) == (slo + ilo, shi + ihi) else "ecart",
        "Le total est bien la somme du sous-total licences et de la ligne intégration telle qu'écrite.",
        f"{slo + ilo:.0f}–{shi + ihi:.0f} K$", lines["TOTAL indicatif"][2], f"{PLAN} (annexe A)"))
    return f


def audit_counts(root: Path = ROOT) -> list[Finding]:
    policy = docx.Document(root / POLICY)
    paras = [p.text.strip() for p in policy.paragraphs]
    principles = sum(1 for p in paras if re.match(r"Principe \d+", p))
    classif = next(t for t in policy.tables if t.rows[0].cells[0].text.strip() == "Niveau")
    kpi = next(t for t in policy.tables if t.rows[0].cells[0].text.strip() == "KPI")
    start, end = paras.index(next(p for p in paras if p.startswith("4. Exigences"))), \
        paras.index(next(p for p in paras if p.startswith("5. R")))
    compliance_items = [p for p in paras[start + 1:end] if p and not re.match(r"4\.\d", p)]
    deck = _slides_text(root / DECK)
    s5 = deck[4]
    claims = {k: int(v) for v, k in re.findall(r"(\d+)\s+(principes|niveaux|contrôles|KPIs)", s5)}
    found = {"principes": principles, "niveaux": len(classif.rows) - 1, "KPIs": len(kpi.rows) - 1}
    out = []
    for i, (k, label) in enumerate([("principes", "principes"), ("niveaux", "niveaux de classification"),
                                    ("KPIs", "KPIs de pilotage")], 1):
        out.append(Finding(f"C0{i}", f"Slide 5 : « {claims[k]} {label} »", "ok" if claims[k] == found[k] else "ecart",
                           f"La politique en contient {found[k]}.", str(claims[k]), str(found[k]), f"{POLICY} · {DECK} (slide 5)"))
    matrix = any("matrice" in p.lower() for p in paras)
    out.append(Finding("C04", f"Slide 5 : « {claims['contrôles']} contrôles de conformité »", "non_tracable",
                       f"Aucune liste de {claims['contrôles']} contrôles ni matrice de conformité dans le dépôt "
                       f"(matrice citée slide 14 : {'présente' if matrix else 'absente'} de la politique). "
                       f"La section 4 de la politique compte {len(compliance_items)} rubriques (RGPD, CCPA, PCI-DSS).",
                       f"{claims['contrôles']} contrôles identifiables", f"{len(compliance_items)} rubriques en §4",
                       f"{POLICY} · {DECK} (slides 5 et 14)"))
    out.append(Finding("C05", "README : présentation de 14 slides", "ok" if len(deck) == 14 else "ecart",
                       f"La présentation compte {len(deck)} slides.", "14", str(len(deck)), DECK))
    return out


def audit_timeline(root: Path = ROOT) -> list[Finding]:
    policy = "\n".join(_paragraphs(root / POLICY))
    plan = docx.Document(root / PLAN)
    waves = next(t for t in plan.tables if t.rows[0].cells[0].text.strip() == "Vague")
    last = waves.rows[-1].cells[1].text.strip()
    phase3 = re.search(r"Phase 3 \(([^)]*)\)", policy).group(1)
    phase2 = re.search(r"Phase 2 \(([^)]*)\)[^.]*\.[^.]*\.\s*([^.]*Center of Excellence)", policy)
    deck = _slides_text(root / DECK)
    central = re.search(r"Centralisé pendant le pilote \((M[^)]*)\)", deck[6]).group(1)
    return [Finding(
        "D01", "Calendrier : 18 ou 24 mois ; bascule vers le CoE", "a_harmoniser",
        "Le plan termine le rollout à M18 (pilote + 3 vagues) ; la politique place la phase 3 sur "
        f"{phase3} ; la politique bascule vers le CoE en phase 2{' (' + phase2.group(1) + ')' if phase2 else ''}, "
        f"la slide 7 garde un modèle centralisé {central}. Les deux lectures se défendent "
        "(déploiement outillé vs trajectoire d'organisation), mais elles ne sont pas formulées pareil.",
        "un calendrier unique", f"plan : fin {last} · politique : phase 3 {phase3} · slide 7 : centralisé {central}",
        f"{POLICY} · {PLAN} · {DECK} (slides 7 et 8)")]


def audit(root: Path = ROOT) -> list[Finding]:
    return audit_maturity(root) + audit_budget(root) + audit_counts(root) + audit_timeline(root)


def as_dicts(findings: list[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]
