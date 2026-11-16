import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text(encoding='utf-8'))


class ReusablePluginTests(unittest.TestCase):
    def test_marketplace_packages_and_skills_are_discoverable(self):
        expected = {
            'agent-workflows': {'repo-scaffold', 'ticket', 'graphify', 'technical-blog-writing'},
            'session-token-audit': {'session-token-audit'},
        }
        entries = {entry['name']: entry for entry in MARKETPLACE['plugins']}
        for name, skills in expected.items():
            with self.subTest(plugin=name):
                plugin = ROOT / entries[name]['source']['path']
                manifest = json.loads((plugin / 'plugin.json').read_text(encoding='utf-8'))
                compatibility = json.loads((plugin / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
                self.assertEqual(manifest['name'], name)
                self.assertEqual(compatibility['name'], name)
                self.assertEqual(compatibility['version'], manifest['version'])
                self.assertLessEqual(len(manifest['extensions']['com.openai']['interface']['shortDescription']), 30)
                self.assertEqual({path.parent.name for path in (plugin / 'skills').glob('*/SKILL.md')}, skills)
                for skill in skills:
                    source = (plugin / 'skills' / skill / 'SKILL.md').read_text(encoding='utf-8')
                    self.assertTrue(source.startswith('---\n'))
                    self.assertIn(f'name: {skill}\n', source.split('---', 2)[1])

    def test_token_audit_discovers_children_without_double_counting(self):
        script = ROOT / 'plugins/session-token-audit/skills/session-token-audit/scripts/audit_sessions.py'
        spec = importlib.util.spec_from_file_location('session_audit', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = [
                {'type': 'session_meta', 'payload': {'id': 'root'}},
                {'type': 'token_usage_record', 'payload': {'response_id': 'r1', 'usage': {'input_tokens': 10}}},
                {'type': 'token_usage_record', 'payload': {'response_id': 'r1', 'usage': {'input_tokens': 10}}},
            ]
            child = [
                {'type': 'session_meta', 'payload': {'id': 'child', 'parent_thread_id': 'root'}},
                {'type': 'token_usage_record', 'payload': {'response_id': 'r2', 'usage': {'input_tokens': 5}}},
            ]
            for name, events in [('parent.jsonl', parent), ('child.jsonl', child)]:
                (root / name).write_text('\n'.join(json.dumps(event) for event in events), encoding='utf-8')
            result = module.audit(root, 'root')
        sessions = {session['id']: session for session in result['sessions']}
        self.assertEqual(set(sessions), {'root', 'child'})
        self.assertEqual(sessions['root']['usage']['input_tokens'], 10)
        self.assertEqual(sessions['child']['usage']['input_tokens'], 5)
        self.assertEqual(result['missing'], [])
