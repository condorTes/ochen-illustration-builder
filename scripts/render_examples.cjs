// Optional documentation tool. Not required to run the application.
const fs = require('node:fs');
const sharp = require(process.env.SHARP_MODULE || 'sharp');
(async () => {
  for (const name of ['learning','teamwork','focus']) {
    await sharp(fs.readFileSync(`examples/${name}.svg`))
      .resize({width:900,height:900,fit:'inside'}).png().toFile(`docs/${name}.png`);
  }
})();
