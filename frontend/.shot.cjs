const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:\\Users\\Micro\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1254\\chrome-headless-shell-win64\\chrome-headless-shell.exe',
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
  await page.goto('http://127.0.0.1:3000', { waitUntil: 'load', timeout: 60000 });
  await page.waitForTimeout(9000);
  await page.screenshot({ path: 'C:\\Users\\Micro\\AppData\\Local\\Temp\\opencode\\tela-app.png', fullPage: false });
  await browser.close();
  console.log('SHOT_OK');
})().catch((e) => { console.error('SHOT_ERR: ' + e.message); process.exit(1); });
