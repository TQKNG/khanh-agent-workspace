"""Check generated MDX pages against the Mintlify format standard.

Usage: check_pages.py PAGES_DIR [--root REPO_ROOT]
PAGES_DIR holds the .mdx files. REPO_ROOT holds diagrams/src, and defaults to PAGES_DIR.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SECRET_PATTERNS = (
    re.compile(r'AccountKey=[A-Za-z0-9+/=]{8,}'),
    re.compile(r'(?i)\b(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*["\']?[A-Za-z0-9+/_\-]{12,}'),
    re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    re.compile(r'\bsk-[A-Za-z0-9]{20,}'),
)
PNG = re.compile(r'/images/diagrams/([A-Za-z0-9_\-]+)\.png')


def split_frontmatter(text):
    if not text.startswith('---\n'):
        return None, text
    end = text.find('\n---\n', 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5:]


def prose_lines(body):
    """Yield (number, line) for lines outside code fences."""
    inside = False
    for number, line in enumerate(body.splitlines(), 1):
        if line.lstrip().startswith('```'):
            inside = not inside
            continue
        if not inside:
            yield number, line


def check_page(path, root):
    errors, warnings = [], []
    text = path.read_text(encoding='utf-8')
    front, body = split_frontmatter(text)
    if front is None:
        return ['Missing frontmatter.'], warnings, 0
    fields = {match.group(1) for match in re.finditer(r'^([A-Za-z]+):', front, re.M)}
    for field in ('title', 'description', 'keywords'):
        if field not in fields:
            errors.append(f'Frontmatter lacks {field}.')
    title = re.search(r'^title:\s*"?(.*?)"?\s*$', front, re.M)
    number = re.match(r'(\d+(?:\.\d+)?)\b', title.group(1)) if title else None
    if body.count('```') % 2:
        errors.append('Unbalanced code fence.')
    if '\u2014' in text:
        errors.append('Em dash found; use a plain hyphen.')
    for line_number, line in prose_lines(body):
        if re.match(r'# ', line):
            errors.append(f'Line {line_number}: H1 found; Mintlify renders the title.')
        heading = re.match(r'#{2,4}\s+(\d+(?:\.\d+)+)\b', line)
        if heading and number and '.' in number.group(1):
            if not heading.group(1).startswith(number.group(1) + '.'):
                errors.append(f'Line {line_number}: heading number {heading.group(1)} does not match page number {number.group(1)}.')
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            errors.append('Possible secret value found; remove it.')
            break
    for name in sorted(set(PNG.findall(text))):
        if not (root / 'diagrams/src' / f'{name}.drawio').is_file():
            errors.append(f'Diagram {name}.png has no source diagrams/src/{name}.drawio.')
    for match in re.finditer(r'!\[[^\]]*\]\((https?://[^)]+)\)', text):
        warnings.append(f'External image {match.group(1)[:60]}; prefer /images/diagrams/ for architecture diagrams.')
    for match in re.finditer(r'<img\b[^>]*>', text):
        if 'alt=' not in match.group(0):
            errors.append('Image without alt text.')
    return errors, warnings, text.count('[OWNER INPUT REQUIRED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pages', type=Path)
    parser.add_argument('--root', type=Path)
    args = parser.parse_args()
    root = args.root or args.pages
    report, failed, placeholders = {}, False, 0
    for path in sorted(args.pages.rglob('*.mdx')):
        errors, warnings, count = check_page(path, root)
        placeholders += count
        report[str(path.relative_to(args.pages))] = {'errors': errors, 'warnings': warnings, 'owner_input_markers': count}
        failed = failed or bool(errors)
    print(json.dumps({'pass': not failed, 'owner_input_markers': placeholders, 'pages': report}, indent=2))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
