"""Part quantity stored on the design object.

A Body (or any part) can carry an integer property ``Cantidad`` (group
"Fabricación"). 1st Nesting reads it when the part is added and writes the
table quantity back to it, so the quantity is saved with the .FCStd file.
``Quantity`` and ``NestingQuantity`` are also read for other languages/tools.
"""
PROPERTY = "Cantidad"
GROUP = "Fabricación"
READ_NAMES = (PROPERTY, "Quantity", "NestingQuantity")
SOURCE_DOC = "SourceDocument"
SOURCE_OBJ = "SourceObject"
MAX_QUANTITY = 5000


def read_quantity(obj):
    """Return the stored quantity (>= 1) or None when the object has none."""
    for name in READ_NAMES:
        try:
            if obj is not None and name in obj.PropertiesList:
                value = int(getattr(obj, name))
                if value >= 1:
                    return min(MAX_QUANTITY, value)
        except Exception:
            continue
    return None


def write_quantity(obj, quantity, create=True):
    """Store quantity on obj; add the property when missing and create is True."""
    try:
        quantity = max(1, min(MAX_QUANTITY, int(quantity)))
        if PROPERTY not in obj.PropertiesList:
            if not create:
                return False
            obj.addProperty("App::PropertyInteger", PROPERTY, GROUP,
                            "Número de piezas a fabricar (1st Nesting)")
        if int(getattr(obj, PROPERTY)) != quantity:
            setattr(obj, PROPERTY, quantity)
        return True
    except Exception:
        return False


def remember_source(preview_obj, source_obj):
    """Record which design object a preview copy came from."""
    try:
        for name in (SOURCE_DOC, SOURCE_OBJ):
            if name not in preview_obj.PropertiesList:
                preview_obj.addProperty("App::PropertyString", name, "1st Nesting")
        preview_obj.SourceDocument = source_obj.Document.Name
        preview_obj.SourceObject = source_obj.Name
    except Exception:
        pass


def source_of(preview_obj):
    """Return the design object a preview copy came from, or None."""
    try:
        import FreeCAD as App
        doc_name = getattr(preview_obj, SOURCE_DOC, "")
        if doc_name not in App.listDocuments():
            return None
        return App.getDocument(doc_name).getObject(getattr(preview_obj, SOURCE_OBJ, ""))
    except Exception:
        return None
