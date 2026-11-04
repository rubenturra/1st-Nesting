"""Sheet thickness/material helpers and offcut-library file names."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import Nesting1stSheetSpec as S


class FileNameTests(unittest.TestCase):
    def test_plasma_offcut_name(self):
        info = S.parse_offcut_filename(
            r'D:\Retales\Retal_Nesting_Result_Plancha_001_e10mm_20261103-2215_1.90m2.dxf')
        self.assertEqual(info['thickness'], 10.0)
        self.assertEqual(info['date'], '2026-11-03 22:15')
        self.assertAlmostEqual(info['area_m2'], 1.90)
        self.assertEqual(info['name'], 'Retal_Nesting_Result_Plancha_001_e10mm_20261103-2215_1.90m2')

    def test_decimal_thickness_and_unknown(self):
        self.assertEqual(S.parse_offcut_filename('Retal_a_e2,5mm_x.dxf')['thickness'], 2.5)
        self.assertEqual(S.parse_offcut_filename('offcut.dxf')['thickness'], 0.0)
        # "steel10mm" is not a thickness marker.
        self.assertEqual(S.parse_offcut_filename('steel10mm.dxf')['thickness'], 0.0)

    def test_list_folder_newest_first(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('Retal_a_e10mm_20261101-1000_1.00m2.dxf',
                         'Retal_b_e8mm_20261103-0900_0.50m2.DXF', 'notes.txt'):
                Path(folder, name).write_text('0\nEOF\n')
            entries = S.list_offcut_files(folder)
            self.assertEqual([e['thickness'] for e in entries], [8.0, 10.0])
            self.assertTrue(all(os.path.isabs(e['path']) for e in entries))
        self.assertEqual(S.list_offcut_files('/does/not/exist'), [])


class BlockingTests(unittest.TestCase):
    def test_no_thickness_never_blocks(self):
        self.assertIsNone(S.sheet_thickness_problem([{'type': 'rectangular'}], {'a': [5.0]}))

    def test_matching_parts_and_flat_parts_pass(self):
        sheets = [{'thickness': 10}, {'thickness': 0}]
        self.assertIsNone(S.sheet_thickness_problem(sheets, {'a': [10.0004], 'dxf': []}))

    def test_wrong_part_blocks(self):
        problem = S.sheet_thickness_problem([{'thickness': 10}], {'b': [8.0], 'a': [10.0]},
                                            {'b': 'Pletina'})
        self.assertEqual(problem, {'kind': 'parts', 'reference': 10.0, 'names': ['b']})

    def test_mixed_sheets_block(self):
        problem = S.sheet_thickness_problem([{'thickness': 10}, {'thickness': 8}], {})
        self.assertEqual(problem, {'kind': 'mixed_sheets', 'values': [8.0, 10.0]})

    def test_labels_and_common_spec(self):
        self.assertEqual(S.spec_suffix({'thickness': 10, 'material': 'S275'}), ' · 10 mm · S275')
        self.assertEqual(S.spec_suffix({'thickness': 25.4}, 'inch'), ' · 1 inch')
        self.assertEqual(S.spec_suffix({}), '')
        self.assertEqual(S.common_spec([{'thickness': 0}, {'thickness': 6, 'material': 'S235'},
                                        {'material': 'S235'}, {'material': 'AISI 304'}]),
                         (6.0, 'S235 / AISI 304'))


if __name__ == '__main__':
    unittest.main()
