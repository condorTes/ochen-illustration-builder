import unittest
import xml.etree.ElementTree as ET
from pydantic import ValidationError
from app.main import Compose, Palette, Adapt, adapt, compose_scene, render_svg


class EditorTests(unittest.TestCase):
    def test_format_preserves_duplicates_layers_roles_and_angles(self):
        scene=compose_scene(Compose(ids=['book','coin']))
        scene.items[0].angle=35
        scene.items[1].role='background'
        scene.items.append(scene.items[0].model_copy())
        scene.custom_palette=Palette(background=['#111111','#222222','#333333'],objects=['#444444','#555555','#666666'])
        result=adapt(Adapt(scene=scene,width=630,height=1200,size='S'))['scene']
        self.assertEqual([(i['id'],i['role'],i['angle']) for i in result['items']],
                         [(i.id,i.role,i.angle) for i in scene.items])
        self.assertEqual(result['custom_palette'],scene.custom_palette.model_dump())
        self.assertEqual(scene.size,'L')

    def test_custom_background_never_uses_object_colors(self):
        scene=compose_scene(Compose(ids=['flowers','book']))
        scene.custom_palette=Palette(background=['#112233','#334455','#556677'],objects=['#778899','#99AABB','#BBCCDD'])
        scene.items[0].role='background'
        for palette in ['purple','teal','peach']:
            scene.palette=palette
            root=ET.fromstring(render_svg(scene))
            bg=list(root)[1]
            colors={v.lower() for n in bg.iter() for k,v in n.attrib.items() if k in ['fill','stroke']}
            self.assertTrue(colors.isdisjoint({c.lower() for c in scene.custom_palette.objects}))
            self.assertIn('#112233',colors)

    def test_palette_rejects_css_and_wrong_length(self):
        for colors in [['red']*3,['#123456'],['url(https://example.com)']*3]:
            with self.assertRaises(ValidationError):
                Palette(background=colors,objects=['#123456']*3)
