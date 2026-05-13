/**
 * Extract every ```mermaid block from docs/**\/*.md into diagrams/*.mmd,
 * and rewrite the markdown to reference the (to-be-rendered) SVG via a
 * plain Markdown image tag.
 *
 * Naming convention:
 *   diagrams/<relpath-with-slash-as-double-underscore>__<nth-block>.mmd
 * e.g.
 *   diagrams/quick_start__lite_101__01.mmd
 *
 * The corresponding rendered SVG lives at
 *   static/img/diagrams/quick_start__lite_101__01.svg
 * and the markdown references it as
 *   ![<alt>](/img/diagrams/quick_start__lite_101__01.svg)
 *
 * `alt` is auto-generated from the first non-empty mermaid line (e.g. the
 * "flowchart LR" / "sequenceDiagram" header). Override by editing the
 * markdown afterward — re-extraction is idempotent.
 */

import {readFileSync, writeFileSync, mkdirSync, readdirSync, statSync} from 'node:fs';
import {join, relative, dirname} from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname;
const DOCS = join(ROOT, 'docs');
const DIAGRAMS = join(ROOT, 'diagrams');
mkdirSync(DIAGRAMS, {recursive: true});

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (name.endsWith('.md')) out.push(p);
  }
  return out;
}

function slugForFile(mdPath) {
  // docs/quick_start/lite_101.md  ->  quick_start__lite_101
  const rel = relative(DOCS, mdPath).replace(/\.md$/, '');
  return rel.replace(/\//g, '__');
}

function deriveAlt(mermaidSrc) {
  const first = mermaidSrc.split(/\r?\n/).find((l) => l.trim().length > 0) || 'diagram';
  return first.trim();
}

let totalExtracted = 0;
const mdFiles = walk(DOCS);

for (const mdPath of mdFiles) {
  let text = readFileSync(mdPath, 'utf8');
  const slug = slugForFile(mdPath);
  let nth = 0;
  // Match  ```mermaid\n...\n```  blocks. Greedy is fine — fences don't nest.
  text = text.replace(/```mermaid\n([\s\S]*?)\n```/g, (match, body) => {
    nth += 1;
    const idx = String(nth).padStart(2, '0');
    const mmdName = `${slug}__${idx}.mmd`;
    const svgPath = `/img/diagrams/${slug}__${idx}.svg`;
    writeFileSync(join(DIAGRAMS, mmdName), body.trim() + '\n');
    totalExtracted += 1;
    const alt = deriveAlt(body);
    return `![${alt}](${svgPath})`;
  });
  writeFileSync(mdPath, text);
}

console.log(`Extracted ${totalExtracted} mermaid blocks across ${mdFiles.length} files`);
console.log(`Sources in: ${DIAGRAMS}/`);
console.log(`Run \`npm run diagrams\` to render to static/img/diagrams/*.svg`);
