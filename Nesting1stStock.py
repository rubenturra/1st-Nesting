"""Sheet stock: keep the Sheet & Offcut Materials list between sessions.

The list is written to ``<FreeCAD user data>/1st-Nesting/sheet_stock.json``
after every change and restored when the panel opens. DXF offcuts keep their
imported geometry, so they stay usable even if the DXF file is moved.
Set ``BaseApp/Preferences/Mod/IPNesting/KeepSheetStock`` to False to disable.
"""
import json
import os
import tempfile

SCHEMA_VERSION = 1
FILE_NAME = "sheet_stock.json"


def stock_path(user_dir=None):
    if user_dir is None:
        import FreeCAD as App
        user_dir = App.getUserAppDataDir()
    return os.path.join(user_dir, "1st-Nesting", FILE_NAME)


def enabled():
    if os.environ.get("NESTING1ST_NO_STOCK"):
        return False
    try:
        import FreeCAD as App
        return bool(App.ParamGet(
            "User parameter:BaseApp/Preferences/Mod/IPNesting").GetBool("KeepSheetStock", True))
    except Exception:
        return True


def _clean(value):
    """JSON-safe copy (tuples become lists, unknown objects are dropped)."""
    if isinstance(value, dict):
        cleaned = {str(k): _clean(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v is not _DROP}
    if isinstance(value, (list, tuple)):
        return [item for item in (_clean(v) for v in value) if item is not _DROP]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return _DROP


_DROP = object()


def save_stock(materials, path=None):
    path = path or stock_path()
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    payload = {"schema_version": SCHEMA_VERSION,
               "materials": [_clean(dict(m)) for m in materials or []]}
    fd, temporary = tempfile.mkstemp(prefix=".stock-", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        os.replace(temporary, path)
    except Exception:
        try:
            os.remove(temporary)
        except OSError:
            pass
        raise


def load_stock(path=None):
    """Return the saved materials (valid entries only); [] when missing/corrupt."""
    path = path or stock_path()
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return []
    result = []
    for material in (data.get("materials") if isinstance(data, dict) else None) or []:
        if not isinstance(material, dict):
            continue
        outer = material.get("outer")
        if str(material.get("type", "")).lower() not in ("rectangular", "dxf"):
            continue
        if not isinstance(outer, list) or len(outer) < 3:
            continue
        try:
            count = max(1, int(material.get("count", material.get("quantity", 1))))
        except (TypeError, ValueError):
            count = 1
        material["count"] = material["quantity"] = count
        material["duplicate"] = False
        result.append(material)
    return result
