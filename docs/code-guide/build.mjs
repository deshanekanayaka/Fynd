/** Builds the local code guide from Markdown pages and a shared HTML layout. */
import { readFile, readdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import matter from "gray-matter";
import MarkdownIt from "markdown-it";

const guideDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryDirectory = path.resolve(guideDirectory, "../..");
const outputPath = path.resolve(guideDirectory, "../code-guide.html");
const checkOnly = process.argv.includes("--check");
const markdown = new MarkdownIt({ html: false });
const escape = markdown.utils.escapeHtml;

/** Collects Python files recursively so a new module cannot go undocumented. */
async function pythonFiles(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory() && entry.name !== "__pycache__") {
      files.push(...(await pythonFiles(entryPath)));
    } else if (entry.isFile() && entry.name.endsWith(".py")) {
      files.push(path.relative(repositoryDirectory, entryPath));
    }
  }
  return files;
}

/** Reads page metadata and Markdown in the declared navigation order. */
async function readPages() {
  const pages = [];
  const directory = path.join(guideDirectory, "pages");
  for (const filename of (await readdir(directory)).sort()) {
    if (!filename.endsWith(".md")) continue;
    const { data, content } = matter(
      await readFile(path.join(directory, filename), "utf8"),
    );
    for (const field of ["id", "title", "group", "summary", "updated"]) {
      if (typeof data[field] !== "string" || !data[field].trim()) {
        throw new Error(`${filename}: ${field} must be a non-empty string.`);
      }
    }
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(data.updated) ||
      Number.isNaN(Date.parse(data.updated))
    ) {
      throw new Error(
        `${filename}: updated must be an ISO date such as 2026-11-08.`,
      );
    }
    if (!/^[a-z0-9-]+$/.test(data.id) || !Number.isFinite(data.order)) {
      throw new Error(
        `${filename}: use a lowercase hyphenated id and numeric order.`,
      );
    }
    if (
      !Array.isArray(data.related) ||
      data.related.some((id) => typeof id !== "string")
    ) {
      throw new Error(`${filename}: related must be a list of page IDs.`);
    }
    if (data.source !== undefined && typeof data.source !== "string") {
      throw new Error(
        `${filename}: source must be a repository-relative path.`,
      );
    }
    pages.push({ ...data, content, filename });
  }
  pages.sort(
    (left, right) =>
      left.order - right.order || left.id.localeCompare(right.id),
  );
  const ids = pages.map((page) => page.id);
  if (new Set(ids).size !== ids.length)
    throw new Error("Page IDs must be unique.");
  if (pages[0]?.id !== "overview")
    throw new Error("The first page must be overview.");
  for (const page of pages) {
    for (const id of page.related) {
      if (!ids.includes(id))
        throw new Error(`${page.filename}: unknown related page ${id}.`);
    }
  }
  const documented = pages.map((page) => page.source).filter(Boolean);
  if (new Set(documented).size !== documented.length) {
    throw new Error("Each source path must have only one walkthrough.");
  }
  const missing = (
    await pythonFiles(path.join(repositoryDirectory, "src/fynd"))
  ).filter((filename) => !documented.includes(filename));
  if (missing.length)
    throw new Error(`Add walkthroughs for: ${missing.join(", ")}.`);
  return pages;
}

// These shared sections keep their existing bookmark IDs after the migration.
const sectionIds = new Map([
  ["Why this file exists", "why"],
  ["The flow", "flow"],
  ["A small example", "example"],
  ["The pieces inside", "functions"],
]);
markdown.renderer.rules.heading_open = (
  tokens,
  index,
  options,
  environment,
  renderer,
) => {
  const text = tokens[index + 1].content;
  const slug =
    sectionIds.get(text) ||
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  const base = `${environment.id}-${slug}`;
  let id = base;
  for (let suffix = 2; environment.headings.has(id); suffix++)
    id = `${base}-${suffix}`;
  environment.headings.add(id);
  tokens[index].attrSet("id", id);
  return renderer.renderToken(tokens, index, options);
};
markdown.renderer.rules.table_open = () => '<div class="table-wrap"><table>\n';
markdown.renderer.rules.table_close = () => "</table></div>\n";
markdown.renderer.rules.ordered_list_open = () => '<ol class="flow">\n';
markdown.renderer.rules.fence = (tokens, index) => {
  const token = tokens[index];
  const label = token.info.trim().split(/\s+/).slice(1).join(" ") || "Example";
  return (
    `<figure class="code-block"><figcaption><span>${escape(label)}</span>` +
    `<button class="copy" type="button" aria-label="Copy ${escape(label)}">Copy</button>` +
    `</figcaption><pre><code>${escape(token.content.trimEnd())}</code></pre></figure>\n`
  );
};

