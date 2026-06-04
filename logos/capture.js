const puppeteer = require('puppeteer-core');
const path = require('path');

const CHROME = process.env.HOME + '/.cache/puppeteer/chrome/linux-149.0.7827.54/chrome-linux64/chrome';

// args: mode [htmlfile] [durationSeconds]
const mode = process.argv[2] || 'shots';
const htmlFile = process.argv[3] || 'flow_animation.html';
// CHROME path below is from `npx @puppeteer/browsers install chrome@stable`; re-run if missing.
const durArg = parseFloat(process.argv[4]) || 4.7;
const FILE = 'file://' + path.resolve(__dirname, htmlFile) + '?capture=1';

async function seek(page, ms) {
  await page.evaluate((t) => {
    document.getAnimations().forEach(a => { a.pause(); a.currentTime = t; });
  }, ms);
}

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: ['--no-sandbox', '--force-color-profile=srgb', '--hide-scrollbars'],
    defaultViewport: { width: 1080, height: 1920, deviceScaleFactor: 1 },
  });
  const page = await browser.newPage();
  await page.goto(FILE, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 200));

  if (mode === 'shots') {
    const times = [700, 1600, 2050, 2500, 3000, 3600, 4400];
    for (const t of times) {
      await seek(page, t);
      await new Promise(r => setTimeout(r, 60));
      const f = `shot_${String(t).padStart(4,'0')}.png`;
      await page.screenshot({ path: f });
      console.log('wrote', f);
    }
  } else {
    const fps = 30, dur = durArg;         // seconds
    const total = Math.round(fps * dur);
    // optional batch range: argv[5]=startFrame, argv[6]=count
    const start = parseInt(process.argv[5]) || 0;
    const count = parseInt(process.argv[6]) || (total - start);
    const end = Math.min(start + count, total);
    for (let i = start; i < end; i++) {
      const t = (i / fps) * 1000;
      await seek(page, t);
      const f = `frames/f_${String(i).padStart(4,'0')}.png`;
      await page.screenshot({ path: f });
    }
    console.log('wrote frames', start, 'to', end - 1, 'of', total);
  }

  await browser.close();
})();
