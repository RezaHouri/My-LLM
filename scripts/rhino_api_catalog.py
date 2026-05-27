"""
Rhino API templates for large-scale synthetic SFT row generation.

Used by make_synthetic.py — each entry: (user_template, assistant_template, lang, topic).
Placeholders: {name}, {x}, {y}, {z}, {r}, {layer}, {units}, {filter}, {n}, etc.
"""

from __future__ import annotations

# fmt: off
PYTHON_RS = [
    ("Rhino.Python: call rs.{name}() on the active document.", "import rhinoscriptsyntax as rs\n\nresult = rs.{name}()\nprint(result)", "python", "api"),
    ("Write Rhino.Python using rs.{name} with error handling.", "import rhinoscriptsyntax as rs\n\ntry:\n    result = rs.{name}()\nexcept Exception as e:\n    print(\"Error:\", e)\nelse:\n    print(result)", "python", "api"),
    ("How do I use rhinoscriptsyntax.{name} in Rhino 8?", "import rhinoscriptsyntax as rs\n\n# {name} — see Rhino command help for arguments\nresult = rs.{name}()\n", "python", "api"),
]

PYTHON_GEOM = [
    ("Add a {shape} in Rhino.Python at ({x},{y},{z}).", "import rhinoscriptsyntax as rs\n\npt = ({x}, {y}, {z})\n# Create {shape} at pt (adjust API for your case)\nobj = rs.AddPoint(pt)\n", "python", "geometry"),
    ("Rhino.Python script: create geometry type '{shape}' radius {r}.", "import rhinoscriptsyntax as rs\nimport scriptcontext as sc\n\ncenter = ({x}, {y}, {z})\nradius = {r}\n# Example: sphere\nobj = rs.AddSphere(center, radius)\nif obj:\n    sc.doc.Views.Redraw()", "python", "geometry"),
]

PYTHON_DOC = [
    ("Set current layer to '{layer}' in Rhino.Python.", "import rhinoscriptsyntax as rs\n\nname = \"{layer}\"\nif not rs.IsLayer(name):\n    rs.AddLayer(name)\nrs.CurrentLayer(name)", "python", "layers"),
    ("List objects on layer '{layer}'.", "import rhinoscriptsyntax as rs\n\nids = rs.ObjectsByLayer(\"{layer}\")\nprint(len(ids) if ids else 0, \"objects\")", "python", "layers"),
    ("Rhino.Python: get document unit system name.", "import rhinoscriptsyntax as rs\n\nprint(rs.UnitSystemName())", "python", "document"),
]

CSHARP_GEOM = [
    ("RhinoCommon C#: create {shape} with radius {r} at origin.", "using Rhino.Geometry;\n\nvar center = Point3d.Origin;\nvar radius = {r}d;\n// {shape} example — sphere\nvar sphere = new Sphere(center, radius);\nvar brep = Brep.CreateFromSphere(sphere);\nif (brep != null)\n    doc.Objects.AddBrep(brep);", "csharp", "geometry"),
    ("C#: add {shape} to RhinoDoc at ({x},{y},{z}).", "using Rhino.Geometry;\n\nvar pt = new Point3d({x}, {y}, {z});\nvar id = doc.Objects.AddPoint(pt);", "csharp", "geometry"),
]

CSHARP_DOC = [
    ("C# RhinoCommon: set model units to {units}.", "using Rhino;\n\ndoc.ModelUnitSystem = UnitSystem.{units};\ndoc.AdjustModelUnitSystem(UnitSystem.{units}, false);", "csharp", "document"),
    ("RhinoCommon: print ModelAbsoluteTolerance.", "RhinoApp.WriteLine(doc.ModelAbsoluteTolerance.ToString());", "csharp", "document"),
    ("C#: select all objects on layer index 0.", "foreach (var obj in doc.Objects)\n    if (obj.Attributes.LayerIndex == 0)\n        obj.Select(true);", "csharp", "selection"),
]

CONCEPT = [
    ("When should I use {api} vs {alt} in Rhino scripting?", "Use {api} for document-level scripting and quick automation.\nUse {alt} for precise geometry, booleans, and types you pass between components.\nCombine: build with {alt}, add to doc via scriptcontext or doc.Objects.", "concept", "api_design"),
    ("Why did my Rhino boolean operation return null?", "Common causes: open breps, tolerance mismatch, non-manifold geometry, or inputs not fully intersecting.\nCheck IsSolid, naked edges, and ModelAbsoluteTolerance. Scale geometry near origin.", "concept", "booleans"),
    ("Explain RhinoDoc vs scriptcontext.doc.", "In Rhino.Python inside Rhino, scriptcontext.doc is the active document.\nIn C# commands, prefer the command's Doc property. In Compute, pass RhinoDoc explicitly.", "concept", "python_runtime"),
]

# rs function names (subset of common rhinoscriptsyntax)
RS_FUNCTIONS = [
    "AddSphere", "AddBox", "AddCircle", "AddLine", "AddPolyline", "AddCone", "AddCylinder",
    "AddLayer", "CurrentLayer", "LayerNames", "DeleteLayer", "LayerColor", "LayerLocked",
    "SelectedObjects", "SelectObject", "UnselectAllObjects", "GetObject", "GetObjects",
    "ObjectLayer", "ObjectColor", "ObjectName", "HideObject", "ShowObject",
    "MoveObject", "CopyObject", "RotateObject", "ScaleObject",
    "AddPoint", "AddTextDot", "AddLeader",
    "JoinSurfaces", "BooleanUnion", "BooleanDifference", "BooleanIntersection",
    "MeshBrep", "AddMesh", "IsPolysurfaceClosed", "SurfaceVolume",
    "WorldXYPlane", "AddPlaneSurface", "BoundingBox",
    "ZoomExtents", "Command", "Echo", "Redraw",
    "ObjectsByLayer", "ObjectsByType", "IsLayer", "UnitSystemName",
]

SHAPES = ["sphere", "box", "cylinder", "cone", "circle", "line", "polyline"]
LAYERS = ["Default", "Geometry", "Construction", "Export", "RhinoLLM", "Temp", "Hidden"]
UNITS = ["Millimeters", "Meters", "Inches", "Feet", "Centimeters"]
API_PAIRS = [
    ("rhinoscriptsyntax", "Rhino.Geometry"),
    ("rs.AddSphere", "Brep.CreateFromSphere"),
    ("RhinoDoc.ActiveDoc", "scriptcontext.doc"),
]
