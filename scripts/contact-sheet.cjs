const fs = require('node:fs');
const path = require('node:path');
const sharp = require(process.env.SHARP_MODULE || 'sharp');
(async () => {
 for (const size of ['L', 'S']) {
  const files = fs.readdirSync(`assets/source/${size}`).filter(f => f.endsWith('.svg'));
  const layers = [];
  for (let i=0; i<files.length; i++) {
   const x=(i%4)*320, y=Math.floor(i/4)*260;
   const input = fs.readFileSync(path.join('assets/source',size,files[i]));
   layers.push({input:await sharp(input).resize(290,210,{fit:'inside'}).png().toBuffer(),left:x+10,top:y+5});
   const label=files[i].replace(/&/g,'&amp;').replace(/</g,'&lt;');
   layers.push({input:Buffer.from(`<svg width="320" height="30"><text x="8" y="22" font-size="15" font-family="Arial">${label}</text></svg>`),left:x,top:y+225});
  }
  await sharp({create:{width:1280,height:Math.ceil(files.length/4)*260,channels:4,background:'white'}}).composite(layers).png().toFile(`docs/contact-${size}.png`);
 }
})();
