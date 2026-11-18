// Data exported from the research project by tools/export_web.py (re-run `npm run data` after changes).
//
// ——— Contract: what the web reads (keep in sync with tools/export_web.py) ———
// web/src/data/site.json
//   config       data/website.json without `gate`: title, description, footer, contact {name, email},
//                home {heading, paragraphs[], photo, photo_caption}, story {menu, line, button},
//                home_curiosities [{title, text}], portraits {personSlug: imageKey}, cloudflare {domain},
//                gate.open is not exported; country / region (optional, default region for the history timeline,
//                see lib/events.js),
//                hasStory (derived: data/story.md exists)
//   root         slug of person 1;   aliases {kekule: slug} (SAME – an ancestor appearing more than once)
//   people       {slug: {k, slug, name, y, years, st, status, gen, sex ('M'|'F'), rel, line, lineSlug, facts[],
//                 note, summary, records[], father, mother, fatherUnknown, motherUnknown, child, spouse,
//                 family, ownFamily, path[], side[{name, text, records[], sex?}], docs[{img, caption}],
//                 memories[{kind: 'anecdote'|'curiosity'|'memory', text, source}], children[],
//                 also[{k, rel, line, child}]}}
//                 `status` (label of st), `rel` (relation to person 1) and `years` (short span) are English
//                 display strings produced by the exporter.
//   families     {id: {id, father, mother, fatherUnknown, child, children[], marriage[], records[], line, gen, side[]}}
//                 id = "<father-slug>-and-<mother-slug>" (or "<slug>-family" when one parent is unknown)
//   records      [{key, kind ('B'|'M'|'D'|'C'|'O'), kindName, date, title, summary, scan, archive, volume, vdesc,
//                 portal, url, img (crop exists), full (full-res crop exists), readBy, checkedBy[], boxes[[x0,y0,x1,y1]],
//                 orig, translation, people[]}]
//   lines        {slug: {k, slug, name, desc, color, story[], unknown, root, people[], gens {slug: generation}}}
//   places       [{name, lat, lon, lines[{k, people[]}], years [min, max] | null, hypothesis}]
//   issues       [{title, text}]   text starts with "Resolved:" (hidden), "Hypothesis:" or "Open:"
//   stats        {ancestors, documented, records, generations}
//   hypotheses   [{line, title, text, items[{name, text}], records[]}]
//   docs         [{img, caption, kind, date, people[]}]   kind: certificate | photo | map | register_copy |
//                 document | screenshot | other
// web/src/generated/   log.md, questions.md, offline_sources.md, curiosities.md, story.md (frontmatter title, lead),
//                      fan.svg, fan_hrefs.json
// web/public/img/<key>.jpg (web-size crops), web/public/full/<key>.jpg (full resolution), web/public/login.html
// web/src/news.json    [{version, date, title, points[], people[{k, new, records[]}]}]
import site from '../data/site.json';

export const { people, families, lines, stats, issues, hypotheses, docs, config } = site;
/** Number of family lines as words for headings ("Eight family lines"). */
export const linesTitle = (n) => (['No family lines', 'One family line', 'Two family lines', 'Three family lines', 'Four family lines',
  'Five family lines', 'Six family lines', 'Seven family lines', 'Eight family lines'][n] ?? `${n} family lines`);
export const root = people[site.root];
export const records = Object.fromEntries(site.records.map((r) => [r.key, r]));
export const recordList = site.records;
export const byK = Object.fromEntries([
  ...Object.values(people).map((p) => [p.k, p]),
  ...Object.entries(site.aliases ?? {}).map(([k, slug]) => [Number(k), people[slug]]),
]);
export const lineByK = Object.fromEntries(Object.values(lines).map((l) => [l.k, l]));

export const href = {
  person: (slug) => `/person/${slug}/`,
  family: (id) => `/family/${id}/`,
  line: (slug) => `/line/${slug}/`,
  record: (key) => `/source/${key}/`,
};

