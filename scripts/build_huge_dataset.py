#!/usr/bin/env python3
"""
One-command pipeline to build a large rhino_sft.jsonl for Gemma / QLoRA training.

Steps:
  1. init_seed.py (if missing)
  2. download_sources.py (samples + docs crawl)
  3. build_dataset.py (augmented samples + docs, keep seed)
  4. make_synthetic.py (10k+ template rows, deduped merge)
  5. build_dataset.py --append-seed --split-eval (final dedupe + train/eval split)

Usage:
  python scripts/build_huge_dataset.py
  python scripts/build_huge_dataset.py --quick          # skip download, synthetic only
  python scripts/build_huge_dataset.py --synthetic 8000
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "dataset.yaml"
OUT_PATH = REPO_ROOT / "data" / "processed" / "rhino_sft.jsonl"


def load_yaml_config() -> dict:
    try:
        import yaml
    except ImportError:
        return {}
    if not CONFIG_PATH.exists():
        return {}
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


def run(cmd: list[str], cwd: Path) -> None:
    print("\n>>", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build large Rhino SFT dataset")
    parser.add_argument("--quick", action="store_true", help="Skip download; extend existing JSONL")
    parser.add_argument("--synthetic", type=int, default=None, help="Override synthetic row count")
    parser.add_argument("--max-pages", type=int, default=None, help="Max doc pages to fetch")
    parser.add_argument("--no-split", action="store_true", help="Skip train/eval split")
    args = parser.parse_args()

    cfg = load_yaml_config()
    dl = cfg.get("download", {})
    syn = cfg.get("synthetic", {})
    build = cfg.get("build", {})

    synthetic_count = args.synthetic or syn.get("count", 12000)
    max_pages = args.max_pages or dl.get("max_pages", 150)
    augment = build.get("augment_per_file", 4)
    py = sys.executable
    scripts = REPO_ROOT / "scripts"

    if not OUT_PATH.exists():
        run([py, str(scripts / "init_seed.py")], REPO_ROOT)

    if not args.quick:
        crawl_flag = ["--crawl-guides"] if dl.get("crawl_guides", True) else []
        run(
            [py, str(scripts / "download_sources.py"), *crawl_flag, "--max-pages", str(max_pages)],
            REPO_ROOT,
        )
        run(
            [py, str(scripts / "build_dataset.py"), "--append-seed", "--augment", str(augment)],
            REPO_ROOT,
        )

    run([py, str(scripts / "make_synthetic.py"), "--count", str(synthetic_count)], REPO_ROOT)

    split_args = [] if args.no_split else ["--split-eval"]
    run(
        [py, str(scripts / "build_dataset.py"), "--finalize-only", *split_args],
        REPO_ROOT,
    )

    # Stats
    if OUT_PATH.exists():
        n = sum(1 for _ in OUT_PATH.read_text(encoding="utf-8").splitlines() if _.strip())
        print(f"\n=== Done: {n} training rows in {OUT_PATH} ===")
        eval_path = REPO_ROOT / "data" / "processed" / "rhino_sft_eval.jsonl"
        if eval_path.exists():
            ne = sum(1 for _ in eval_path.read_text(encoding="utf-8").splitlines() if _.strip())
            print(f"    {ne} eval rows in {eval_path}")
        goal = cfg.get("targets", {}).get("goal_rows", 10000)
        if n < goal:
            print(f"    Tip: increase --synthetic (goal in config: {goal}) or run download with --max-pages 200")
    return 0


if __name__ == "__main__":
    sys.exit(main())
