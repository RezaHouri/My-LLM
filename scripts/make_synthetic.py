#!/usr/bin/env python3
"""
Generate large-scale template-based Rhino Q&A rows for rhino_sft.jsonl.

Usage:
  python scripts/make_synthetic.py --count 12000
  python scripts/make_synthetic.py --count 5000 --out data/processed/rhino_sft.jsonl --seed 42
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "data" / "processed" / "rhino_sft.jsonl"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from rhino_api_catalog import (  # noqa: E402
    API_PAIRS,
    CONCEPT,
    CSHARP_DOC,
    CSHARP_GEOM,
    LAYERS,
    PYTHON_DOC,
    PYTHON_GEOM,
    PYTHON_RS,
    RS_FUNCTIONS,
    SHAPES,
    UNITS,
)

# --- Legacy hand templates (kept for variety) ---
PYTHON_TEMPLATES = [
    (
        "In Rhino.Python, add a sphere at ({x}, {y}, {z}) with radius {r}.",
        """import rhinoscriptsyntax as rs

center = ({x}, {y}, {z})
radius = {r}
sphere_id = rs.AddSphere(center, radius)
if sphere_id:
    print("Sphere created:", sphere_id)
else:
    print("Failed to create sphere")
""",
        "python",
        "geometry",
    ),
    (
        "Rhino.Python: create a layer named '{layer}' and set it current.",
        """import rhinoscriptsyntax as rs

layer_name = "{layer}"
if not rs.IsLayer(layer_name):
    rs.AddLayer(layer_name)
rs.CurrentLayer(layer_name)
""",
        "python",
        "layers",
    ),
    (
        "Using rhinoscriptsyntax, get all selected object ids.",
        """import rhinoscriptsyntax as rs

ids = rs.SelectedObjects()
if not ids:
    print("No objects selected")
else:
    print("Selected count:", len(ids))
""",
        "python",
        "selection",
    ),
]

CSHARP_TEMPLATES = [
    (
        "RhinoCommon C#: add a sphere at origin with radius {r}.",
        """using Rhino;
using Rhino.Geometry;

double radius = {r};
var sphere = new Sphere(Point3d.Origin, radius);
var brep = Brep.CreateFromSphere(sphere);
if (brep != null)
    doc.Objects.AddBrep(brep);
""",
        "csharp",
        "geometry",
    ),
    (
        "C# RhinoCommon: set document unit system to {units}.",
        """using Rhino;
using Rhino.DocObjects;

var unit = UnitSystem.{units};
doc.ModelUnitSystem = unit;
doc.AdjustModelUnitSystem(unit, false);
""",
        "csharp",
        "document",
    ),
]

CONCEPT_TEMPLATES = [
    (
        "What is RhinoDoc.ActiveDoc vs scriptcontext in Rhino.Python?",
        """In Rhino.Python inside Rhino, scriptcontext.doc is the active document
