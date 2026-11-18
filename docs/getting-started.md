# Getting started – a guide for complete beginners

This guide takes you from zero to your first documented ancestor. You do not need to know anything about
genealogy or programming. Plan about one hour for the setup and the family interview.

## 1. Install Claude Code
1. Get a Claude subscription (Pro to try, Max for a whole family tree) at [claude.com](https://claude.com).
2. Install **Claude Code** – the desktop app (Mac/Windows) is the easiest. Log in.

## 2. Install the skill
In Claude Code type:
```
/plugin marketplace add petrnetusil/genealogy-skill
/plugin install genealogy@genealogy-skill
```
Restart Claude Code. (Manual installation without plugins is described in the [README](../README.md#installation).)

If your ancestors come from regions whose archives work only in a web browser, or you want to use FamilySearch,
also install the browser plugin:
```
/plugin install playwright@claude-plugins-official
```

## 3. Start your project
Say: *"I want to build my family tree."* Claude will:
- check that Python, Node.js, ImageMagick and git are installed and help you install what is missing
  (you approve every installation),
- ask where to create the project (default `~/Genealogy`),
- offer the optional **network guard** – a tiny safety check that keeps all downloads polite to archives.
  Saying yes is recommended.

From now on, **always open Claude Code in this project folder**. Claude reads `data/STATUS.md` and continues where you
stopped. You can close the app at any time – nothing is lost.

## 4. The family interview (the most valuable hour)
Claude asks step by step about you (or the person the tree is for), your parents, grandparents and great-grandparents:
names (women with their maiden names), years and places of birth, marriages, deaths, occupations, house addresses.
Answer what you know; "I don't know" is a perfectly good answer.

Then collect **documents**: birth/baptism and marriage certificates, death notices and prayer cards, family books,
letters, photos with notes on the back, an exported tree from MyHeritage/Geni/FamilySearch (GEDCOM). A phone photo is
enough. Put them into the `documents/` folder of the project and tell Claude. Claude rotates, crops and reads them,
assigns them to the right people and compares them with what it already knows.

**Ask your oldest relatives now**, while you can. Claude can prepare a list of questions for them.

## 5. Into the archives
Claude starts with the youngest ancestor who has no document yet and looks for the **youngest event** of that person
(death, then marriage, then baptism) – that is the fastest way back in time. It finds the right register book,
downloads the page, reads the entry, saves a crop with the place highlighted, writes a transcription and translation,
and records the person. Every search, including failures, goes into the research log.

Your role: decide when there are two possible readings or two candidate ancestors. Claude shows you the crop and its
reasoning.

Typical things to say:
- *"Continue."* – Claude picks the next most promising branch.
- *"Go as deep as possible on my father's side."*
- *"Show me the crop of that baptism."*
- *"Let the independent model check the uncertain readings."*
- *"Write the story of the family for my relatives."*

## 6. The website
Say *"Show me the website."* Claude builds a preview that opens in your browser. When you are happy, Claude helps you
publish it – see [website.md](website.md).

## Costs and time
A tree with a few hundred ancestors takes many sessions. Archives are free (FamilySearch needs a free account).
Publishing on Cloudflare or Netlify is free for a family website.

## When to ask a human
If you hit a wall (missing registers, contradicting sources, a line that matters legally), contact a professional
genealogist or a genealogical society. Your project – with a source and an image for every fact – is an excellent
starting point for them.
