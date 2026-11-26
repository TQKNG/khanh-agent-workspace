import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/repo-scaffold'
RELEASE = SKILL / 'assets/starter/.github'
PLACEHOLDER = re.compile(r'{{([A-Z_]+)}}')


def section(markdown, heading):
    match = re.search(rf'^## {re.escape(heading)}\n(.*?)(?=^## |\Z)', markdown, re.M | re.S)
    if match is None:
        raise AssertionError(f'Missing section: {heading}')
    return match.group(1)


class RepoScaffoldReleaseTests(unittest.TestCase):
    def setUp(self):
        self.skill = (SKILL / 'SKILL.md').read_text(encoding='utf-8')

    def test_release_starter_files_exist(self):
        for path in ('workflows/release.yml', 'release-please-config.json', '.release-please-manifest.json', 'RELEASING.md'):
            with self.subTest(path=path):
                self.assertTrue((RELEASE / path).is_file())
        self.assertFalse((RELEASE / 'CHANGELOG.md').exists(), 'The changelog must be generated, not shipped as a starter file')
        self.assertFalse((SKILL / 'assets/release').exists(), 'Release files must live in the starter .github directory')

    def test_release_config_is_valid_json_with_a_root_package(self):
        config = json.loads((RELEASE / 'release-please-config.json').read_text(encoding='utf-8'))
        manifest = json.loads((RELEASE / '.release-please-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(set(config['packages']), {'.'})
        self.assertEqual(set(manifest), {'.'})
        package = config['packages']['.']
        self.assertEqual(package['release-type'], '{{RELEASE_TYPE}}')
        self.assertEqual(package['changelog-path'], 'CHANGELOG.md')
        self.assertFalse(package['include-component-in-tag'])

    def test_release_workflow_uses_minimal_permissions(self):
        workflow = (RELEASE / 'workflows/release.yml').read_text(encoding='utf-8')
        self.assertRegex(workflow, r'(?m)^permissions: \{\}$')
        job_permissions = re.findall(r'(?m)^ {6}([a-z-]+): (read|write)$', workflow)
        self.assertEqual(sorted(job_permissions), [('contents', 'write'), ('pull-requests', 'write')])
        self.assertNotIn('write-all', workflow)
        self.assertNotIn('pull_request_target', workflow)

    def test_release_workflow_runs_only_on_the_default_branch(self):
        workflow = (RELEASE / 'workflows/release.yml').read_text(encoding='utf-8')
        triggers = workflow.split('\non:\n', 1)[1].split('\n\n', 1)[0]
        self.assertEqual([line.strip() for line in triggers.splitlines() if line.strip()], ['push:', 'branches:', "- '{{DEFAULT_BRANCH}}'"])
        self.assertIn('googleapis/release-please-action@v4', workflow)
        self.assertIn('config-file: .github/release-please-config.json', workflow)
        self.assertIn('manifest-file: .github/.release-please-manifest.json', workflow)

    def test_releasing_guide_covers_review_publish_and_generated_changelog(self):
        guide = (RELEASE / 'RELEASING.md').read_text(encoding='utf-8')
        review = section(guide, 'Review and publish a version')
        self.assertIn('Review the release pull request', review)
        self.assertIn('Merge the release pull request', review)
        self.assertIn('Do not edit `CHANGELOG.md` by hand', review)
        section(guide, 'Deployment')
        settings = section(guide, 'Repository settings')
        self.assertIn('Allow GitHub Actions to create and approve pull requests', settings)
        self.assertIn('do not trigger other workflows', settings)
        self.assertIn('Approve workflows to run', settings)

    def test_release_placeholders_are_documented_by_the_skill(self):
        names = set()
        for path in ('workflows/release.yml', 'release-please-config.json', '.release-please-manifest.json', 'RELEASING.md'):
            names.update(PLACEHOLDER.findall((RELEASE / path).read_text(encoding='utf-8')))
        self.assertEqual(names, {'PROJECT_NAME', 'DEFAULT_BRANCH', 'RELEASE_TYPE', 'CURRENT_VERSION', 'DEPLOYMENT_NOTES'})
        release = section(self.skill, '4. Release setup')
        for referenced in ('release-type', '.release-please-manifest.json', 'RELEASING.md', 'default branch'):
            with self.subTest(referenced=referenced):
                self.assertIn(referenced, release)

    def test_skill_inspects_release_state_before_proposing(self):
        release = section(self.skill, '4. Release setup')
        for topic in ('Versions in manifests', 'Tags from', 'GitHub releases from', 'Changelogs such as', 'Release tools such as', 'Deployment workflows', 'Recent commit messages'):
            with self.subTest(topic=topic):
                self.assertIn(topic, release)
        self.assertIn('Inspect the current release state before recommending release files', release)
        self.assertIn('Inspect its release state', section(self.skill, '1. Shared intake and inspection'))

    def test_skill_routes_release_work_through_new_and_existing_flows(self):
        self.assertIn('#4-release-setup', section(self.skill, '2. New repository workflow'))
        self.assertIn('release inventory', section(self.skill, '3. Existing repository workflow'))
        release = section(self.skill, '4. Release setup')
        self.assertIn('assets/starter/.github', release)
        self.assertIn('Do not modify, replace, or remove an existing release or deployment workflow unless the user specifically approves',
                      section(self.skill, '3. Existing repository workflow'))
        self.assertIn('Never hand-write or edit `CHANGELOG.md`', release)
        self.assertIn('`permissions: {}`', release)

    def test_skill_names_a_question_tool_for_each_agent(self):
        intake = section(self.skill, '1. Shared intake and inspection')
        for rule in ('`request_user_input` in Codex CLI', '`AskUserQuestion` in Claude Code CLI', '`ask_user` in GitHub Copilot CLI', '`vscode/askQuestions` in GitHub Copilot in VS Code'):
            with self.subTest(rule=rule):
                self.assertIn(rule, intake)

    def test_agents_template_can_be_filled_without_changing_its_layout(self):
        template = (SKILL / 'assets/starter/AGENTS.md').read_text(encoding='utf-8')
        self.assertTrue(200 <= len(template.splitlines()) <= 300)
        self.assertNotIn('Remove sections', template)
        self.assertNotIn('Remove unused convention slots', template)
        self.assertNotIn('{{REASON}}', template)
        self.assertIn("Keep the template's layout", self.skill)

    def test_skill_limits_the_starter_license_to_mit(self):
        new_repository = section(self.skill, '2. New repository workflow')
        self.assertIn('only when MIT is selected', new_repository)
        self.assertIn('checked against the official text', new_repository)

    def test_unreleased_projects_start_at_the_documented_version(self):
        config = json.loads((RELEASE / 'release-please-config.json').read_text(encoding='utf-8'))
        self.assertEqual(config['packages']['.']['initial-version'], '0.1.0')

    def test_skill_links_resolve(self):
        for target in re.findall(r'\]\(([^)#]+)\)', self.skill):
            if target.startswith('https://'):
                continue
            with self.subTest(target=target):
                self.assertTrue((SKILL / target).exists())
        anchors = {re.sub(r'[^a-z0-9 -]', '', heading.lower()).replace(' ', '-') for heading in re.findall(r'(?m)^## (.+)$', self.skill)}
        links = re.findall(r'\]\(#([^)]+)\)', self.skill)
        self.assertTrue(links)
        for anchor in links:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, anchors)


if __name__ == '__main__':
    unittest.main()
