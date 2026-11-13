from pathlib import Path
import json
import math
import re
import xml.etree.ElementTree as ET

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated
from typing import Literal
from app.ai import select_objects, settings

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / 'assets/catalog.json').read_text(encoding='utf-8'))
OBJECTS = {item['id']: item for item in CATALOG['objects']}
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
app = FastAPI(title='Очень · конструктор иллюстраций')


class Item(BaseModel):
    id: str
    x: float = Field(ge=-10000, le=10000, allow_inf_nan=False)
    y: float = Field(ge=-10000, le=10000, allow_inf_nan=False)
    angle: float = Field(default=0, ge=-360, le=360, allow_inf_nan=False)
    role: Literal['main', 'background'] = 'main'


HexColor = Annotated[str, Field(pattern=r'^#[0-9a-fA-F]{6}$')]


class Palette(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(default='Моя палитра', max_length=60)
    background: list[HexColor] = Field(min_length=3, max_length=3)
    objects: list[HexColor] = Field(min_length=3, max_length=3)


class Scene(BaseModel):
    custom_palette: Palette | None = None
    width: int = Field(default=1200, ge=200, le=4000)
    height: int = Field(default=630, ge=200, le=4000)
    size: Literal['L', 'S'] = 'L'
    palette: Literal['purple', 'teal', 'peach'] = 'purple'
    scale: float = Field(default=.35, gt=0, le=5, allow_inf_nan=False)
    items: list[Item] = Field(default_factory=list, max_length=30)


class Compose(BaseModel):
    idea: str = Field(default='', max_length=600)
    names: str = Field(default='', max_length=1000)
    ids: list[str] = Field(default_factory=list, max_length=10)
    width: int = Field(default=1200, ge=200, le=4000)
    height: int = Field(default=630, ge=200, le=4000)
    size: Literal['L', 'S'] = 'L'
    palette: Literal['purple', 'teal', 'peach'] = 'purple'
    layout: Literal['balanced', 'diagonal', 'title'] = 'balanced'


def dimensions(key, size):
    if key not in OBJECTS:
        raise HTTPException(422, f'Неизвестный предмет: {key}')
    return OBJECTS[key]['variants'][size]['main']['viewBox'][2:]


def compose_scene(req):
    ids = list(dict.fromkeys(req.ids))
    unknown = []
    if req.names.strip():
        for name in re.split(r'[,;\n]+', req.names.lower()):
            name = name.strip().replace('ё', 'е')
            if not name:
                continue
            found = next((key for key, obj in OBJECTS.items() if name in
                          [key, obj['label'].lower().replace('ё','е')] +
                          [t.replace('ё','е') for t in obj['tags']]), None)
            if found:
                if found not in ids:
                    ids.append(found)
            else:
                unknown.append(name)
    if unknown:
        raise HTTPException(422, 'Не найдены: ' + ', '.join(unknown) + '. Выберите предметы из библиотеки.')
    if not ids:
        raise HTTPException(422, 'Выберите хотя бы один предмет.')
    if len(ids) > 10:
        raise HTTPException(422, 'Для автоматической сборки доступно до 10 предметов.')
    dims = [dimensions(key, req.size) for key in ids]
    # Equal scaling for every object preserves the source relative proportions.
    left = req.width * (.36 if req.layout == 'title' else .06)
    top = req.height * .08
    area_w, area_h = req.width-left-req.width*.06, req.height*.84
    best = None
    for cols in range(1,len(ids)+1):
        rows = math.ceil(len(ids)/cols)
        row_heights = [max(h for w,h in dims[r*cols:(r+1)*cols]) for r in range(rows)]
        row_widths = [sum(w for w,h in dims[r*cols:(r+1)*cols]) for r in range(rows)]
        gap = 90 if req.size == 'L' else 45
        scale = min(area_w/max(w+gap*(min(cols,len(ids)-r*cols)-1) for r,w in enumerate(row_widths)),
                    area_h/(sum(row_heights)+gap*(rows-1)))
        if best is None or scale > best[0]:
            best = (scale,cols,row_heights,row_widths,gap)
    scale,cols,heights,widths,gap = best
    if req.layout == 'diagonal':
        scale *= .85
    items=[]
    y=top+(area_h-(sum(heights)+gap*(len(heights)-1))*scale)/2
    for r,rh in enumerate(heights):
        count=min(cols,len(ids)-r*cols)
        x=left+(area_w-(widths[r]+gap*(count-1))*scale)/2
        for j in range(count):
            index=r*cols+j
            w,h=dims[index]
            offset=(j-(count-1)/2)*req.height*.05 if req.layout=='diagonal' else 0
            items.append(Item(id=ids[index],x=x,y=y+(rh-h)*scale/2+offset))
            x+=(w+gap)*scale
        y+=(rh+gap)*scale
    return Scene(width=req.width,height=req.height,size=req.size,palette=req.palette,scale=scale,items=items)


COLOR_MAPS = {
    'purple': {},
    'peach': {'#d7cdf5':'#FDD7B9','#aa9bf0':'#FAC896','#7864d7':'#D27532',
              '#f9ecb0':'#F9ECB0','#f9a3aa':'#80DADA','#ffe3e1':'#BEEBEB'},
    'teal': {'#d7cdf5':'#BEEBEB','#aa9bf0':'#80DADA','#7864d7':'#5ABEBE',
             '#f9ecb0':'#FFD4F2','#f9a3aa':'#6D7BFC','#ffe3e1':'#B6C6FE'},
}


def load_svg(relative, prefix, palette=None, custom_map=None):
    root=ET.fromstring((ROOT/relative).read_bytes())
    mapping={n.attrib['id']: prefix+n.attrib['id'] for n in root.iter() if 'id' in n.attrib}
    for node in root.iter():
        for attr,value in list(node.attrib.items()):
            if attr=='id':
                node.set(attr,mapping[value])
            else:
                for old,new in mapping.items():
                    value=value.replace(f'url(#{old})', f'url(#{new})')
                    if attr.endswith('href') and value=='#'+old:
                        value='#'+new
                if attr in ('fill','stroke'):
                    colors=custom_map if custom_map is not None else COLOR_MAPS.get(palette,{})
                    value=colors.get(value.lower(),value)
                node.set(attr,value)
    return root


def render_svg(scene):
    root=ET.Element(f'{{{NS}}}svg', {'width':str(scene.width),'height':str(scene.height),
                    'viewBox':f'0 0 {scene.width} {scene.height}', 'fill':'none'})
    ET.SubElement(root,f'{{{NS}}}title').text='Композиция · очень'
    custom=None
    if scene.custom_palette:
        custom=dict(zip(['#d7cdf5','#aa9bf0','#7864d7','#f9ecb0','#f9a3aa','#ffe3e1'],
                        scene.custom_palette.background+scene.custom_palette.objects))
    bg_colors={
        'purple':['#d7cdf5','#aa9bf0','#7864d7'],
        'teal':['#beebeb','#80dada','#5abebe'],
        'peach':['#fdd7b9','#fac896','#d27532']}[scene.palette]
    bg_map=dict(zip(bg_colors,scene.custom_palette.background)) if custom is not None else None
    bg=load_svg(CATALOG['backgrounds'][scene.size][scene.palette]['path'],'bg-',custom_map=bg_map)
    # Crop, never stretch, the original square background to the chosen format.
    bg.set('width',str(scene.width)); bg.set('height',str(scene.height))
    bg.set('preserveAspectRatio','xMidYMid slice')
    root.append(bg)
    for index,item in enumerate(scene.items):
        w,h=dimensions(item.id,scene.size)
        variant=OBJECTS[item.id]['variants'][scene.size][item.role]
        source=load_svg(variant['path'],f'item-{index}-',scene.palette,custom)
        group=ET.SubElement(root,f'{{{NS}}}g',{
            'id':f'object-{index}-{item.id}', 'data-index':str(index),
            'transform':f'translate({item.x} {item.y}) scale({scene.scale}) rotate({item.angle} {w/2} {h/2})'})
        ET.SubElement(group,f'{{{NS}}}title').text=OBJECTS[item.id]['label']
        # Preserve root presentation attributes such as fill="none" on nested SVG.
        source.set('width',str(w)); source.set('height',str(h))
        source.set('overflow','visible')
        group.append(source)
    return ET.tostring(root,encoding='unicode')


@app.get('/api/catalog')
def catalog():
    return CATALOG


class Adapt(BaseModel):
    scene: Scene
    width: int = Field(ge=200, le=4000)
    height: int = Field(ge=200, le=4000)
    size: Literal['L','S']


@app.post('/api/adapt')
def adapt(req: Adapt):
    scene=req.scene.model_copy(deep=True)
    factor=min(req.width/scene.width,req.height/scene.height)
    source_factor=2 if scene.size=='L' and req.size=='S' else .5 if scene.size=='S' and req.size=='L' else 1
    scale=scene.scale*factor*source_factor
    if not 0<scale<=5:
        raise HTTPException(422,'Для этого размера масштаб слишком велик. Выберите другой формат.')
    for item in scene.items:
        ow,oh=dimensions(item.id,scene.size)
        nw,nh=dimensions(item.id,req.size)
        cx=(item.x+ow*scene.scale/2)/scene.width
        cy=(item.y+oh*scene.scale/2)/scene.height
        item.x=cx*req.width-nw*scale/2
        item.y=cy*req.height-nh*scale/2
    scene.width,scene.height,scene.size,scene.scale=req.width,req.height,req.size,scale
    scene=Scene.model_validate(scene.model_dump())
    return {'scene':scene.model_dump(),'svg':render_svg(scene)}


@app.post('/api/scene')
def validate_scene(scene: Scene):
    return {'scene':scene.model_dump(),'svg':render_svg(scene)}


@app.post('/api/palette')
def validate_palette(palette: Palette):
    return palette


@app.get('/api/capabilities')
def capabilities():
    return {'ai_available': bool(settings()['GROQ_API_KEY'])}


@app.post('/api/compose')
def compose(req: Compose):
    selection = None
    if req.idea.strip():
        selection = select_objects(req.idea, OBJECTS)
        req = req.model_copy(update={'names':'','ids':[i.id for i in selection.items]})
    scene=compose_scene(req)
    if selection:
        roles = {i.id:i.role for i in selection.items}
        for item in scene.items:
            item.role = roles[item.id]
        scene.items.sort(key=lambda item:item.role=='main')
    return {'scene':scene.model_dump(), 'svg':render_svg(scene),
            'explanation':selection.explanation if selection else None}


@app.post('/api/render')
def render(scene: Scene):
    return Response(render_svg(scene),media_type='image/svg+xml')


@app.post('/api/export')
def export(scene: Scene):
    return Response(render_svg(scene),media_type='image/svg+xml',
                    headers={'Content-Disposition':'attachment; filename="ochen-composition.svg"'})


@app.get('/')
def index():
    return FileResponse(ROOT/'web/index.html')


app.mount('/web',StaticFiles(directory=ROOT/'web'),name='web')
app.mount('/assets',StaticFiles(directory=ROOT/'assets'),name='assets')
