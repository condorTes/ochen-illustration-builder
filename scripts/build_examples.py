"""Rebuild submission examples from original vectors, without API calls."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.main import Compose, compose_scene, render_svg

CASES=[
    ('learning', ['book','coin','pen'],1200,630,'L','purple',{'pen':'background'}),
    ('teamwork', ['phone','puzzle','folder'],1000,1000,'L','teal',{'folder':'background'}),
    ('focus', ['headphones','lamp','book'],630,1200,'S','peach',{'book':'background','lamp':'background'}),
]
for name,ids,w,h,size,palette,roles in CASES:
    scene=compose_scene(Compose(ids=ids,width=w,height=h,size=size,palette=palette,layout='cluster'))
    for item in scene.items:
        item.role=roles.get(item.id,'main')
    scene.items.sort(key=lambda i:i.role=='main')
    (ROOT/'examples'/f'{name}.json').write_text(json.dumps(scene.model_dump(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'examples'/f'{name}.svg').write_bytes(render_svg(scene).encode('utf-8'))
    print(name)
