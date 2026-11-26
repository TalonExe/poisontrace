import ast
from collections import Counter
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import textwrap
import tokenize


def python_annotations(path):
    source = path.read_text(encoding='utf-8-sig')
    tree = ast.parse(source, filename=str(path))
    return dict(comments=[t.string for t in tokenize.generate_tokens(io.StringIO(source).readline)
                          if t.type == tokenize.COMMENT],
                strings=[n.value.value for n in ast.walk(tree) if isinstance(n, ast.Expr)
                         and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)])


def annotation_snapshot(root):
    records = {}
    for directory in ('backend/src', 'backend/tests', 'scripts'):
        for path in (root/directory).rglob('*.py'):
            if '__pycache__' not in path.parts:
                records[path.relative_to(root).as_posix()] = python_annotations(path)
    return records


def audit_annotations(root, baseline):
    current = annotation_snapshot(root)
    for name in current.keys() | baseline.keys():
        before = baseline.get(name, {})
        after = current.get(name, {})
        for kind in ('comments', 'strings'):
            if Counter(before.get(kind, [])) != Counter(after.get(kind, [])):
                raise ValueError(f'{name}: {kind} changed relative to entry')


def static_checks(root, baseline):
    count = 0
    for directory in ('backend/src', 'backend/tests', 'scripts'):
        for path in (root/directory).rglob('*.py'):
            if '__pycache__' not in path.parts:
                compile(path.read_bytes(), str(path), 'exec')
                count += 1
    tree = ast.parse((root/'scripts/verify_container.py').read_text())
    embedded = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'execute':
            embedded.extend(n.value for n in ast.walk(node.args[0]) if isinstance(n, ast.Constant)
                            and isinstance(n.value, str) and '\n' in n.value)
    if len(embedded) != 2:
        raise ValueError('Expected both embedded container programs')
    for index, program in enumerate(embedded):
        compile(textwrap.dedent(program), f'container-program-{index}', 'exec')
    seeds = sorted((root/'backend/src/poisontrace/seeds/scenarios').glob('*.yaml'))
    if len(seeds) != 5:
        raise ValueError('Expected five packaged scenario seeds')
    for seed in seeds:
        if seed.read_bytes() != (root/'backend/scenarios'/seed.name).read_bytes():
            raise ValueError('Packaged seed differs: ' + seed.name)
    audit_annotations(root, baseline)
    if os.environ.get('POISONTRACE_VERIFY_JS_BASELINE'):
        subprocess.run([os.environ['POISONTRACE_VERIFY_NODE'], str(root/'scripts/verification_annotations.mjs'),
                        'verify', os.environ['POISONTRACE_VERIFY_JS_BASELINE']], cwd=root, check=True)
    print(f'PASS: {count} Python files compiled, two embedded programs, five byte-identical seeds, entry annotations preserved')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    baseline = json.loads(Path(os.environ['POISONTRACE_VERIFY_BASELINE']).read_text())
    static_checks(root, baseline)
