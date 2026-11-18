// Family tree statistics for the page /statistics/ – computed at build time from site.json.
// Idea and list of occupations adapted (MIT) from zbysekvoda/rodokmen-plus, template/web/src/lib/statistiky.js,
// itself a rewrite of tools/statistiky.py from hnizdiljan/rodokmen-skill@d172316 (Jan Hnízdil):
// https://github.com/hnizdiljan/rodokmen-skill/blob/d172316bc190d0f44894fa67115505729d587c6a/skills/rodokmen/tools/statistiky.py
// Rewritten for this data model (Kekulé numbers, person facts, pedigree collapse via `also`, side relatives from SIDE).
import site from '../data/site.json';
import { people, recordList, lines, life, dateKey, href, APPROX_PREFIX, DATE_PREFIX } from './data.js';
import { buildKinData } from './relationship.js';

// EDITABLE: keyword (start of a word, lower case – "Smith" with a capital is a surname) → occupation; first match wins.
// Facts are written in English; add words from your own records (or other languages) as needed.
const OCCUPATIONS = [
  ['weaver', 'weaver'], ['clothier', 'clothier'], ['cloth-maker', 'clothier'], ['shoemaker', 'shoemaker'], ['cobbler', 'shoemaker'],
  ['tailor', 'tailor'], ['seamstress', 'seamstress'], ['blacksmith', 'blacksmith'], ['smith', 'blacksmith'], ['wheelwright', 'wheelwright'],
  ['mason', 'mason'], ['bricklayer', 'mason'], ['carpenter', 'carpenter'], ['joiner', 'joiner'], ['cabinet', 'joiner'],
  ['cooper', 'cooper'], ['glazier', 'glazier'], ['potter', 'potter'], ['tanner', 'tanner'], ['dyer', 'dyer'], ['tinsmith', 'tinsmith'],
  ['locksmith', 'locksmith'], ['turner', 'turner'], ['miller', 'miller'], ['baker', 'baker'], ['butcher', 'butcher'], ['brewer', 'brewer'],
  ['maltster', 'maltster'], ['farmer', 'farmer'], ['peasant', 'farmer'], ['husbandman', 'farmer'], ['yeoman', 'farmer'],
  ['cottager', 'cottager'], ['smallholder', 'smallholder'], ['crofter', 'smallholder'], ['retired farmer', 'retired farmer'],
  ['lodger', 'lodger'], ['farmhand', 'farmhand'], ['farm servant', 'farmhand'], ['servant', 'servant'], ['maid(?!en)', 'maid'],
  ['gardener', 'gardener'], ['shepherd', 'shepherd'], ['gamekeeper', 'gamekeeper'], ['forester', 'forester'], ['huntsman', 'gamekeeper'],
  ['engine driver', 'engine driver'], ['railway', 'railwayman'], ['coachman', 'coachman'], ['carter', 'carter'], ['merchant', 'merchant'],
  ['shopkeeper', 'shopkeeper'], ['grocer', 'shopkeeper'], ['innkeeper', 'innkeeper'], ['publican', 'innkeeper'], ['teacher', 'teacher'],
  ['schoolmaster', 'teacher'], ['clerk', 'clerk'], ['official', 'official'], ['gendarme', 'gendarme'], ['policeman', 'policeman'],
  ['mayor', 'mayor'], ['reeve', 'reeve'], ['soldier', 'soldier'], ['veteran', 'soldier'], ['miner', 'miner'],
  ['day labourer', 'day labourer'], ['day laborer', 'day labourer'], ['labourer', 'labourer'], ['laborer', 'labourer'],
  ['factory worker', 'factory worker'], ['worker', 'worker'], ['foreman', 'foreman'], ['lacemaker', 'lacemaker'], ['spinner', 'spinner'],
  ['flax', 'flax worker'], ['linen', 'linen weaver'], ['sexton', 'sexton'], ['sacristan', 'sexton'], ['midwife', 'midwife'],
].map(([kw, name]) => [new RegExp(`(?<![\\p{L}\\p{N}])${kw}`, 'u'), name]);

const avg = (xs) => (xs.length ? Math.round((xs.reduce((a, b) => a + b, 0) / xs.length) * 10) / 10 : null);
const counts = (xs) => [...xs.reduce((m, x) => m.set(x, (m.get(x) ?? 0) + 1), new Map())]
  .map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count || String(a.name).localeCompare(String(b.name), 'en'));
const gen = (k) => Math.floor(Math.log2(k));
const ref = (p, extra = {}) => ({ slug: p.slug, name: p.name, years: p.years, href: href.person(p.slug), ...extra });
const century = (y) => Math.floor((y - 1) / 100) + 1;   // 1701–1800 = 18th century

