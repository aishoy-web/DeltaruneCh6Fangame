"""Regression tests for scr_layer_tilemap_get_id_fixed.py."""
import unittest

from scr_layer_tilemap_get_id_fixed import scr_layer_tilemap_get_id_fixed


class MockLayerAPI:
    def __init__(self, elements, types):
        self.elements = elements
        self.types = types
        self.layer_requests = []
        self.type_requests = []

    def layer_get_all_elements(self, layer):
        self.layer_requests.append(layer)
        return self.elements

    def layer_get_element_type(self, element_id):
        self.type_requests.append(element_id)
        return self.types[element_id]


class LayerTilemapGetIdFixedTests(unittest.TestCase):
    def test_first_tilemap_found_in_order(self):
        api = MockLayerAPI([11, 22, 33, 44], {11: 2, 22: 5, 33: 5, 44: 1})
        result = scr_layer_tilemap_get_id_fixed(api, 'GroundTiles')
        self.assertEqual(result, 22)
        self.assertEqual(api.layer_requests, ['GroundTiles'])
        self.assertEqual(api.type_requests, [11, 22])

    def test_none_found(self):
        api = MockLayerAPI([11, 22], {11: 1, 22: 3})
        self.assertEqual(scr_layer_tilemap_get_id_fixed(api, 7), -1)
        self.assertEqual(api.type_requests, [11, 22])

    def test_empty_layer(self):
        api = MockLayerAPI([], {})
        self.assertEqual(scr_layer_tilemap_get_id_fixed(api, 'empty'), -1)
        self.assertEqual(api.type_requests, [])

    def test_first_element_matches(self):
        api = MockLayerAPI([91, 92], {91: 5, 92: 5})
        self.assertEqual(scr_layer_tilemap_get_id_fixed(api, 0), 91)
        self.assertEqual(api.type_requests, [91])

    def test_generator_elements(self):
        api = MockLayerAPI((x for x in (4, 5)), {4: 0, 5: 5})
        self.assertEqual(scr_layer_tilemap_get_id_fixed(api, 'Tiles'), 5)


if __name__ == '__main__':
    unittest.main()
