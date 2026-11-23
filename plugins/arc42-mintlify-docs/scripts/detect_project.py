"""Detect whether a product is already documented in docs.json and compare it with the format profile.

The result is structural evidence only. Page content must still be read before any update.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PROFILE_PATH = Path(__file__).resolve().parents[1] / 'references/format-profile.json'


def collect_pages(node):
    """Return every page path under a navigation node."""
    if isinstance(node, str):
        return [node]
    pages = []
    if isinstance(node, list):
        for item in node:
            pages.extend(collect_pages(item))
    elif isinstance(node, dict):
        for key in ('pages', 'groups', 'tabs', 'menu'):
            pages.extend(collect_pages(node.get(key, [])))
    return pages


def collect_groups(node):
    """Return group names in order, including nested groups."""
    names = []
    if isinstance(node, list):
        for item in node:
            names.extend(collect_groups(item))
    elif isinstance(node, dict):
        if node.get('group'):
            names.append(node['group'])
        for key in ('pages', 'groups', 'tabs'):
            names.extend(collect_groups(node.get(key, [])))
    return names


def normalize_group(name):
    return re.sub(r'^[\d.\s]+', '', str(name)).strip().lower()


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def find_entry(docs, product, slug):
    products = docs.get('navigation', {}).get('products', [])
    wanted = {slugify(product), slug}
    for entry in products:
        if slugify(str(entry.get('product', ''))) in wanted:
            return entry, 'name'
    for entry in products:
        paths = collect_pages(entry)
        if paths and sum(1 for path in paths if path.startswith(slug + '/')) > len(paths) / 2:
            return entry, 'path prefix'
    return None, None


def match_page(page, slug, paths, used):
    """Match a profile page to an existing path by file-name stems."""
    for stem in page['match']:
        stem = stem.replace('{slug}', slug)
        for path in paths:
            if path in used:
                continue
            last = path.rsplit('/', 1)[-1]
            if stem == slug:
                if last == slug and '/overview/' in '/' + path:
                    return path
            elif '/' in stem:
                if stem in path:
                    return path
            elif last == stem or last.startswith(stem + '-') or last.endswith('-' + stem):
                return path
    return None


def detect(docs, product, slug):
    profile = json.loads(PROFILE_PATH.read_text())
    entry, how = find_entry(docs, product, slug)
    if entry is None:
        return {'mode': 'new', 'product': product, 'slug': slug, 'entry': None,
                'summary': ['No navigation entry or pages found. Create the full product.']}
    paths = collect_pages(entry)
    groups = collect_groups(entry)
    expected_groups = profile['navigation']['groups']
    present, missing, used = {}, [], set()
    for space in profile['spaces']:
        for page in space['pages']:
            key = space['key'] + '.' + page['key']
            if page.get('repeatable'):
                continue
            found = match_page(page, slug, paths, used)
            if found:
                present[key] = found
                used.add(found)
            elif not page.get('conditional'):
                missing.append(key)
    decision_pages = [p for p in paths if re.search(r'/ad-\d+', p)]
    extra = [p for p in paths if p not in used and p not in decision_pages]
    seen = {normalize_group(g) for g in groups}
    group_gaps = [g for g in expected_groups if normalize_group(g) not in seen and g != 'API reference']
    deviations = []
    if group_gaps:
        deviations.append('Missing groups: ' + ', '.join(group_gaps))
    if decision_pages and not any('decision' in name for name in seen):
        deviations.append('Decision pages are not in a "Decision records" group')
    if paths and not any(p.startswith(slug + '/') for p in paths):
        deviations.append('Paths do not use the <slug>/<section>/ convention; keep them as they are')
    summary = [f'Found navigation entry by {how} with {len(paths)} pages.',
               f'{len(present)} profile pages present, {len(missing)} required pages missing, {len(decision_pages)} decision records.']
    if missing:
        summary.append('Missing: ' + ', '.join(missing))
    summary.extend(deviations)
    return {'mode': 'update', 'product': product, 'slug': slug, 'entry': entry.get('product'),
            'matched_by': how, 'present': present, 'missing': missing, 'extra': extra,
            'decision_records': decision_pages, 'deviations': deviations, 'summary': summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docs-json', type=Path, required=True)
    parser.add_argument('--product', required=True)
    parser.add_argument('--slug', required=True)
    args = parser.parse_args()
    try:
        docs = json.loads(args.docs_json.read_text())
    except (OSError, ValueError) as error:
        print(json.dumps({'error': str(error)}))
        return 2
    print(json.dumps(detect(docs, args.product, args.slug), indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
