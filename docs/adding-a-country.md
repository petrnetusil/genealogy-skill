# Adding a country

The research method is universal; what differs between countries are the record types, the archives and their
portals. A country is supported by:

1. **A country guide** – `skills/genealogy/reference/countries/<country>.md`. Use the Belgium and Czech Republic guides
   as models. Cover:
   - record types and their periods (parish registers, civil registration, censuses/population registers,
     land records, notarial records, military),
   - access rules (how many years until records are public),
   - portals: what is online, whether an account is needed, whether images can be downloaded,
   - languages and a glossary of the most common words in records,
   - a step-by-step workflow and where to get human help (societies, reading rooms),
   - sources with links.
   Add the country to `reference/countries/README.md`.
2. **Optional tools** – a script that finds volumes or downloads images from a portal *that allows it*. Every network
   request must go through `tools/polite.py`; add the host with a conservative limit. Never automate logins,
   never scrape paid services.
3. **Tests** – offline tests with saved HTML samples (see `tests/`).

Open a pull request or an issue with your guide. Please do not include personal data of anyone.