const anc = Object.values(people).filter((p) => p.k > 1);
const L = new Map(anc.map((p) => [p.slug, life(p)]));

// ——— ancestors by generation (pedigree collapse: a person appearing several times fills several slots) ———
const slots = anc.flatMap((p) => [p.k, ...(p.also ?? []).map((a) => a.k)].map((k) => ({ k, p })));
const maxGen = slots.length ? Math.max(...slots.map((s) => gen(s.k))) : 0;
export const generations = Array.from({ length: maxGen }, (_, i) => i + 1).map((g) => {
  const here = slots.filter((s) => gen(s.k) === g);
  return { g, known: here.length, doc: here.filter((s) => s.p.st === 'doc').length, total: 2 ** g,
    pct: Math.round((here.length / 2 ** g) * 1000) / 10 };
});

// ——— how well documented ———
const ST = [['doc', 'documented in registers'], ['prob', 'probable'], ['fam', 'from the family'], ['mh', 'from an online tree'], ['unk', 'unknown']];
export const status = ST.map(([st, label]) => ({ st, label, count: anc.filter((p) => p.st === st).length })).filter((x) => x.count);

// ——— family lines ———
export const lineStats = Object.values(lines).sort((a, b) => a.k - b.k).map((l) => {
  const ms = l.people.map((s) => people[s]).filter(Boolean);
  const ys = ms.map((p) => L.get(p.slug)?.by ?? L.get(p.slug)?.dy).filter(Boolean);
  return { name: l.name, slug: l.slug, color: l.color, href: href.line(l.slug), count: ms.length,
    doc: ms.filter((p) => p.st === 'doc').length, oldest: ys.length ? Math.min(...ys) : null,
    gens: Math.max(...Object.values(l.gens ?? { x: 0 })) + 1 };
});

// ——— oldest ———
const recs = recordList.filter((r) => /\d{4}/.test(r.date)).sort((a, b) => dateKey(a.date) - dateKey(b.date));
export const oldestRecord = recs[0] ? { title: recs[0].title, date: recs[0].date, href: href.record(recs[0].key), kind: recs[0].kindName } : null;
const withBirth = anc.filter((p) => L.get(p.slug).by).sort((a, b) => L.get(a.slug).by - L.get(b.slug).by);
export const oldestPerson = withBirth[0] ? ref(withBirth[0], { year: L.get(withBirth[0].slug).by }) : null;
export const recordKinds = counts(recordList.map((r) => r.kindName));

// ——— age at death (adults only – ancestors at least lived to marry) ———
const lifespans = anc.map((p) => ({ p, l: L.get(p.slug) })).filter(({ l }) => l.age != null && l.age >= 15 && l.age < 110);
const cents = [...new Set(lifespans.map(({ l }) => century(l.by ?? l.dy - l.age)))].sort();
export const lifeByCentury = cents.map((c) => {
  const here = lifespans.filter(({ l }) => century(l.by ?? l.dy - l.age) === c);
  const m = here.filter(({ p }) => p.sex === 'M').map(({ l }) => l.age), f = here.filter(({ p }) => p.sex === 'F').map(({ l }) => l.age);
  return { century: c, men: avg(m), menN: m.length, women: avg(f), womenN: f.length };
}).filter((r) => r.menN + r.womenN >= 3);
export const lifeAll = {
  men: avg(lifespans.filter(({ p }) => p.sex === 'M').map(({ l }) => l.age)), menN: lifespans.filter(({ p }) => p.sex === 'M').length,
  women: avg(lifespans.filter(({ p }) => p.sex === 'F').map(({ l }) => l.age)), womenN: lifespans.filter(({ p }) => p.sex === 'F').length,
};
const byAge = [...lifespans].sort((a, b) => b.l.age - a.l.age);
export const oldestLived = byAge.slice(0, 5).map(({ p, l }) => ref(p, { age: l.age }));

