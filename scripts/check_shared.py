"""检查 Backend/Jupyter 共享目录、Contents API 和 Parquet 互读；可选重建验证。"""

import argparse
from pathlib import Path
import subprocess
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]


def compose(*args: str, code: str | None = None) -> None:
    subprocess.run(
        ["docker", "compose", *args],
        input=code,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        check=True,
    )


def python(service: str, code: str) -> None:
    compose("exec", "-T", "--user", "1000:100", service, "python", "-", code=code)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recreate", action="store_true", help="重建 Backend/Jupyter 后验证数据保留")
    args = parser.parse_args()
    name = f"shared-check-{uuid4().hex}"
    setup = f'''
import os
from pathlib import Path
import pandas as pd
assert os.getuid() == 1000
project = Path('/shared/projects/{name}')
run = Path('/shared/runs/{name}')
'''
    verify = setup + r'''
assert (project / 'example.py').read_text() == 'value = 42\n'
assert (project / 'jupyter.txt').read_text() == 'saved through Contents API'
assert pd.read_parquet(run / 'backend.parquet').to_dict('list') == {'value': [1, 2, 3]}
assert pd.read_parquet(run / 'jupyter.parquet').to_dict('list') == {'value': [2, 4, 6]}
print('PASS: uid=1000, project files and both Parquet files')
'''
    try:
        python("backend", setup + r'''
project.mkdir()
run.mkdir()
(project / 'example.py').write_text('value = 42\n')
pd.DataFrame({'value': [1, 2, 3]}).to_parquet(run / 'backend.parquet', index=False)
print('PASS: Backend writes project and report')
''')
        python("jupyter", setup + r'''
import json
from urllib.request import Request, urlopen
assert (project / 'example.py').read_text() == 'value = 42\n'
frame = pd.read_parquet(run / 'backend.parquet')
assert frame.to_dict('list') == {'value': [1, 2, 3]}
(frame * 2).to_parquet(run / 'jupyter.parquet', index=False)
base = 'http://127.0.0.1:8888/api/contents/'
headers = {'Authorization': 'token ' + os.environ['JUPYTER_TOKEN'], 'Content-Type': 'application/json'}
with urlopen(Request(base + 'projects/' + project.name, headers=headers), timeout=10) as response:
    assert 'example.py' in [item['name'] for item in json.load(response)['content']]
body = json.dumps({'type': 'file', 'format': 'text', 'content': 'saved through Contents API'}).encode()
with urlopen(Request(base + 'projects/' + project.name + '/jupyter.txt', data=body, headers=headers, method='PUT'), timeout=10) as response:
    assert response.status == 201
print('PASS: Jupyter reads report, writes Parquet and saves file through Contents API')
''')
        python("backend", verify)
        if args.recreate:
            compose("up", "-d", "--no-build", "--force-recreate", "--wait", "backend", "jupyter")
            python("backend", verify)
            python("jupyter", verify)
            print("PASS: data survives container recreation")
    finally:
        python("backend", setup + '''
for directory in (project, run):
    if directory.exists():
        for file in directory.iterdir():
            file.unlink()
        directory.rmdir()
print('Removed test files')
''')


if __name__ == "__main__":
    main()
