"""CLI per BUILD_SPEC.md section 4.6.

    python -m data_loader --all
    python -m data_loader --ur
    python -m data_loader --manual
    python -m data_loader --benchmarks
    python -m data_loader --validate

Only builds the FALLBACK corpus — the live search path (services/live_search.py)
needs no CLI, it runs per-request.
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp932

from config import DATA_DIR
from data_loader import build_corpus
from services import corpus

README_PATH = os.path.join(DATA_DIR, "README.md")
MANUAL_DIR = os.path.join(DATA_DIR, "manual")


def _append_readme(lines: list[str]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(README_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n## Run at {timestamp}\n\n")
        for line in lines:
            f.write(f"- {line}\n")


def run_ur() -> None:
    count = build_corpus.run()
    _append_readme([f"Ingested {count} real UR properties from ur_properties_raw.json (source: ur-net.go.jp, gathered by hand/research)"])
    print(f"UR: ingested {count} rows. Total corpus rows: {corpus.count_rows()}")


def run_manual() -> None:
    os.makedirs(MANUAL_DIR, exist_ok=True)
    files = glob.glob(os.path.join(MANUAL_DIR, "*.json"))
    if not files:
        print(f"No manual listings found in {MANUAL_DIR} — nothing to ingest.")
        _append_readme(["Manual ingest: 0 files found in data/manual/"])
        return
    print(f"Found {len(files)} manual files — manual ingestion parser not yet implemented for this format.")
    _append_readme([f"Manual ingest: found {len(files)} files in data/manual/ (parser TODO)"])


def run_benchmarks() -> None:
    """Recomputes ward rent_by_layout percentiles from whatever's in the
    corpus right now — no network calls. Real MLIT/e-Stat CSVs (ward median
    transaction/rent context) still need to be downloaded by hand per
    BUILD_SPEC.md section 4.3 and merged in separately; this only fills the
    part derivable from our own corpus."""
    from config import BENCHMARKS_PATH

    all_rows = corpus.query_fallback(limit=10_000)
    by_ward_layout: dict[str, dict[str, list[int]]] = {}
    for row in all_rows:
        if not row.ward or not row.layout:
            continue
        by_ward_layout.setdefault(row.ward, {}).setdefault(row.layout, []).append(row.rent_jpy)

    wards = {}
    for ward, layouts in by_ward_layout.items():
        rent_by_layout = {}
        for layout, rents in layouts.items():
            rents.sort()
            n = len(rents)
            rent_by_layout[layout] = {
                "p25": rents[int(n * 0.25)],
                "median": rents[int(n * 0.5)],
                "p75": rents[min(int(n * 0.75), n - 1)],
                "n": n,
            }
        wards[ward] = {"rent_by_layout": rent_by_layout}

    data = {
        "generated_at": datetime.now(timezone.utc).date().isoformat(),
        "source": "Computed from local fallback corpus (see data/README.md for provenance). "
        "Real MLIT/e-Stat ward price context not yet merged in.",
        "wards": wards,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(BENCHMARKS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _append_readme([f"Rebuilt benchmarks.json from corpus: {len(wards)} wards with rent_by_layout data"])
    print(f"benchmarks.json written: {len(wards)} wards")


def run_validate() -> None:
    rows = corpus.query_fallback(limit=10_000)
    n = len(rows)
    print(f"Total rows: {n}")
    if n == 0:
        print("No rows in corpus — run --ur first.")
        return

    null_counts = Counter()
    fields = ["address", "ward", "nearest_station", "layout", "area_sqm", "conditions_text"]
    for row in rows:
        for field in fields:
            if getattr(row, field) in (None, ""):
                null_counts[field] += 1

    print("Null rates:")
    for field in fields:
        pct = null_counts[field] / n * 100
        print(f"  {field}: {pct:.0f}%")

    conditions_null_pct = null_counts["conditions_text"] / n * 100
    print(f"\nconditions_text missing: {conditions_null_pct:.0f}% (target: <20%)")

    ward_dist = Counter(r.ward for r in rows if r.ward)
    print(f"\nWard distribution ({len(ward_dist)} wards): {dict(ward_dist)}")

    layout_dist = Counter(r.layout for r in rows if r.layout)
    print(f"Layout distribution: {dict(layout_dist)}")

    outliers = [r for r in rows if r.rent_jpy < 20_000 or r.rent_jpy > 1_000_000]
    if outliers:
        print(f"\nRent outliers (<¥20,000 or >¥1,000,000): {len(outliers)}")
        for r in outliers[:10]:
            print(f"  {r.id}: ¥{r.rent_jpy:,} — {r.title}")
    else:
        print("\nNo rent outliers found.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--ur", action="store_true")
    parser.add_argument("--manual", action="store_true")
    parser.add_argument("--benchmarks", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    if args.all or args.ur:
        run_ur()
    if args.all or args.manual:
        run_manual()
    if args.all or args.benchmarks:
        run_benchmarks()
    if args.all or args.validate:
        run_validate()


if __name__ == "__main__":
    main()
