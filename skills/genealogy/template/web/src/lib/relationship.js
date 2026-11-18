// "How are we related?" – the relationship of two people computed from Kekulé numbers.
// The parents of person k are 2k and 2k + 1; a person appearing in the tree more than once (pedigree collapse, SAME)
// has several numbers (people[x].also), so they may have several children and several paths lead to a common
// ancestor. Side relatives (SIDE) are treated as siblings of the person they are listed with – only when their
// description says so unambiguously ("brother of Jan"), otherwise they are just "relative (…)".
// This file must not import the site data: it also runs in the browser (page /relationship/) and gets data as parameters.

const ORD_WORDS = ['', 'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth'];
const ordinal = (n) => {
  const s = n % 100 >= 11 && n % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' })[n % 10] ?? 'th';
  return `${n}${s}`;
};
const ordWord = (n) => ORD_WORDS[n] ?? ordinal(n);
/** "great-" n times: '', 'great-', 'great-great-', then '3rd great-', '4th great-' … */
export const greats = (n) => (n <= 0 ? '' : n <= 2 ? 'great-'.repeat(n) : `${ordinal(n)} great-`);
const removed = (n) => (n === 1 ? 'once removed' : n === 2 ? 'twice removed' : n === 3 ? 'three times removed' : `${n} times removed`);
const norm = (t = '') => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

// ——— relationship names ———
const F = (s, m, f, x) => (s === 'F' ? f : s === 'M' ? m : x ?? m);
/** Ancestor at distance d (1 = parent). */
export const ancestorTerm = (d, s) =>
  d === 1 ? F(s, 'father', 'mother', 'parent') : `${greats(d - 2)}${F(s, 'grandfather', 'grandmother', 'grandparent')}`;
/** Ancestor couple at distance d (parents, grandparents, great-grandparents …). */
export const ancestorsPlural = (d) => (d === 1 ? 'parents' : `${greats(d - 2)}grandparents`);
/** Descendant at distance d (1 = child). */
export const descendantTerm = (d, s) =>
  d === 1 ? F(s, 'son', 'daughter', 'child') : `${greats(d - 2)}${F(s, 'grandson', 'granddaughter', 'grandchild')}`;
/** Sibling (d = 1) or cousin (d = 2 first cousin, d = 3 second cousin …). */
export const cousinTerm = (d, s, half = false) => {
  if (d === 1) return `${half ? 'half-' : ''}${F(s, 'brother', 'sister', 'sibling')}`;
  return `${ordWord(d - 1)} cousin`;
};

/**
 * Relationship of person A to person B when A is dA generations below the common ancestor and B dB generations.
 * sexA = sex of A; zSex = sex of the link person (B's ancestor at A's level, or A's ancestor at B's level) for the
 * descriptive form. Returns { term, desc } – term is the usual name, desc a description ("sister of
 * great-grandfather"), may be empty.
 */
export function kinTerm(dA, dB, sexA, zSex, half = false) {
  if (dA === 0 && dB === 0) return { term: 'the same person', desc: '' };
  if (dA === 0) return { term: ancestorTerm(dB, sexA), desc: '' };
  if (dB === 0) return { term: descendantTerm(dA, sexA), desc: '' };
  if (dA === dB) return { term: cousinTerm(dA, sexA, half), desc: '' };
  if (dA < dB) {   // A is generation(s) higher: sibling / cousin of B's ancestor
    const z = ancestorTerm(dB - dA, zSex);
    const desc = `${cousinTerm(dA, sexA, half)} of ${z}`;
    if (dA === 1) {
      const n = dB - 2;   // 0 uncle, 1 great-uncle …
      return { term: `${greats(n)}${F(sexA, 'uncle', 'aunt', 'uncle/aunt')}`, desc };
    }
    return { term: `${ordWord(dA - 1)} cousin ${removed(dB - dA)}`, desc };
  }
  // A is generation(s) lower: descendant of B's sibling / cousin
  const desc = `${descendantTerm(dA - dB, sexA)} of ${cousinTerm(dB, zSex, half)}`;
  if (dB === 1) {
    const n = dA - 2;
    return { term: `${greats(n)}${F(sexA, 'nephew', 'niece', 'nephew/niece')}`, desc };
  }
  return { term: `${ordWord(dB - 1)} cousin ${removed(dA - dB)}`, desc };
}

// ——— side relatives: when is it certainly a sibling ———
// "Brother of Jan", "Younger sister of Marie (1890)", "Elder brother of Josef Novák"
const SIB = /(?:^|[,;.]\s+)(?:(?:[Yy]ounger|[Oo]lder|[Ee]lder|[Ee]ldest|[Yy]oungest|[Aa]nother)\s+)?([Ss]ister|[Bb]rother|[Ss]ibling)\s+of\s+(\p{Lu}\p{Ll}+)(?:\s+\p{Lu}\p{Ll}+)?(?:\s*\((\d{1,4})\))?/u;
const UNSURE = /half-|step|illegitimate|previously (?:thought|considered)|perhaps|possibly|probably|\(\?\)|\bc\. /i;

