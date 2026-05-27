#!/usr/bin/env python3
"""
Generate template-based Rhino Q&A rows and append to rhino_sft.jsonl.

Usage:
  python scripts/make_synthetic.py
  python scripts/make_synthetic.py --count 100 --out data/processed/rhino_sft.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "data" / "processed" / "rhino_sft.jsonl"

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
    (
        "Rhino.Python: add a box from corner {c1} to corner {c2}.",
        """import rhinoscriptsyntax as rs

corner1 = {c1}
corner2 = {c2}
box_id = rs.AddBox(rs.BoundingBox([corner1, corner2]))
if box_id:
    rs.SelectObject(box_id)
""",
        "python",
        "geometry",
    ),
    (
        "Explain when to use rhinoscriptsyntax vs Rhino.Geometry in a script.",
        """Use rhinoscriptsyntax (rs) for quick document-level scripting: selection,
layers, simple geometry creation, and iterating objects.

Use Rhino.Geometry for precise construction, booleans, mesh/brep operations,
and passing geometry between components without relying on document ids.

Typical pattern: build with Rhino.Geometry, then add to the document via
scriptcontext.doc.Objects.AddBrep(brep) or rs.Add* helpers.
""",
        "concept",
        "api_design",
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
    (
        "RhinoCommon: iterate selected objects and print their ids.",
        """using Rhino;
using Rhino.DocObjects;

var sel = doc.Objects.GetSelectedObjects(false, false);
foreach (var obj in sel)
    RhinoApp.WriteLine(obj.Id.ToString());
""",
        "csharp",
        "selection",
    ),
    (
        "C#: boolean union two breps with error handling.",
        """using Rhino.Geometry;

Brep[] result = Brep.CreateBooleanUnion(new[] {{ brepA, brepB }}, doc.ModelAbsoluteTolerance);
if (result == null || result.Length == 0)
    RhinoApp.WriteLine("Boolean union failed");
else
    doc.Objects.AddBrep(result[0]);
""",
        "csharp",
        "booleans",
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
    (
        "How do document units affect tolerance for booleans?",
        """Booleans and intersections use the document's absolute tolerance
(ModelAbsoluteTolerance), derived from the unit system and angle tolerance.

Always model at sensible unit scale (e.g. millimeters for product design)
and avoid geometry far from the origin to reduce boolean failures.
""",
        "concept",
        "tolerance",
    ),
]


def fill_template(user: str, assistant: str) -> tuple[str, str]:
    vals = {
        "x": round(random.uniform(-50, 50), 2),
        "y": round(random.uniform(-50, 50), 2),
        "z": round(random.uniform(0, 20), 2),
        "r": round(random.uniform(1, 25), 2),
        "layer": random.choice(["RhinoLLM", "Geometry", "Export", "Temp"]),
        "c1": "(0,0,0)",
        "c2": "(10,10,10)",
        "units": random.choice(["Millimeters", "Meters", "Inches"]),
    }
    return user.format(**vals), assistant.format(**vals)


def generate_row() -> dict:
    pool = PYTHON_TEMPLATES + CSHARP_TEMPLATES + CONCEPT_TEMPLATES
    user, assistant, lang, topic = random.choice(pool)
    user, assistant = fill_template(user, assistant)
    return {
        "messages": [
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant.strip()},
        ],
        "meta": {"lang": lang, "topic": topic},
    }


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    existing = load_jsonl(args.out)
    new_rows = [generate_row() for _ in range(args.count)]

    # dedupe by assistant hash
    seen = {json.dumps(r["messages"][1]["content"]) for r in existing}
    merged = existing[:]
    for r in new_rows:
        key = json.dumps(r["messages"][1]["content"])
        if key not in seen:
            seen.add(key)
            merged.append(r)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(merged)} rows ({args.count} synthetic requested) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
