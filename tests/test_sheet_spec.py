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


class PlanTests(unittest.TestCase):
    def test_no_thickness_is_one_classic_run(self):
        plan = S.plan_batches([{'id': 1, 'type': 'rectangular'}], {'a': [5.0], 'b': [8.0]})
        self.assertIsNone(plan['problem'])
        self.assertEqual(plan['batches'], [{'thickness': 0.0, 'sheet_ids': [1], 'names': ['a', 'b']}])

    def test_one_run_per_thickness(self):
        sheets = [{'id': 1, 'thickness': 10}, {'id': 2, 'thickness': 20},
                  {'id': 3, 'thickness': 10}, {'id': 4, 'thickness': 30}]
        parts = {'a10': [10.0004], 'b20': [20.0], 'c10': [10.0], 'd30': [30.0, 30.0]}
        plan = S.plan_batches(sheets, parts)
        self.assertIsNone(plan['problem'])
        self.assertEqual([(b['thickness'], b['sheet_ids'], sorted(b['names'])) for b in plan['batches']],
                         [(10.0, [1, 3], ['a10', 'c10']), (20.0, [2], ['b20']), (30.0, [4], ['d30'])])

    def test_sheet_without_parts_is_skipped(self):
        plan = S.plan_batches([{'id': 1, 'thickness': 10}, {'id': 2, 'thickness': 20}], {'a': [10.0]})
        self.assertEqual([b['thickness'] for b in plan['batches']], [10.0])

    def test_part_without_sheet_blocks(self):
        plan = S.plan_batches([{'id': 1, 'thickness': 10}], {'b': [8.0], 'a': [10.0]}, {'b': 'Pletina'})
        self.assertEqual(plan['problem'], {'kind': 'parts', 'names': ['b'], 'values': [10.0]})
        self.assertEqual(S.unmatched_parts([{'thickness': 10}, {'thickness': 8}], {'b': [8.0]}), set())

    def test_missing_sheet_thickness_and_flat_parts(self):
        plan = S.plan_batches([{'id': 1, 'thickness': 10}, {'id': 2, 'label': 'Sin'}], {'a': [10.0]})
        self.assertEqual(plan['problem'], {'kind': 'sheets_without_thickness', 'labels': ['Sin']})
        one = S.plan_batches([{'id': 1, 'thickness': 10}], {'a': [10.0], 'dxf': []})
        self.assertEqual(sorted(one['batches'][0]['names']), ['a', 'dxf'])
        two = S.plan_batches([{'id': 1, 'thickness': 10}, {'id': 2, 'thickness': 20}],
                             {'a': [10.0], 'b': [20.0], 'dxf': []})
        self.assertEqual(two['problem'], {'kind': 'flat_parts', 'names': ['dxf']})
        none = S.plan_batches([{'id': 1, 'thickness': 10}], {'dxf': []})
        self.assertEqual(none['batches'][0]['names'], ['dxf'])

class LabelTests(unittest.TestCase):
    def test_labels_and_common_spec(self):
        self.assertEqual(S.spec_suffix({'thickness': 10, 'material': 'S275'}), ' · 10 mm · S275')
        self.assertEqual(S.spec_suffix({'thickness': 25.4}, 'inch'), ' · 1 inch')
        self.assertEqual(S.spec_suffix({}), '')
        self.assertEqual(S.common_spec([{'thickness': 0}, {'thickness': 6, 'material': 'S235'},
                                        {'material': 'S235'}, {'material': 'AISI 304'}]),
                         (6.0, 'S235 / AISI 304'))


if __name__ == '__main__':
    unittest.main()
