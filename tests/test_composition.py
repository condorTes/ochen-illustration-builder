import hashlib
import unittest
import xml.etree.ElementTree as ET
from fastapi import HTTPException
from app.main import CATALOG, OBJECTS, ROOT, Compose, Scene, compose_scene, render_svg


class CompositionTests(unittest.TestCase):
    def test_source_hashes(self):
        for obj in CATALOG['objects']:
            for variants in obj['variants'].values():
                for variant in variants.values():
                    self.assertEqual(hashlib.sha256((ROOT/variant['path']).read_bytes()).hexdigest(),variant['sha256'])

    def test_layout_stays_inside_canvas(self):
        for size in ['L','S']:
            for width,height in [(1200,630),(1000,1000),(630,1200)]:
                for count in range(1,11):
                    for layout in ['balanced','diagonal','title']:
                        scene=compose_scene(Compose(ids=list(OBJECTS)[:count],width=width,height=height,size=size,layout=layout))
                        for item in scene.items:
                            w,h=OBJECTS[item.id]['variants'][size]['main']['viewBox'][2:]
                            self.assertGreaterEqual(item.x,0)
                            self.assertGreaterEqual(item.y,0)
                            self.assertLessEqual(item.x+w*scene.scale,width+.01)
                            self.assertLessEqual(item.y+h*scene.scale,height+.01)

    def test_geometry_preserved_across_palettes_and_duplicates(self):
        scene=compose_scene(Compose(ids=['book','lamp','phone']))
        scene.items.append(scene.items[0].model_copy())
        scene.items[1].role='background'
        for palette in ['purple','teal','peach']:
            scene.palette=palette
            root=ET.fromstring(render_svg(scene))
            groups=[n for n in root if 'data-index' in n.attrib]
            self.assertEqual(len(groups),4)
            for item,group in zip(scene.items,groups):
                source=ET.parse(ROOT/OBJECTS[item.id]['variants'][scene.size][item.role]['path'])
                paths=lambda tree:[n.get('d') for n in tree.iter() if n.tag.endswith('}path')]
                self.assertEqual(paths(source),paths(group))
            self.assertFalse(any(n.tag.endswith('}image') for n in root.iter()))
            ids=[n.get('id') for n in root.iter() if n.get('id')]
            self.assertEqual(len(ids),len(set(ids)))

    def test_unknown_objects_rejected(self):
        for req in [Compose(names='дракон'),Compose(ids=['missing']),Compose()]:
            with self.assertRaises(HTTPException):
                compose_scene(req)

    def test_names_and_json_roundtrip(self):
        scene=compose_scene(Compose(names='Книга, кошелёк, лампа'))
        self.assertEqual([i.id for i in scene.items],['book','wallet','lamp'])
        self.assertEqual(Scene.model_validate_json(scene.model_dump_json()),scene)

if __name__=='__main__':
    unittest.main()
