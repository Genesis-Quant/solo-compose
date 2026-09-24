"""真实调用 Solo DS：因子、回测成功，以及错误 wheel 哈希导致任务失败。

根目录运行 python scripts/check_scheduler.py。保留测试输入、锁文件及报告供检查。
使用 algos/scheme/tests/fixtures/research 的测试包和已有 DolphinDB 2026-06 行情。
"""

import json
import subprocess
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
WORKER = "dolphinscheduler-standalone"


def docker(*args: str, code: str | None = None) -> str:
    result = subprocess.run(
        ["docker", "compose", *args],
        cwd=ROOT,
        input=code,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def python(service: str, code: str, user: str = "1000:100", project: str | None = None) -> str:
    command = ["uv", "run", "--project", project, "--no-sync"] if project else []
    return docker("exec", "-T", "--user", user, service, *command, "python", "-", code=code)


def query(expression: str):
    return json.loads(
        python(
            "backend",
            f"""
import json
from core.scheduler.client import DolphinSchedulerClient
with DolphinSchedulerClient() as client:
    print(json.dumps({expression}))
""",
        )
    )


PREPARE = """
import hashlib
import json
import os
import subprocess
from pathlib import Path

os.umask(0o002)
root = Path(RUN_ROOT)
packages = root / "packages"
packages.mkdir(parents=True)
subprocess.run(["uv", "build", SCHEME, "--wheel", "--out-dir", str(packages)], check=True)
subprocess.run(["uv", "build", FIXTURE, "--wheel", "--out-dir", str(packages)], check=True)
wheel = next(packages.glob("solo_runtime_fixture-*.whl"))
component = dict(package="solo-runtime-fixture", version="1.0.0", wheel=str(wheel),
                 sha256=hashlib.sha256(wheel.read_bytes()).hexdigest())
dependencies = [f"{name} @ {path.as_uri()}" for name, path in [
    ("scheme", next(packages.glob("scheme-*.whl"))),
    ("solo-runtime-fixture", wheel),
]]
for kind in ("factor", "backtest", "bad-hash"):
    directory = root / kind
    environment = directory / "environment"
    environment.mkdir(parents=True)
    (environment / "pyproject.toml").write_text(
        '[project]\\nname="solo-scheduler-check"\\nversion="1.0.0"\\nrequires-python=">=3.12,<3.13"\\n'
        + 'dependencies=' + json.dumps(dependencies) + '\\n[tool.uv]\\npackage=false\\n')
    subprocess.run(["uv", "lock", "--project", str(environment), "--python", "3.12"], check=True)
    task = dict(kind=kind if kind != "bad-hash" else "factor",
                environment=dict(lockfile=str(environment / "uv.lock")),
                output=str(directory / "output"))
    if kind == "backtest":
        task.update(algos=dict(model=dict(component, entry="solo_runtime_fixture:ModelAlgo")),
                    context="solo_runtime_fixture:Context",
                    backtest=dict(start="2026-06-01", end="2026-06-03", market_data="stock_daily",
                                  symbols=["000001.XSHE", "600000.XSHG"], benchmark="000300.XSHG",
                                  config=dict(cash=100000, commission=0.0, tax=0.0)))
    else:
        factor = dict(component, entry="solo_runtime_fixture:Factor")
        if kind == "bad-hash":
            factor["sha256"] = "0" * 64
        task.update(factor=factor,
                    analysis=dict(start="2026-06-01", end="2026-06-06", columns=["score"],
                                  return_periods=[1, 5], groups=2, n_select=1, weight="equal",
                                  calendar_symbol="000300.XSHG"))
    (directory / "input.json").write_text(json.dumps(task, indent=2))
print(json.dumps({"directory": str(root)}))
"""


def main() -> None:
    run_root = f"/shared/runs/scheduler-check-{uuid4().hex[:12]}"
    fixture = f"/tmp/solo-fixture-{uuid4().hex[:12]}"
    scheme = f"/tmp/solo-scheme-{uuid4().hex[:12]}"
    docker("cp", str(ROOT / "algos/scheme/tests/fixtures/research"), f"{WORKER}:{fixture}")
    docker("exec", "-T", WORKER, "mkdir", "-p", scheme)
    for item in ("pyproject.toml", "README.md", "src"):
        docker("cp", str(ROOT / "algos/scheme" / item), f"{WORKER}:{scheme}/{item}")
    # 工作区源码可能包含开发缓存，uv build 只打包 pyproject 声明的模块。
    print("Preparing isolated wheel environments...", flush=True)
    python(
        WORKER, f"RUN_ROOT={run_root!r}\nFIXTURE={fixture!r}\nSCHEME={scheme!r}\n" + PREPARE, user="solo"
    )
    summary = {"directory": run_root, "runs": {}}
    for case in ("factor", "backtest", "bad-hash"):
        kind = "factor" if case == "bad-hash" else case
        input_file = f"{run_root}/{case}/input.json"
        before = {row["id"] for row in query(f"client.instances({kind!r})")}
        query(f"client.start({kind!r}, {input_file!r})")
        deadline = time.monotonic() + 600
        instance = None
        previous_state = None
        while time.monotonic() < deadline:
            candidates = query(f"client.instances({kind!r})")
            instance = next(
                (
                    row
                    for row in candidates
                    if row["id"] not in before and input_file in json.dumps(row)
                ),
                None,
            )
            if instance:
                state = instance["state"]
                if state != previous_state:
                    print(
                        f"{case}: instance={instance['id']} state={state}", flush=True
                    )
                    previous_state = state
                if state in {"SUCCESS", "FAILURE", "STOP", "KILL", "PAUSE"}:
                    break
            time.sleep(3)
        else:
            raise TimeoutError(f"{case} did not finish in 600 seconds: {instance}")
        tasks = query(f"client.tasks({instance['id']})")
        assert len(tasks) == 1, tasks
        task_id = tasks[0]["id"]
        log = query(f"client.log({task_id}, limit=10000)")["message"]
        expected = "FAILURE" if case == "bad-hash" else "SUCCESS"
        assert instance["state"] == expected, log
        if case == "bad-hash":
            assert "SHA256" in log, log
        summary["runs"][case] = {
            "instance_id": instance["id"],
            "task_id": task_id,
            "state": expected,
        }

    # 三个服务均以业务 UID 读取同一批 Parquet；不只检查文件是否存在。
    for service in (WORKER, "backend", "jupyter"):
        counts = json.loads(
            python(
                service,
                f"""
import json
from pathlib import Path
import pandas as pd
root = Path({run_root!r})
counts = {{}}
for case in ("factor", "backtest"):
    output = root / case / "output"
    manifest = json.loads((output / "run.json").read_text())
    assert manifest["versions"]["scheme"] == "1.0.0"
    counts[case] = {{p.name: len(pd.read_parquet(p)) for p in output.glob("*.parquet")}}
    assert len(counts[case]) == 5, counts
    assert any(counts[case].values()), counts
assert not (root / "bad-hash" / "output" / "run.json").exists()
print(json.dumps(counts))
""",
                project=f"{run_root}/factor/environment" if service == WORKER else None,
            )
        )
        print(f"{service}: shared Parquet readable", flush=True)
        summary["reports"] = counts
    python(
        "backend",
        f"from pathlib import Path\nPath({run_root!r} + '/verification.json').write_text({json.dumps(summary, indent=2)!r})",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
