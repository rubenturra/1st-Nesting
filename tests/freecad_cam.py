"""Real CAM eligibility, multi-sheet placements and saved-result bridge geometry."""
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest

from freecad_bridges import App, Part, languages, rectangle
from Path.Base import Util as CAMUtil
from Nesting1stResult import NestingResultImporter
from Nesting1stResultGroups import create_sheet_group, add_to_sheet_group, sheet_local_shape
from Nesting1stBridgeModel import load_result, create_document
from Nesting1stResultDXF import result_parts, top_view_shape


class CAMResultTests(unittest.TestCase):
    def tearDown(self):
        for name in list(App.listDocuments()):
            App.closeDocument(name)

    def make_result(self):
        wire = Part.makePolygon([App.Vector(x, y, 0) for x, y in rectangle(0, 0, 10, 20) + [[0, 0]]])
        solid = Part.makeBox(10, 20, 4).cut(Part.makeCylinder(2, 4, App.Vector(5, 10, 0)))
        sources = [dict(source_part_index=i, part_id='part_%d' % i, label='Part %d' % i,
                        source_type='3d' if i < 2 else 'dxf', points=rectangle(0, 0, 10, 20),
                        shape_brep=(solid if i < 2 else wire).exportBrepToString(),
                        normalization_offset=[0, 0, 0]) for i in range(4)]
        data = dict(sourceParts=sources,
                    sheets=[dict(width=200, height=160, sheet_instance_index=i) for i in range(2)],
                    placements=[dict(id='test_%d' % i, source_part_index=i, instance_index=i,
                                     sheet_instance_index=i % 2, x=40 + 30 * (i // 2), y=30,
                                     rotation=90 if i % 2 else 0) for i in range(4)], unplaced=[])
        importer = NestingResultImporter(SimpleNamespace(display_units='mm'))
        self.assertTrue(importer.import_result(data, show_summary=False))
        return importer, data

    def assert_parts(self, doc, data):
        for index, placement in enumerate(data['placements']):
            obj = doc.getObject('Nesting_test_%d' % index)
            self.assertEqual(obj.TypeId, 'Part::Feature')
            self.assertIsNone(obj.getParentGeoFeatureGroup())
            self.assertTrue(CAMUtil.isValidBaseObject(obj), obj.Name)
            expected = Part.Shape()
            expected.importBrepFromString(data['sourceParts'][index]['shape_brep'])
            expected.Placement = App.Placement(App.Vector(placement['x'] + 250 * (index % 2), 30, 0),
                                               App.Rotation(App.Vector(0, 0, 1), placement['rotation']))
            self.assertLess((obj.Shape.BoundBox.Center - expected.BoundBox.Center).Length, 1e-7)
            self.assertAlmostEqual(obj.Shape.Volume, expected.Volume)
            projected = top_view_shape(obj)
            self.assertAlmostEqual(projected.BoundBox.XMin, expected.BoundBox.XMin)
            self.assertAlmostEqual(projected.BoundBox.XMax, expected.BoundBox.XMax)
        self.assertEqual(len(result_parts(doc)), 4)

    def test_every_placed_3d_and_2d_feature_is_a_cam_candidate_after_refresh(self):
        importer, data = self.make_result()
        doc = importer.result_doc
        self.assertEqual(doc.SheetGroup_1.TypeId, 'App::DocumentObjectGroup')
        self.assertEqual(doc.SheetGroup_1.DisplayOffset.x, 250)
        self.assert_parts(doc, data)
        self.assertTrue(importer.import_result(data, show_summary=False))
        self.assertIs(importer.result_doc, doc)
        self.assert_parts(doc, data)

    def test_saved_results_and_bridge_roundtrip_keep_sheet_local_geometry(self):
        importer, data = self.make_result()
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'result.FCStd')
            importer.result_doc.saveAs(path)
            App.closeDocument(importer.result_doc.Name)
            doc = App.openDocument(path)
            self.assert_parts(doc, data)
            layout = load_result(SimpleNamespace())
            self.assertAlmostEqual(layout.parts[1]['shape'].BoundBox.XMax, 40)
            bridged = create_document(layout, languages.tr)
            for i in range(4):
                obj = bridged.getObject('Part_%d' % (i + 1))
                self.assertTrue(CAMUtil.isValidBaseObject(obj))
                original = doc.getObject('Nesting_test_%d' % i)
                self.assertLess((obj.Shape.BoundBox.Center - original.Shape.BoundBox.Center).Length, 1e-7)
            path = str(Path(directory) / 'bridges.FCStd')
            bridged.saveAs(path)
            App.closeDocument(bridged.Name)
            App.openDocument(path)
            recovered = load_result(SimpleNamespace())
            self.assertAlmostEqual(recovered.parts[1]['shape'].BoundBox.XMax, 40)

    def test_legacy_groups_and_new_annotation_offsets_are_supported(self):
        doc = App.newDocument('GroupCompatibility')
        legacy = doc.addObject('App::Part', 'LegacySheet')
        legacy.Placement.Base = App.Vector(150, 0, 0)
        modern = create_sheet_group(doc, 'SheetFolder', 'Sheet 2', 150)
        for group in (legacy, modern):
            obj = doc.addObject('Part::Feature', 'Outline')
            obj.Shape = Part.makePolygon([App.Vector(20, 0, 0), App.Vector(40, 0, 0)])
            add_to_sheet_group(group, obj)
            add_to_sheet_group(group, obj)
            self.assertAlmostEqual(obj.getGlobalPlacement().Base.x, 150)
            self.assertAlmostEqual(sheet_local_shape(obj).BoundBox.XMin, 20)
        self.assertTrue(CAMUtil.isValidBaseObject(obj))


if __name__ == '__main__':
    unittest.main()
