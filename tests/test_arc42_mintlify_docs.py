import copy
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/arc42-mintlify-docs'
SHA = 'a' * 40


def load(name):
    spec = importlib.util.spec_from_file_location(name, PLUGIN / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate = load('validate_session')
detect = load('detect_project')
check = load('check_pages')
PROFILE = json.loads((PLUGIN / 'references/format-profile.json').read_text(encoding='utf-8'))


def user(value):
    return {'value': value, 'provenance': 'user', 'citation': 'message 1'}


def valid_session():
    facts = {'f1': {'claim': 'The service exists.', 'citation': 'README.md', 'status': 'implemented'}}
    pages = {f"{s['key']}.{p['key']}": {'status': 'ready', 'facts': ['f1']} for s in PROFILE['spaces'] for p in s['pages']}
    session = {
        'destination': {'repository': 'tqkng/docs', 'subdomain': 'kcode-workspace'},
        'answers': {key: user('x') for key in validate.USER_ONLY},
        'source': {'repository': 'owner/repo', 'ref': 'main', 'confirmed_ref': 'main', 'ref_user_citation': 'message 2', 'revision': SHA},
        'questions': [{'question': 'Scope?', 'answer': 'All', 'state': 'answered'}],
        'facts': facts,
        'pages': pages,
        'diagrams': [{'type': 'sc', 'doc_number': 'SC-Example-001', 'page': 'overview.context'}],
    }
    session['answers']['input_kind'] = user('repository')
    session['answers']['delivery_mode'] = user('draft')
    session['answers']['generation_mode'] = user('implemented_only')
    session['answers']['product_slug'] = user('example')
    session['answers']['project_mode'] = {'value': 'new', 'provenance': 'evidence', 'citation': 'detect output'}
    session['confirmation'] = {'reviewed': True, 'user_citation': 'message 3', 'fingerprint': validate.source_fingerprint(session)}
    return session


class PluginPackageTests(unittest.TestCase):
    def test_manifests_and_marketplace_agree(self):
        manifest = json.loads((PLUGIN / 'plugin.json').read_text(encoding='utf-8'))
        compat = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        market = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text(encoding='utf-8'))
        entries = {entry['name']: entry for entry in market['plugins']}
        self.assertEqual(manifest['name'], 'arc42-mintlify-docs')
        self.assertEqual(compat['version'], manifest['version'])
        self.assertEqual(entries['arc42-mintlify-docs']['source']['path'], './plugins/arc42-mintlify-docs')
        self.assertIn('arc42-gitbook-docs', entries)
        self.assertLessEqual(len(manifest['extensions']['com.openai']['interface']['shortDescription']), 30)

    def test_claude_code_marketplace_lists_the_plugin(self):
        market = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text(encoding='utf-8'))
        entry = next(e for e in market['plugins'] if e['name'] == 'arc42-mintlify-docs')
        plugin = ROOT / entry['source']
        manifest = json.loads((plugin / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['name'], entry['name'])
        self.assertTrue(entry['source'].startswith('./') and '..' not in entry['source'])
        self.assertTrue((plugin / 'skills/setup/SKILL.md').is_file())
        self.assertTrue(market['owner']['name'])

    def test_each_skill_has_frontmatter_and_existing_references(self):
        for name in ('setup', 'generate-arc42-docs', 'refresh-format-profile'):
            source = (PLUGIN / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8')
            self.assertTrue(source.startswith('---\n'))
            self.assertIn(f'name: {name}\n', source.split('---', 2)[1])
        for ref in ('intake-and-evidence', 'mintlify-format-standard', 'diagram-integration', 'detect-and-update'):
            self.assertTrue((PLUGIN / 'references' / f'{ref}.md').is_file())

    def test_no_em_dash_and_no_gitbook_leftovers(self):
        for path in PLUGIN.rglob('*'):
            if path.is_file() and path.suffix in {'.md', '.json', '.py'}:
                text = path.read_text(encoding='utf-8')
                self.assertNotIn('—', text, path)
                if path.name != 'mintlify-format-standard.md':
                    self.assertNotIn('GitBook', text, path)

    def test_sentences_are_one_per_line_in_skills(self):
        for path in (PLUGIN / 'skills').rglob('SKILL.md'):
            for line in path.read_text(encoding='utf-8').splitlines():
                if line.startswith(('#', '-', '|', '---', 'name:', 'description:')) or not line.strip():
                    continue
                sentence = re.sub(r'^\d+\. ', '', line)
                self.assertEqual(sentence.count('. '), 0, f'{path}: {line}')


class ProfileTests(unittest.TestCase):
    def test_six_groups_in_report_tool_order(self):
        self.assertEqual([s['group'] for s in PROFILE['spaces']], PROFILE['navigation']['groups'])
        self.assertEqual(PROFILE['navigation']['groups'][0], 'Overview')
        self.assertEqual(len(PROFILE['spaces']), 6)

    def test_page_keys_unique_and_arc42_prefixes_present(self):
        keys = [f"{s['key']}.{p['key']}" for s in PROFILE['spaces'] for p in s['pages']]
        self.assertEqual(len(keys), len(set(keys)))
        files = [p['file'] for s in PROFILE['spaces'] for p in s['pages']]
        for number in range(1, 13):
            self.assertTrue(any(f'/{number:02d}-' in f for f in files), number)

    def test_diagram_types_match_standard_and_runtime_uses_seq(self):
        used = {d['type'] for s in PROFILE['spaces'] for p in s['pages'] for d in p.get('diagrams', [])}
        self.assertEqual(used, set(PROFILE['diagram_types']))
        runtime = next(p for s in PROFILE['spaces'] for p in s['pages'] if p['key'] == 'runtime')
        self.assertEqual([d['type'] for d in runtime['diagrams']], ['seq'])
        self.assertNotIn('mermaid-sequence', runtime['blocks'])


class ValidatorTests(unittest.TestCase):
    def test_blank_example_is_not_ready(self):
        example = json.loads((PLUGIN / 'references/session.example.json').read_text(encoding='utf-8'))
        self.assertTrue(validate.validate_session(example))

    def test_complete_session_passes_write_phase(self):
        self.assertEqual(validate.validate_session(valid_session()), [])

    def test_other_destination_is_rejected(self):
        session = valid_session()
        session['destination']['repository'] = 'someone/else'
        self.assertTrue(any('Destination' in e for e in validate.validate_session(session)))

    def test_changed_scope_after_confirmation_reopens(self):
        session = valid_session()
        session['facts']['f2'] = {'claim': 'New.', 'citation': 'x', 'status': 'implemented'}
        self.assertTrue(any('changed since user confirmation' in e for e in validate.validate_session(session)))

    def test_unchanged_page_needs_update_mode_and_path(self):
        session = valid_session()
        session['pages']['overview.goals'] = {'status': 'unchanged', 'path': 'x/overview/01-introduction-and-goals'}
        session['confirmation']['fingerprint'] = validate.source_fingerprint(session)
        self.assertTrue(any('unchanged' in e for e in validate.validate_session(session)))
        session['answers']['project_mode']['value'] = 'update'
        session['confirmation']['fingerprint'] = validate.source_fingerprint(session)
        self.assertEqual(validate.validate_session(session), [])

    def test_unknown_diagram_type_is_rejected(self):
        session = valid_session()
        session['diagrams'].append({'type': 'sequence', 'doc_number': 'SD-Example-001', 'page': 'architecture.runtime'})
        session['confirmation']['fingerprint'] = validate.source_fingerprint(session)
        self.assertTrue(any('diagram-standards type' in e for e in validate.validate_session(session)))

    def test_runtime_scenario_uses_seq_type(self):
        session = valid_session()
        session['diagrams'].append({'type': 'seq', 'doc_number': 'SEQ-Example-001', 'page': 'architecture.runtime'})
        session['confirmation']['fingerprint'] = validate.source_fingerprint(session)
        self.assertEqual(validate.validate_session(session), [])

    def test_merge_needs_approval_and_checks(self):
        session = valid_session()
        self.assertTrue(validate.validate_session(session, 'merge'))


class DetectionTests(unittest.TestCase):
    DOCS = {'navigation': {'products': [{'product': 'Report Tool', 'pages': [
        {'group': 'Overview', 'pages': ['overview/report-automation-tool', 'overview/01-introduction-and-goals',
                                        'overview/02-architecture-constraints', 'overview/03-context-and-scope', 'overview/04-solution-strategy']},
        {'group': 'Solution architecture and design', 'pages': ['architecture/05-building-block-view', 'architecture/06-runtime-view',
            'architecture/07-deployment-view', 'architecture/08-crosscutting-concepts', 'architecture/09-architecture-decisions',
            {'group': 'Decision records', 'pages': ['architecture/09-architecture-decisions/ad-001-durable-functions']},
            'architecture/10-quality-requirements', 'architecture/11-risks-and-technical-debt']},
        {'group': 'Getting started', 'pages': ['quickstart', 'getting-started/getting-started/prerequisites-and-configuration']},
    ]}]}}

    def test_unknown_product_is_new(self):
        result = detect.detect(self.DOCS, 'Brand New', 'brand-new')
        self.assertEqual(result['mode'], 'new')

    def test_existing_product_reports_missing_pages(self):
        result = detect.detect(self.DOCS, 'Report Tool', 'report-automation-tool')
        self.assertEqual(result['mode'], 'update')
        self.assertEqual(result['present']['overview.landing'], 'overview/report-automation-tool')
        self.assertIn('architecture.glossary', result['missing'])
        self.assertIn('security.security-overview', result['missing'])
        self.assertEqual(len(result['decision_records']), 1)
        self.assertTrue(any('Missing groups' in d for d in result['deviations']))


class PageCheckTests(unittest.TestCase):
    GOOD = '---\ntitle: "1.2 Introduction and Goals"\ndescription: "Goals."\nkeywords:\n  - "Example"\n---\n\n## 1.2.1 Introduction\n\nText.\n'

    def run_check(self, text, with_source=False, name='page.mdx'):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / name).write_text(text, encoding='utf-8')
            if with_source:
                (root / 'diagrams/src').mkdir(parents=True)
                (root / 'diagrams/src/SC-Example-001.drawio').write_text('<mxfile/>', encoding='utf-8')
            errors, _, _ = check.check_page(root / name, root)
            return errors

    def test_good_page_passes(self):
        self.assertEqual(self.run_check(self.GOOD), [])

    def test_wrong_heading_number_h1_and_em_dash_fail(self):
        bad = self.GOOD.replace('## 1.2.1', '## 1.3.1') + '\n# Title\n\nA — B\n'
        errors = ' '.join(self.run_check(bad))
        self.assertIn('does not match', errors)
        self.assertIn('H1', errors)
        self.assertIn('Em dash', errors)

    def test_diagram_without_source_fails_and_with_source_passes(self):
        page = self.GOOD + '\n<img src="/images/diagrams/SC-Example-001.png" alt="Context" />\n'
        self.assertTrue(any('no source' in e for e in self.run_check(page)))
        self.assertEqual(self.run_check(page, with_source=True), [])

    def test_mermaid_sequence_on_runtime_page_fails(self):
        page = self.GOOD + '\n```mermaid\nsequenceDiagram\n    A->>B: x\n```\n'
        self.assertTrue(any('Mermaid sequenceDiagram' in e for e in self.run_check(page, name='06-runtime-view.mdx')))
        self.assertFalse(any('Mermaid sequenceDiagram' in e for e in self.run_check(page)))

    def test_secret_values_fail(self):
        page = self.GOOD + '\nAccountKey=abcdefghijklmnop1234\n'
        self.assertTrue(any('secret' in e for e in self.run_check(page)))


if __name__ == '__main__':
    unittest.main()
