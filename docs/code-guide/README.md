# Maintaining the code guide

The guide explains the current Python code in plain words. Open [the built guide](../code-guide.html) in a browser; viewing needs no server, dependencies, or network connection.

## Where to edit

| File                                       | Purpose                                                                                                 |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| `pages/*.md`                               | One walkthrough per source file, plus the overview and test-suite introduction. Edit explanations here. |
| `template.html`                            | The shared header, sidebar container, and page layout.                                                  |
| `styles.css`                               | Shared design tokens and styles; Tailwind compiles its utility rules.                                   |
| `assets/guide.js`                          | Search, page navigation, table of contents, and copy buttons.                                           |
| `build.mjs`                                | Reads Markdown, builds navigation, renders pages, and checks coverage and links.                        |
| `package.json` / `package-lock.json`       | Pinned build tools and reproducible dependency versions.                                                |
| `../code-guide.html` / `assets/styles.css` | Generated output. Rebuild rather than editing these directly.                                           |

## Rebuild after an edit

Use Node.js 22 or newer. From the repository root:

```sh
cd docs/code-guide
npm ci
npm run build
npm run check
```

`npm ci` is needed on first setup or after dependency changes. It installs build tools and may need network access; building and viewing the guide use local files. `node_modules/` and npm debug logs are ignored by Git.

Keep generated HTML and CSS with the guide so readers can open it without running the build. If moving or sharing the output, keep the `code-guide/assets/` directory at the same relative location.

## Add a walkthrough

Create `pages/your-module.md` with metadata like this:

```yaml
---
id: your-module
title: your_module.py
group: Shared foundations
order: 50
updated: "2026-11-08"
source: src/fynd/your_module.py
summary: Explains what the file receives, does, and returns.
related: [models, cache]
---
```

Then write ordinary Markdown with these headings:

```markdown
## Why this file exists

Explain what would be difficult or repeated without it.

## The flow

1. **Input**

   Say what the caller supplies.

2. **Work**

   Say what changes or gets checked.

3. **Output**

   Say what the caller receives.

## A small example

Use a short fenced code block.

## The pieces inside

| Name            | What it does         |
| --------------- | -------------------- |
| `function_name` | A brief explanation. |
```

The first word after an opening code fence is the language; remaining words become the example’s label. For example, an opening fence of three backticks followed by `python A cache lookup` labels the example “A cache lookup”.

The sidebar, search text, heading anchors, and related-file links are generated. `updated` records the date you last checked the explanation against the code. `order` controls page order, and groups appear in the order of their first page. Use an existing group name to keep related files together. `navTitle` optionally gives a long page title a shorter navigation label. `note` optionally adds a plain-text implementation note. Pages without a source path, such as the overview, can omit `source`.

## Keep the guide accurate

Update the relevant page when described behaviour changes. Distinguish current implementation from intended product behaviour, and label invented examples as illustrative. Avoid copying measurements into prose when a link to the measurement file will do.

The check fails for missing Python source walkthroughs, duplicate page IDs or source paths, broken related-page links, missing local files, duplicate HTML anchors, inline CSS/JavaScript, and stale generated HTML. It checks structure and coverage, not whether an explanation is factually correct or accessible in every browser. Review meaning alongside code changes.

## Styling and interaction

Reuse the shared layout and CSS classes instead of adding markup for each page. Colour, type, and surface choices live in the token block in `styles.css`. Tailwind utilities are compiled locally, so there is no CDN dependency. Responsive rules and print styles also live in that file.

Keep `assets/guide.js` as a regular deferred script: browser modules and fetched JSON can be restricted when the guide is opened directly from disk. Markdown is rendered at build time, so the browser does not load content files or a Markdown parser. With JavaScript off, all walkthroughs remain readable.
