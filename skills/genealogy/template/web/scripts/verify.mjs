// Check after deployment (`npm run deploy` runs it at the end, manually `node scripts/verify.mjs`):
// opens the website without signing in, like a stranger, and tells whether the family question protects it.
// A new Netlify site is often "Private" (team protection) – the family then sees a Netlify login instead of the question,
// and the owner does not notice because they are signed in to Netlify.
// The address and protection state come from netlify-cli (site linked in .netlify/state.json); --url <address> = just open the address.
import { npxSync } from "./npx.mjs";
import { existsSync, readFileSync } from "node:fs";

const GATE = /document\.cookie\s*=\s*'genealogy=/;   // the login page (login.html from tools/export_web.py)
// the export builds the Netlify gate only with a question in the settings; the Cloudflare gate always, for an open site with OPEN = true
const hasGate = existsSync("netlify/edge-functions/gate.js") ||
  (existsSync("cloudflare/worker.js") && !/OPEN = true/.test(readFileSync("cloudflare/worker.js", "utf8")));
const a = process.argv.slice(2);
let url = a[a.indexOf("--url") + 1] && a.includes("--url") ? a[a.indexOf("--url") + 1] : null;
let siteId = null;

function finish(code, ...lines) {
  console.log(lines.join("\n"));
  process.exit(code);
}

function teamProtection() {
  const id = siteId || "<site_id from web/.netlify/state.json>";
  finish(1,
    "ERROR: the website is protected by a Netlify login (team protection, \"Private\") – the family will see a Netlify login instead of the family question.",
    "To switch it off (this changes the user's account settings – ask them first):",
    `  npx -y netlify-cli@latest api updateSite --data '{"site_id":"${id}","body":{"sso_login":false}}'`,
    "  (Windows PowerShell/cmd: JSON in double quotes \"…\" with \\\" inside.)",
    "Or in the site administration: Project configuration → Access & security → Visitor access → Project visibility →",
    "  Edit visibility → Public (Production and Deploy Preview) → Save. The family question then protects the website.",
    "Then again: node scripts/verify.mjs");
}

if (!url && !existsSync(".netlify/state.json") && existsSync(".wrangler/url.txt")) {
  url = readFileSync(".wrangler/url.txt", "utf8").trim();   // saved by scripts/deploy_cloudflare.mjs
}

if (!url) {
  try {
    siteId = JSON.parse(readFileSync(".netlify/state.json", "utf8")).siteId;
  } catch {}
  if (!siteId) {
    finish(0, "Check skipped: this folder is not linked to a Netlify site (.netlify/state.json).",
      "Open the website address in a private window – the family question must appear.");
  }
  const r = npxSync(["-y", "netlify-cli@latest", "api", "getSite", "--data", JSON.stringify({ site_id: siteId })],
    { encoding: "utf8" });
  let site = null;
  try {
    site = JSON.parse(r.stdout.slice(r.stdout.indexOf("{")));
  } catch {}
  if (!site) {
    finish(0, "Check skipped: the site details could not be loaded from Netlify (netlify-cli api getSite).",
      "Open the website address in a private window – the family question must appear.");
  }
  if (site.sso_login) teamProtection();
  url = site.ssl_url || site.url;
}

// A new workers.dev subdomain takes several minutes to propagate. If the computer asks too early, it remembers
// "does not exist" and then cannot see the site for a while – so we first wait via Cloudflare DNS (DoH), not the computer.
async function waitForDns(host) {
  for (let i = 0; i < 36; i++) {
    try {
      const r = await fetch(`https://cloudflare-dns.com/dns-query?name=${host}&type=A`, { headers: { accept: "application/dns-json" } });
      if ((await r.json()).Answer?.length) return true;
    } catch {}
    if (i === 0) console.log("Waiting for the new address to propagate (may take a few minutes)…");
    await new Promise((ok) => setTimeout(ok, 5000));
  }
  return false;
}
const host = new URL(url).hostname;
if (host.endsWith(".workers.dev") && !(await waitForDns(host))) {
  finish(0, `The address ${url} is still propagating. Open it in a private window in a few minutes, or run: npm run verify`);
}

let res, text;
for (let attempt = 0; attempt < 3; attempt++) {   // right after deployment the site may be missing for a few seconds
  try {
    res = await fetch(url, { redirect: "manual", headers: { "cache-control": "no-cache" } });
    text = await res.text();
    if (res.status !== 404 || attempt === 2) break;
  } catch (e) {
    if (attempt === 2 && e.cause?.code === "ENOTFOUND" && host.endsWith(".workers.dev")) {
      finish(0, `The website is uploaded, but this computer does not know the address ${url} yet (the new address is propagating).`,
        "The computer or router may remember \"does not exist\" for up to 30 minutes. Then open it in a private window",
        "or run: npm run verify (it works right away on a phone over mobile data, for example).");
    }
    if (attempt === 2) finish(1, `ERROR: the website ${url} cannot be opened (${e.cause?.code || e.message}).`);
  }
  await new Promise((ok) => setTimeout(ok, 5000));
}

const location = res.headers.get("location") || "";
if (GATE.test(text)) {
  finish(0, `OK: ${url} shows the family question to visitors who are not signed in.`);
}
if ((res.status >= 300 && res.status < 400 && /netlify\.com/.test(location)) ||
    ((res.status === 401 || res.status === 403) && /netlify|login/i.test(text))) {
  teamProtection();
}
if (res.status === 429) {
  finish(1, `ERROR: ${url} returned 429 – the daily limit of the free Cloudflare plan is used up (100,000 requests, resets at midnight UTC).`,
    "The gate still protects the website, nobody can get in right now. If it happens again, consider a paid plan or smaller crops.");
}
if ((res.status === 403 || res.status === 503) && /cf-chl|challenge-platform|Just a moment/i.test(text)) {
  finish(1, `ERROR: ${url} showed a Cloudflare verification page (bot protection), not the family question.`,
    "Open the address in a private browser window. Safari with a content blocker shows it as an empty 403 page –",
    "try another browser. If the question appears in the browser, the website is fine.");
}
if (res.status === 200) {
  if (hasGate) {
    finish(1, `ERROR: ${url} opens without the family question although the website settings have one.`,
      "The gate was not deployed – deploy only with `npm run deploy` / `npm run deploy-cloudflare`, not by dragging the folder (Netlify Drop).");
  }
  finish(0, `Note: ${url} is open without signing in (data/website.json has no family question) – anyone can see it.`);
}
finish(1, `ERROR: ${url} returned an unexpected response ${res.status}${location ? " → " + location : ""}. Open it in a private window and check.`);
