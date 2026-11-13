// Editor persistence and non-destructive format changes.
let snapshots = [null], cursor = 0, customPalette = null, travelling = false;
const clone = value => value == null ? null : JSON.parse(JSON.stringify(value));
const emptyCanvas = $('canvas').innerHTML;
const baseDisplay = display, baseControls = controls;
function saveLocal() {
  try { scene ? localStorage.setItem('ochen-scene-v1', JSON.stringify(scene)) : localStorage.removeItem('ochen-scene-v1'); }
  catch { status('Автосохранение недоступно. Используйте «Сохранить проект».',true); }
}
function remember() {
  if (!travelling && JSON.stringify(scene) !== JSON.stringify(snapshots[cursor])) {
    snapshots = snapshots.slice(0,cursor+1);
    snapshots.push(clone(scene));
    if (snapshots.length>60) snapshots.shift();
    cursor=snapshots.length-1;
  }
  saveLocal();
}
controls = function () {
  baseControls();
  $('undo').disabled=busy||cursor===0;
  $('redo').disabled=busy||cursor===snapshots.length-1;
  for(const id of ['saveScene','clearScene']) $(id).disabled=busy||!scene;
  for(const id of ['format','size','layout','palette','openScene','loadPalette','resetPalette']) $(id).disabled=busy;
  $('up').disabled=busy||selected<0||selected===scene?.items.length-1;
  $('down').disabled=busy||selected<=0;
  $('canvas').classList.toggle('busy',busy);
  $('editor').disabled=busy||selected<0;
  $('export').disabled=busy||!scene||!scene.items.length;
  $('compose').disabled=busy;
  document.querySelectorAll('.demo').forEach(b=>b.disabled=busy);
};
display = function(svg) { remember(); baseDisplay(svg); };
function syncScene() {
  if(!scene)return;
  const format=`${scene.width},${scene.height}`;
  if(![...$('format').options].some(o=>o.value===format)) $('format').add(new Option(`${scene.width} × ${scene.height}`,format));
  $('format').value=format;$('size').value=scene.size;$('palette').value=scene.palette;
  customPalette=scene.custom_palette||null; paletteView(); library();
}
function paletteView() {
  $('paletteName').textContent=customPalette?customPalette.name:'Выбрана палитра из библиотеки';
  $('resetPalette').hidden=!customPalette;$('swatches').replaceChildren();
  if(customPalette)[...customPalette.background,...customPalette.objects].forEach((color,i)=>{
    const swatch=document.createElement('span');swatch.style.background=color;
    swatch.title=`${i<3?'Фон':'Предмет'}: ${color}`;$('swatches').append(swatch);
  });
}
async function travel(delta) {
  if(busy||cursor+delta<0||cursor+delta>=snapshots.length)return;
  busy=true;++renderVersion;cursor+=delta;scene=clone(snapshots[cursor]);selected=-1;travelling=true;controls();
  try {syncScene();saveLocal();if(scene)await render();else{$('canvas').innerHTML=emptyCanvas;fitCanvas();controls();}}
  finally{travelling=false;busy=false;controls();}
  status(delta<0?'Действие отменено.':'Действие повторено.');
}
$('undo').onclick=()=>travel(-1);$('redo').onclick=()=>travel(1);
document.addEventListener('keydown',e=>{
  if(['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName))return;
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();travel(e.shiftKey?1:-1);}
});
async function adaptScene() {
  if(!scene){library();return;}if(busy)return;
  busy=true;++renderVersion;controls();
  try{const {width,height,size}=config();const data=await(await request('/api/adapt',{scene,width,height,size})).json();
    scene=data.scene;display(data.svg);status('Формат обновлён. Повороты, состояния и дубликаты сохранены.');
  }catch(e){status(e.message,true);}finally{busy=false;syncScene();controls();}
}
$('format').onchange=$('size').onchange=adaptScene;
$('layout').onchange=async()=>{
  if(!scene||busy)return;
  busy=true;++renderVersion;controls();
  try{const data=await(await request('/api/relayout',{scene,layout:$('layout').value})).json();
    scene=data.scene;display(data.svg);status('Новая раскладка готова. Слои и состояния сохранены.');
  }catch(e){status(e.message,true);}finally{busy=false;controls();}
};
document.querySelectorAll('.demo').forEach(button=>button.onclick=async()=>{
  if(busy)return;busy=true;++renderVersion;controls();
  try{const response=await fetch('/api/examples/'+button.dataset.example);
    if(!response.ok)throw Error('Не удалось открыть пример.');
    const data=await response.json();scene=data.scene;selected=-1;syncScene();display(data.svg);
    status('Открыт готовый пример. Это сохранённая композиция, без запроса к ИИ. Можно редактировать.');
  }catch(e){status(e.message,true);}finally{busy=false;controls();}
});
function downloadJSON(value,name){
  const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function readJSON(input){const file=input.files[0];input.value='';if(!file)return null;
  if(file.size>100000)throw Error('Максимальный размер файла — 100 КБ.');
  try{return JSON.parse(await file.text());}catch{throw Error('Не удалось прочитать JSON. Используйте сохранённый проект или образец палитры.');}
}
$('saveScene').onclick=()=>downloadJSON(scene,'ochen-project.json');
$('openScene').onclick=()=>$('sceneFile').click();
$('sceneFile').onchange=async()=>{
  try{const json=await readJSON($('sceneFile'));if(!json)return;busy=true;++renderVersion;controls();
    const data=await(await request('/api/scene',json)).json();scene=data.scene;selected=-1;syncScene();display(data.svg);status('Проект открыт.');
  }catch(e){status(e.message,true);}finally{busy=false;controls();}
};
$('clearScene').onclick=()=>{++renderVersion;scene=null;selected=-1;remember();$('canvas').innerHTML=emptyCanvas;$('dimensions').textContent='Холст пуст';fitCanvas();controls();status('Холст очищен. Действие можно отменить.');};
$('loadPalette').onclick=()=>$('paletteFile').click();
$('paletteExample').onclick=()=>downloadJSON({name:'Моя палитра',background:['#D7CDF5','#AA9BF0','#7864D7'],objects:['#F9ECB0','#F9A3AA','#FFE3E1']},'ochen-palette.json');
$('paletteFile').onchange=async()=>{
  try{const json=await readJSON($('paletteFile'));if(!json)return;busy=true;++renderVersion;controls();
    customPalette=await(await request('/api/palette',json)).json();
    if(scene){scene.custom_palette=clone(customPalette);await render();}paletteView();
    status('Палитра применена. Первые три цвета — фон, остальные — основные предметы.');
  }catch(e){status(e.message,true);}finally{busy=false;controls();}
};
$('resetPalette').onclick=()=>{customPalette=null;if(scene){scene.custom_palette=null;render();}paletteView();};
$('palette').onchange=()=>{customPalette=null;if(scene){scene.palette=$('palette').value;scene.custom_palette=null;render();}paletteView();};
// Wait for the existing catalog request without starting a second initialization.
let restoreAttempts=0;
async function restore(){
  if(!catalog){if(restoreAttempts++<100)setTimeout(restore,150);return;}
  controls();let saved;try{saved=localStorage.getItem('ochen-scene-v1');}catch{return;}
  if(!saved)return;
  try{busy=true;controls();const data=await(await request('/api/scene',JSON.parse(saved))).json();
    scene=data.scene;syncScene();display(data.svg);status('Восстановлен последний проект из этого браузера.');
  }catch{status('Не удалось восстановить прошлую сцену. Можно открыть сохранённый проект.',true);}
  finally{busy=false;controls();}
}
restore();
