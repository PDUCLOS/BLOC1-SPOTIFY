"""Point d'entrée : ``python -m gouvernance [--users N] [--out docs/demo]``.

Enchaîne : génération synthétique -> contrôles (avant) -> remédiation -> contrôles (après)
-> audit des livrables -> rapport JSON + HTML. Code de sortie 0 ; le rapport dit ce qui échoue.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb

from . import audit_livrables, checks, remediate, report
from .generate import generate

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m gouvernance", description=__doc__.splitlines()[0])
    ap.add_argument("--users", type=int, default=5000, help="nombre d'utilisateurs synthétiques (10 événements chacun)")
    ap.add_argument("--seed", type=int, default=38777)
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "demo")
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "sample", help="dossier des CSV générés")
    args = ap.parse_args(argv)

    t0 = time.perf_counter()
    ds = generate(n_users=args.users, seed=args.seed)
    paths = ds.write_csv(args.data)
    t1 = time.perf_counter()
    con = checks.connect(paths)
    before = checks.run_all(con, "raw")
    k_before = checks.kpis(before, con, "raw")
    t2 = time.perf_counter()
    stats = remediate.remediate(con)
    after = checks.run_all(con, "clean")
    k_after = checks.kpis(after, con, "clean")
    t3 = time.perf_counter()
    findings = audit_livrables.audit(ROOT)
    t4 = time.perf_counter()

    payload = {
        "meta": {
            "genere_le": datetime.now().strftime("%Y-%m-%d %H:%M"), "graine": args.seed,
            "duckdb": duckdb.__version__, "python": sys.version.split()[0],
            "lignes": {k: len(v) for k, v in ds.tables.items()},
            "durees_s": {"generation": t1 - t0, "controles_avant": t2 - t1,
                         "remediation_et_controles_apres": t3 - t2, "audit_livrables": t4 - t3},
        },
        "synthese": {"ok_avant": k_before["controles_ok"], "ok_apres": k_after["controles_ok"],
                     "total": k_after["controles_total"]},
        "kpis_avant": k_before, "kpis_apres": k_after,
        "kpis": report.kpi_rows(k_before, k_after),
        "remediation": stats,
        "controles_avant": checks.as_dicts(before), "controles_apres": checks.as_dicts(after),
        "audit_livrables": audit_livrables.as_dicts(findings),
    }
    js, html = report.write(args.out, payload)
    s = payload["synthese"]
    print(f"Contrôles conformes : {s['ok_avant']} -> {s['ok_apres']} / {s['total']}")
    for r in payload["kpis"]:
        print(f"  {r['label']:<52} {r['before']:>9} -> {r['after']:>9}  (cible {r['target']}) {'OK' if r['ok'] else 'NON'}")
    ecarts = [f for f in findings if f.statut != "ok"]
    print(f"Audit des livrables : {len(findings) - len(ecarts)} cohérents, {len(ecarts)} à signaler "
          f"({', '.join(f.id for f in ecarts)})")
    print(f"Rapport : {js} · {html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
