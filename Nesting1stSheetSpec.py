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


def sheet_thickness_values(materials):
    values = []
    for material in materials or []:
        thickness = material_thickness(material)
        if thickness and not any(same_thickness(thickness, v) for v in values):
            values.append(thickness)
    return sorted(values)


def unmatched_parts(materials, parts):
    """Names of 3D parts whose thickness has no sheet (empty if no sheet thickness)."""
    values = sheet_thickness_values(materials)
    if not values:
        return set()
    return {name for name, depths in (parts or {}).items()
            if depths and any(not any(same_thickness(d, v) for v in values) for d in depths)}


def plan_batches(materials, parts, labels=None):
    """Split a job by thickness: one nesting run per sheet thickness with parts.

    Returns {"problem": None | {...}, "skipped": [...], "batches": [...]};
    "skipped" lists 3D parts without a sheet of their thickness (left out). Each batch is
    {"thickness": t, "sheet_ids": [...], "names": [...]}. Without any sheet
    thickness there is one batch with everything (thickness 0).
    Problems block nesting:
      sheets_without_thickness - some stock has a thickness and some has not
      flat_parts               - DXF/SVG parts while several thicknesses run
      nothing                  - no sheet thickness matches any part
    """
    labels = labels or {}
    materials = list(materials or [])
    parts = dict(parts or {})
    order = lambda names: sorted(names, key=lambda n: str(labels.get(n, n)).lower())
    values = sheet_thickness_values(materials)
    if not values:
        return {"problem": None, "skipped": [], "batches": [{"thickness": 0.0,
                "sheet_ids": [m.get("id") for m in materials], "names": list(parts)}]}
    missing = [m for m in materials if not material_thickness(m)]
    if missing:
        return {"problem": {"kind": "sheets_without_thickness",
                            "labels": [str(m.get("label", "")) for m in missing]},
                "skipped": [], "batches": []}
    # Parts without a sheet of their thickness stay red and are not nested.
    skipped = order(unmatched_parts(materials, parts))
    parts = {n: d for n, d in parts.items() if n not in skipped}
    batches = []
    for value in values:
        names = [n for n, depths in parts.items()
                 if depths and all(same_thickness(d, value) for d in depths)]
        if names:
            batches.append({"thickness": value, "names": names, "sheet_ids":
                            [m.get("id") for m in materials if same_thickness(material_thickness(m), value)]})
    flat = [n for n, depths in parts.items() if not depths]
    if flat and not batches and len(values) == 1:
        batches.append({"thickness": values[0], "names": [], "sheet_ids":
                        [m.get("id") for m in materials]})
    if flat:
        if len(batches) == 1:
            batches[0]["names"].extend(flat)
        elif len(batches) > 1:
            return {"problem": {"kind": "flat_parts", "names": order(flat)},
                    "skipped": skipped, "batches": []}
    if not batches:
        return {"problem": {"kind": "nothing", "values": values, "names": skipped},
                "skipped": skipped, "batches": []}
    return {"problem": None, "skipped": skipped, "batches": batches}


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
