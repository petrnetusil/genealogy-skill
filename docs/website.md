# The family website

The website is generated from your project data. You never edit HTML – you tell Claude what to change.

## What is on it
- **Home**: introduction, family story teaser, curiosities, map, the family lines, fan chart.
- **Ancestors** (pedigree), **Lines** (the eight great-grandparent lines), **Families**, a page for every **person**
  with a short readable summary and collapsible research notes.
- **Records**: every register entry as an image crop with the exact place highlighted, transcription, translation,
  who read and who checked it.
- **Stories**, **Curiosities**, **Documents** (family certificates and photos), **Map**, **Statistics**,
  **How are we related?**, **Open questions**, **Research log**, **News** (what is new in each version).

## Preview
Say *"Show me the website."* Claude runs `tools/export_web.py` and the local preview (`npm run preview` in `web/`).

## Publishing
Claude publishes only when you ask, and only when a **family question** is set (data/website.json → `gate`):
visitors must answer e.g. *"What was grandma's dog called?"*. Supported hosting:
- **Cloudflare Workers** (recommended, free): you create the account; Claude runs the deployment.
- **Netlify** (free), or your own server (Docker/nginx, CapRover).

Every deployment becomes a new entry on the **News** page (version number, date, what was added). Deploy in larger
batches rather than after every small change.

## Several websites (optional)
You can publish separate websites for different family sides, e.g. your father's ancestors and your mother's,
each with its own family question. Define them in `data/variants.json`:
```json
[
  {"name": "father", "root": 2, "title": "The Dubois family", "gate": {"question": "…", "answer": "…"}, "domain": ""},
  {"name": "mother", "root": 3, "title": "The Peeters family", "gate": {"question": "…", "answer": "…"}, "domain": ""}
]
```
`tools/deploy_all.sh` then deploys the main site and every variant and checks that each one is protected
(it expects HTTP 401 without the answer).

## Sensitive content
Before publishing, Claude goes through sensitive items with you (illegitimate births, crimes, illnesses, causes of
death of recently deceased people, political persecution). Only what you approve goes online. Living people appear
with name and birth year only.
