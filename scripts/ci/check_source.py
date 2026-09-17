"""Parse tracked sources without importing applications or running scheduled jobs."""
import ast
import json
from pathlib import Path
import subprocess
import sys

files = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
checked = 0
failures = []
for filename in filter(None, files):
    path = Path(filename)
    if not path.is_file():
        continue
    try:
        if path.suffix == '.py':
            ast.parse(path.read_bytes(), filename=filename)
        elif path.name in ('package.json', 'package-lock.json') or path.suffix == '.ipynb':
            json.loads(path.read_text())
        elif path.suffix in ('.js', '.cjs', '.mjs'):
            result = subprocess.run(['node', '--check', filename], capture_output=True, text=True)
            if result.returncode:
                failures.append(filename + ': JavaScript syntax error (run node --check locally)')
        else:
            continue
        checked += 1
    except (SyntaxError, ValueError, UnicodeError) as exc:
        failures.append(filename + ': ' + type(exc).__name__)
print(f'Parsed {checked} source/manifest files; {len(failures)} errors. This is not a behavioral test suite.')
for failure in failures:
    print(failure)
sys.exit(bool(failures))
