"""Offcut library: choose a saved DXF offcut from a folder, filtered by thickness.

File names such as ``Retal_<doc>_<sheet>_e10mm_20261103-2215_1.90m2.dxf``
provide thickness, date and reusable area. Other DXF files are listed with an
unknown thickness.
"""
import os

import FreeCAD as App
from PySide import QtGui, QtCore

from Nesting1stLanguages import tr, translate_buttons, ui_call, ui_widget, register_window
from Nesting1stSheetSpec import format_number, list_offcut_files, same_thickness

PREF_FOLDER = "OffcutLibraryFolder"
ALL, UNKNOWN = "__all__", "__unknown__"


def _prefs():
    return App.ParamGet("User parameter:BaseApp/Preferences/Mod/IPNesting")


def library_folder():
    try:
        return str(_prefs().GetString(PREF_FOLDER, "") or "")
    except Exception:
        return ""


def set_library_folder(folder):
    try:
        _prefs().SetString(PREF_FOLDER, str(folder or ""))
    except Exception:
        pass


class _SortItem(QtGui.QTableWidgetItem):
    """Sort by the numeric/ISO value stored in UserRole, not the shown text."""
    def __lt__(self, other):
        a, b = self.data(QtCore.Qt.UserRole), other.data(QtCore.Qt.UserRole)
        try:
            return a < b
        except TypeError:
            return str(a) < str(b)


