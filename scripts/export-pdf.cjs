const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

async function main() {
  const root = path.resolve(__dirname, '..');
  const output = path.join(root, 'output', 'pdf');
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    for (const [folder, filename, label] of [
      ['resume', '이지민_경력기술서.pdf', '이지민 · QA Engineer'],
      ['qa-portfolio', '이지민_포트폴리오.pdf', '이지민 · QA Portfolio'],
    ]) {
      if (process.argv.includes('--resume') && folder !== 'resume') continue;
      const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
      await page.goto(pathToFileURL(path.join(root, 'site', folder, 'index.html')).href);
      await page.emulateMedia({ media: 'print' });
      await page.evaluate(async () => {
        document.querySelectorAll('details').forEach(el => { el.open = true; });
        document.querySelectorAll('a[href^="assets/"]').forEach(el => {
          el.href = new URL(el.getAttribute('href'), 'https://duo2208.github.io/resume/qa-portfolio/').href;
        });
        await document.fonts.ready;
      });
      await page.pdf({
        path: path.join(output, filename),
        format: 'A4', preferCSSPageSize: true, printBackground: true,
        displayHeaderFooter: true,
        headerTemplate: '<span></span>',
        footerTemplate: `<div style="width:100%;padding:0 15mm;font-family:Arial,sans-serif;font-size:8px;color:#667085;display:flex;justify-content:space-between"><span>${label}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`,
      });
      console.log(filename);
      await page.close();
    }
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
