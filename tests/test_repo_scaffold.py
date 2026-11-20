import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/repo-scaffold'
RELEASE = SKILL / 'assets/release'
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
        for path in ('.github/workflows/release.yml', 'release-please-config.json', '.release-please-manifest.json', 'RELEASING.md'):
            with self.subTest(path=path):
                self.assertTrue((RELEASE / path).is_file())
        self.assertFalse((RELEASE / 'CHANGELOG.md').exists(), 'The changelog must be generated, not shipped as a starter file')

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
        workflow = (RELEASE / '.github/workflows/release.yml').read_text(encoding='utf-8')
        self.assertRegex(workflow, r'(?m)^permissions: \{\}$')
        job_permissions = re.findall(r'(?m)^ {6}([a-z-]+): (read|write)$', workflow)
        self.assertEqual(sorted(job_permissions), [('contents', 'write'), ('pull-requests', 'write')])
        self.assertNotIn('write-all', workflow)
        self.assertNotIn('pull_request_target', workflow)

    def test_release_workflow_runs_only_on_the_default_branch(self):
        workflow = (RELEASE / '.github/workflows/release.yml').read_text(encoding='utf-8')
        triggers = workflow.split('\non:\n', 1)[1].split('\n\n', 1)[0]
        self.assertEqual([line.strip() for line in triggers.splitlines() if line.strip()], ['push:', 'branches:', "- '{{DEFAULT_BRANCH}}'"])
        self.assertIn('googleapis/release-please-action@v4', workflow)
        self.assertIn('manifest-file: .release-please-manifest.json', workflow)

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

    def test_release_placeholders_are_documented_by_the_skill(self):
        names = set()
        for path in RELEASE.rglob('*'):
            if path.is_file():
                names.update(PLACEHOLDER.findall(path.read_text(encoding='utf-8')))
        self.assertEqual(names, {'PROJECT_NAME', 'DEFAULT_BRANCH', 'RELEASE_TYPE', 'CURRENT_VERSION', 'DEPLOYMENT_NOTES'})
        release = section(self.skill, 'Release setup')
        for referenced in ('release-type', '.release-please-manifest.json', 'RELEASING.md', 'default branch'):
            with self.subTest(referenced=referenced):
                self.assertIn(referenced, release)

    def test_skill_inspects_release_state_before_proposing(self):
        release = section(self.skill, 'Release setup')
        for topic in ('Versions:', 'Tags:', 'Releases:', 'Changelogs:', 'Release tooling:', 'Deployment:', 'Conventions:'):
            with self.subTest(topic=topic):
                self.assertIn(topic, release)
        self.assertIn('Inspect the current release state before recommending anything', release)
        self.assertIn('Inspect the release state', section(self.skill, 'Inspect first'))

    def test_skill_routes_release_work_through_new_and_existing_flows(self):
        self.assertIn('assets/release', section(self.skill, 'New repository'))
        self.assertIn('release inventory', section(self.skill, 'Existing repository'))
        release = section(self.skill, 'Release setup')
        self.assertIn('Do not modify, replace, or remove an existing release or deployment workflow unless the user specifically approves', release)
        self.assertIn('Never hand write or edit `CHANGELOG.md`', release)
        self.assertIn('`permissions: {}`', release)

    def test_skill_links_resolve(self):
        for target in re.findall(r'\]\(([^)#]+)\)', self.skill):
            with self.subTest(target=target):
                self.assertTrue((SKILL / target).exists())
        anchors = {re.sub(r'[^a-z0-9 -]', '', heading.lower()).replace(' ', '-') for heading in re.findall(r'(?m)^## (.+)$', self.skill)}
        for anchor in re.findall(r'\]\(#([^)]+)\)', self.skill):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, anchors)


if __name__ == '__main__':
    unittest.main()
