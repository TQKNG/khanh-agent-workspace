import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/arc42-gitbook-docs'
SPEC = importlib.util.spec_from_file_location('readiness', PLUGIN / 'scripts/validate_session.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BLUEPRINT = json.loads((PLUGIN / 'references/site-blueprint.json').read_text())


def valid_session(kind='repository'):
    values = {key: 'explicit answer' for key in MODULE.REQUIRED_ANSWERS}
    values.update(input_kind=kind, delivery_mode='draft', onboarding_path='direct',
                  api_testing='disabled', generation_mode='implemented_only' if kind == 'repository' else 'approved_design')
    session = {
        'answers': {key: {'value': value, 'provenance': 'user', 'citation': 'user-message:1'} for key, value in values.items()},
        'source': {'repository': 'owner/repo', 'ref': 'main', 'revision': 'a' * 40, 'confirmed_ref': 'main', 'ref_user_citation': 'user-message:1'} if kind == 'repository' else {'brief': 'User supplied product brief', 'version': 'brief-1'},
        'questions': [{'question': 'Confirm source and scope?', 'answer': 'Confirmed', 'state': 'answered'}],
        'confirmation': {'reviewed': True, 'user_citation': 'user-message:2', 'fingerprint': 'source-scope-v1'},
        'facts': {'f1': {'claim': 'Example fact for structural test only', 'status': 'implemented' if kind == 'repository' else 'design', 'citation': 'source:1', 'user_confirmation': 'user-message:2'}},
        'pages': {s['key'] + '.' + p['key']: {'status': 'ready', 'facts': ['f1']} for s in BLUEPRINT['spaces'] for p in s['pages']}
    }
    session['confirmation']['fingerprint'] = MODULE.source_fingerprint(session)
    return session


class ReadinessTests(unittest.TestCase):
    def test_repository_plan_and_idea(self):
        for kind in ('repository', 'plan', 'idea'):
            with self.subTest(kind=kind):
                self.assertEqual(MODULE.validate_session(valid_session(kind)), [])

    def test_every_required_answer_blocks_individually(self):
        for key in MODULE.REQUIRED_ANSWERS:
            with self.subTest(key=key):
                session = valid_session()
                del session['answers'][key]
                self.assertTrue(MODULE.validate_session(session))

    def test_silence_is_not_an_answer(self):
        for answer in ('', None, False):
            session = valid_session()
            session['questions'][0]['answer'] = answer
            self.assertTrue(MODULE.validate_session(session))

    def test_default_branch_is_not_confirmation(self):
        session = valid_session()
        session['answers']['source']['provenance'] = 'default'
        self.assertTrue(MODULE.validate_session(session))

    def test_repository_ref_requires_explicit_confirmation(self):
        session = valid_session()
        session['source']['confirmed_ref'] = 'dev'
        self.assertTrue(MODULE.validate_session(session))

    def test_cli_rejects_unanswered_example(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, str(PLUGIN / 'scripts/validate_session.py'), str(PLUGIN / 'references/session.example.json')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)['ready'])

    def test_cli_accepts_answered_session(self):
        import subprocess
        import sys
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.json'
            path.write_text(json.dumps(valid_session()))
            result = subprocess.run([sys.executable, str(PLUGIN / 'scripts/validate_session.py'), str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)['ready'])

    def test_mutable_revision_rejected(self):
        session = valid_session()
        session['source']['revision'] = 'main'
        self.assertTrue(MODULE.validate_session(session))

    def test_unanswered_question_blocks(self):
        session = valid_session()
        session['questions'].append({'question': 'Which retention?', 'state': 'open'})
        self.assertTrue(MODULE.validate_session(session))

    def test_unresolved_or_missing_page_blocks(self):
        for status in ('blocked', None):
            session = valid_session()
            session['pages']['security.privacy'] = {'status': status}
            self.assertTrue(MODULE.validate_session(session))

    def test_explicit_omission_requires_user_reason(self):
        session = valid_session()
        session['pages']['api.operations'] = {'status': 'omitted'}
        self.assertTrue(MODULE.validate_session(session))
        session['pages']['api.operations'].update(reason='No API in approved scope', user_citation='user-message:3')
        session['confirmation']['fingerprint'] = MODULE.source_fingerprint(session)
        self.assertEqual(MODULE.validate_session(session), [])

    def test_fabricated_or_unknown_fact_rejected(self):
        for status in ('unknown', 'inferred', 'conflicting'):
            session = valid_session()
            session['facts']['f1']['status'] = status
            self.assertTrue(MODULE.validate_session(session))

    def test_design_needs_user_confirmation(self):
        session = valid_session('idea')
        del session['facts']['f1']['user_confirmation']
        self.assertTrue(MODULE.validate_session(session))

    def test_scope_change_reopens_gate(self):
        session = valid_session()
        session['confirmation']['reviewed'] = False
        self.assertTrue(MODULE.validate_session(session))

    def test_changed_source_fails_even_if_reviewed_remains_true(self):
        session = valid_session()
        session['source']['revision'] = 'b' * 40
        self.assertTrue(MODULE.validate_session(session))

    def test_draft_does_not_merge(self):
        self.assertTrue(MODULE.validate_session(valid_session(), 'merge'))

    def test_exact_revision_approval_and_verification(self):
        session = valid_session()
        session['answers']['delivery_mode']['value'] = 'merge'
        session['reviewed_revision'] = 'revision-2'
        session['merge_approval'] = {'approved': True, 'revision': 'revision-1', 'user_citation': 'user-message:4'}
        session['verification'] = dict.fromkeys(('content_readback', 'links', 'secrets', 'scope'), 'pass')
        self.assertTrue(MODULE.validate_session(session, 'merge'))
        session['merge_approval']['revision'] = 'revision-2'
        session['confirmation']['fingerprint'] = MODULE.source_fingerprint(session)
        self.assertEqual(MODULE.validate_session(session, 'merge'), [])
        session['verification']['links'] = 'fail'
        self.assertTrue(MODULE.validate_session(session, 'merge'))

    def test_malformed_records_fail_closed(self):
        for session in (None, [], {'answers': []}, {'answers': {}, 'source': []}, {'answers': {}, 'questions': [None]}):
            self.assertTrue(MODULE.validate_session(session))


