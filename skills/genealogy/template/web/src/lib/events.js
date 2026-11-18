// Historical events for the "Life story" timeline on a person's page.
//
// EDITABLE: this is a short, general European selection – events that touched ordinary rural and town families.
// Add, remove or reword events for your own family's regions; keep the list short (a person's page shows at most
// five events from their lifetime). Selection originally inspired (MIT) by tools/udalosti.json from
// zbysekvoda/rodokmen-plus (Zbyšek Voda).
//
// where: list of region codes the event applies to ('*' = everywhere).
// w (weight): 3 = touched everyone, 2 = major, 1 = minor or regional.
// Region of a person = first match of REGIONS against their facts (birth, marriage, death places), otherwise
// the optional "region" (e.g. "belgium") or "country" (e.g. "Belgium", "Czechia") from data/website.json,
// otherwise none – then only '*' events are shown.

import { config } from './data.js';

const CZ = ['bohemia', 'moravia'];
const HABSBURG = ['bohemia', 'moravia', 'slovakia'];
const BE = ['belgium'];
const ALL = ['*'];

export const EVENTS = [
  { from: 1618, to: 1648, where: HABSBURG, w: 3, title: "Thirty Years' War", text: 'armies crossed the land, villages were deserted, many died of hunger and disease' },
  { from: 1620, to: 1620, where: CZ, w: 2, title: 'Battle of White Mountain', text: 'after the defeat of the Estates came re-Catholicisation and the exile of non-Catholics' },
  { from: 1680, to: 1680, where: CZ, w: 3, title: 'Plague and peasant revolt', text: 'a great plague epidemic; rebellious serfs and the first robot (labour duty) patent' },
  { from: 1713, to: 1715, where: CZ, w: 2, title: 'The last great plague', text: 'plague columns were raised in its memory' },
  { from: 1740, to: 1748, where: [...CZ, ...BE], w: 2, title: 'War of the Austrian Succession', text: 'Prussian and French armies in Bohemia; the French occupied the Austrian Netherlands' },
  { from: 1756, to: 1763, where: CZ, w: 2, title: "Seven Years' War", text: 'more wars with Prussia, soldiers quartered in the villages, conscription and war levies' },
  { from: 1767, to: 1767, where: ['slovakia'], w: 2, title: 'Theresian urbarium', text: 'Maria Theresa fixed how much labour duty lords could demand in Hungary' },
  { from: 1770, to: 1772, where: HABSBURG, w: 3, title: 'Great famine', text: 'after failed harvests about a tenth of the population of Bohemia died' },
  { from: 1770, to: 1771, where: CZ, w: 1, title: 'House numbering', text: 'houses received numbers and the inhabitants were listed' },
  { from: 1775, to: 1775, where: CZ, w: 3, title: 'Peasant revolt and robot patent', text: 'labour duty limited to at most three days a week' },
  { from: 1778, to: 1779, where: ['bohemia'], w: 2, title: 'War of the Bavarian Succession ("Potato War")', text: 'Prussian armies marched through north-eastern Bohemia' },
  { from: 1781, to: 1781, where: CZ, w: 3, title: 'Abolition of serfdom', text: "subjects could marry, move and learn a trade without their lord's consent; Patent of Toleration" },
  { from: 1785, to: 1785, where: ['slovakia'], w: 3, title: 'Abolition of serfdom in Hungary', text: 'Joseph II allowed subjects to move and marry without their lord\'s consent' },
  { from: 1789, to: 1790, where: BE, w: 2, title: 'Brabant Revolution', text: 'revolt against Joseph II and the short-lived United Belgian States' },
  { from: 1795, to: 1814, where: BE, w: 3, title: 'French rule', text: 'annexed by France; conscription, and civil registration of births, marriages and deaths from 1796' },
  { from: 1798, to: 1798, where: BE, w: 2, title: "Peasants' War", text: 'rural uprising against French conscription, harshly suppressed' },
  { from: 1805, to: 1809, where: HABSBURG, w: 1, title: 'Napoleonic Wars', text: 'battle of Austerlitz 1805, conscription, high prices' },
  { from: 1811, to: 1811, where: HABSBURG, w: 2, title: 'State bankruptcy', text: 'money lost four fifths of its value' },
  { from: 1815, to: 1815, where: BE, w: 2, title: 'Waterloo and the United Kingdom of the Netherlands', text: 'after Napoleon\'s defeat the region was joined to the Netherlands' },
  { from: 1816, to: 1817, where: ALL, w: 1, title: 'The year without a summer', text: 'a cold summer, failed harvests and high prices' },
  { from: 1830, to: 1831, where: BE, w: 3, title: 'Belgian Revolution and independence', text: 'Belgium broke away from the Netherlands and became a kingdom' },
  { from: 1831, to: 1832, where: CZ, w: 2, title: 'Cholera', text: 'the first great cholera epidemic' },
  { from: 1831, to: 1831, where: ['slovakia'], w: 2, title: 'Cholera and peasant uprising', text: 'cholera epidemic and a revolt of serfs in eastern Slovakia' },
  { from: 1846, to: 1847, where: BE, w: 3, title: 'Flemish famine', text: 'potato blight and the collapse of home linen weaving brought hunger, typhus and emigration' },
  { from: 1848, to: 1848, where: CZ, w: 3, title: 'Revolution and end of labour duty', text: 'end of the robot and of serfdom; farmers became owners of their land' },
  { from: 1848, to: 1849, where: ['slovakia'], w: 3, title: 'Revolution and end of serfdom in Hungary', text: 'end of labour duty; fighting of the Hungarian revolution' },
  { from: 1849, to: 1849, where: BE, w: 2, title: 'Cholera', text: 'the worst cholera epidemic of the century' },
  { from: 1866, to: 1866, where: ['bohemia'], w: 3, title: 'Austro-Prussian War and cholera', text: 'battles of Trutnov and Königgrätz (Hradec Králové); cholera followed the armies' },
  { from: 1866, to: 1866, where: ['moravia'], w: 2, title: 'Austro-Prussian War and cholera', text: 'Prussian armies in Moravia, followed by cholera' },
  { from: 1869, to: 1869, where: CZ, w: 1, title: 'Eight years of compulsory schooling', text: 'the imperial school law' },
  { from: 1914, to: 1918, where: HABSBURG, w: 3, title: 'First World War', text: 'men at the front, shortages and requisitions at home' },
  { from: 1914, to: 1918, where: BE, w: 3, title: 'First World War and German occupation', text: 'invasion, refugees, the front on the Yser, hunger under occupation' },
  { from: 1918, to: 1918, where: HABSBURG, w: 3, title: 'Founding of Czechoslovakia', text: '28 October 1918; the Spanish flu struck as well' },
  { from: 1918, to: 1919, where: BE, w: 2, title: 'Spanish flu', text: 'the influenza pandemic after the war' },
  { from: 1929, to: 1934, where: ALL, w: 2, title: 'Great Depression', text: 'unemployment and poverty' },
  { from: 1938, to: 1938, where: HABSBURG, w: 2, title: 'Munich Agreement', text: 'mobilisation and loss of the border regions' },
  { from: 1939, to: 1945, where: CZ, w: 3, title: 'Protectorate and Second World War', text: 'occupation, forced labour, rationing' },
  { from: 1939, to: 1945, where: ['slovakia'], w: 3, title: 'Slovak State and Second World War', text: 'war; in 1944 the Slovak National Uprising' },
  { from: 1940, to: 1944, where: BE, w: 3, title: 'Second World War and German occupation', text: 'invasion in May 1940, forced labour, rationing; liberation in September 1944' },
  { from: 1948, to: 1948, where: HABSBURG, w: 3, title: 'Communist coup', text: 'the communists took power; nationalisation' },
  { from: 1949, to: 1960, where: HABSBURG, w: 2, title: 'Collectivisation', text: 'private farmers were forced into collective farms' },
  { from: 1968, to: 1968, where: HABSBURG, w: 2, title: 'Prague Spring and invasion', text: 'Warsaw Pact armies invaded in August' },
  { from: 1989, to: 1989, where: HABSBURG, w: 3, title: 'Velvet Revolution', text: 'end of one-party rule' },
  { from: 1993, to: 1993, where: HABSBURG, w: 2, title: 'Dissolution of Czechoslovakia', text: 'the Czech Republic and Slovakia were founded' },
];

