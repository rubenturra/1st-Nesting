"""Sheet/offcut thickness and material helpers.

Pure Python (no FreeCAD/Qt imports) so they can be unit tested anywhere.
Thickness is stored in millimetres; 0 means "not specified".
"""
import math
import os
import re

TOLERANCE_MM = 0.001

COMMON_MATERIALS = (
    "S235",
    "S275",
    "S355",
    "AISI 304",
    "AISI 316",
    "Aluminio",
    "Galvanizado",
)

_THICKNESS_RE = re.compile(r'(?:^|[_\-\s])e(\d+(?:[.,]\d+)?)\s*mm(?=$|[_\-\s.])', re.IGNORECASE)
_DATE_RE = re.compile(r'(?:^|_)(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(?=$|_)')
_AREA_RE = re.compile(r'(?:^|_)(\d+(?:[.,]\d+)?)\s*m2(?=$|[_.])', re.IGNORECASE)


def same_thickness(first, second):
    return math.isclose(float(first), float(second), abs_tol=TOLERANCE_MM, rel_tol=1e-6)


def material_thickness(material):
    """Return the sheet thickness in mm, or 0.0 when not specified/invalid."""
    try:
        value = float((material or {}).get("thickness", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) and value > TOLERANCE_MM else 0.0


def material_name(material):
    return str((material or {}).get("material", "") or "").strip()


def format_number(value):
    return ("%.3f" % float(value)).rstrip("0").rstrip(".") or "0"


def format_thickness(value_mm, units="mm"):
    if str(units).lower() == "inch":
        return format_number(float(value_mm) / 25.4) + " inch"
    return format_number(value_mm) + " mm"


def spec_suffix(material, units="mm"):
    """Text appended to a material label, e.g. ' · 10 mm · S275'."""
    parts = []
    thickness = material_thickness(material)
    if thickness:
        parts.append(format_thickness(thickness, units))
    name = material_name(material)
    if name:
        parts.append(name)
    return "".join(" · " + part for part in parts)


def material_suffix(material):
    """Only the material name, e.g. ' · S275' (thickness has its own column)."""
    name = material_name(material)
    return " · " + name if name else ""


def parse_offcut_filename(path):
    """Read thickness, date and area from names such as
    Retal_<doc>_<sheet>_e10mm_20261103-2215_1.90m2.dxf."""
    stem = os.path.splitext(re.split(r"[\\/]", str(path or ""))[-1])[0]
    info = {"name": stem, "thickness": 0.0, "date": "", "area_m2": 0.0}
    match = _THICKNESS_RE.search(stem)
    if match:
        info["thickness"] = float(match.group(1).replace(",", "."))
    match = _DATE_RE.search(stem)
    if match:
        y, mo, d, h, mi = match.groups()
        info["date"] = "%s-%s-%s %s:%s" % (y, mo, d, h, mi)
    match = _AREA_RE.search(stem)
    if match:
        info["area_m2"] = float(match.group(1).replace(",", "."))
    return info


def list_offcut_files(folder):
    """Return parsed info for every DXF in folder, newest first."""
    entries = []
    try:
        names = os.listdir(folder)
    except OSError:
        return entries
    for name in names:
        path = os.path.join(folder, name)
        if not name.lower().endswith(".dxf") or not os.path.isfile(path):
            continue
        info = parse_offcut_filename(path)
        info["path"] = os.path.abspath(path)
        try:
            info["mtime"] = os.path.getmtime(path)
        except OSError:
            info["mtime"] = 0.0
        entries.append(info)
    entries.sort(key=lambda e: (e["date"], e["mtime"]), reverse=True)
    return entries


def sheet_thickness_problem(materials, parts, labels=None):
    """Decide whether nesting must be blocked.

    materials: sheet/offcut dicts; parts: {name: [depths in mm]} of 3D parts;
    labels: {name: label}.  Returns None, or a dict describing the problem:
      {"kind": "mixed_sheets", "values": [..]}
      {"kind": "parts", "reference": t, "names": [..]}
    Sheets without a thickness and flat parts (no depths) are not checked.
    """
    values = []
    for material in materials or []:
        thickness = material_thickness(material)
        if thickness and not any(same_thickness(thickness, v) for v in values):
            values.append(thickness)
    if not values:
        return None
    if len(values) > 1:
        return {"kind": "mixed_sheets", "values": sorted(values)}
    reference = values[0]
    names = [name for name, depths in (parts or {}).items()
             if depths and any(not same_thickness(d, reference) for d in depths)]
    if not names:
        return None
    labels = labels or {}
    names.sort(key=lambda n: str(labels.get(n, n)).lower())
    return {"kind": "parts", "reference": reference, "names": names}


def common_spec(materials):
    """Thickness and material shared by the job (for result documents)."""
    thickness = 0.0
    for material in materials or []:
        thickness = material_thickness(material)
        if thickness:
            break
    names = []
    for material in materials or []:
        name = material_name(material)
        if name and name not in names:
            names.append(name)
    return thickness, " / ".join(names)
