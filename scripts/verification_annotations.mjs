import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parsers } from '../frontend/node_modules/prettier/plugins/babel.mjs';
import postcss from '../frontend/node_modules/postcss/lib/postcss.mjs';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const [mode, filename] = process.argv.slice(2);
if (!['snapshot', 'verify'].includes(mode) || !filename) throw new Error('Expected snapshot|verify and baseline filename');
const files = [];
function collect(directory) {
  if (!fs.existsSync(directory)) return;
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const item = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error('Annotation inputs must not be symbolic links');
    if (entry.isDirectory()) collect(item);
    else if (/\.(js|jsx|mjs|css)$/.test(item)) files.push(item);
  }
}
for (const directory of ['frontend/src', 'frontend/e2e', 'scripts']) collect(path.join(root, directory));
for (const name of fs.readdirSync(path.join(root, 'frontend')))
  if (/\.(js|mjs)$/.test(name)) files.push(path.join(root, 'frontend', name));
const records = {};
for (const file of files.sort()) {
  const source = fs.readFileSync(file, 'utf8');
  const record = { comments: [], strings: [] };
  if (file.endsWith('.css')) {
    postcss.parse(source).walkComments(comment => record.comments.push(comment.toString()));
  } else {
    const tree = await parsers.babel.parse(source);
    record.comments = (tree.comments || []).map(comment => source.slice(comment.start, comment.end));
    function walk(value) {
      if (!value || typeof value !== 'object') return;
      if (value.type === 'ExpressionStatement' && value.expression?.type === 'StringLiteral')
        record.strings.push(value.expression.value);
      if (value.type === 'Directive') record.strings.push(value.value.value);
      for (const [key, child] of Object.entries(value)) {
        if (['loc', 'comments', 'leadingComments', 'trailingComments', 'innerComments', 'tokens'].includes(key)) continue;
        if (Array.isArray(child)) child.forEach(walk);
        else if (child && typeof child === 'object') walk(child);
      }
    }
    walk(tree.program);
  }
  record.comments.sort();
  record.strings.sort();
  records[path.relative(root, file).replaceAll('\\', '/')] = record;
}
if (mode === 'snapshot') fs.writeFileSync(filename, JSON.stringify(records));
else {
  const baseline = JSON.parse(fs.readFileSync(filename, 'utf8'));
  for (const name of new Set([...Object.keys(records), ...Object.keys(baseline)])) {
    const empty = { comments: [], strings: [] };
    if (JSON.stringify(records[name] || empty) !== JSON.stringify(baseline[name] || empty))
      throw new Error(`${name}: comments or standalone strings changed relative to entry`);
  }
  console.log(`PASS: JavaScript, JSX and CSS annotations preserved across ${files.length} files`);
}