class PackageTests(unittest.TestCase):
    def test_six_space_order_and_arc42_coverage(self):
        self.assertEqual([s['key'] for s in BLUEPRINT['spaces']], ['overview', 'architecture', 'getting-started', 'api', 'security', 'releases'])
        self.assertEqual(len(BLUEPRINT['spaces'][0]['pages']), 5)
        self.assertIn('quality', [p['key'] for p in BLUEPRINT['spaces'][1]['pages']])
        for space in BLUEPRINT['spaces']:
            keys = {p['key'] for p in space['pages']}
            self.assertEqual(len(keys), len(space['pages']))
            for page in space['pages']:
                self.assertTrue(page['content'])
                self.assertTrue(set(page['blocks']) <= set(BLUEPRINT['blocks']))
                if 'parent' in page:
                    self.assertIn(page['parent'], keys)

    def test_manifest_identity_version_and_prompts_preserved(self):
        portable = json.loads((PLUGIN / 'plugin.json').read_text())
        compat = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text())
        self.assertEqual(portable['name'], compat['name'])
        self.assertEqual(portable['version'], compat['version'])
        self.assertEqual(portable['version'], '0.3.0')
        interface = portable['extensions']['com.openai']['interface']
        self.assertEqual(interface['defaultPrompt'], compat['interface']['defaultPrompt'])
        self.assertLessEqual(len(interface['shortDescription']), 30)
        self.assertNotIn('skills', portable)

    def test_all_entrypoints_require_questions_and_validator(self):
        for skill in (PLUGIN / 'skills').glob('*/SKILL.md'):
            body = skill.read_text()
            self.assertTrue(body.startswith('---\nname: '))
            self.assertIn('Always ask', body)
            self.assertIn('readiness', body.lower())
            self.assertNotIn('defaulting to the repository default', body)

    def test_reference_links_resolve(self):
        import re
        for document in PLUGIN.rglob('*.md'):
            for target in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', document.read_text()):
                if '://' not in target:
                    self.assertTrue((document.parent / target).exists(), f'{document}: {target}')

    def test_api_template_and_retry_guards(self):
        body = (PLUGIN / 'references/block-and-delivery-standard.md').read_text()
        for value in ('builtin:openapi', 'models=true', 'downloadLink=true', 'x-hideTryItPanel', 'expectedRevision', '50 changes', 'uncertain writes', 'shared spec'):
            self.assertIn(value, body)


if __name__ == '__main__':
    unittest.main()
