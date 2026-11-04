"""
Nesting1stAddSheet

Dialog for adding rectangular sheets or DXF offcuts.
The dialog only collects and validates user input.
The parent panel is responsible for storing the result.
"""
from Nesting1stLanguages import tr, translate_buttons, ui_call, ui_widget, register_window

import os
import FreeCAD as App
from Nesting1stSheetSpec import (COMMON_MATERIALS, format_number,
                                 parse_offcut_filename, same_thickness)
from PySide import QtGui, QtCore

MM_PER_INCH = 25.4


# Collect rectangular sheet dimensions or a DXF path and quantity for the parent panel.
class AddSheetOrOffcutDialog(QtGui.QDialog):
    """
    Dialog for adding either:
      - a rectangular sheet;
      - a DXF offcut.

    Result is available through:
      result_type
      result_data
    """

    # Restore the last sheet dimensions and build the modal sheet/offcut input dialog.
    def __init__(self, parent=None, panel=None):
        super(AddSheetOrOffcutDialog, self).__init__(parent)

        self.result_type = None
        self.result_data = None
        self._panel = panel
        self._display_units = self._get_display_units()

        self._last_width_mm = 2000.0
        self._last_height_mm = 2800.0
        self._last_quantity = 1
        self._last_thickness_mm = 0.0
        self._last_material = ""

        self._load_last_rectangular_sheet()
        self._load_last_spec()

        ui_call(self, 'setWindowTitle', tr('add_sheet_or_offcut'))
        self.setModal(True)
        self.setMinimumWidth(420)

        self._build_ui()
        register_window(self)

    # Read mm or inch from the parent panel, defaulting to mm.
    def _get_display_units(self):
        try:
            units = str(
                getattr(
                    self._panel,
                    "display_units",
                    "mm"
                )
                or "mm"
            ).strip().lower()

            if units not in ("mm", "inch"):
                return "mm"

            return units

        except Exception:
            return "mm"

    # Return the 1st Nesting FreeCAD preference group, or None when unavailable.
    def _prefs(self):
        try:
            return App.ParamGet(
                "User parameter:BaseApp/Preferences/Mod/IPNesting"
            )
        except Exception:
            return None

    # Parse dot/comma decimal text; return None for empty, fractional or invalid input.
    def _parse_decimal(self, text):
        try:
            value = str(text or "").strip()

            if not value or "/" in value:
                return None

            return float(
                value.replace(",", ".")
            )

        except Exception:
            return None

    # Convert millimetres to the dialog display units.
    def _mm_to_display(self, value_mm):
        if self._display_units == "inch":
            return float(value_mm) / MM_PER_INCH

        return float(value_mm)

    # Convert a value in the dialog display units to millimetres.
    def _display_to_mm(self, value):
        if self._display_units == "inch":
            return float(value) * MM_PER_INCH

        return float(value)

    # Format a millimetre dimension in display units without trailing decimal zeros.
    def _format_dimension(self, value_mm):
        value = self._mm_to_display(value_mm)

        return (
            "%.6f" % value
        ).rstrip("0").rstrip(".") or "0"

    # Restore saved sheet dimensions and quantity, replacing nonpositive values with defaults.
    def _load_last_rectangular_sheet(self):
        p = self._prefs()

        if not p:
            return

        try:
            self._last_width_mm = float(
                str(
                    p.GetString(
                        "LastSheetWidthMm",
                        "2000.0"
                    )
                ).replace(",", ".")
            )
        except Exception:
            self._last_width_mm = 2000.0

        try:
            self._last_height_mm = float(
                str(
                    p.GetString(
                        "LastSheetHeightMm",
                        "2800.0"
                    )
                ).replace(",", ".")
            )
        except Exception:
            self._last_height_mm = 2800.0

        try:
            self._last_quantity = int(
                p.GetInt(
                    "LastSheetQuantity",
                    1
                )
            )
        except Exception:
            self._last_quantity = 1

        if self._last_width_mm <= 0.0:
            self._last_width_mm = 2000.0

        if self._last_height_mm <= 0.0:
            self._last_height_mm = 2800.0

        if self._last_quantity < 1:
            self._last_quantity = 1

    # Persist sheet dimensions in millimetres and the requested quantity.
    def _save_last_rectangular_sheet(
        self,
        width_mm,
        height_mm,
        quantity
    ):
        p = self._prefs()

        if not p:
            return

        try:
            p.SetString(
                "LastSheetWidthMm",
                "%.6f" % float(width_mm)
            )

            p.SetString(
                "LastSheetHeightMm",
                "%.6f" % float(height_mm)
            )

            p.SetInt(
                "LastSheetQuantity",
                int(quantity)
            )

        except Exception:
            pass

    # Restore the last thickness/material; the parts' gauge wins when known.
    def _load_last_spec(self):
        p = self._prefs()
        if p:
            try:
                self._last_thickness_mm = max(0.0, float(str(
                    p.GetString("LastSheetThicknessMm", "0")).replace(",", ".")))
            except Exception:
                self._last_thickness_mm = 0.0
            try:
                self._last_material = str(p.GetString("LastSheetMaterial", "") or "")
            except Exception:
                self._last_material = ""
        self._parts_thickness_mm = self._read_parts_thickness()
        if self._parts_thickness_mm:
            self._last_thickness_mm = self._parts_thickness_mm

    # Reference thickness of the 3D parts already in the panel, or 0.
    def _read_parts_thickness(self):
        try:
            result = self._panel._thickness_checker.measure()
            reference = result.get("reference")
            return float(reference) if reference else 0.0
        except Exception:
            return 0.0

    def _save_last_spec(self, thickness_mm, material):
        p = self._prefs()
        if not p:
            return
        try:
            p.SetString("LastSheetThicknessMm", "%.6f" % float(thickness_mm))
            p.SetString("LastSheetMaterial", str(material or ""))
        except Exception:
            pass

    # Read the thickness (mm) and material fields; None when the thickness is invalid.
    def _read_spec(self):
        text = str(self.thickness_edit.text() or "").strip()
        if not text:
            thickness_mm = 0.0
        else:
            value = self._parse_decimal(text)
            if value is None or value < 0.0:
                self._show_warning(tr('sheet_spec.invalid_thickness'))
                return None
            thickness_mm = self._display_to_mm(value)
        material = str(self.material_combo.currentText() or "").strip()
        self._save_last_spec(thickness_mm, material)
        return thickness_mm, material

    # Refresh the width and height labels with the active unit suffix.
    def _update_dimension_labels(self):
        suffix = (
            "inch"
            if self._display_units == "inch"
            else "mm"
        )

        ui_call(
            self.width_label, 'setText', tr('sheet_width_x_s') % suffix
        )

        ui_call(
            self.height_label, 'setText', tr('sheet_height_y_s') % suffix
        )

        ui_call(
            self.thickness_label, 'setText', tr('sheet_spec.thickness_s') % suffix
        )
    
    # Build the sheet and DXF sections and the Cancel button.
    def _build_ui(self):
        layout = QtGui.QVBoxLayout(self)

        info = ui_widget(
            QtGui.QLabel, tr('add_a_rectangular_sheet_or_import_a_dxf_offcut')
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self._build_spec_section(layout)
        self._build_rectangular_sheet_section(layout)
        self._build_dxf_section(layout)

        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Cancel
        )
        buttons.rejected.connect(self.reject)
        translate_buttons(buttons)
        layout.addWidget(buttons)

    # Thickness and material shared by the rectangular sheet and the DXF offcut.
    def _build_spec_section(self, parent_layout):
        box = ui_widget(QtGui.QGroupBox, tr('sheet_spec.group'))
        grid = QtGui.QGridLayout(box)

        self.thickness_label = QtGui.QLabel()
        grid.addWidget(self.thickness_label, 0, 0)
        self.thickness_edit = QtGui.QLineEdit(
            self._format_dimension(self._last_thickness_mm)
            if self._last_thickness_mm > 0.0 else "")
        self.thickness_edit.setValidator(
            QtGui.QDoubleValidator(0.0, 100000.0, 3, self))
        ui_call(self.thickness_edit, 'setToolTip', tr('sheet_spec.thickness_tooltip'))
        grid.addWidget(self.thickness_edit, 0, 1)

        grid.addWidget(ui_widget(QtGui.QLabel, tr('sheet_spec.material')), 1, 0)
        self.material_combo = QtGui.QComboBox()
        self.material_combo.setEditable(True)
        self.material_combo.addItem("")
        self.material_combo.addItems(list(COMMON_MATERIALS))
        self.material_combo.setEditText(self._last_material)
        try:
            ui_call(self.material_combo.lineEdit(), 'setPlaceholderText',
                    tr('sheet_spec.material_placeholder'))
        except Exception:
            pass
        grid.addWidget(self.material_combo, 1, 1)

        if self._parts_thickness_mm:
            info = ui_widget(QtGui.QLabel, tr('sheet_spec.parts_reference_s')
                             % (self._format_dimension(self._parts_thickness_mm)
                                + (" inch" if self._display_units == "inch" else " mm")))
            info.setStyleSheet("color: gray;")
            grid.addWidget(info, 2, 0, 1, 2)

        parent_layout.addWidget(box)

    # Add the width, height, quantity and Add rectangular sheet controls.
    def _build_rectangular_sheet_section(self, parent_layout):
        sheet_box = ui_widget(QtGui.QGroupBox, tr('rectangular_sheet'))
        sheet_layout = QtGui.QVBoxLayout(sheet_box)

        width_row = QtGui.QHBoxLayout()

        self.width_label = QtGui.QLabel()
        width_row.addWidget(self.width_label)

        self.width_edit = QtGui.QLineEdit(
            self._format_dimension(
                self._last_width_mm
            )
        )
        self.width_edit.setValidator(
            QtGui.QDoubleValidator(0.0, 1000000.0, 3, self)
        )
        width_row.addWidget(self.width_edit)
        sheet_layout.addLayout(width_row)

        height_row = QtGui.QHBoxLayout()

        self.height_label = QtGui.QLabel()
        height_row.addWidget(self.height_label)

        self.height_edit = QtGui.QLineEdit(
            self._format_dimension(
                self._last_height_mm
            )
        )
        self.height_edit.setValidator(
            QtGui.QDoubleValidator(0.0, 1000000.0, 3, self)
        )
        height_row.addWidget(self.height_edit)
        sheet_layout.addLayout(height_row)

        quantity_row = QtGui.QHBoxLayout()
        quantity_row.addWidget(
            ui_widget(QtGui.QLabel, tr('quantity'))
        )

        self.quantity_spin = QtGui.QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(100000)
        self.quantity_spin.setValue(self._last_quantity)
        quantity_row.addWidget(self.quantity_spin)
        sheet_layout.addLayout(quantity_row)

        self.add_rectangular_btn = ui_widget(
            QtGui.QPushButton, tr('add_rectangular_sheet')
        )
        self.add_rectangular_btn.clicked.connect(
            self._on_add_rectangular_clicked
        )
        sheet_layout.addWidget(self.add_rectangular_btn)

        parent_layout.addWidget(sheet_box)
        self._update_dimension_labels()

    # Add the DXF quantity control and file-selection button.
    def _build_dxf_section(self, parent_layout):
        dxf_box = ui_widget(QtGui.QGroupBox, tr('dxf_offcut'))
        dxf_layout = QtGui.QVBoxLayout(dxf_box)

        info = ui_widget(
            QtGui.QLabel, tr('import_a_dxf_file_and_use_its_closed_contour_as_an_offcut')
        )
        info.setWordWrap(True)
        dxf_layout.addWidget(info)

        dxf_quantity_row = QtGui.QHBoxLayout()
        dxf_quantity_row.addWidget(
            ui_widget(QtGui.QLabel, tr('quantity'))
        )

        self.dxf_quantity_spin = QtGui.QSpinBox()
        self.dxf_quantity_spin.setMinimum(1)
        self.dxf_quantity_spin.setMaximum(100000)
        self.dxf_quantity_spin.setValue(1)
        dxf_quantity_row.addWidget(self.dxf_quantity_spin)

        dxf_layout.addLayout(dxf_quantity_row)

        self.add_dxf_btn = ui_widget(
            QtGui.QPushButton, tr('add_dxf_offcut')
        )
        self.add_dxf_btn.clicked.connect(
            self._on_add_dxf_clicked
        )
        dxf_layout.addWidget(self.add_dxf_btn)

        self.library_btn = ui_widget(
            QtGui.QPushButton, tr('offcut_library.button')
        )
        ui_call(self.library_btn, 'setToolTip', tr('offcut_library.tooltip'))
        self.library_btn.clicked.connect(self._on_library_clicked)
        dxf_layout.addWidget(self.library_btn)

        parent_layout.addWidget(dxf_box)

    # Validate dimensions and quantity, store the result in millimetres and accept the dialog.
    def _on_add_rectangular_clicked(self):
        try:
            width_value = self._parse_decimal(
                self.width_edit.text()
            )

            height_value = self._parse_decimal(
                self.height_edit.text()
            )

            quantity = int(
                self.quantity_spin.value()
            )

            if width_value is None or width_value <= 0.0:
                self._show_warning(
                    tr('sheet_width_must_be_greater_than_zero')
                )
                return

            if height_value is None or height_value <= 0.0:
                self._show_warning(
                    tr('sheet_height_must_be_greater_than_zero')
                )
                return

            if quantity < 1:
                self._show_warning(
                    tr('quantity_must_be_at_least_1')
                )
                return

            spec = self._read_spec()
            if spec is None:
                return

            # Store all geometry internally in mm.
            width_mm = self._display_to_mm(
                width_value
            )

            height_mm = self._display_to_mm(
                height_value
            )

            self._save_last_rectangular_sheet(
                width_mm,
                height_mm,
                quantity
            )

            self.result_type = "rectangular"
            self.result_data = {
                "width": width_mm,
                "height": height_mm,
                "quantity": quantity,
                "thickness": spec[0],
                "material": spec[1],
            }

            self.accept()

        except Exception:
            self._show_warning(
                tr('enter_valid_decimal_values_for_sheet_width_and_height')
            )

    # Choose an existing DXF file, store its absolute path and quantity and accept the dialog.
    def _on_add_dxf_clicked(self):
        path, _ = QtGui.QFileDialog.getOpenFileName(
            self,
            tr('select_dxf_offcut'),
            "",
            tr('dxf_files_dxf_dxf_all_files')
        )

        if not path:
            return

        path = os.path.abspath(str(path))

        if not os.path.exists(path):
            self._show_warning(
                tr('the_selected_dxf_file_does_not_exist')
            )
            return

        self._accept_dxf(path, int(self.dxf_quantity_spin.value()))

    # Pick a saved offcut from the library folder (filtered by thickness).
    def _on_library_clicked(self):
        from Nesting1stOffcutLibrary import OffcutLibraryDialog
        text = str(self.thickness_edit.text() or "").strip()
        value = self._parse_decimal(text) if text else None
        thickness_mm = self._display_to_mm(value) if value else 0.0
        dialog = OffcutLibraryDialog(self, thickness_mm=thickness_mm,
                                     display_units=self._display_units)
        if dialog.exec_() != QtGui.QDialog.Accepted or not dialog.selected_path:
            return
        self._accept_dxf(dialog.selected_path, int(self.dxf_quantity_spin.value()))

    # Reconcile the dialog thickness with the one written in the file name, then accept.
    def _accept_dxf(self, path, quantity):
        spec = self._read_spec()
        if spec is None:
            return
        thickness_mm, material = spec
        name_thickness = parse_offcut_filename(path)["thickness"]
        if name_thickness:
            if not thickness_mm:
                thickness_mm = name_thickness
            elif not same_thickness(name_thickness, thickness_mm):
                answer = QtGui.QMessageBox.question(
                    self, tr('sheet_spec.dxf_name_thickness_title'),
                    tr('sheet_spec.dxf_name_thickness_q')
                    % (format_number(name_thickness) + " mm",
                       format_number(thickness_mm) + " mm",
                       format_number(name_thickness) + " mm"),
                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                    QtGui.QMessageBox.Yes)
                if answer == QtGui.QMessageBox.Yes:
                    thickness_mm = name_thickness

        self.result_type = "dxf"
        self.result_data = {
            "path": path,
            "quantity": quantity,
            "thickness": thickness_mm,
            "material": material,
        }

        self.accept()

    # Display a warning in the sheet/offcut dialog.
    def _show_warning(self, message):
        QtGui.QMessageBox.warning(
            self,
            tr('add_sheet_or_offcut'),
            message
        )

