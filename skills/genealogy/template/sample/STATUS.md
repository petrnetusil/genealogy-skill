# Family tree status and working rules

This file is the entry point. After every restart (new conversation, shortened context) Claude reads it first,
then the end of `research_log.md` and the section "Work in progress".

## For whom
- Root person: (fill in – name, year and place of birth)
- Who works with Claude and how they like to communicate (language, level of detail): (fill in)

## What is where
| File | Content |
|---|---|
| `data/people.py` | Direct ancestors by Kekulé number + family lines, side relatives, open questions, hypotheses. |
| `data/records.json` | Every register record used (key = image name). |
| `data/volumes.json` | Register volumes (archive, reference, link). |
| `data/transcripts.json` | Transcription of the original and English translation of each record. |
| `data/highlights.json` | Frames – which part of the crop we read. |
| `data/research_log.md` | Log of ALL searches, including unsuccessful ones. |
| `data/family_info.md` | What the family said, family documents. |
| `data/curiosities.md`, `data/story.md` | Texts for the website. |
| `data/archive_requests.md`, `data/offline_sources.md` | What could only be found in an archive reading room or office. |
| `data/places.json`, `data/documents.json`, `data/website.json` | Map, family photos and documents, website settings. |
| `data/lines.json`, `data/memories.json` | Short stories of the family lines, family memories per person. |
| `data/variants.json`, `data/watched.json` | Optional partial websites (one branch each), watched repositories/archives. |
| `data/proof_summary.md`, `data/sensitive_review.md` | Proof arguments for difficult links, sensitive details awaiting approval. |
| `data/cases/` | Case files for hard problems (competing candidates, see `tools/cases.py`). |
| `crops/`, `sources/` | Record crops for the website (1800 px) and in full resolution. |
| `documents/` | Family documents and photos from the user (originals). |
| `work/` | Working files (downloaded pages, check images) – not for the website. |
| `web/` | Family website. `cd web && npm run preview` (data + build + preview); after data changes `npm run data && npm run build` is enough. |

## Rules
1. Before announcing anything as new, search `people.py`, `records.json` and `research_log.md` (name, place, year).
2. A detail is "documented" (doc) only when I have read it directly on the image. I check readings by helpers myself.
3. Every search (even unsuccessful) goes into `research_log.md`.
4. Uncertain readings are marked (?) – nothing is guessed.
5. For every new record: crop (`tools/crop.py`), frame (`tools/frame.py`) and transcription with translation.
6. After changing data I run `python3 -I tools/check.py`.

## Work in progress (keep updated)
- (nothing yet)
