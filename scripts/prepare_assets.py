"""Build a deterministic catalog without modifying the original SVG files."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NAMES = {
    'book': ('Книга', ['книга', 'знания', 'обучение', 'чтение']),
    'phone': ('Телефон', ['телефон', 'связь', 'технологии', 'онлайн']),
    'puzzle': ('Пазлы', ['пазлы', 'команда', 'решение', 'сотрудничество']),
    'coin': ('Монета', ['монета', 'деньги', 'инвестиции', 'экономия']),
    'headphones': ('Наушники', ['наушники', 'музыка', 'фокус', 'аудио']),
    'lamp': ('Лампа', ['лампа', 'свет', 'идея', 'работа']),
    'flowers': ('Цветы', ['цветы', 'подарок', 'забота', 'рост']),
    'wallet': ('Кошелек', ['кошелек', 'кошелёк', 'бюджет', 'финансы']),
    'folder': ('Папка', ['папка', 'документы', 'порядок', 'проект']),
    'pen': ('Ручка', ['ручка', 'письмо', 'творчество', 'план']),
}
SPECIAL = {
    ('L','flowers'): ('Group 2136136344', 'Group 2136136347'),
    ('S','flowers'): ('Group 2136136345', 'Group 2136136346'),
    ('S','book'): ('Group 2136136335', 'Group 2136136341'),
    ('S','folder'): ('Group 2136136337', 'Group 2136136342'),
    ('S','pen'): ('Group 2136136336', 'Group 2136136343'),
}

def inspect(size, name):
    path = ROOT / 'assets' / 'source' / size / (name + '.svg')
    raw = path.read_bytes()
    tree = ET.fromstring(raw)
    assert tree.tag == '{http://www.w3.org/2000/svg}svg', path
    ids = {n.attrib['id'] for n in tree.iter() if 'id' in n.attrib}
    for node in tree.iter():
        assert node.tag.split('}')[-1] not in {'image','script','foreignObject'}, path
        for key, value in node.attrib.items():
            assert not key.lower().startswith('on'), path
            if key.split('}')[-1] == 'href':
                assert value.startswith('#') and value[1:] in ids, path
    return {'path': path.relative_to(ROOT).as_posix(),
            'viewBox': [float(n) for n in tree.attrib['viewBox'].split()],
            'sha256': hashlib.sha256(raw).hexdigest(),
            'pathCount': sum(n.tag.endswith('}path') for n in tree.iter())}

def main():
    catalog = {'version': 1, 'objects': [], 'backgrounds': {}}
    for key, (label, tags) in NAMES.items():
        item = {'id': key, 'label': label, 'tags': tags, 'variants': {}}
        for size in ['L','S']:
            names = SPECIAL.get((size,key), (label, label+'-1'))
            item['variants'][size] = {role: inspect(size, name) for role,name in zip(['main','background'],names)}
            variants = item['variants'][size]
            assert variants['main']['viewBox'] == variants['background']['viewBox'], (key,size)
        catalog['objects'].append(item)
    for size in ['L','S']:
        catalog['backgrounds'][size] = {palette: inspect(size,name) for palette,name in
            [('purple','Фон'),('teal','Фон-1'),('peach','Фон-2')]}
    (ROOT/'assets/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Validated: 10 objects, 40 variants, 6 backgrounds; source bytes preserved.')

if __name__ == '__main__':
    main()