// ——— age at (first) marriage ———
const MARR = new RegExp(`^(?:\\d\\.\\s*)?×\\s*(?:${APPROX_PREFIX}\\s*)?(?:${DATE_PREFIX})?(1[5-9]\\d{2}|20\\d{2})\\b`, 'i');
const marriages = anc.map((p) => {
  const ys = (p.facts ?? []).map((f) => (f.match(MARR) || [])[1]).filter(Boolean).map(Number);
  const by = L.get(p.slug).by;
  if (!ys.length || !by) return null;
  const age = Math.min(...ys) - by;
  return age >= 14 && age <= 70 ? { p, age, year: Math.min(...ys) } : null;
}).filter(Boolean);
const med = (xs) => { const s = [...xs].sort((a, b) => a - b); return s.length ? s[Math.floor(s.length / 2)] : null; };
export const marriageAge = ['M', 'F'].map((sex) => {
  const xs = marriages.filter((m) => m.p.sex === sex).map((m) => m.age);
  return { sex, avg: avg(xs), median: med(xs), n: xs.length, min: Math.min(...xs), max: Math.max(...xs) };
}).filter((m) => m.n > 0);
export const marriageByCentury = [...new Set(marriages.map((m) => century(m.year)))].sort().map((c) => {
  const here = marriages.filter((m) => century(m.year) === c);
  const m = here.filter((x) => x.p.sex === 'M').map((x) => x.age), f = here.filter((x) => x.p.sex === 'F').map((x) => x.age);
  return { century: c, men: avg(m), menN: m.length, women: avg(f), womenN: f.length };
}).filter((r) => r.menN + r.womenN >= 3);
export const youngest = [...marriages].sort((a, b) => a.age - b.age).slice(0, 3).map((m) => ref(m.p, { age: m.age, year: m.year }));

// ——— first names ———
const first = (p) => p.name.replace(/\([^)]*\)/g, '').replace(/^\?\s*/, '').trim().split(/\s+/)[0];
export const namesMen = counts(anc.filter((p) => p.sex === 'M').map(first).filter((n) => /^\p{Lu}/u.test(n))).slice(0, 10);
export const namesWomen = counts(anc.filter((p) => p.sex === 'F').map(first).filter((n) => /^\p{Lu}/u.test(n))).slice(0, 10);

// ——— trades and occupations (each occupation counted once per person) ———
const NOT_OWN = /^(father|mother|son|daughter|brother|sister|father-in-law|son-in-law|daughter-in-law|grandfather|grandson|godparent|godfather|godmother|witness)\b/i;   // someone else's occupation
const occOf = (p) => [...new Set((p.facts ?? []).filter((f) => !NOT_OWN.test(f)).flatMap((f) => {
  const hit = OCCUPATIONS.find(([re]) => re.test(f.split(/\s\((?:son|daughter)|;\s*(?:father|son|daughter)/)[0]));
  return hit ? [hit[1]] : [];
}))];
export const occupations = counts(anc.flatMap(occOf)).slice(0, 16);
export const occPeople = anc.filter((p) => occOf(p).length).length;

// ——— places (from the map: how many ancestors are linked to a place) ———
export const places = (site.places ?? []).filter((pl) => !pl.hypothesis)
  .map((pl) => ({ name: pl.name, count: new Set(pl.lines.flatMap((l) => l.people)).size, years: pl.years }))
  .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, 'en')).slice(0, 14);
export const placeCount = (site.places ?? []).filter((pl) => !pl.hypothesis).length;
export const birthPlaces = counts(anc.map((p) => L.get(p.slug).place).filter((x) => x && /^\p{Lu}/u.test(x) && x.length < 40)).slice(0, 10);

// ——— number of children per family (only children the tree knows: the child in the line + siblings listed with it) ———
const kin = buildKinData(people);
// siblings listed with the child in the line (the same name listed twice counts once)
const sibNames = kin.filter((n) => n.side && n.sib).reduce((m, n) => m.set(n.sib, (m.get(n.sib) ?? new Set()).add(n.n.replace(/\s+(?:jr\.?|junior)$/i, '').toLowerCase())), new Map());
const sibCount = new Map([...sibNames].map(([k, v]) => [k, v.size]));
const STATED = /\bone of (\d{1,2}) children\b/i;   // "Jan was one of 9 children" – number of children of the line child's parents
export const families = Object.values(site.families).map((f) => {
  const kids = f.children.filter((c) => people[c]);
  let n = kids.length + kids.reduce((s, c) => s + (sibCount.get(c) ?? 0), 0);
  const texts = kids.flatMap((c) => people[c].side.map((s) => `${s.name} ${s.text}`));
  for (const t of texts) { const m = t.match(STATED); if (m) n = Math.max(n, Number(m[1])); }
  const par = [f.father, f.mother].filter(Boolean).map((x) => people[x]);
  return { id: f.id, n, href: href.family(f.id), names: par.map((p) => p.name.replace(/\s*\([^)]*\)/g, '')).join(' & ') };
});
export const childHist = [1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => ({ n, count: families.filter((f) => (n === 9 ? f.n >= 9 : f.n === n)).length }));
export const biggestFamilies = [...families].sort((a, b) => b.n - a.n).filter((f) => f.n >= 4).slice(0, 5);

// ——— summary ———
export const summary = {
  ancestors: anc.length,
  documented: anc.filter((p) => p.st === 'doc').length,
  records: recordList.length,
  generations: maxGen + 1,
  lines: Object.keys(lines).length,
  places: placeCount,
  implex: anc.filter((p) => (p.also ?? []).length).length,
};
