import json
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/diagram-standards'
SKILL = PLUGIN / 'skills/diagram-standards'
SCRIPTS = SKILL / 'scripts'
TYPES = {
    'sc': 'system-context', 'bc': 'business-context', 'l1-whitebox': 'l1-whitebox',
    'l1-deployment': 'l1-deployment', 'l2-component': 'l2-component', 'seq': 'sequence',
    'class': 'class', 'state': 'state',
}


def run(*args, stdin=None):
    return subprocess.run([sys.executable, '-I', *map(str, args)], input=stdin, capture_output=True, text=True)


class ManifestTests(unittest.TestCase):
    def test_manifests_agree_and_are_listed_in_both_marketplaces(self):
        manifests = [json.loads((PLUGIN / path).read_text(encoding='utf-8'))
                     for path in ('plugin.json', '.claude-plugin/plugin.json', '.codex-plugin/plugin.json')]
        self.assertEqual({m['name'] for m in manifests}, {'diagram-standards'})
        self.assertEqual(len({m['version'] for m in manifests}), 1)
        claude = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text(encoding='utf-8'))
        codex = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text(encoding='utf-8'))
        self.assertIn('diagram-standards', [p['name'] for p in claude['plugins']])
        self.assertIn('diagram-standards', [p['name'] for p in codex['plugins']])
        self.assertLessEqual(len(manifests[2]['interface']['shortDescription']), 30)

    def test_skills_have_frontmatter_matching_their_folder(self):
        for name in ('diagram-standards', 'new-diagram'):
            source = (PLUGIN / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8')
            self.assertTrue(source.startswith('---\n'))
            self.assertIn(f'name: {name}\n', source.split('---', 2)[1])

    def test_no_em_dash_in_plugin_files(self):
        for path in PLUGIN.rglob('*'):
            if path.is_file() and path.suffix in {'.md', '.json', '.py', '.sh', '.yml', '.mmd'}:
                self.assertNotIn('—', path.read_text(encoding='utf-8'), path)


class TemplateTests(unittest.TestCase):
    def test_every_template_parses_and_keeps_title_block_and_legend(self):
        for key, stem in TYPES.items():
            text = (SKILL / 'templates' / f'{stem}.drawio').read_text(encoding='utf-8')
            ET.fromstring(text)
            for needle in ('Document Title', 'Document Number', 'Version Number', 'Prepared By', 'Legend'):
                self.assertIn(needle, text, (key, needle))

    def test_new_diagram_fills_the_title_block_for_each_template(self):
        for key in ('sc', 'bc', 'l1-whitebox', 'l1-deployment', 'l2-component', 'class', 'state'):
            with tempfile.TemporaryDirectory() as directory:
                result = run(SCRIPTS / 'new_diagram.py', key, 'X-Test-001', '--title', 'Test Title',
                             '--author', 'Jane Doe', '--date', '2027.01.05', '--out-dir', directory)
                self.assertEqual(result.returncode, 0, result.stderr)
                tree = ET.parse(Path(directory) / 'X-Test-001.drawio')
                plain = ' '.join(re.sub(r'<[^>]+>', '', cell.get('value') or '') for cell in tree.iter('mxCell'))
                for value in ('Test Title', 'X-Test-001', 'Prepared By: Jane Doe', 'Date: 2027.01.05'):
                    self.assertIn(value, plain, (key, value))

    def test_uml_templates_share_the_sequence_frame_and_footer(self):
        def footer(stem):
            tree = ET.parse(SKILL / 'templates' / f'{stem}.drawio')
            cells = {c.get('id'): c for c in tree.iter('mxCell')}
            return {i: (cells[i].get('style'), cells[i].find('mxGeometry').attrib)
                    for i in ('frame', 'hdr', 'legbox', 't1', 't2', 't3', 't4', 't5')}
        reference = footer('sequence')
        for stem in ('class', 'state'):
            self.assertEqual(footer(stem), reference, stem)

    def test_class_template_has_uml_classes_and_relationships(self):
        text = (SKILL / 'templates/class.drawio').read_text(encoding='utf-8')
        for needle in ('swimlane', 'interface', 'enumeration', 'diamondThin', 'endArrow=block;endFill=0'):
            self.assertIn(needle, text, needle)

    def test_state_template_has_pseudostates_and_transitions(self):
        text = (SKILL / 'templates/state.drawio').read_text(encoding='utf-8')
        for needle in ('shape=endState', 'rhombus', 'Composite state', 'event [guard] / action'):
            self.assertIn(needle, text, needle)

    def test_new_diagram_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            args = [SCRIPTS / 'new_diagram.py', 'sc', 'X-Test-001', '--title', 'T', '--author', 'A', '--out-dir', directory]
            self.assertEqual(run(*args).returncode, 0)
            self.assertNotEqual(run(*args).returncode, 0)


class SequenceConverterTests(unittest.TestCase):
    SOURCE = SKILL / 'references/sequence-example.mmd'

    def convert(self, source, directory):
        out = Path(directory) / 'out.drawio'
        result = run(SCRIPTS / 'mermaid_seq_to_drawio.py', source, out, '--title', 'T', '--number', 'SEQ-X-001', '--author', 'A')
        return result, out

    def test_example_converts_with_frames_numbers_and_title_block(self):
        with tempfile.TemporaryDirectory() as directory:
            result, out = self.convert(self.SOURCE, directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = out.read_text(encoding='utf-8')
            ET.fromstring(text)
            self.assertIn('shape=umlFrame', text)
            self.assertIn('1. Request action', text)
            self.assertIn('SEQ-X-001', text)
            self.assertLess(text.index('id="frame"'), text.index('id="legbox"'))

    def test_mdx_input_selects_the_requested_block(self):
        page = '```mermaid\nsequenceDiagram\n    A->>B: one\n```\n\n```mermaid\nsequenceDiagram\n    C->>D: two\n```\n'
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'page.mdx'
            source.write_text(page, encoding='utf-8')
            result, out = self.convert(source, directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('one', out.read_text(encoding='utf-8'))

    def test_unsupported_syntax_stops_with_a_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'bad.mmd'
            source.write_text('sequenceDiagram\n    A->>A: self\n', encoding='utf-8')
            result, _ = self.convert(source, directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('self-message', result.stderr)


class HookTests(unittest.TestCase):
    HOOK = PLUGIN / 'hooks/scripts/check_diagram_sources.py'

    def check(self, path):
        return run(self.HOOK, stdin=json.dumps({'tool_input': {'file_path': str(path)}}))

    def test_page_without_source_is_flagged_and_with_source_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'docs.json').write_text('{}', encoding='utf-8')
            page = root / 'p.mdx'
            page.write_text('![x](/images/diagrams/A-001.png)\n', encoding='utf-8')
            self.assertEqual(self.check(page).returncode, 2)
            (root / 'diagrams/src').mkdir(parents=True)
            (root / 'diagrams/src/A-001.drawio').write_text('<mxfile/>', encoding='utf-8')
            (root / 'images/diagrams').mkdir(parents=True)
            (root / 'images/diagrams/A-001.png').write_bytes(b'png')
            self.assertEqual(self.check(page).returncode, 0)

    def test_missing_png_is_tolerated_when_the_export_workflow_is_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'docs.json').write_text('{}', encoding='utf-8')
            (root / 'diagrams/src').mkdir(parents=True)
            (root / 'diagrams/src/A-001.drawio').write_text('<mxfile/>', encoding='utf-8')
            page = root / 'p.mdx'
            page.write_text('![x](/images/diagrams/A-001.png)\n', encoding='utf-8')
            self.assertEqual(self.check(page).returncode, 2)
            (root / '.github/workflows').mkdir(parents=True)
            (root / '.github/workflows/export-diagrams.yml').write_text('name: x\n', encoding='utf-8')
            self.assertEqual(self.check(page).returncode, 0)

    def test_workflow_template_installs_a_pinned_draw_io_with_roboto(self):
        text = (SKILL / 'ci/export-diagrams.yml').read_text(encoding='utf-8')
        self.assertIn('DRAWIO_VERSION', text)
        self.assertIn('fonts-roboto', text)
        self.assertIn('test -s', text)


if __name__ == '__main__':
    unittest.main()
