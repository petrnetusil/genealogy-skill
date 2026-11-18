// Uploads the finished website (dist/) to Cloudflare – `npm run deploy-cloudflare` runs it after the export and build.
// tools/export_web.py builds wrangler.jsonc and the gate cloudflare/worker.js. After uploading, the check
// scripts/verify.mjs runs on the address wrangler prints (https://<worker>.<subdomain>.workers.dev; worker =
// cloudflare.worker from data/website.json, default "genealogy").
//
// Two projects on one account: with the same worker name the second would overwrite the first. So before the first
// deployment from this folder (no .wrangler/url.txt for this worker) we check whether a worker with that name already
// exists on the account; if so, we stop with advice. Deliberate overwrite (the same project from another computer):
// `node scripts/deploy_cloudflare.mjs --overwrite`.
//
// workers.dev subdomain: a new account has none. Wrangler run from Claude registers it itself, but takes the name
// from package.json (always "genealogy-web" – taken). So we run it from the folder .wrangler/subdomain, whose
// package.json carries the name from data/website.json (cloudflare.subdomain); if taken, we try it with a number.
import { spawnSync } from "node:child_process";
import { npxSpawn, npxSync } from "./npx.mjs";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

const argv = process.argv.slice(2).filter((a) => a !== "--overwrite");
const overwrite = process.argv.includes("--overwrite");
const VALID = /^[a-z0-9](?:[a-z0-9-]{0,48}[a-z0-9])?$/;

// Worker name from wrangler.jsonc, which the export builds (the first line is a comment).
function workerName() {
  try {
    return JSON.parse(readFileSync("wrangler.jsonc", "utf8").replace(/^\s*\/\/.*$/gm, "")).name || "genealogy";
  } catch {
    return "genealogy";
  }
}

function slug(t) {
  return String(t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 50).replace(/-+$/, "");
}

// data/website.json (also with a BOM from Windows). An unreadable file stops the deployment: with the default name a new
// account would permanently get a different subdomain (it cannot be changed via the API). A missing file = no settings.
function readWebsite() {
  try {
    return JSON.parse(readFileSync("../data/website.json", "utf8").replace(/^\uFEFF/, ""));
  } catch (e) {
    if (e.code === "ENOENT") return {};
    console.error(`ERROR: data/website.json cannot be read (${e.message}) – fix it and run the deployment again.`);
    process.exit(1);
  }
}

function subdomainFromWebsite() {
  const web = readWebsite();
  return slug(web.cloudflare?.subdomain) || slug(web.title) || "genealogy";
}

// --check-free [<name> …]: is the subdomain <name>.workers.dev free? Asks Cloudflare DNS (DoH), not the computer –
// that would remember "does not exist" and then not see the new address for up to 30 minutes. A taken subdomain has a
// record for *.<name>.workers.dev; an empty answer = probably free (only the deployment is certain; it then tries a numbered variant).
if (argv[0] === "--check-free") {
  const doh = process.env.GENEALOGY_DOH || "https://cloudflare-dns.com/dns-query";
  let taken = false;
  for (const name of argv.length > 1 ? argv.slice(1) : [subdomainFromWebsite()]) {   // without a name: the one from website.json
    if (!VALID.test(name)) {
      console.log(`${name}: cannot be used – only lower-case letters without accents, digits and hyphens (at most 50 characters)`);
      process.exit(2);
    }
    const r = await fetch(`${doh}?name=${workerName()}.${name}.workers.dev&type=A`, { headers: { accept: "application/dns-json" } });
    const has = ((await r.json()).Answer || []).length > 0;
    taken ||= has;
    console.log(`${name}: ${has ? "taken" : "free (probably)"}  →  https://${workerName()}.${name}.workers.dev`);
  }
  process.exit(taken && argv.length <= 2 ? 1 : 0);
}
if (argv.length) {
  console.error(`ERROR: unknown option ${argv[0]} (known: --check-free <name> and --overwrite).`);
  process.exit(2);
}

