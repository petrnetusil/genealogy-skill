// Sign-in gate for Netlify (Edge Function). tools/export_web.py builds edge-functions/gate.js from this template
// – do not edit by hand. The answer to the family question is not here, only its fingerprint (SHA-256),
// which the login page stores in a cookie.
const HASH = '{{HASH}}';

export default async (request, context) => {
  const url = new URL(request.url);
  if (url.pathname === '/login.html') return context.next();
  if (context.cookies.get('genealogy') === HASH) {
    const res = await context.next();
    res.headers.set('X-Robots-Tag', 'noindex, nofollow');
    return res;
  }
  const login = await fetch(new URL('/login.html', url));
  return new Response(await login.text(), {
    status: 401,
    headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex, nofollow' },
  });
};

export const config = { path: '/*' };
