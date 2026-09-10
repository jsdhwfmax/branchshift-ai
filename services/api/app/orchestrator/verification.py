"""Commands and fail-closed parsers for sandbox-generated validation evidence."""

from __future__ import annotations

import re
import shlex
import textwrap


def _guarded_python_command(script: str, error_marker: str) -> str:
    wrapped = (
        "try:\n" + textwrap.indent(script, "    ") + "\nexcept Exception as exc:\n"
        f"    print('__BRANCHSHIFT_{error_marker}=' + type(exc).__name__ + ': ' "
        "+ str(exc).replace('\\n', ' ')[:300])\n"
        "    raise SystemExit(1)\n"
    )
    return ".venv/bin/python -I -c " + shlex.quote(wrapped)


def junit_metrics_command(report_path: str) -> str:
    # The orchestrator supplies this script; repository stdout is never parsed as test counts.
    script = f"import json, xml.etree.ElementTree as ET\nroot=ET.parse({report_path!r}).getroot()\n"
    script += '''cases = list(root.iter('testcase'))
failed = sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
skipped = sum(c.find('skipped') is not None for c in cases)
print('__BRANCHSHIFT_TESTS_COLLECTED=' + str(len(cases)))
print('__BRANCHSHIFT_TESTS_PASSED=' + str(len(cases) - failed - skipped))
print('__BRANCHSHIFT_TESTS_FAILED=' + str(failed))
failures = []
seen = set()
for case in cases:
    issue = case.find('failure')
    if issue is None:
        issue = case.find('error')
    if issue is None:
        continue
    message = (issue.get('message') or ''.join(issue.itertext()).strip())[:600]
    if message in seen:
        continue
    seen.add(message)
    name = (case.get('classname', '') + '::' + case.get('name', 'unknown'))[:180]
    failures.append({'test': name, 'message': message})
    if len(failures) == 3:
        break
print('__BRANCHSHIFT_FAILURES=' + json.dumps(failures, separators=(',', ':')))
'''
    return _guarded_python_command(script, "METRICS_ERROR")


def runtime_version_command() -> str:
    script = (
        "import importlib.metadata; "
        "version=importlib.metadata.version('pydantic'); "
        "print('__BRANCHSHIFT_PYDANTIC_MAJOR='+version.split('.')[0])"
    )
    return _guarded_python_command(script, "RUNTIME_ERROR")


def test_contract_command(marker: str) -> str:
    """Fingerprint test source/data and pytest configuration without importing repository code."""
    if marker not in {"CONTRACT_BEFORE", "CONTRACT_AFTER"}:
        raise ValueError("Unsupported contract evidence marker")
    script = '''import configparser, hashlib, json, os, pathlib, tomllib
root = pathlib.Path.cwd()
files = {}
total = 0
ignored = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', '.mypy_cache'}
for directory, dirs, names in os.walk(root):
    dirs[:] = sorted(name for name in dirs if name not in ignored)
    for name in sorted(names):
        path = pathlib.Path(directory) / name
        relative = path.relative_to(root)
        protected = (any(part in {'test', 'tests', '__tests__'} for part in relative.parts)
                     or name == 'conftest.py' or name.startswith('test_')
                     or name.endswith('_test.py'))
        if not protected:
            continue
        if path.is_symlink():
            raise ValueError('Symlinked test files are unsupported')
        total += path.stat().st_size
        if total > 2_000_000 or len(files) >= 500:
            raise ValueError('Test contract exceeds bounded evidence limits')
        files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
configuration = {}
manifest = root / 'pyproject.toml'
if manifest.exists():
    parsed = tomllib.loads(manifest.read_text())
    configuration['pyproject.toml'] = parsed.get('tool', {}).get('pytest', {})
for name in ('pytest.ini', '.pytest.ini', 'tox.ini', 'setup.cfg'):
    path = root / name
    if path.exists():
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(path.read_text())
        configuration[name] = {section: dict(parser[section]) for section in parser.sections()
                               if section in {'pytest', 'tool:pytest'}}
payload = json.dumps({'files': files, 'configuration': configuration}, sort_keys=True).encode()
digest = hashlib.sha256(payload).hexdigest()
'''
    script += f"print('__BRANCHSHIFT_{marker}=' + digest)\n"
    return _guarded_python_command(script, f"{marker}_ERROR")


def marker_text(output: str, name: str) -> str:
    matches = re.findall(rf"^__BRANCHSHIFT_{re.escape(name)}=([^\n]+)$", output, re.MULTILINE)
    return matches[0] if len(matches) == 1 else ""


def marker_int(output: str, name: str) -> int:
    matches = re.findall(rf"^__BRANCHSHIFT_{re.escape(name)}=(-?\d+)$", output, re.MULTILINE)
    # Duplicate evidence is ambiguous, even when the final value looks successful.
    return int(matches[0]) if len(matches) == 1 else -1
