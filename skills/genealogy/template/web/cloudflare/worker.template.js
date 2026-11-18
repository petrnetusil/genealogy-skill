// Sign-in gate for Cloudflare (a Worker with static assets). tools/export_web.py builds cloudflare/worker.js from this
// template – do not edit by hand. The answer to the family question is not here, only its fingerprint (SHA-256),
// which the login page stores in a cookie. wrangler.jsonc has run_worker_first: true, so the gate stands in front
// of every file of the website (without it Cloudflare would serve pages and images past the gate).
const HASH = '{{HASH}}';
const OPEN = {{OPEN}};
const ROBOTS = 'noindex, nofollow';

function cookie(request, name) {
  for (const part of (request.headers.get('cookie') || '').split(';')) {
    const i = part.indexOf('=');
    if (i > 0 && part.slice(0, i).trim() === name) return part.slice(i + 1).trim();
  }
  return null;
}

async function asset(request, env, extra = {}) {
  const res = await env.ASSETS.fetch(request);
  const out = new Response(res.body, res);
  out.headers.set('X-Robots-Tag', ROBOTS);
  for (const [k, v] of Object.entries(extra)) out.headers.set(k, v);
  return out;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/login' || url.pathname === '/login.html') {
      return asset(request, env, { 'Cache-Control': 'no-store' });
    }
    if (OPEN || (HASH && cookie(request, 'genealogy') === HASH)) return asset(request, env);
    // Cloudflare serves /login.html as /login (redirect) – fetch the page directly.
    const login = await env.ASSETS.fetch(new Request(new URL('/login', url)));
    return new Response(await login.text(), {
      status: 401,
      headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': ROBOTS },
    });
  },
};
