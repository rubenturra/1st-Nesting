"""Sheet stock file: round trip, JSON cleaning and corrupt files."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import Nesting1stStock as S

RECT = {"id": 3, "type": "rectangular", "label": "Sheet", "width": 2000.0, "height": 1000.0,
        "outer": [(0, 0), (2000, 0), (2000, 1000), (0, 1000)], "count": 4, "quantity": 4,
        "thickness": 10.0, "material": "S275", "grain": "X", "duplicate": True}


class StockTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = S.stock_path(folder)
            dxf = dict(RECT, type="dxf", path="C:/x.dxf", contour_info=[{"area": 1.0, "bad": object()}])
            S.save_stock([RECT, dxf], path)
            loaded = S.load_stock(path)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0]["outer"][1], [2000, 0])
            self.assertEqual((loaded[0]["thickness"], loaded[0]["material"], loaded[0]["count"]),
                             (10.0, "S275", 4))
            self.assertFalse(loaded[0]["duplicate"])
            self.assertEqual(loaded[1]["contour_info"], [{"area": 1.0}])
            self.assertEqual(os.listdir(os.path.dirname(path)), ["sheet_stock.json"])

    def test_missing_corrupt_and_invalid(self):
        with tempfile.TemporaryDirectory() as folder:
            path = S.stock_path(folder)
            self.assertEqual(S.load_stock(path), [])
            os.makedirs(os.path.dirname(path))
            Path(path).write_text("{not json")
            self.assertEqual(S.load_stock(path), [])
            S.save_stock([{"type": "rectangular", "outer": [[0, 0]]}, {"type": "other"}], path)
            self.assertEqual(S.load_stock(path), [])


if __name__ == "__main__":
    unittest.main()