class OffcutLibraryDialog(QtGui.QDialog):
    def __init__(self, parent=None, thickness_mm=0.0, display_units="mm"):
        super(OffcutLibraryDialog, self).__init__(parent)
        self.selected_path = None
        self._entries = []
        self._wanted_thickness = float(thickness_mm or 0.0)
        self._units = display_units if display_units in ("mm", "inch") else "mm"
        ui_call(self, 'setWindowTitle', tr('offcut_library.title'))
        self.setModal(True)
        self.resize(1040, 480)
        self._build_ui()
        register_window(self)
        self._load(library_folder())

    def _build_ui(self):
        layout = QtGui.QVBoxLayout(self)

        folder_row = QtGui.QHBoxLayout()
        folder_row.addWidget(ui_widget(QtGui.QLabel, tr('offcut_library.folder')))
        self.folder_edit = QtGui.QLineEdit()
        self.folder_edit.setReadOnly(True)
        folder_row.addWidget(self.folder_edit, 1)
        browse = ui_widget(QtGui.QPushButton, tr('offcut_library.browse'))
        browse.clicked.connect(self._choose_folder)
        folder_row.addWidget(browse)
        layout.addLayout(folder_row)

        filter_row = QtGui.QHBoxLayout()
        filter_row.addWidget(ui_widget(QtGui.QLabel, tr('offcut_library.thickness_filter')))
        self.filter_combo = QtGui.QComboBox()
        self.filter_combo.currentIndexChanged.connect(self._fill_table)
        filter_row.addWidget(self.filter_combo)
        filter_row.addStretch(1)
        self.count_label = QtGui.QLabel()
        filter_row.addWidget(self.count_label)
        layout.addLayout(filter_row)

        self.table = QtGui.QTableWidget(0, 4)
        ui_call(self.table, 'setHorizontalHeaderLabels', [
            tr('offcut_library.col_name'), tr('offcut_library.col_thickness'),
            tr('offcut_library.col_area'), tr('offcut_library.col_date')])
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        try:
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QtGui.QHeaderView.Stretch)
            for col in (1, 2, 3):
                header.setSectionResizeMode(col, QtGui.QHeaderView.ResizeToContents)
        except Exception:
            pass
        self.table.itemDoubleClicked.connect(lambda *_: self._accept_selected())
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.table.itemSelectionChanged.connect(self._update_preview)
        # The list on the left, the selected offcut drawn on the right.
        from Nesting1stDxfPreview import OffcutPreview
        self.preview = OffcutPreview()
        split = QtGui.QSplitter(QtCore.Qt.Horizontal)
        split.addWidget(self.table)
        split.addWidget(self.preview)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([600, 420])
        layout.addWidget(split, 1)

        self.empty_label = QtGui.QLabel()
        self.empty_label.setStyleSheet("color: gray;")
        layout.addWidget(self.empty_label)

        buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel)
        self.use_btn = ui_widget(QtGui.QPushButton, tr('offcut_library.use'))
        self.use_btn.setDefault(True)
        buttons.addButton(self.use_btn, QtGui.QDialogButtonBox.AcceptRole)
        self.open_btn = ui_widget(QtGui.QPushButton, tr('offcut_library.open_folder'))
        buttons.addButton(self.open_btn, QtGui.QDialogButtonBox.ActionRole)
        self.open_btn.clicked.connect(self._open_folder)
        buttons.accepted.connect(self._accept_selected)
        buttons.rejected.connect(self.reject)
        translate_buttons(buttons)
        layout.addWidget(buttons)
        self._update_buttons()

    def _choose_folder(self):
        folder = QtGui.QFileDialog.getExistingDirectory(
            self, tr('offcut_library.select_folder'), self.folder_edit.text() or "")
        if folder:
            set_library_folder(os.path.abspath(str(folder)))
            self._load(os.path.abspath(str(folder)))

    def _open_folder(self):
        folder = self.folder_edit.text()
        if folder and os.path.isdir(folder):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))

    def _thickness_text(self, value):
        if self._units == "inch":
            return format_number(value / 25.4) + " inch"
        return format_number(value) + " mm"

    def _load(self, folder):
        self.folder_edit.setText(folder or "")
        self._entries = list_offcut_files(folder) if folder and os.path.isdir(folder) else []
        values = []
        for entry in self._entries:
            t = entry["thickness"]
            if t and not any(same_thickness(t, v) for v in values):
                values.append(t)
        values.sort()
        blocked = self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        self.filter_combo.addItem(str(tr('offcut_library.all')), ALL)
        for value in values:
            self.filter_combo.addItem(self._thickness_text(value), value)
        if any(not e["thickness"] for e in self._entries):
            self.filter_combo.addItem(str(tr('offcut_library.unknown')), UNKNOWN)
        index = 0
        if self._wanted_thickness:
            for i, value in enumerate(values):
                if same_thickness(value, self._wanted_thickness):
                    index = i + 1
        self.filter_combo.setCurrentIndex(index)
        self.filter_combo.blockSignals(blocked)
        self._fill_table()

    def _visible_entries(self):
        wanted = self.filter_combo.itemData(self.filter_combo.currentIndex())
        if wanted in (None, ALL):
            return list(self._entries)
        if wanted == UNKNOWN:
            return [e for e in self._entries if not e["thickness"]]
        return [e for e in self._entries if e["thickness"] and same_thickness(e["thickness"], float(wanted))]

    def _fill_table(self, *args):
        entries = self._visible_entries()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for row, entry in enumerate(entries):
            self.table.insertRow(row)
            cells = (
                (entry["name"], entry["name"].lower()),
                (self._thickness_text(entry["thickness"]) if entry["thickness"]
                 else str(tr('offcut_library.unknown')), entry["thickness"]),
                ("%.2f" % entry["area_m2"] if entry["area_m2"] else "", entry["area_m2"]),
                (entry["date"], entry["date"] or ""),
            )
            for col, (text, key) in enumerate(cells):
                item = _SortItem(text)
                item.setData(QtCore.Qt.UserRole, key)
                if col == 0:
                    item.setData(QtCore.Qt.UserRole + 1, entry["path"])
                    item.setToolTip(entry["path"])
                if col in (1, 2):
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)
        if entries:
            self.table.selectRow(0)
        folder = self.folder_edit.text()
        if not folder:
            ui_call(self.empty_label, 'setText', tr('offcut_library.no_folder'))
        elif not self._entries:
            ui_call(self.empty_label, 'setText', tr('offcut_library.empty'))
        elif not entries:
            ui_call(self.empty_label, 'setText', tr('offcut_library.none_with_thickness'))
        else:
            self.empty_label.setText("")
        self.count_label.setText(str(tr('offcut_library.count_d_of_d')) % (len(entries), len(self._entries)))
        self._update_buttons()

    def _update_buttons(self):
        self.use_btn.setEnabled(bool(self.table.selectedItems()))
        self.open_btn.setEnabled(bool(self.folder_edit.text()))

    def _selected_path(self):
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return item.data(QtCore.Qt.UserRole + 1) if item else None

    def _update_preview(self):
        path = self._selected_path()
        entry = next((e for e in self._entries if e["path"] == path), None)
        info = []
        if entry:
            if entry["thickness"]:
                info.append(self._thickness_text(entry["thickness"]))
            if entry["area_m2"]:
                info.append("%.2f m²" % entry["area_m2"])
        self.preview.set_path(str(path) if path else None, "  ·  ".join(info))

    def _accept_selected(self):
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return
        item = self.table.item(rows[0].row(), 0)
        path = item.data(QtCore.Qt.UserRole + 1) if item else None
        if path and os.path.exists(path):
            self.selected_path = str(path)
            self.accept()