if (!existsSync("wrangler.jsonc") || !existsSync("cloudflare/worker.js")) {
  console.error("ERROR: wrangler.jsonc or cloudflare/worker.js is missing – run `npm run deploy-cloudflare` (the export builds them).");
  process.exit(1);
}

const base = subdomainFromWebsite();
const proposals = [base, ...[0, 1, 2].map(() => `${base}-${Math.floor(1000 + Math.random() * 9000)}`)];


function deploy(subdomain) {
  const folder = resolve(".wrangler", "subdomain");
  mkdirSync(folder, { recursive: true });
  writeFileSync(resolve(folder, "package.json"), JSON.stringify({ name: subdomain, private: true }) + "\n");
  return new Promise((done) => {
    let text = "";
    // relative path: no spaces even in the shell fallback (project in "C:\Users\Jan Novak\…")
    const p = npxSpawn(["-y", "wrangler@4", "deploy", "--config", join("..", "..", "wrangler.jsonc")],
      { cwd: folder, stdio: ["inherit", "pipe", "pipe"] });
    p.stdout.on("data", (d) => { process.stdout.write(d); text += d; });
    p.stderr.on("data", (d) => { process.stderr.write(d); text += d; });
    p.on("close", (code) => done({ code, text }));
  });
}

// Is there already a worker with the same name from another project on the account?
const worker = workerName();
let previous = "";
try {
  previous = readFileSync(resolve(".wrangler", "url.txt"), "utf8").trim();
} catch {}
if (!overwrite && !previous.startsWith(`https://${worker}.`)) {
  const r = npxSync(["-y", "wrangler@4", "deployments", "list", "--name", worker, "--json"], { encoding: "utf8" });
  if (r.status === 0) {
    console.error(`\nThe Cloudflare account already has a website "${worker}" – probably from another family tree project. Uploading would overwrite it.`,
      `\nGive this project a different worker name: in data/website.json "cloudflare": {"worker": "${worker}-…"} (lower-case letters,`,
      "hyphens) and run the deployment again. If it really is the same project (e.g. from another computer):",
      "`node scripts/deploy_cloudflare.mjs --overwrite`.");
    process.exit(1);
  }
  // 10007 = no such worker on the account; another error (not signed in, new account) – the deployment reports it itself
}

let output;
for (const subdomain of proposals) {
  output = await deploy(subdomain);
  if (output.code === 0 || !/Could not automatically register/i.test(output.text)) break;
  console.log(`\nThe subdomain "${subdomain}.workers.dev" is taken, trying another one…\n`);
}

if (output.code !== 0) {
  if (/verify your email/i.test(output.text)) {
    console.error("\nCloudflare needs a verified account e-mail before the first deployment. Ask the user to open dash.cloudflare.com,",
      "click the e-mail verification in the bar at the top or in My Profile and confirm the link in their mailbox.",
      "Then run the deployment again – the subdomain will be kept.");
  } else if (/not (logged in|authenticated)|wrangler login/i.test(output.text)) {
    console.error("\nNot signed in to Cloudflare: `npx -y wrangler@4 login` (approve in the browser within 2 minutes), then again.");
  } else if (/workers\/onboarding/.test(output.text)) {
    console.error("\nThe workers.dev subdomain could not be created. Choose it once by hand at the link above (Workers → onboarding)",
      "and run the deployment again – or put a different cloudflare.subdomain into data/website.json.");
  }
  process.exit(output.code ?? 1);
}

const address = (output.text.match(/https:\/\/[a-z0-9.-]+\.workers\.dev/i) || [])[0];
if (!address) {
  console.log("Uploaded. I did not find the website address in the output – check it: node scripts/verify.mjs --url <address>");
  process.exit(0);
}
writeFileSync(resolve(".wrangler", "url.txt"), address + "\n");   // for a later `npm run verify`
console.log(`\nThe website is uploaded: ${address}`);
const r = spawnSync("node", ["scripts/verify.mjs", "--url", address], { stdio: "inherit" });
process.exit(r.status ?? 1);
