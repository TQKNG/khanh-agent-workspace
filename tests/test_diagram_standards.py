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

    def test_hooks_file_nests_events_under_a_hooks_key(self):
        config = json.loads((PLUGIN / 'hooks/hooks.json').read_text(encoding='utf-8'))
        self.assertIn('hooks', config)
        command = config['hooks']['PostToolUse'][0]['hooks'][0]['command']
        self.assertTrue((PLUGIN / 'hooks/scripts/check_diagram_sources.py').is_file())
        self.assertIn('${CLAUDE_PLUGIN_ROOT}/hooks/scripts/check_diagram_sources.py', command)

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

    def test_new_diagram_fills_the_title_block_for_each_c4_template(self):
        for key in ('sc', 'bc', 'l1-whitebox', 'l1-deployment', 'l2-component'):
            with tempfile.TemporaryDirectory() as directory:
                result = run(SCRIPTS / 'new_diagram.py', key, 'X-Test-001', '--title', 'Test Title',
                             '--author', 'Jane Doe', '--date', '2027.01.05', '--out-dir', directory)
                self.assertEqual(result.returncode, 0, result.stderr)
                tree = ET.parse(Path(directory) / 'X-Test-001.drawio')
                plain = ' '.join(re.sub(r'<[^>]+>', '', cell.get('value') or '') for cell in tree.iter('mxCell'))
                for value in ('Test Title', 'X-Test-001', 'Prepared By: Jane Doe', 'Date: 2027.01.05'):
                    self.assertIn(value, plain, (key, value))

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


def shell_of(path):
    """Style, x, width and height of the frame, title block and legend box (y moves with the body height)."""
    cells = {c.get('id'): c for c in ET.parse(path).iter('mxCell')}
    result = {}
    for i in ('frame', 'hdr', 'legbox', 't1', 't2', 't3', 't4', 't5'):
        g = cells[i].find('mxGeometry')
        result[i] = (cells[i].get('style'), g.get('x'), g.get('width'), g.get('height'))
    return result


class UmlConverterTests(unittest.TestCase):
    CLASS = SKILL / 'references/class-example.mmd'
    STATE = SKILL / 'references/state-example.mmd'

    def convert(self, script, source, directory, number='X-001'):
        out = Path(directory) / 'out.drawio'
        result = run(SCRIPTS / script, source, out, '--title', 'T', '--number', number, '--author', 'A')
        return result, out

    def test_examples_convert_and_match_the_committed_templates(self):
        for script, source, stem in (('mermaid_class_to_drawio.py', self.CLASS, 'class'),
                                     ('mermaid_state_to_drawio.py', self.STATE, 'state')):
            with tempfile.TemporaryDirectory() as directory:
                result, out = self.convert(script, source, directory)
                self.assertEqual(result.returncode, 0, result.stderr)
                ET.fromstring(out.read_text(encoding='utf-8'))
                template = SKILL / 'templates' / f'{stem}.drawio'
                self.assertEqual(len(list(ET.parse(out).iter('mxCell'))), len(list(ET.parse(template).iter('mxCell'))), stem)

    def test_converted_shell_matches_the_sequence_converter(self):
        with tempfile.TemporaryDirectory() as directory:
            seq = Path(directory) / 'seq.drawio'
            result = run(SCRIPTS / 'mermaid_seq_to_drawio.py', SKILL / 'references/sequence-example.mmd', seq,
                         '--title', 'T', '--number', 'X-001', '--author', 'A')
            self.assertEqual(result.returncode, 0, result.stderr)
            reference = shell_of(seq)
            for script, source in (('mermaid_class_to_drawio.py', self.CLASS), ('mermaid_state_to_drawio.py', self.STATE)):
                result, out = self.convert(script, source, directory)
                self.assertEqual(result.returncode, 0, result.stderr)
                converted = shell_of(out)
                for key in reference:
                    self.assertEqual(converted[key][:3], reference[key][:3], (script, key))

    def test_class_output_has_uml_shapes_and_state_output_has_pseudostates(self):
        with tempfile.TemporaryDirectory() as directory:
            result, out = self.convert('mermaid_class_to_drawio.py', self.CLASS, directory)
            text = out.read_text(encoding='utf-8')
            for needle in ('swimlane', '\u00abinterface\u00bb', 'diamondThin', 'endArrow=block;endFill=0', 'X-001'):
                self.assertIn(needle, text, needle)
            result, out = self.convert('mermaid_state_to_drawio.py', self.STATE, directory)
            text = out.read_text(encoding='utf-8')
            for needle in ('shape=endState', 'rhombus', 'submit [valid]', 'Processing'):
                self.assertIn(needle, text, needle)

    def test_no_shapes_overlap_in_the_body(self):
        for script, source in (('mermaid_class_to_drawio.py', self.CLASS), ('mermaid_state_to_drawio.py', self.STATE)):
            with tempfile.TemporaryDirectory() as directory:
                result, out = self.convert(script, source, directory)
                boxes = []
                for cell in ET.parse(out).iter('mxCell'):
                    g = cell.find('mxGeometry')
                    if cell.get('vertex') == '1' and cell.get('parent') == '1' and cell.get('id', '')[:2] in ('c_', 's_'):
                        boxes.append((cell.get('id'), *(float(g.get(k)) for k in ('x', 'y', 'width', 'height'))))
                nested = {'s_3', 's_4', 's_5', 's_6'}  # the composite state and its inner states
                for i, a in enumerate(boxes):
                    for b in boxes[i + 1:]:
                        if script.startswith('mermaid_state') and a[0] in nested and b[0] in nested:
                            continue
                        apart = a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1] or a[2] + a[4] <= b[2] or b[2] + b[4] <= a[2]
                        self.assertTrue(apart, (script, a[0], b[0]))

    def test_class_converter_rejects_what_it_cannot_draw(self):
        cases = (('mermaid_class_to_drawio.py', 'classDiagram\n    A --> A\n', 'self-relationship'),
                 ('mermaid_class_to_drawio.py', 'classDiagram\n    note for A "x"\n', 'unsupported'),
                 ('mermaid_state_to_drawio.py', 'stateDiagram-v2\n    A --> A\n', 'self-transition'),
                 ('mermaid_state_to_drawio.py', 'stateDiagram-v2\n    state X {\n        state Y {\n        }\n    }\n', 'nested'),
                 ('mermaid_state_to_drawio.py', 'stateDiagram-v2\n    A --> B\n    state C {\n        A --> D\n    }\n', 'inside and outside'))
        for script, source, message in cases:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'bad.mmd'
                path.write_text(source, encoding='utf-8')
                result, _ = self.convert(script, path, directory)
                self.assertNotEqual(result.returncode, 0, source)
                self.assertIn(message, result.stderr, source)

    def test_too_wide_diagram_asks_to_split(self):
        source = 'classDiagram\n' + ''.join(f'    Root --> Leaf{i}\n' for i in range(8))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'wide.mmd'
            path.write_text(source, encoding='utf-8')
            result, _ = self.convert('mermaid_class_to_drawio.py', path, directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('split', result.stderr)

    def test_mdx_input_selects_the_requested_block(self):
        page = '```mermaid\nclassDiagram\n    class A\n```\n\n```mermaid\nclassDiagram\n    class B\n```\n'
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'page.mdx'
            source.write_text(page, encoding='utf-8')
            out = Path(directory) / 'out.drawio'
            result = run(SCRIPTS / 'mermaid_class_to_drawio.py', source, out, '--title', 'T', '--number', 'X-001',
                         '--author', 'A', '--block', '2')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('value="B"', out.read_text(encoding='utf-8'))


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
