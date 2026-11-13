import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from app.main import (Compose, Scene, Relayout, OBJECTS, ROOT, compose_scene,
                      render_svg, relayout, example)


class SubmissionTests(unittest.TestCase):
    def test_cluster_all_counts_and_formats(self):
        for size in ['L','S']:
            for w,h in [(1200,630),(1000,1000),(630,1200)]:
                for n in range(1,11):
                    scene=compose_scene(Compose(ids=list(OBJECTS)[:n],width=w,height=h,size=size))
                    for item in scene.items:
                        ow,oh=OBJECTS[item.id]['variants'][size]['main']['viewBox'][2:]
                        self.assertGreaterEqual(item.x,0)
                        self.assertGreaterEqual(item.y,0)
                        self.assertLessEqual(item.x+ow*scene.scale,w+.01)
                        self.assertLessEqual(item.y+oh*scene.scale,h+.01)

    def test_relayout_preserves_edits(self):
        scene=compose_scene(Compose(ids=['book','lamp']))
        scene.items[0].angle=25
        scene.items[1].role='background'
        scene.items.append(scene.items[0].model_copy())
        result=relayout(Relayout(scene=scene,layout='title'))['scene']
        self.assertEqual([(i['id'],i['role'],i['angle']) for i in result['items']],
                         [(i.id,i.role,i.angle) for i in scene.items])

    def test_examples_are_reproducible_standalone_vectors(self):
        for name in ['learning','teamwork','focus']:
            data=example(name)
            self.assertEqual(data['svg'],(ROOT/'examples'/f'{name}.svg').read_text(encoding='utf-8'))
            root=ET.fromstring(data['svg'])
            self.assertEqual(len([n for n in root if 'data-index' in n.attrib]),3)
            for node in root.iter():
                self.assertNotIn(node.tag.split('}')[-1],['image','script','foreignObject'])
                for key,value in node.attrib.items():
                    if key.endswith('href'):self.assertTrue(value.startswith('#'))
            # Re-edit a parsed project and export again, retaining the original paths.
            scene=Scene.model_validate(data['scene']);scene.items[0].angle=30
            edited=ET.fromstring(render_svg(scene))
            paths=lambda tree:[n.get('d') for n in tree.iter() if n.tag.endswith('}path')]
            self.assertEqual(paths(root),paths(edited))
