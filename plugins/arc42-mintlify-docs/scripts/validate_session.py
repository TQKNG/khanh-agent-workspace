"""Validate a documentation intake record before Mintlify writes or merges.

This is a structural gate, not a substitute for inspecting source or user answers.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

PROFILE_PATH = Path(__file__).resolve().parents[1] / 'references/format-profile.json'
DESTINATION = {'repository': 'tqkng/docs', 'subdomain': 'kcode-workspace'}
REQUIRED_ANSWERS = ('input_kind', 'source', 'product_name', 'product_slug', 'audience', 'purpose',
                    'scope', 'content_policy', 'delivery_mode', 'generation_mode', 'project_mode')
USER_ONLY = tuple(key for key in REQUIRED_ANSWERS if key != 'project_mode')
DIAGRAM_PREFIX = {'bc': 'BC', 'sc': 'SC', 'l1-whitebox': 'LVL1_Whitebox',
                  'l1-deployment': 'LVL1-DeploymentView', 'l2-component': 'LVL2_ComponentView',
                  'seq': 'SEQ'}


def source_fingerprint(session):
    payload = {key: session.get(key) for key in ('answers', 'source', 'questions', 'facts', 'pages', 'diagrams')}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def expected_pages():
    profile = json.loads(PROFILE_PATH.read_text())
    return {space['key'] + '.' + page['key'] for space in profile['spaces'] for page in space['pages']}


def validate_session(session, phase='write'):
    errors = []
    if not isinstance(session, dict):
        return ['Session must be an object.']
    answers = session.get('answers', {})
    if not isinstance(answers, dict):
        return ['answers must be an object.']
    for key in REQUIRED_ANSWERS:
        answer = answers.get(key)
        if not isinstance(answer, dict) or not answer.get('value'):
            errors.append(f'Ask for {key}.')
        elif not answer.get('citation'):
            errors.append(f'Record a citation for {key}.')
        elif key in USER_ONLY and answer.get('provenance') != 'user':
            errors.append(f'Obtain user confirmation for {key}.')
        elif key == 'project_mode' and answer.get('provenance') not in ('user', 'evidence'):
            errors.append('Record how project_mode was determined.')

    def value(key):
        answer = answers.get(key)
        return answer.get('value') if isinstance(answer, dict) else None

    destination = session.get('destination', {})
    if destination != DESTINATION:
        errors.append('Destination must be repository tqkng/docs on subdomain kcode-workspace.')
    kind = value('input_kind')
    if kind not in ('repository', 'plan', 'idea'):
        errors.append('input_kind must be repository, plan or idea.')
    if value('delivery_mode') not in ('draft', 'merge'):
        errors.append('Ask for draft or merge delivery.')
    if value('project_mode') not in ('new', 'update'):
        errors.append('project_mode must be new or update.')
    if value('generation_mode') not in ('implemented_only', 'approved_design'):
        errors.append('Confirm implemented_only or approved_design.')
    if kind in ('plan', 'idea') and value('generation_mode') != 'approved_design':
        errors.append('Plan and idea input require approved_design.')
    slug = value('product_slug')
    if slug and not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', str(slug)):
        errors.append('product_slug must be lowercase words joined by hyphens.')
    source = session.get('source', {})
    if not isinstance(source, dict):
        errors.append('source must be an object.')
    elif kind == 'repository':
        for key in ('repository', 'ref', 'revision'):
            if not source.get(key):
                errors.append(f'Confirm source {key}.')
        if source.get('confirmed_ref') != source.get('ref') or not source.get('ref_user_citation'):
            errors.append('Ask the user to confirm the exact repository ref.')
        if not re.fullmatch(r'[0-9a-f]{40}', str(source.get('revision', ''))):
            errors.append('Repository revision must be an immutable 40-character SHA.')
    elif not source.get('brief') or not source.get('version'):
        errors.append('Obtain a confirmed brief and version for the plan or idea.')
    questions = session.get('questions', [])
    if not isinstance(questions, list) or not questions:
        errors.append('Ask and record at least one question.')
    else:
        for question in questions:
            if not isinstance(question, dict) or not question.get('question') or not question.get('answer') or question.get('state') != 'answered':
                errors.append('Resolve every intake question before construction.')
    confirmation = session.get('confirmation', {})
    if not isinstance(confirmation, dict) or confirmation.get('reviewed') is not True or not confirmation.get('user_citation') or not confirmation.get('fingerprint'):
        errors.append('User must confirm the current source/scope fingerprint.')
    elif confirmation.get('fingerprint') != source_fingerprint(session):
        errors.append('Source/scope changed since user confirmation; ask again.')
    facts = session.get('facts', {})
    if not isinstance(facts, dict):
        return errors + ['facts must be an object.']
    for fact_id, fact in facts.items():
        if not isinstance(fact, dict) or not fact.get('claim') or not fact.get('citation'):
            errors.append(f'Fact {fact_id} lacks a claim or source.')
            continue
        if fact.get('status') not in ('implemented', 'design'):
            errors.append(f'Resolve fact {fact_id}; unknowns and inferences cannot pass as facts.')
        if fact.get('status') == 'design' and (value('generation_mode') != 'approved_design' or not fact.get('user_confirmation')):
            errors.append(f'Design fact {fact_id} needs explicit user confirmation.')
    expected = expected_pages()
    pages = session.get('pages', {})
    if not isinstance(pages, dict):
        return errors + ['pages must be an object.']
    for key in sorted(expected):
        decision = pages.get(key)
        if not isinstance(decision, dict):
            errors.append(f'Ask for page decision {key}.')
        elif decision.get('status') == 'omitted':
            if not decision.get('reason') or not decision.get('user_citation'):
                errors.append(f'Page {key} requires an explicit omission reason and user answer.')
        elif decision.get('status') == 'unchanged':
            if value('project_mode') != 'update' or not decision.get('path'):
                errors.append(f'Page {key} can be unchanged only in update mode with its detected path.')
        elif decision.get('status') == 'ready':
            refs = decision.get('facts')
            if not isinstance(refs, list) or not refs or any(ref not in facts for ref in refs):
                errors.append(f'Page {key} needs valid evidence references.')
        else:
            errors.append(f'Resolve page {key}.')
    if set(pages) - expected:
        errors.append('Unknown page keys require an approved profile extension.')
    for index, diagram in enumerate(session.get('diagrams', [])):
        kind_key = diagram.get('type') if isinstance(diagram, dict) else None
        if kind_key not in DIAGRAM_PREFIX:
            errors.append(f'Diagram {index} must use a diagram-standards type: {sorted(DIAGRAM_PREFIX)}.')
            continue
        pattern = rf"{re.escape(DIAGRAM_PREFIX[kind_key])}-[A-Za-z0-9]+-\d{{3}}"
        if not re.fullmatch(pattern, str(diagram.get('doc_number', ''))):
            errors.append(f'Diagram {index} document number must look like {DIAGRAM_PREFIX[kind_key]}-ProductName-001.')
        if diagram.get('page') not in expected:
            errors.append(f'Diagram {index} must name a profile page key.')
    if phase == 'merge':
        approval = session.get('merge_approval', {})
        checks = session.get('verification', {})
        if value('delivery_mode') != 'merge':
            errors.append('Draft mode never authorizes merge.')
        if not isinstance(approval, dict) or approval.get('approved') is not True or not approval.get('user_citation') or not session.get('reviewed_revision') or approval.get('revision') != session.get('reviewed_revision'):
            errors.append('Obtain approval for the exact reviewed revision.')
        for key in ('content_readback', 'links', 'secrets', 'scope', 'diagram_sources'):
            if not isinstance(checks, dict) or checks.get(key) != 'pass':
                errors.append(f'Merge verification missing: {key}.')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    parser.add_argument('--phase', choices=('write', 'merge'), default='write')
    args = parser.parse_args()
    try:
        errors = validate_session(json.loads(args.session.read_text()), args.phase)
    except (OSError, ValueError, TypeError) as error:
        errors = [str(error)]
    print(json.dumps({'ready': not errors, 'phase': args.phase, 'questions_required': errors}, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
