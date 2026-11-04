# Sheet stock

The **Sheet & Offcut Materials** list works as a stock: every sheet and offcut
you add stays there after closing the panel or restarting FreeCAD. The list is
saved after each change (add, remove, count, order, grain and hole selection)
to `<FreeCAD user data>/1st-Nesting/sheet_stock.json`, outside the workbench
folder, so updates do not erase it.

DXF offcuts keep their imported contours, so they still work if the DXF file is
moved. Thickness and material are kept too. Remove a row with **Remove** to
take it out of the stock.

Set the boolean preference `BaseApp/Preferences/Mod/IPNesting/KeepSheetStock`
to `False` to start every session with an empty list. Automated tests set the
environment variable `NESTING1ST_NO_STOCK=1` so they never touch the user's file.