// ——— dates ———
// Canonical form in the data: "12 Mar 1873"; also "Mar 1873", "1873". For robustness the old numeric forms
// "12. 3. 1873", "12.03.1873", "12/03/1873" (day/month/year) and "3/1867" (month/year) are understood too.
export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH_RE = 'jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?';
const monthNo = (m) => MONTHS.findIndex((x) => x.toLowerCase() === m.slice(0, 3).toLowerCase()) + 1;
/** Words that make a date approximate ("c. 1720", "before 1740", "between 1680 and 1685", "~1700", "≈1700"). */
export const APPROX_RE = /(?:^|[\s(])(?:c\.|ca\.|abt\.?|about|before|after|between|~|≈)/i;
/** Date prefix pattern (without the year) used inside other regexes: "12 Mar ", "Mar ", "12. 3. ", "12/03/", "3/". */
export const DATE_PREFIX = `(?:(?:\\d{1,2}[./]\\s*){1,2}|(?:\\d{1,2}\\s+)?(?:${MONTH_RE})\\.?,?\\s+)`;
/** Approximation prefix pattern used inside other regexes. */
export const APPROX_PREFIX = '(?:~|≈|c\\.|ca\\.|abt\\.?|about|before|after|between)';

/** First date in a text → { d, m, y, i } (missing parts are 0), or null. */
export function parseDate(text = '') {
  const t = String(text);
  const found = [];
  let m;
  if ((m = t.match(new RegExp(`\\b(?:(\\d{1,2})\\s+)?(${MONTH_RE})\\.?,?\\s+(\\d{4})\\b`, 'i')))) {
    found.push({ d: Number(m[1] || 0), m: monthNo(m[2]), y: Number(m[3]), i: m.index });
  }
  if ((m = t.match(/\b(\d{1,2})[./]\s*(\d{1,2})[./]\s*(\d{4})\b/))) found.push({ d: Number(m[1]), m: Number(m[2]), y: Number(m[3]), i: m.index });
  else if ((m = t.match(/\b(\d{1,2})[./](\d{4})\b/))) found.push({ d: 0, m: Number(m[1]), y: Number(m[2]), i: m.index });
  if ((m = t.match(/\b(1\d{3}|20\d{2})\b/))) found.push({ d: 0, m: 0, y: Number(m[1]), i: m.index });
  if (!found.length) return null;
  // the earliest match wins; at the same position the most detailed one
  found.sort((a, b) => a.i - b.i || (b.d > 0) - (a.d > 0) || (b.m > 0) - (a.m > 0));
  const r = found[0];
  if (r.m > 12) r.m = 0;
  return r;
}

/** Sortable number from dates like "12 May 1811", "Mar 1867", "12. 5. 1811", "3/1867", "1797". */
export function dateKey(date = '') {
  const p = parseDate(date);
  return p ? p.y * 10000 + p.m * 100 + p.d : 99990000;
}

/** Old numeric dates "6. 10. 1959" / "6.10.1959" / "6/10/1959" → "6 Oct 1959"; everything else unchanged. */
export const fmtDate = (t = '') => t.replace(/\b(\d{1,2})[./]\s*(\d{1,2})[./]\s*(\d{4})\b/g,
  (m, d, mo, y) => (mo >= 1 && mo <= 12 ? `${Number(d)} ${MONTHS[mo - 1]} ${y}` : m));

/** English ordinal: 1st, 2nd, 3rd, 4th, 11th, 21st … */
export const ordinal = (n) => {
  const s = n % 100 >= 11 && n % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' })[n % 10] ?? 'th';
  return `${n}${s}`;
};
/** "great-" prefix n times: '', 'great-', 'great-great-', then '3rd great-', '4th great-' … */
export const greats = (n) => (n <= 0 ? '' : n <= 2 ? 'great-'.repeat(n) : `${ordinal(n)} great-`);

export const genName = (g) =>
  ['root person', 'parents', 'grandparents', 'great-grandparents', '4th generation (great-great-grandparents)'][g] ??
  `${ordinal(g)} generation (${greats(g - 2)}grandparents)`;

export const statusClass = (st) => ({ doc: 'st-doc', prob: 'st-prob', fam: 'st-fam', mh: 'st-mh' })[st] ?? 'st-unk';

// ——— Human details for medallions and person chapters ———
const yearOf = (t = '') => Number((t.match(/\b(1[0-9]{3}|20[0-9]{2})\b/) || [])[1]) || null;
const exact = (t = '') => { const d = parseDate(t); return !!(d && d.d && d.m) && !APPROX_RE.test(t); };
const dateOf = (t = '') => { const d = parseDate(t); return d ? [d.d, d.m, d.y] : []; };
/** Approximation and date at the start of a fact without its symbol ("c. 12 Mar 1873 ") – the rest is usually the place. */
const FACT_DATE_RE = new RegExp(`^(?:${APPROX_PREFIX}\\s*)?(?:(?:${DATE_PREFIX})?\\d{4}(?:\\s*and\\s*(?:${DATE_PREFIX})?\\d{4})?)?\\s*`, 'i');
/** Monogram from the initials of the first name and surname ("Pierre Dubois" → "PD"). */
export const initials = (name = '') => {
  const w = name.replace(/\([^)]*\)/g, '').split(/\s+/).filter((x) => /^\p{Lu}/u.test(x));
  return ((w[0]?.[0] ?? '') + (w.length > 1 ? w[w.length - 1][0] : '')) || '?';
};
// Lower-case words at the start of a fact that are not the person's own occupation.
const NOT_OCC = /^(son|daughter|widow|widower|godparent|godfather|godmother|witness|perhaps|probably|possibly|c\.|lived|living|family|record|according|student|resident|born|baptised|baptized|married|died|buried|same person|see|née|nee|also|from|in|at|of)\b/;
/** Parse a person's facts: birth, marriages, death, occupation, place and dated milestones. */
export function life(p) {
  const f = p.facts ?? [];
  const birth = f.find((x) => x.startsWith('*')) ?? '';
  const death = f.find((x) => x.startsWith('†')) ?? '';
  const marriages = f.filter((x) => x.startsWith('×'));
  const rest = f.filter((x) => !/^[*†×]/.test(x));
  const ys = (p.years || '').match(/\d{4}/g) ?? [];
  const by = yearOf(birth) ?? (/^(\*|\d)/.test(p.years || '') ? Number(ys[0]) || null : null);
  const dy = yearOf(death) ?? (/[–-]\s*\d{4}|^†/.test(p.years || '') ? Number(ys[ys.length - 1]) || null : null);
  let age = null, ageExact = false;
  if (by && dy && dy >= by) {
    age = dy - by;
    if (exact(birth) && exact(death)) {
      const [d1, m1] = dateOf(birth), [d2, m2] = dateOf(death);
      if (m2 < m1 || (m2 === m1 && d2 < d1)) age -= 1;
      ageExact = true;
    }
    if (APPROX_RE.test(p.years || '')) ageExact = false;
  }
  // an age stated in the death record wins: "† 3 May 1850 (aged 64)", "age c. 64", "64 years"
  const stated = death.match(/\b(?:aged?|age)\s+(?:c\.\s*|about\s+)?(\d{1,3})\b/i) || death.match(/\b(\d{1,3})\s*(?:years?|yrs?)\b/i);
  if (stated && Number(stated[1]) > 0 && Number(stated[1]) < 115) { age = Number(stated[1]); ageExact = !/c\.|about/i.test(stated[0]); }
  const ageText = age && age >= 1 && (stated || (dy && by)) ? `lived to ${ageExact ? '' : 'about '}${age}` : '';
  const placeOf = (t) => t.replace(/^[*†×]\s*/, '').replace(FACT_DATE_RE, '').split(/,|\s\(|\sno\.|\s–/)[0].trim();
  const place = placeOf(birth);
  const occ = rest.map((x) => x.match(/^(\p{Ll}[\p{Ll}' -]{2,30}?)(?=\s(?:in|at|on|of|from|near|for)\s|\s\(|,|;|$)/u)?.[1])
    .filter((x) => x && !NOT_OCC.test(x)).pop();
  const milestones = rest.map((x) => ({ text: x, year: Number((x.match(/\((\d{4})\)\s*$/) || [])[1]) || null })).filter((m) => m.year);
  const other = rest.filter((x) => !/\(\d{4}\)\s*$/.test(x));
  return { birth, death, marriages, by, dy, age, ageText, place, occ: occ || '', milestones, other };
}
/** "1787–1878" → "* 1787 · † 1878" for medallions. */
export const lifeSpan = (p) => {
  const y = (p.years || '').trim();
  if (!y) return '';
  if (/^[*†]/.test(y) || /^(?:~|≈|c\.|ca\.|abt|about\b|before\b|after\b|between\b|lived\b)/i.test(y)) return y;
  const [a, b] = y.split('–').map((s) => s.trim());
  if (b === undefined) return y;
  return [a && `* ${a}`, b && `† ${b}`].filter(Boolean).join(' · ');
};
const MARRIAGE_YEAR_RE = new RegExp(`^×\\s*(?:${APPROX_PREFIX}\\s*)?(?:${DATE_PREFIX})?(\\d{4})\\b`, 'i');
/** Year of the marriage of person k's parents: the father's "× date …" fact naming the mother (or vice versa). */
export const marriageYear = (k) => {
  const f = byK[2 * k], m = byK[2 * k + 1];
  const last = (p) => (p?.name || '').replace(/\([^)]*\)/g, '').trim().split(/\s+/).pop() || '#';
  const pick = (p, other) => (p?.facts ?? []).filter((x) => x.startsWith('×'))
    .filter((x) => x.includes(last(other)) || x.includes((other?.name || '#').split(' ')[0]))
    .map((x) => (x.match(MARRIAGE_YEAR_RE) || [])[1]).find(Boolean);
  const y = pick(f, m) ?? pick(m, f);
  return y ? Number(y) : null;
};
/** Portrait of a person, if assigned in data/website.json → portraits: { slug: image }. */
export const portrait = (p) => config.portraits?.[p.slug] ?? null;
/** Earliest year in the family tree (for the chronicle intro). */
export const earliestYear = Math.min(...Object.values(people).map((p) => yearOf(p.years || '') ?? 9999));
/** Public address of a page for e-mails ("https://domain/person/x/"), or just the path without a domain. */
export const pageUrl = (path) => (config.cloudflare?.domain ? `https://${config.cloudflare.domain}${path}` : path);
