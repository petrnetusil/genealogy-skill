# Privacy, ethics and third-party services

## Living people
- On the website only name and birth year (`note="Living – basic data only."`). No addresses, phone numbers,
  personal ID numbers, health data, divorces, illegitimate children of living or recently deceased people without
  the family's consent.
- Data from family trees (GEDCOM) and from relatives are often exactly that – fine for research, on the website only
  with consent.
- In Europe the GDPR applies to living people; a private, password-protected family website with basic data is the
  safe way.

## Sensitive content – only after the user's approval
Sensitive are: illegitimacy, crime and prison, illness and disability, suicide, **causes of death of the recently
deceased**, political activity and persecution (also victims of war and dictatorship), religion and conversions in
the 20th century, divorces, debts, family conflicts. Register data older than the closing periods are public, but
consideration applies to them too (no ridicule).
1. **Collect** every sensitive finding in `data/sensitive_review.md` with three sections:
   - *Pending* (finding, source, whom it concerns, what must be verified first),
   - *Decided – do not publish* (finding, reason),
   - *Decided – published with this wording* (the exact approved wording).
2. **Ask the user** – once per finding, with the proposed wording; do not decide for them.
3. Approved snippets go into `website.json` → `sensitive_approved` (a list of text snippets, e.g.
   `["died in the asylum"]`) – `check.py` then stops reporting them as `SENSITIVE`. The snippet must contain the
   reported word; when the text changes, it is reported again.
4. Go through `sensitive_review.md` again before every deploy.

`python3 -I tools/check.py` reports `SENSITIVE` for texts from roughly the last 100 years (suicide, illness,
divorce, debts, illegitimate child…) that go to the website – in people's notes and summaries, in "Open questions"
(`ISSUES`), side relatives, curiosities, stories and memories.

## Images of recent documents
On certificates and register extracts of roughly the last 100 years **blur or crop away personal ID numbers (birth
numbers, social security numbers) and causes of death** before the image goes to the website (keep the original in
`documents/`). Example with ImageMagick: `magick in.jpg -region 600x80+400+1200 -blur 0x12 out.jpg` (region =
width x height + left + top in pixels), then check the result visually.

## Before publishing go through with the user
1. The list of living people on the website and what the website says about them.
2. Family photos and documents – do the people on them (or their families) agree? Is the author of each photo and
   caption credited?
3. `data/sensitive_review.md` – nothing pending that would go to the website.
4. The gate question and answer (`website.json`) – set and hard enough?
5. Contact on the website – does the user want their e-mail there?
Only then publish (`npm run deploy-cloudflare`, or `npm run deploy` for Netlify, or `bash tools/deploy_all.sh` with
site variants – see `web.md`).

## Paid and third-party services (MyHeritage, Ancestry, Geni, FamilySearch, national library accounts)
- Logins, payments and subscriptions are handled **only by the user**. They log in themselves in their own browser
  window; you never type or store passwords. Free trials turn into paid subscriptions automatically – remind the user
  when the trial ends and where to cancel it.
- **No mass browsing or downloading.** A real experience: an automated download of ~180 records from MyHeritage got
  the account blocked "for possible misuse" – in the middle of a paid trial. Read only individual records that are
  needed, at a human pace; rather ask the user for an export (GEDCOM) or specific pages.
- Data from there are status `mh` and are always verified in the registers.
- Some portals with sensitive data (victims, prisoners) ask the user to accept terms when entering; the skill's tools
  for them require the user to confirm the terms personally (`consent` command run by the user with `!`). You never
  confirm it for them.
- Works that may only be read (e.g. out-of-commerce works in national digital libraries): read, take notes with page
  references, do not download or print.

## Archive portals
They are free and public, but servers have limited capacity: download only images you really read, no whole volumes
at once, at most a few parallel requests (the brake `tools/polite.py` takes care of scripts). Always cite to the level
of the image (so it can be checked).

## Data in git and sharing
The project contains the family's personal data. If the user wants it on GitHub, then **only as a private
repository**.
