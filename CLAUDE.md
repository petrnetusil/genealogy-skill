# Maintaining genealogy-skill

Releasing a new version: bump the number in three places at once – `.claude-plugin/plugin.json` (`version`),
`skills/genealogy/VERSION` (Claude uses it to offer users a project update) and README ("Current version: X.Y.Z (date)").
Add a section `## X.Y.Z – D Mon YYYY` at the top of `CHANGELOG.md` (New / Fixes / Guides, short user-facing bullets).
After commit and push, create a tag and a GitHub release with that section as notes:
`awk '/^## X.Y.Z /{f=1;next} /^## /{f=0} f' CHANGELOG.md > /tmp/notes.md && gh release create vX.Y.Z --target main --title "X.Y.Z" --notes-file /tmp/notes.md`.
When the format between `tools/` and `template/web/` changes, also test updating a project created with the previous
version (`new_project.py` on the same folder, `npm install`, `npm run data`, `npm run build`).
Never commit personal data: the sample family in `template/sample/` is fictional.