/** Sex from an explicit `sex` field or from a kinship word in the name or description; otherwise unknown. */
export function guessSex(side, word = '') {
  if (side.sex === 'M' || side.sex === 'F') return side.sex;
  const t = `${word} ${side.text ?? ''}`.slice(0, 120);
  if (/\b(sister|daughter|aunt|niece|wife|widow|mother)\b/i.test(t)) return 'F';
  if (/\b(brother|son|uncle|nephew|husband|widower|father)\b/i.test(t)) return 'M';
  return null;
}

/**
 * Find whose sibling a side relative is. ownerK = number of the person they are listed with; candidates are that
 * person, their parents and their child (entries like "Younger brother of Ladislav" are often listed with
 * Ladislav's father). The first name decides, and if names repeat, the birth year in brackets. Returns { k, word } or null.
 */
export function sideSibling(side, ownerK, personByK) {
  if (/\sand\s|&|^siblings/i.test(side.name) || UNSURE.test(side.text.slice(0, 80))) return null;
  for (const src of [side.text, side.name]) {
    const m = src.match(SIB);
    if (!m) continue;
    const [, word, given, num] = m;
    const cands = [ownerK, ownerK >> 1, 2 * ownerK, 2 * ownerK + 1].filter((k) => k >= 1 && personByK[k]);
    const stem = norm(given).slice(0, 3);
    let hit = cands.filter((k) => norm(personByK[k].name.replace(/^\(?\?\)?\s*/, '')).slice(0, 3) === stem);
    if (hit.length > 1 && num && num.length === 4 && /^(1[5-9]|20)/.test(num)) hit = hit.filter((k) => (personByK[k].years || '').includes(num));
    if (hit.length === 1) return { k: hit[0], word };
    return null;
  }
  return null;
}

/**
 * Data for the computation from site.json (people). Returns a list of nodes: people of the tree (id = slug) and
 * side relatives (id = slug~i). Compact so that it can be embedded into the page.
 */
export function buildKinData(people) {
  const byK = {};
  for (const p of Object.values(people)) {
    byK[p.k] = p;
    for (const a of p.also ?? []) byK[a.k] = p;
  }
  const nodes = [];
  for (const p of Object.values(people).sort((a, b) => a.k - b.k)) {
    nodes.push({ id: p.slug, n: p.name, y: p.years, s: p.sex, k: [p.k, ...(p.also ?? []).map((a) => a.k)], st: p.st });
  }
  for (const p of Object.values(people).sort((a, b) => a.k - b.k)) {
    (p.side ?? []).forEach((sd, i) => {
      const sib = sideSibling(sd, p.k, byK);
      const nm = sd.name.replace(/\s*\([^)]*\)\s*$/, '').trim();
      const y = (sd.name.match(/\(([^)]*\d{4}[^)]*)\)\s*$/) || [])[1] ?? '';
      nodes.push({ id: `${p.slug}~${i}`, n: nm, y, s: guessSex(sd, sib?.word), side: 1,
        sib: sib ? byK[sib.k].slug : null, of: p.slug, t: sd.text.slice(0, 160) });
    });
  }
  return nodes;
}

/** Index over the nodes (in the browser and at build time). */
export function indexKin(nodes) {
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const byK = {};
  for (const n of nodes) if (!n.side) for (const k of n.k) byK[k] = n.id;
  const children = {};   // id → children (people whose parent it is)
  const canon = (n) => n.k[0];
  const parents = (id) => {
    const n = byId[id];
    if (!n) return [];
    if (n.side) {
      if (!n.sib) return [];
      return parents(n.sib);
    }
    const k = canon(n);
    return [2 * k, 2 * k + 1].map((x) => byK[x] ?? `#${x}`);
  };
  for (const n of nodes) for (const p of parents(n.id)) (children[p] ??= []).push(n.id);
  return { nodes, byId, byK, parents, children };
}

/** Ancestors of a node including multiple paths (pedigree collapse): map id → Map(d → previous state "id@d" one generation lower). */
function ancestors(ix, id) {
  const seen = new Map([[id, new Map([[0, null]])]]);
  let front = [[id, 0]];
  for (let d = 1; front.length && d < 40; d++) {
    const next = [];
    for (const [x, dx] of front) {
      if (String(x).startsWith('#')) continue;   // unknown parent – leads no higher
      for (const p of ix.parents(x)) {
        const m = seen.get(p) ?? new Map();
        if (m.has(d)) continue;
        m.set(d, `${x}@${dx}`);
        seen.set(p, m);
        next.push([p, d]);
      }
    }
    front = next;
  }
  return seen;
}
const minD = (anc, id) => Math.min(...anc.get(id).keys());
/** Path [start, parent, …, ancestor] to ancestor id at distance d. */
const chain = (anc, id, d) => {
  const out = [];
  let key = `${id}@${d}`;
  while (key) {
    const i = key.lastIndexOf('@');
    const x = key.slice(0, i), dx = Number(key.slice(i + 1));
    out.push(x);
    key = anc.get(x).get(dx);
  }
  return out.reverse();
};
const sexOf = (ix, id) => {
  if (String(id).startsWith('#')) return Number(id.slice(1)) % 2 ? 'F' : 'M';
  return ix.byId[id]?.s ?? null;
};

