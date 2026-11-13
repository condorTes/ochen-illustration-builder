"""HTTP checks against an already-running local instance; never calls the AI API."""
import json
import sys
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import xml.etree.ElementTree as ET

base = sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8000'

def get(path):
    with urlopen(base+path, timeout=10) as response:
        return response.read()

def post(path, data):
    request=Request(base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
    with urlopen(request,timeout=10) as response:
        return response.read()

assert b'<!doctype html>' in get('/')
assert len(json.loads(get('/api/catalog'))['objects'])==10
for name in ['learning','teamwork','focus']:
    data=json.loads(get('/api/examples/'+name))
    exported=post('/api/export',data['scene'])
    root=ET.fromstring(exported)
    assert len([node for node in root if 'data-index' in node.attrib])==3
scene=json.loads(post('/api/compose',{'names':'Книга, лампа'}))['scene']
assert len(scene['items'])==2
scene=json.loads(post('/api/adapt',{'scene':scene,'width':630,'height':1200,'size':'S'}))['scene']
assert scene['size']=='S'
post('/api/render',scene)
post('/api/scene',scene)
post('/api/palette',{'background':['#112233']*3,'objects':['#445566']*3})
try:
    post('/api/compose',{'names':'несуществующий объект'})
    raise AssertionError('Unknown object accepted')
except HTTPError as error:
    assert error.code==422
print('HTTP smoke checks passed: page, catalog, 3 examples, compose, adapt, render, import, palette, export, rejection.')
