#!/usr/bin/env python3
"""Write ~50 hand-curated seed rows to data/processed/rhino_sft.jsonl.

Refuses to overwrite a non-empty dataset unless --force is passed, because the
shipped training file is the full corpus.
"""
import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "processed" / "rhino_sft.jsonl"

SEED = [
    ("In Rhino.Python, add a sphere at the origin with radius 5.", "import rhinoscriptsyntax as rs\n\nid = rs.AddSphere((0, 0, 0), 5.0)\nif id:\n    print(\"Created\", id)", "python", "geometry"),
    ("RhinoCommon C#: create a box from 0,0,0 to 10,10,10.", "using Rhino.Geometry;\n\nvar box = new Box(new BoundingBox(Point3d.Origin, new Point3d(10, 10, 10)));\ndoc.Objects.AddBox(box);", "csharp", "geometry"),
    ("Explain rs vs Rhino.Geometry in Rhino.Python.", "Use rhinoscriptsyntax (rs) for document-level scripting: layers, selection, simple creation.\nUse Rhino.Geometry for precise brep/mesh ops; add results via scriptcontext.doc.Objects.AddBrep(brep).", "concept", "api_design"),
    ("Rhino.Python: list all layer names.", "import rhinoscriptsyntax as rs\n\nfor name in rs.LayerNames():\n    print(name)", "python", "layers"),
    ("C#: get active RhinoDoc and model tolerance.", "var doc = RhinoDoc.ActiveDoc;\ndouble tol = doc.ModelAbsoluteTolerance;\nRhinoApp.WriteLine($\"Tolerance: {tol}\");", "csharp", "document"),
    ("Join two breps in Rhino.Python with error check.", "import rhinoscriptsyntax as rs\n\nids = rs.SelectedObjects()\nif not ids or len(ids) < 2:\n    print(\"Select at least two surfaces/breps\")\nelse:\n    result = rs.JoinSurfaces(ids, delete_input=True)\n    if result:\n        print(\"Joined:\", result)", "python", "booleans"),
    ("Grasshopper C#: output selected brep ids.", "var doc = RhinoDoc.ActiveDoc;\nvar ids = new List<Guid>();\nforeach (var obj in doc.Objects.GetSelectedObjects(false, false))\n    if (obj.Geometry is Brep)\n        ids.Add(obj.Id);\nA = ids;", "csharp", "grasshopper"),
    ("Set document units to millimeters via RhinoCommon.", "doc.ModelUnitSystem = UnitSystem.Millimeters;\ndoc.AdjustModelUnitSystem(UnitSystem.Millimeters, false);", "csharp", "document"),
    ("Rhino.Python: mesh a brep selected by user.", "import rhinoscriptsyntax as rs\n\nbrep_id = rs.GetObject(\"Select brep\", filter=rs.filter.polysurface)\nif brep_id:\n    meshes = rs.MeshBrep(brep_id)\n    if meshes:\n        for m in meshes:\n            rs.AddMesh(m)", "python", "mesh"),
    ("What is scriptcontext.doc in Rhino.Python?", "scriptcontext.doc is the active RhinoDoc in the running Rhino session. Use doc.Objects.Add* when adding geometry built with Rhino.Geometry.", "concept", "python_runtime"),
    ("Add a circle in the XY plane, radius 12, Rhino.Python.", "import rhinoscriptsyntax as rs\n\nplane = rs.WorldXYPlane()\ncircle_id = rs.AddCircle(plane, 12.0)", "python", "geometry"),
    ("C#: boolean difference brepA minus brepB.", "var result = Brep.CreateBooleanDifference(\n    new[] { brepA }, new[] { brepB }, doc.ModelAbsoluteTolerance);\nif (result != null && result.Length > 0)\n    doc.Objects.AddBrep(result[0]);", "csharp", "booleans"),
    ("Delete all objects on layer Temp.", "import rhinoscriptsyntax as rs\n\nif rs.IsLayer(\"Temp\"):\n    ids = rs.ObjectsByLayer(\"Temp\")\n    if ids:\n        rs.DeleteObjects(ids)", "python", "layers"),
    ("Why do booleans fail on open breps?", "Boolean operations need valid closed solids or consistently oriented shells. Open breps, gaps, and tolerance issues return null. Check IsSolid and fix naked edges.", "concept", "booleans"),
    ("Move selection by vector (1,0,0) in Rhino.Python.", "import rhinoscriptsyntax as rs\n\nids = rs.SelectedObjects()\nif ids:\n    rs.MoveObject(ids, (1, 0, 0))", "python", "transform"),
    ("C#: create a vertical cylinder, radius 5, height 20.", "var baseCircle = new Circle(Plane.WorldXY, 5.0);\nvar cylinder = new Cylinder(baseCircle, 20.0);\nvar brep = cylinder.ToBrep(true, true);\ndoc.Objects.AddBrep(brep);", "csharp", "geometry"),
    ("Difference between AddBrep and AddSurface?", "AddBrep stores a Brep (solids or multi-face shells). AddSurface stores a single surface. Use breps for solids and boolean workflows.", "concept", "geometry"),
    ("Select all curves on the current layer.", "import rhinoscriptsyntax as rs\n\nlayer = rs.CurrentLayer()\nids = rs.ObjectsByLayer(layer)\ncurves = [i for i in ids if rs.IsCurve(i)]\nif curves:\n    rs.SelectObjects(curves)", "python", "selection"),
    ("C#: add a line from (0,0,0) to (10,5,0).", "var line = new Line(new Point3d(0, 0, 0), new Point3d(10, 5, 0));\ndoc.Objects.AddLine(line);", "csharp", "geometry"),
    ("Volume of a closed polysurface in rs.", "import rhinoscriptsyntax as rs\n\nobj = rs.GetObject(\"Select closed solid\", filter=rs.filter.polysurface)\nif obj and rs.IsPolysurfaceClosed(obj):\n    vol = rs.SurfaceVolume(obj)\n    if vol:\n        print(\"Volume:\", vol[0])", "python", "analysis"),
    ("Import Rhino.Geometry Point3d in IronPython.", "import clr\nclr.AddReference(\"RhinoCommon\")\nfrom Rhino.Geometry import Point3d\n\npt = Point3d(1.0, 2.0, 3.0)", "python", "geometry"),
    ("C#: offset a planar curve by 2 units.", "var curves = curve.Offset(Plane.WorldXY, 2.0, doc.ModelAbsoluteTolerance, CurveOffsetCornerStyle.Sharp);\nif (curves != null)\n    foreach (var c in curves)\n        doc.Objects.AddCurve(c);", "csharp", "geometry"),
    ("Best practice iterating many Rhino objects in Python.", "Filter early with rs.ObjectsByType or rs.ObjectsByLayer. Avoid repeated rs.ObjectType per id in tight loops; batch by layer when possible.", "concept", "performance"),
    ("Create a closed rectangular polyline in rs.", "import rhinoscriptsyntax as rs\n\npts = [(0, 0, 0), (10, 0, 0), (10, 8, 0), (0, 8, 0), (0, 0, 0)]\nrs.AddPolyline(pts)", "python", "geometry"),
    ("C#: union multiple breps.", "var result = Brep.CreateBooleanUnion(breps, doc.ModelAbsoluteTolerance);\nif (result != null)\n    foreach (var b in result)\n        doc.Objects.AddBrep(b);", "csharp", "booleans"),
    ("Rhino.Python: hide layer Construction.", "import rhinoscriptsyntax as rs\n\nif rs.IsLayer(\"Construction\"):\n    rs.LayerVisible(\"Construction\", False)", "python", "layers"),
    ("What is ModelAbsoluteTolerance?", "Document absolute tolerance in model units, used by intersections and booleans. Derived from unit system and angle tolerance settings.", "concept", "tolerance"),
    ("Add text dot at a point in Rhino.Python.", "import rhinoscriptsyntax as rs\n\nrs.AddTextDot((5, 5, 0), \"Label\")", "python", "annotation"),
    ("C#: explode a block instance.", "var obj = doc.Objects.FindId(blockInstanceId);\nif (obj is InstanceObject inst)\n    inst.Explode(true);", "csharp", "blocks"),
    ("DupBorder on a surface in rs.", "import rhinoscriptsyntax as rs\n\nsrf = rs.GetObject(\"Surface\", filter=rs.filter.surface)\nif srf:\n    border = rs.DuplicateSurfaceBorder(srf)\n    if border:\n        rs.AddCurve(border)", "python", "geometry"),
    ("C#: test if a brep is solid.", "bool solid = brep.IsSolid;", "csharp", "analysis"),
    ("Create cone in Rhino.Python.", "import rhinoscriptsyntax as rs\n\nbase = rs.WorldXYPlane()\nheight = (0, 0, 15)\nid = rs.AddCone(base, 6, height)", "python", "geometry"),
    ("When to use RhinoDoc.ActiveDoc in a command?", "In command classes, use the command's doc property. In static helpers or Grasshopper, pass RhinoDoc explicitly; ActiveDoc is only safe inside an active Rhino command context.", "concept", "csharp"),
    ("C#: add a point at coordinates.", "doc.Objects.AddPoint(new Point3d(3, 4, 5));", "csharp", "geometry"),
    ("Project curves to CPlane in rs.", "import rhinoscriptsyntax as rs\n\ncurves = rs.GetObjects(\"Curves\", rs.filter.curve)\nif curves:\n  projected = rs.ProjectToPlane(curves, rs.ViewCPlane())", "python", "transform"),
    ("Explain naked edges on a brep.", "Naked edges are boundary edges not joined to another face. They prevent solid booleans and indicate open or non-manifold geometry.", "concept", "mesh"),
    ("C#: create extrusion from profile curve.", "var ext = Extrusion.Create(profile, height, true);\nif (ext != null)\n    doc.Objects.AddExtrusion(ext);", "csharp", "geometry"),
    ("Rhino.Python: zoom extents.", "import rhinoscriptsyntax as rs\n\nrs.ZoomExtents(None, True)", "python", "view"),
    ("Get object layer name in C#.", "var obj = doc.Objects.FindId(id);\nstring layerName = doc.Layers[obj.Attributes.LayerIndex].Name;", "csharp", "layers"),
    ("Fillet curves radius 3 in rs.", "import rhinoscriptsyntax as rs\n\ncrvs = rs.GetObjects(\"Curves\", rs.filter.curve)\nif crvs and len(crvs) >= 2:\n    rs.FilletCurves(crvs, 3.0)", "python", "geometry"),
    ("C#: translate brep by vector.", "var xform = Transform.Translation(new Vector3d(10, 0, 0));\nbrep.Transform(xform);\ndoc.Objects.AddBrep(brep);", "csharp", "transform"),
    ("How does Grasshopper pass geometry to Rhino?", "Grasshopper works on Rhino.Geometry types; baking uses GH bake components or doc.Objects.Add* in scripted components.", "concept", "grasshopper"),
    ("Rhino.Python: object color from layer.", "import rhinoscriptsyntax as rs\n\nobj = rs.GetObject(\"Object\")\nif obj:\n    layer = rs.ObjectLayer(obj)\n    color = rs.LayerColor(layer)\n    rs.ObjectColor(obj, color)", "python", "attributes"),
    ("C#: create plane from origin and normal.", "var plane = new Plane(new Point3d(0, 0, 0), new Vector3d(0, 0, 1));", "csharp", "geometry"),
    ("Split brep with plane in concept terms.", "Use Brep.Split(plane, tolerance) or RhinoCommon split APIs; ensure plane intersects the brep and tolerance matches the document.", "concept", "booleans"),
    ("Add leader with text in rs.", "import rhinoscriptsyntax as rs\n\npt = rs.GetPoint(\"Leader tip\")\nif pt:\n    rs.AddLeader(pt, \"Note\", (0, 0, 10))", "python", "annotation"),
    ("C#: mesh brep with default settings.", "var mp = MeshingParameters.Default;\nvar meshes = Mesh.CreateFromBrep(brep, mp);\nif (meshes != null)\n    foreach (var m in meshes)\n        doc.Objects.AddMesh(m);", "csharp", "mesh"),
    ("Rhino.Python: lock layer.", "import rhinoscriptsyntax as rs\n\nrs.LayerLocked(\"Default\", True)", "python", "layers"),
    ("Safe pattern for ActiveDoc in compute.", "Do not assume ActiveDoc on a server; pass RhinoDoc from the compute headless document into your functions.", "concept", "compute"),
    ("C#: curve length.", "double length = curve.GetLength();", "csharp", "analysis"),
    ("Create plane surface 10x10 in rs.", "import rhinoscriptsyntax as rs\n\nplane = rs.WorldXYPlane()\nrs.AddPlaneSurface(plane, 10, 10)", "python", "geometry"),
    ("Rhino.Python vs RhinoScript - which for v8?", "Prefer Rhino.Python (IronPython 3 in v8 where available) and rhinoscriptsyntax for scripting; legacy RhinoScript is deprecated for new work.", "concept", "versioning"),
]


def _row_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace a non-empty dataset with the curated seed",
    )
    args = parser.parse_args()

    existing = _row_count(args.out)
    if existing and not args.force:
        print(
            f"Keeping existing dataset ({existing} rows) at {args.out}. "
            f"Pass --force to replace it with {len(SEED)} seed rows."
        )
        return 0

    rows = []
    for user, assistant, lang, topic in SEED:
        rows.append({
            "messages": [
                {"role": "user", "content": user},
                {"role": "assistant", "content": assistant},
            ],
            "meta": {"lang": lang, "topic": topic},
        })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} seed rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
