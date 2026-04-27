#!/usr/bin/env python3
"""
Issue tracking utilities for docs/issues/

Validates metadata and provides query interface for issue files.
"""

import argparse
import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
import yaml


REPO_ROOT = Path(__file__).parent.parent
ISSUES_DIR = REPO_ROOT / "docs" / "issues"

VALID_CATEGORIES = {"ADAPTER", "FAVA", "BUG", "TASK"}
VALID_STATUSES = {"open", "in-progress", "blocked", "done", "wontfix"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}


@dataclass
class Issue:
    """Represents an issue with metadata."""
    id: str
    title: str
    status: str
    priority: str
    created: str
    category: str
    tags: List[str]
    filepath: Path

    @property
    def filename(self) -> str:
        return self.filepath.name


def parse_issue(filepath: Path) -> Optional[Issue]:
    """Parse an issue file and extract metadata."""
    content = filepath.read_text()

    if not content.startswith('---\n'):
        return None

    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return None

    try:
        metadata = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        print(f"ERROR: {filepath.name}: Invalid YAML: {e}", file=sys.stderr)
        return None

    try:
        return Issue(
            id=metadata['id'],
            title=metadata['title'],
            status=metadata['status'],
            priority=metadata['priority'],
            created=metadata['created'],
            category=metadata['category'],
            tags=metadata.get('tags', []),
            filepath=filepath
        )
    except KeyError as e:
        print(f"ERROR: {filepath.name}: Missing required field: {e}", file=sys.stderr)
        return None


def validate_issue(issue: Issue) -> List[str]:
    """Validate an issue's metadata. Returns list of errors."""
    errors = []

    category_pattern = '|'.join(VALID_CATEGORIES)
    if not re.match(rf'^({category_pattern})-\d{{3}}$', issue.id):
        errors.append(f"Invalid ID format: {issue.id} (expected CATEGORY-NNN)")

    id_category = issue.id.split('-')[0]
    if issue.category != id_category:
        errors.append(f"Category mismatch: ID has {id_category}, metadata has {issue.category}")

    if issue.category not in VALID_CATEGORIES:
        errors.append(f"Invalid category: {issue.category} (must be one of {VALID_CATEGORIES})")

    if issue.status not in VALID_STATUSES:
        errors.append(f"Invalid status: {issue.status} (must be one of {VALID_STATUSES})")

    if issue.priority not in VALID_PRIORITIES:
        errors.append(f"Invalid priority: {issue.priority} (must be one of {VALID_PRIORITIES})")

    import datetime
    if isinstance(issue.created, datetime.date):
        created_str = issue.created.isoformat()
    else:
        created_str = str(issue.created)

    if not re.match(r'^\d{4}-\d{2}-\d{2}$', created_str):
        errors.append(f"Invalid created date: {created_str} (expected YYYY-MM-DD)")

    expected_prefix = f"{issue.id}_"
    if not issue.filename.startswith(expected_prefix):
        errors.append(f"Filename doesn't match ID: {issue.filename} (expected to start with {expected_prefix})")

    return errors


def cmd_validate(args):
    """Validate all issues."""
    issues = []
    errors_found = False

    for filepath in sorted(ISSUES_DIR.glob("*.md")):
        if filepath.name == "README.md":
            continue

        issue = parse_issue(filepath)
        if issue is None:
            print(f"ERROR: {filepath.name}: Failed to parse (missing or invalid frontmatter)", file=sys.stderr)
            errors_found = True
            continue

        issues.append(issue)

        errors = validate_issue(issue)
        if errors:
            errors_found = True
            print(f"ERROR: {filepath.name}:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)

    ids = [issue.id for issue in issues]
    duplicates = [id for id in ids if ids.count(id) > 1]
    if duplicates:
        errors_found = True
        print(f"ERROR: Duplicate IDs found: {set(duplicates)}", file=sys.stderr)

    if errors_found:
        print(f"\nValidation failed.", file=sys.stderr)
        return 1
    else:
        print(f"Validation passed. {len(issues)} issues checked.")
        return 0


def cmd_list(args):
    """List issues with optional filtering."""
    issues = []

    for filepath in sorted(ISSUES_DIR.glob("*.md")):
        if filepath.name == "README.md":
            continue

        issue = parse_issue(filepath)
        if issue:
            issues.append(issue)

    if args.status:
        issues = [i for i in issues if i.status == args.status]
    if args.category:
        issues = [i for i in issues if i.category == args.category]
    if args.priority:
        issues = [i for i in issues if i.priority == args.priority]
    if args.tag:
        issues = [i for i in issues if args.tag in i.tags]

    if args.sort == 'id':
        issues.sort(key=lambda i: i.id)
    elif args.sort == 'priority':
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        issues.sort(key=lambda i: (priority_order.get(i.priority, 99), i.id))
    elif args.sort == 'created':
        issues.sort(key=lambda i: str(i.created))

    if not issues:
        print("No issues found matching criteria.")
        return 0

    for issue in issues:
        tags_str = f" [{', '.join(str(t) for t in issue.tags)}]" if issue.tags else ""
        print(f"{issue.id:12} {issue.priority:8} {issue.status:12} {issue.title}{tags_str}")

    print(f"\nTotal: {len(issues)} issues")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Issue tracking utilities")
    subparsers = parser.add_subparsers(dest='command', required=True)

    parser_validate = subparsers.add_parser('validate', help='Validate all issues')
    parser_validate.set_defaults(func=cmd_validate)

    parser_list = subparsers.add_parser('list', help='List issues')
    parser_list.add_argument('--status', choices=sorted(VALID_STATUSES), help='Filter by status')
    parser_list.add_argument('--category', choices=sorted(VALID_CATEGORIES), help='Filter by category')
    parser_list.add_argument('--priority', choices=sorted(VALID_PRIORITIES), help='Filter by priority')
    parser_list.add_argument('--tag', help='Filter by tag')
    parser_list.add_argument('--sort', choices=['id', 'priority', 'created'], default='id', help='Sort order')
    parser_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