/** Builds the sidebar from page metadata rather than a second hand-maintained list. */
function navigation(pages) {
  let result = "";
  const groups = new Map();
  for (const page of pages) {
    if (!groups.has(page.group)) groups.set(page.group, []);
    groups.get(page.group).push(page);
  }
  for (const [group, items] of groups) {
    result += `<section class="nav-group"><h2>${escape(group)}</h2>\n`;
    for (const page of items) {
      // Search includes walkthrough text, so new function names need no search config.
      const search = `${page.title} ${page.summary} ${page.content}`.replace(
        /\s+/g,
        " ",
      );
      result +=
        `<a class="nav-link" href="#${page.id}" data-search="${escape(search)}">` +
        `${escape(page.navTitle || page.title)}</a>\n`;
    }
    result += "</section>\n";
  }
  return result;
}

/** Renders one walkthrough using the same heading, example, and related-file components. */
function article(page, pages) {
  let result =
    `<article id="${page.id}" data-title="${escape(page.navTitle || page.title)}" data-group="${escape(page.group)}">\n` +
    `<div class="eyebrow">${escape(page.group)}</div>\n` +
    `<h1 tabindex="-1">${escape(page.title)}</h1>\n<p class="lead">${escape(page.summary)}</p>\n`;
  if (page.source) {
    result +=
      `<a class="source-link" href="../${escape(page.source)}" target="_blank" rel="noopener">` +
      `${escape(page.source)} <span aria-hidden="true">↗</span></a>\n`;
  }
  result += markdown.render(page.content, { id: page.id, headings: new Set() });
  if (page.note) {
    result +=
      `<aside class="note" aria-label="Current implementation"><strong>Keep in mind</strong>` +
      `<p>${escape(page.note)}</p></aside>\n`;
  }
  if (page.related.length) {
    result += `<h2 id="${page.id}-related">Connected files</h2><div class="related-grid">\n`;
    for (const id of page.related) {
      const linked = pages.find((item) => item.id === id);
      result +=
        `<a href="#${id}" class="related-link"><span>${escape(linked.navTitle || linked.title)}</span>` +
        '<span aria-hidden="true">↗</span></a>\n';
    }
    result += "</div>\n";
  }
  return result + "</article>\n";
}

/** Refuses broken anchors, missing local files, and inline styles or scripts. */
async function checkDocument(html) {
  if (
    /<style\b|\sstyle=|\son\w+=/i.test(html) ||
    /<script(?![^>]*\bsrc=)/i.test(html)
  ) {
    throw new Error("Keep CSS and JavaScript in external files.");
  }
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
  if (new Set(ids).size !== ids.length)
    throw new Error("Generated HTML has duplicate IDs.");
  for (const [, link] of html.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
    if (/^(https?:|mailto:)/.test(link)) continue;
    if (link.startsWith("#")) {
      if (!ids.includes(link.slice(1)))
        throw new Error(`Broken anchor: ${link}`);
    } else {
      const target = path.resolve(path.dirname(outputPath), link);
      if (!target.startsWith(repositoryDirectory + path.sep))
        throw new Error(`Link leaves repository: ${link}`);
      await stat(target).catch(() => {
        throw new Error(`Missing local file: ${link}`);
      });
    }
  }
}

const pages = await readPages();
const template = await readFile(
  path.join(guideDirectory, "template.html"),
  "utf8",
);
// Explicit content dates make builds reproducible after a fresh checkout.
const updated = new Date(
  pages
    .map((page) => page.updated)
    .sort()
    .at(-1),
).toLocaleDateString("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const slots = {
  navigation: navigation(pages),
  articles: pages.map((page) => article(page, pages)).join("\n"),
  updated,
};
const html = template.replace(
  /\{\{(navigation|articles|updated)\}\}/g,
  (_, name) => slots[name],
);
await checkDocument(html);
if (checkOnly) {
  const existing = await readFile(outputPath, "utf8");
  if (existing !== html)
    throw new Error("The HTML is stale. Run npm run build.");
  console.log(
    `Checked ${pages.length} pages: source coverage, metadata, links, and generated HTML are current.`,
  );
} else {
  await writeFile(outputPath, html);
  console.log(`Built ${pages.length} pages at ${outputPath}.`);
}
