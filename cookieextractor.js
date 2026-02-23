// cookie-extractor.js
const fs = require('fs');
const puppeteer = require('puppeteer');

// Export cookies from a website
async function exportCookies(url, outputFile = 'cookies.json') {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'networkidle2' });

  // Grab cookies
  const cookies = await page.cookies();
  fs.writeFileSync(outputFile, JSON.stringify(cookies, null, 2));
  console.log(`Cookies saved to ${outputFile}`);

  await browser.close();
}

// Import cookies to a page
async function importCookies(url, inputFile = 'cookies.json') {
  const cookies = JSON.parse(fs.readFileSync(inputFile, 'utf-8'));
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  await page.setCookie(...cookies);
  await page.goto(url, { waitUntil: 'networkidle2' });

  console.log(`Cookies imported and page loaded: ${url}`);
  await browser.close();
}

// Example usage:
const action = process.argv[2]; // 'export' or 'import'
const url = process.argv[3];

if (!action || !url) {
  console.log('Usage: node cookie-extractor.js <export|import> <url>');
  process.exit(1);
}

if (action === 'export') {
  exportCookies(url);
} else if (action === 'import') {
  importCookies(url);
} else {
  console.log('Invalid action. Use "export" or "import".');
}
