#!/usr/bin/env python3
"""
Heuristic smoke checks for Rhino LLM eval outputs.

Usage:
  python eval/score_outputs.py --predictions eval/runs/latest.jsonl
  python eval/score_outputs.py --text "import rhinoscriptsyntax as rs ..."

Each predictions row:
  {"id": "...", "prompt": "...", "output": "...", "meta": {"lang": "python"}}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PYTHON_MARKERS = [
    r"import\s+rhinoscriptsyntax",
    r"import\s+rhinoscriptsyntax\s+as\s+rs",
    r"scriptcontext",
    r"Rhino\.Geometry",
    r"rs\.\w+",
]

CSHARP_MARKERS = [
    r"RhinoDoc",
    r"Rhino\.Geometry",
    r"Point3d",
    r"Brep\.",
    r"doc\.Objects",
    r"UnitSystem",
]

CONCEPT_MARKERS = [
    r"Rhino\.Python|rhinoscriptsyntax|RhinoCommon",
    r"tolerance|boolean|brep|mesh",
]


def score_output(text: str, lang: str) -> dict:
    text_lower = text.lower()
    checks: dict[str, bool] = {}

    if lang == "python":
        checks["has_rs_or_sc"] = bool(
            re.search(PYTHON_MARKERS[0], text, re.I)
            or re.search(PYTHON_MARKERS[2], text, re.I)
        )
        checks["has_rs_call"] = bool(re.search(PYTHON_MARKERS[4], text))
    elif lang == "csharp":
        checks["has_rhinodoc_or_geometry"] = bool(
            re.search(CSHARP_MARKERS[0], text) or re.search(CSHARP_MARKERS[1], text)
        )
        checks["has_doc_objects"] = bool(re.search(CSHARP_MARKERS[4], text))
    else:
        checks["mentions_rhino_apis"] = any(
            re.search(p, text, re.I) for p in CONCEPT_MARKERS
        )

    checks["non_empty"] = len(text.strip()) > 20
    checks["no_placeholder"] = "TODO" not in text and "your code here" not in text_lower

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {
        "lang": lang,
        "checks": checks,
        "score": passed / total if total else 0.0,
        "passed": passed == total,
    }


def load_predictions(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, help="JSONL with output field")
    parser.add_argument("--text", type=str, help="Single output string")
    parser.add_argument("--lang", default="python", choices=["python", "csharp", "concept"])
    args = parser.parse_args()

    if args.text:
        result = score_output(args.text, args.lang)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1

    if not args.predictions or not args.predictions.exists():
        print("Provide --predictions or --text", file=sys.stderr)
        return 2

    rows = load_predictions(args.predictions)
    n_pass = 0
    for row in rows:
        lang = row.get("meta", {}).get("lang", "python")
        out = row.get("output", "")
        res = score_output(out, lang)
        row_id = row.get("id", "?")
        status = "PASS" if res["passed"] else "FAIL"
        print(f"{row_id} [{lang}] {status} score={res['score']:.2f}")
        if res["passed"]:
            n_pass += 1

    rate = n_pass / len(rows) if rows else 0
    print(f"\nSummary: {n_pass}/{len(rows)} passed ({rate:.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