// EDITABLE: how a person's region is recognised from the place names in their facts (first match wins).
export const REGIONS = [
  ['slovakia', /Bratislav|Trnav|Nitr|Trenčín|Žilin|Bansk|Zvolen|Martin|Orav|Liptov|Spiš|Tatr|Poprad|Prešov|Košic|Slovak|[ľĽôäŕĺ]/],
  ['moravia', /Brno|Brn[aě]|Morav|Jihlav|Olomouc|Třebíč|Znojm|Zlín|Ostrav/],
  ['belgium', /Belgi|Flanders|Vlaanderen|Wallon|Brabant|Antwerp|Gent\b|Ghent|Brugge|Bruges|Brussel|Bruxelles|Leuven|Louvain|Mechelen|Kortrijk|Ieper|Ypres|Oudenaarde|Aalst|Liège|Namur|Charleroi|Mons\b|Hasselt|Tournai/],
  ['bohemia', /Bohemia|Praha|Prague|Čech|[ěščřžůĚŠČŘŽŮ]/],
];

// EDITABLE: country (website.json "country") → default region.
const COUNTRIES = { belgium: 'belgium', czechia: 'bohemia', 'czech republic': 'bohemia', bohemia: 'bohemia', moravia: 'moravia', slovakia: 'slovakia' };

/** Region of a person from their facts, else website.json region/country, else null. */
export function regionOf(p) {
  const t = (p.facts ?? []).join(' ');
  for (const [region, re] of REGIONS) if (re.test(t)) return region;
  return config?.region || COUNTRIES[String(config?.country ?? '').trim().toLowerCase()] || null;
}

/**
 * A few of the most important events during a person's life: by/dy = year of birth/death (either may be missing).
 * Without death a life of 75 years is assumed (at most until today), without birth 60 years before death.
 * Returns at most `max` events sorted by year, with the person's age at the time (if the birth year is known).
 */
export function eventsFor(p, by, dy, max = 5) {
  if (!by && !dy) return [];
  const now = new Date().getFullYear();
  const from = by ?? dy - 60, to = dy ?? Math.min(now, by + 75);
  const region = regionOf(p);
  const hits = EVENTS.filter((e) => (e.where.includes('*') || (region && e.where.includes(region)))
    && e.to >= from && e.from <= to && (by == null || e.from >= by || e.to >= by + 1));
  // weight first, then evenly through the life; then back to chronological order
  const pick = hits.sort((a, b) => b.w - a.w || a.from - b.from).slice(0, max).sort((a, b) => a.from - b.from);
  return pick.map((e) => ({ ...e, age: by != null ? Math.max(0, e.from - by) : null, when: e.from === e.to ? `${e.from}` : `${e.from}–${e.to}` }));
}
