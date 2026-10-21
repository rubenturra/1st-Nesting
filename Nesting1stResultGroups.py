"""Tree folders that keep individual result features available to FreeCAD CAM."""
import FreeCAD as App


def create_sheet_group(document, name, label, offset):
    """Store the presentation offset without an App::Part geometry container."""
    group = document.addObject('App::DocumentObjectGroup', name)
    group.Label = label
    group.addProperty('App::PropertyVector', 'DisplayOffset', '1st Nesting',
                      'Display translation from sheet-local millimetre coordinates.')
    group.DisplayOffset = App.Vector(offset, 0, 0)
    group.setEditorMode('DisplayOffset', 1)
    return group


def add_to_sheet_group(group, obj):
    """Bake a folder's display translation into its child's own placement once."""
    if obj in group.Group:
        return
    if 'DisplayOffset' in group.PropertiesList:
        obj.Placement = App.Placement(group.DisplayOffset, App.Rotation()).multiply(obj.Placement)
    # Legacy App::Part groups already apply their placement through the parent.
    group.addObject(obj)


def sheet_local_shape(obj):
    """Recover normalized bridge geometry from new folders or legacy results."""
    shape = obj.Shape.copy()
    for parent in obj.InList:
        if parent.TypeId == 'App::DocumentObjectGroup' and 'DisplayOffset' in parent.PropertiesList:
            shape.translate(-parent.DisplayOffset)
            break
    return shape