/**
 * All relationships A ↔ B. Returns { same, blood: [{ cas: [id…], dA, dB, pathA, pathB, half, a: {term,desc}, b: {term,desc} }],
 * descendant: { id, dA, dB } | null, spouse: bool, inLaw: … }. (cas = the common ancestor(s).)
 */
export function relate(ix, aId, bId) {
  if (aId === bId) return { same: true, blood: [] };
  const A = ancestors(ix, aId), B = ancestors(ix, bId);
  const common = [...A.keys()].filter((x) => B.has(x));
  const cset = new Set(common);
  // nearest common ancestors: none of their children on the paths is a common ancestor any more
  const lowest = common.filter((c) => !(ix.children[c] ?? []).some((ch) => cset.has(ch)));
  // group married couples at the same distance
  const groups = [];
  const dist = (c) => minD(A, c) + minD(B, c);
  for (const c of lowest.sort((x, y) => dist(x) - dist(y))) {
    // all pairs of distances (with pedigree collapse several paths to the same ancestor), shortest first
    const combos = [...A.get(c).keys()].flatMap((da) => [...B.get(c).keys()].map((db) => [da, db]))
      .sort((x, y) => x[0] + x[1] - (y[0] + y[1]) || x[0] - y[0]);
    for (const [dA, dB] of combos) {
      const g = groups.find((g) => g.dA === dA && g.dB === dB && g.cas.some((o) => spouses(ix, o, c)));
      if (g) g.cas.push(c); else groups.push({ cas: [c], dA, dB });
    }
  }
  groups.sort((x, y) => x.dA + x.dB - (y.dA + y.dB));
  const blood = groups.map((g) => {
    const c = g.cas[0];
    const pathA = chain(A, c, g.dA), pathB = chain(B, c, g.dB);
    const half = g.cas.length === 1 && !String(c).startsWith('#') && g.dA > 0 && g.dB > 0 && hasOtherParent(ix, pathA, pathB);
    // link person for the description: ancestor of the older one at the younger one's level
    const z = (dX, dY, pathX, pathY) => sexOf(ix, dX < dY ? pathY[dY - dX] : pathX[dX - dY]);
    const a = kinTerm(g.dA, g.dB, sexOf(ix, aId), z(g.dA, g.dB, pathA, pathB), half);
    const b = kinTerm(g.dB, g.dA, sexOf(ix, bId), z(g.dB, g.dA, pathB, pathA), half);
    return { ...g, pathA, pathB, half, a, b };
  });
  // no blood tie: nearest common descendant (prefix of Kekulé numbers) and spouses / in-laws
  const nA = ix.byId[aId], nB = ix.byId[bId];
  let spouse = false, inLaw = null;
  const desc = new Map();   // common descendants (number prefix) – with pedigree collapse possibly several
  const ks = (n) => (n && !n.side ? n.k : []);
  for (const ka of ks(nA)) for (const kb of ks(nB)) {
    if ((ka ^ 1) === kb && ka > 1) spouse = true;
    let x = ka, y = kb, da = 0, db = 0;
    while (x !== y) { if (x > y) { x >>= 1; da++; } else { y >>= 1; db++; } }
    const id = ix.byK[x];
    if (id && (!desc.has(id) || da + db < desc.get(id).dA + desc.get(id).dB)) desc.set(id, { id, dA: da, dB: db, kA: ka, kB: kb });
    if (ka > 1 && kb > 1 && (ka >> 1) === (kb ^ 1)) inLaw = { parent: 'a' };   // A is a parent of B's spouse
    if (ka > 1 && kb > 1 && (kb >> 1) === (ka ^ 1)) inLaw = { parent: 'b' };
  }
  // nearest first; with pedigree collapse several paths may lead to descendants (each via another number)
  const descendants = [...desc.values()].sort((x, y) => x.dA + x.dB - (y.dA + y.dB));
  const descendant = descendants[0] ?? null;
  return { same: false, blood, descendant, descendants, spouse, inLaw };
}

function spouses(ix, x, y) {
  const n = (id) => (String(id).startsWith('#') ? [Number(id.slice(1))] : ix.byId[id]?.side ? [] : ix.byId[id]?.k ?? []);
  return n(x).some((a) => n(y).some((b) => (a ^ 1) === b));
}
/** Half relationship: at the common ancestor both have a different (known) other parent. */
function hasOtherParent(ix, pathA, pathB) {
  const childA = pathA[pathA.length - 2], childB = pathB[pathB.length - 2];
  const pa = ix.parents(childA), pb = ix.parents(childB);
  return pa.length === 2 && pb.length === 2 && pa.some((p) => !pb.includes(p)) && !pa.every((p) => String(p).startsWith('#'));
}

/** Father-/mother-in-law and son-/daughter-in-law. */
export const inLawTerms = (sexParent, sexChild) => ({
  parent: F(sexParent, 'father-in-law', 'mother-in-law', 'parent-in-law'),
  child: F(sexChild, 'son-in-law', 'daughter-in-law', 'child-in-law'),
});
