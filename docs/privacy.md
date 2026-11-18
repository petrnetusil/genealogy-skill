# Privacy and ethics

Genealogy is about real people – many of them close relatives, some still alive. The skill follows these rules,
and so should you.

## Living people
- On the website: **name and year of birth only**. No addresses, no exact birth dates, no photos without consent.
- In issues, e-mails to the skill author or public places: no data about living people at all.

## Sensitive information
Illegitimate births, adoptions, crimes and prison, diseases and causes of death, suicides, political persecution,
religion conversions in recent times – Claude lists such findings in `data/sensitive_review.md` and asks you. Only
what you approve is published (`data/website.json` → `sensitive_approved`). Ask yourself: would the descendants mind?

## Recent documents
Certificates from the last ~100 years often show personal ID numbers, exact addresses and medical causes of death.
Claude blurs ID numbers and causes of death on images before they go to the website.

## Your project
Everything stays on your computer. The website is protected by a family question and excluded from search engines,
but anyone who knows the answer sees everything. Back up your project – to a **private** repository or a disk.

## Archives and their rules
Respect the terms of use of each archive and portal: some allow downloads for private research only, some forbid
publishing images. When in doubt, publish your transcription and a link instead of the image. Never let Claude handle
your passwords: you log in yourself.

## Being polite to archives
All tools share a rate limit per website (`tools/polite.py`). Archives that feel overloaded block whole networks –
for hours. Never bypass the brake.