(usually the same as Rhino.RhinoDoc.ActiveDoc in C#).

Use scriptcontext when you need the document for AddObject calls from Python.
In standalone compute/Grasshopper contexts, ensure the correct doc is passed
explicitly rather than assuming ActiveDoc.
""",
        "concept",
        "python_runtime",
    ),
]


def norm_hash(text: str) -> str:
    t = " ".join(text.split()).lower()
    return hashlib.sha256(t.encode()).hexdigest()[:16]


def fill_template(user: str, assistant: str, extra: dict | None = None) -> tuple[str, str]:
    vals = {
        "x": round(random.uniform(-50, 50), 2),
        "y": round(random.uniform(-50, 50), 2),
        "z": round(random.uniform(0, 20), 2),
        "r": round(random.uniform(1, 25), 2),
        "n": random.randint(2, 12),
        "layer": random.choice(LAYERS),
        "shape": random.choice(SHAPES),
        "units": random.choice(UNITS),
        "name": random.choice(RS_FUNCTIONS),
        "api": random.choice([p[0] for p in API_PAIRS]),
        "alt": random.choice([p[1] for p in API_PAIRS]),
        "filter": random.choice(["curve", "surface", "polysurface", "mesh"]),
        "c1": "(0,0,0)",
        "c2": "(10,10,10)",
    }
    if extra:
        vals.update(extra)
    try:
        return user.format(**vals), assistant.format(**vals)
    except KeyError:
        return user, assistant


def row(user: str, assistant: str, lang: str, topic: str) -> dict:
    return {
        "messages": [
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant.strip()},
        ],
        "meta": {"lang": lang, "topic": topic, "source": "synthetic"},
    }


def expand_rs_catalog() -> list[dict]:
    """One row per rs function × a few prompt styles."""
    rows: list[dict] = []
    styles = [
        "Show Rhino.Python code that uses rs.{name}.",
        "Example script calling rhinoscriptsyntax.{name} in Rhino 8.",
        "Minimal rs.{name} snippet with comments.",
    ]
    for fn in RS_FUNCTIONS:
        for style in styles:
            user = style.format(name=fn)
            assistant = (
                f"import rhinoscriptsyntax as rs\n\n"
                f"# rs.{fn} — check Rhino help for required arguments\n"
                f"result = rs.{fn}()\n"
                f"print(result)\n"
            )
            rows.append(row(user, assistant, "python", "api"))
    return rows


def expand_template_pool(pool: list, limit: int | None = None) -> list[dict]:
    rows: list[dict] = []
    for user_tpl, asst_tpl, lang, topic in pool:
        for _ in range(3):
            u, a = fill_template(user_tpl, asst_tpl)
            rows.append(row(u, a, lang, topic))
        if limit and len(rows) >= limit:
            return rows[:limit]
    return rows


def generate_combinatorial(target: int, rng: random.Random) -> list[dict]:
    """Fill up to target rows using catalog + legacy templates."""
    pools = (
        PYTHON_TEMPLATES
        + CSHARP_TEMPLATES
        + CONCEPT_TEMPLATES
        + PYTHON_RS
        + PYTHON_GEOM
        + PYTHON_DOC
        + CSHARP_GEOM
        + CSHARP_DOC
        + CONCEPT
    )

    rows: list[dict] = []
    seen: set[str] = set()

    def add(r: dict) -> bool:
        h = norm_hash(r["messages"][1]["content"])
        if h in seen:
            return False
        seen.add(h)
        rows.append(r)
        return True

    for r in expand_rs_catalog():
        add(r)
        if len(rows) >= target:
            return rows[:target]

    for r in expand_template_pool(pools):
        add(r)
        if len(rows) >= target:
            return rows[:target]

    # Random generation until target
    attempts = 0
    max_attempts = target * 5
    while len(rows) < target and attempts < max_attempts:
        attempts += 1
        rng.shuffle(pools)
        tpl = pools[rng.randrange(len(pools))]
        u, a = fill_template(tpl[0], tpl[1])
        add(row(u, a, tpl[2], tpl[3]))

    return rows[:target]


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def dedupe_rows(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for r in rows:
        h = norm_hash(r["messages"][1]["content"])
        if h in seen:
            continue
        seen.add(h)
        out.append(r)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic Rhino SFT rows")
    parser.add_argument("--count", type=int, default=12000, help="Target new synthetic rows")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Do not merge with existing file; only write synthetic rows",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    random.seed(args.seed)

    synthetic = generate_combinatorial(args.count, rng)
    print(f"Generated {len(synthetic)} synthetic rows (target {args.count})")

    if args.replace:
        merged = dedupe_rows(synthetic)
    else:
        existing = load_jsonl(args.out)
        merged = dedupe_rows(existing + synthetic)
        print(f"Merged with {len(existing)} existing -> {len(merged)} total")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    langs: dict[str, int] = {}
    for r in merged:
        langs[r["meta"]["lang"]] = langs.get(r["meta"]["lang"], 0) + 1
    print(f"Wrote {len(merged)} rows -> {args.out}")
    print(f"  by lang: {langs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
