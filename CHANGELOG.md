# Changelog

## 0.1.0 – 18 Nov 2026
First release of the English, international edition.

Based on [rodokmen-skill](https://github.com/sarsonj/rodokmen-skill) 0.10.1 by Jindřich Šaršon, translated to English
(guide, tools, website, data format) and extended with the improvements of a long real-world research project.

**New compared with the original**
- Everything in English: the skill, tools, data files and fields, and the website. Claude talks to you in your language.
- Country guides: Czech Republic (archives and ready-made tools) and **Belgium** (new); a general guide for the rest of Europe.
- Second-model checks: an independent model (Claude Fable) re-reads uncertain and key entries from enhanced images;
  every record shows *read by* and *checked by* (AI model with version, or a human genealogist).
- More data checks: evidence of stories, chronology, parents missing in baptisms, facts after death, duplicate ancestors.
- Cases for competing hypotheses (who was the father?) and a proof summary of the main line.
- Readable person summaries; long research notes collapsible on the website; storytelling rules for family texts.
- Family-document workflow (rotate, crop, read, assign to people, credit authors), with blurring of personal ID numbers.
- Website: How are we related?, Statistics, Documents, News page per deployed version, historical events, site
  variants per family side (`data/variants.json`, `tools/deploy_all.sh`).
- More tools: search queue, godparent network, searched-books overview, contact sheets, image enhancement,
  book sieve, Arolsen Archives, newspapers, portal health check.
