// Holt für jeden Betrieb einen Screenshot der Startseite und, wenn erkennbar, das Logo.
// Aufruf: node previews.mjs sites.json <ausgabe-ordner>   (danach: python3 images.py <ausgabe-ordner>)
// Braucht Playwright mit Chromium; ein HTTPS_PROXY aus der Umgebung wird übernommen.
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const [sitesFile, out] = process.argv.slice(2);
const sites = JSON.parse(readFileSync(sitesFile, 'utf8'));
const only = process.env.ONLY ? new Set(process.env.ONLY.split(',')) : null;
mkdirSync(out, { recursive: true });

const CONSENT = /^\s*((alle\s+)?(cookies\s+)?(akzeptieren|zustimmen|annehmen|zulassen|erlauben)(\s+und\s+(schließen|weiter))?|alle\s+cookies(\s+(akzeptieren|zulassen|erlauben))?|(ja,?\s*)?(ich\s+)?(stimme\s+zu|bin\s+einverstanden|einverstanden)|ok|okay|verstanden|alles\s+klar|accept(\s+all)?(\s+cookies)?|allow\s+all|alle\s+auswählen)\s*!?\s*$/i;
const HIDE = `#usercentrics-root,#CybotCookiebotDialog,#BorlabsCookieBox,#cookiebanner,#cookie-banner,#cookie-notice,#cookie-law-info-bar,
  .cmplz-cookiebanner,.cc-window,.cookie-banner,.cookie-notice,.cookie-consent,.cookieconsent,#onetrust-banner-sdk,.borlabs-cookie,
  #moove_gdpr_cookie_info_bar,.wpcc-container,.cky-consent-container,.cky-overlay,#cmplz-cookiebanner-container,.ccm-root,#ccm-widget,
  [id^="sp_message_container"],.fc-consent-root,#gdpr-cookie-message,.klaro,.cookies-eu-banner,#jimdo-cookie-notice,.cookie-bar,#cookie-bar
  {display:none!important}`;

const findLogo = () => {
  const vis = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0.05; };
  const text = el => [el.id, el.className?.baseVal ?? el.className, el.getAttribute('alt'), el.getAttribute('src'), el.getAttribute('title'),
    el.getAttribute('aria-label'), el.closest('a')?.className, el.parentElement?.className, el.parentElement?.id].join(' ');
  let best = null;
  for (const el of document.querySelectorAll('img, svg')) {
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.top > 260 || r.bottom < 8 || r.width < 36 || r.height < 18 || r.width > 620 || r.height > 260) continue;
    let score = 0;
    if (/logo|brand|signet|wortmarke|bildmarke/i.test(text(el))) score += 5;
    const href = el.closest('a')?.getAttribute('href') || '';
    if (/^(\/|\.\/|#?$|index\.|home)/i.test(href) || href.replace(/\/$/, '') === location.origin) score += 3;
    if (el.closest('header, nav, [class*="header"], [id*="header"], [class*="navbar"]')) score += 2;
    if (r.left < 420) score += 1;
    if (r.width > 560 && r.height > 180) score -= 4;
    if (score >= 5 && score > (best?.score ?? 0)) best = { score, x: r.left, y: r.top, w: r.width, h: r.height, src: el.currentSrc || el.src?.baseVal || el.src || null };
  }
  return best;
};

async function grab(browser, { slug, url }) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, locale: 'de-DE', timezoneId: 'Europe/Berlin' });
  const page = await ctx.newPage();
  const res = { slug, url };
  try {
    let ok = false;
    for (const u of [url, url.replace('https://', 'http://')]) {
      try { await page.goto(u, { waitUntil: 'domcontentloaded', timeout: 25000 }); ok = true; res.final = page.url(); break; } catch (e) { res.err = String(e.message).split('\n')[0]; }
    }
    if (!ok) return res;
    await page.waitForLoadState('load', { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(1500);
    if (/Checking your request|Just a moment/i.test(await page.title().catch(() => ''))) await page.waitForTimeout(8000);
    if (/agent-proxy/.test(await page.content().catch(() => ''))) { res.err = 'nicht erreichbar'; return res; }
    for (const frame of page.frames()) {  // Cookie-Hinweis wegklicken, sonst verdeckt er die Vorschau
      const hit = [frame.getByRole('button', { name: CONSENT }), frame.getByRole('link', { name: CONSENT }), frame.getByText(CONSENT)];
      let done = false;
      for (const loc of hit) {
        const n = await loc.count().catch(() => 0);
        for (let i = 0; i < n && !done; i++) if (await loc.nth(i).isVisible().catch(() => false)) { await loc.nth(i).click({ timeout: 2000 }).then(() => { done = true; }, () => {}); }
        if (done) break;
      }
      if (done) { res.consent = true; break; }
    }
    await page.addStyleTag({ content: HIDE }).catch(() => {});
    await page.evaluate(() => { window.scrollTo(0, 0); document.documentElement.style.overflow = ''; if (document.body) document.body.style.overflow = ''; });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: `${out}/${slug}-shot.png` });
    res.shot = true;
    const box = await page.evaluate(findLogo).catch(() => null);
    if (box?.src && !/^data:/.test(box.src)) {  // Logo-Datei einzeln auf transparentem Grund rendern
      const lp = await ctx.newPage();
      try {
        await lp.setContent(`<body style="margin:0;background:transparent"><img id="l" src="${box.src.replace(/"/g, '&quot;')}" style="display:block;width:${Math.round(box.w * 2)}px;height:auto;max-height:240px;object-fit:contain"></body>`);
        await lp.waitForFunction(() => document.getElementById('l').complete && document.getElementById('l').naturalWidth > 0, null, { timeout: 8000 });
        await lp.locator('#l').screenshot({ path: `${out}/${slug}-logo.png`, omitBackground: true });
        res.logo = 'datei';
      } catch { /* dann Ausschnitt der Seite */ } finally { await lp.close(); }
    }
    if (box) {  // Ausschnitt der Seite als Ersatz, falls die Datei leer bleibt (images.py entscheidet)
      const p = 10, x = Math.max(0, box.x - p), y = Math.max(0, box.y - p);
      await page.screenshot({ path: `${out}/${slug}-logo-crop.png`, clip: { x, y, width: Math.min(1280 - x, box.w + 2 * p), height: Math.min(800 - y, box.h + 2 * p) } });
      res.logo ??= 'ausschnitt';
    }
  } catch (e) { res.err = String(e.message).split('\n')[0]; }
  finally { await ctx.close(); }
  return res;
}

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined,
  proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined });
const queue = sites.filter(s => !only || only.has(s.slug)), report = [];
await Promise.all(Array.from({ length: 6 }, async () => {
  for (let s; (s = queue.shift());) { const r = await grab(browser, s); report.push(r); console.log(r.shot ? 'ok  ' : 'FAIL', r.logo ? 'logo' : '    ', r.slug, r.err || ''); }
}));
await browser.close();
writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1));
