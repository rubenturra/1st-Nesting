# Sheet thickness, material and offcut library

## Thickness and material

**Add Sheet or Offcut** has a **Sheet thickness and material** box shared by
rectangular sheets and DXF offcuts. Both fields are optional:

- **Thickness** is entered in the panel units and stored in millimetres. When
  3D parts are already in the list, the field starts with their reference
  thickness; otherwise it repeats the last value used.
- **Material** is free text with common suggestions (S235, S275, AISI 304…).

The materials table has a **Thickness** column, shown after **Material**;
double-click it to change or clear the thickness of stock already in the list.
The material name follows the stock name (`Sheet 2000 x 2000 mm · S275`), and
the preview cards and the Material tooltip show both (`… · 10 mm · S275`). Stock with the
same dimensions but another thickness or material gets its own row.

When a DXF name contains a thickness marker such as `_e10mm_`, that thickness is
used if the field is empty. If the field holds a different value, the dialog
asks which one to keep.

## Nesting by thickness

When the sheets and offcuts have thicknesses, **Run nesting** makes one nesting
per thickness, one after another: each run uses only the sheets of that
thickness and the 3D parts of the same thickness. Each result opens in its own
document, labelled `Nesting_Result_10mm`, `Nesting_Result_20mm`, … and a summary
lists them at the end. Sheet thicknesses without parts are skipped.

Parts are marked red only when no sheet has their thickness. Nesting does not
start when:

- some stock has a thickness and some has not (give every sheet a thickness);
- a 3D part has no sheet of its thickness (the message lists them); or
- flat DXF/SVG parts would have to be shared between several thicknesses.

With a single thickness, flat parts join that run. Stock without any thickness
works as before, in one run with the [advisory part check](THICKNESS_CHECK.md).
Pressing **Stop** before a run has a result cancels the remaining thicknesses.

The thickness and material are saved in `nesting_session.json` and on every
`Sheet_N` object of `Nesting_Result` as the properties **Thickness** and
**Material** (group *1st Nesting*), so CAM macros can read them.

## Offcut library

**Offcut library…** in the DXF section lists the DXF files of one folder. The
folder is chosen with **Change…** and remembered in
`BaseApp/Preferences/Mod/IPNesting/OffcutLibraryFolder`.

File names written by plasma CAM macros, such as
`Retal_<document>_<sheet>_e10mm_20261103-2215_1.90m2.dxf`, provide the
thickness, date and reusable area shown in the table. The list is filtered by
the thickness typed in the dialog (choose **All** to see the rest) and can be
sorted by any column. Double-click an offcut, or press **Use selected offcut**,
to add it exactly like **Add DXF offcut**.
