"""Build our package, install it into isolated uv tool homes, and exercise the installed CLI.

Only HungryCrab's own trusted build/install commands run. The synthetic repositories are data;
their workflows and files are never executed. User tool installs and host configuration stay put.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import anyio
from mcp_probe import probe

ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str], *, cwd: Path, env: dict[str, str], code: int = 0) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    if result.returncode != code:
        raise RuntimeError(
            f"{args[0]} exited {result.returncode}, expected {code}: {result.stderr[-2000:]}"
        )
    return result.stdout


def repositories(workspace: Path, env: dict[str, str]) -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    for name in ("prey", "maw"):
        path = workspace / name
        path.mkdir(parents=True)
        (path / "LICENSE").write_text(license_text, encoding="utf-8")
        (path / "README.md").write_text(f"# {name}\n", encoding="utf-8")
        (path / "pyproject.toml").write_text(
            f'[project]\nname = "{name}"\nversion = "1.0.0"\n', encoding="utf-8"
        )
        if name == "prey":
            workflow = path / ".github" / "workflows" / "ci.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
                "    steps:\n      - run: pytest\n      - run: ruff check .\n",
                encoding="utf-8",
            )
        run(["git", "init", "-b", "main"], cwd=path, env=env)
        run(["git", "add", "."], cwd=path, env=env)
        run(
            [
                "git",
                "-c",
                "user.name=Install Test",
                "-c",
                "user.email=test@example.invalid",
                "-c",
                "core.hooksPath=",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-m",
                "test: synthetic install fixture",
            ],
            cwd=path,
            env=env,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", action="store_true", help="also install our eat skill with npx")
    parser.add_argument(
        "--offline", action="store_true", help="use cached build/install dependencies"
    )
    args = parser.parse_args()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required for the installation acceptance test")
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"GH_TOKEN", "GITHUB_TOKEN", "PYTHONPATH"}
    }
    env.update(PYTHONIOENCODING="utf-8", PYTHONNOUSERSITE="1")
    if args.offline:
        env["UV_OFFLINE"] = "true"
    with tempfile.TemporaryDirectory(prefix="crab install ") as temporary:
        directory = Path(temporary)
        built = directory / "dist"
        run([uv, "build", "--out-dir", str(built)], cwd=ROOT, env=env)
        wheel = next(built.glob("*.whl"))
        archive = next(built.glob("*.tar.gz"))
        workspace = directory / "workspace"
        repositories(workspace, env)
        for extra, package in (("base", archive), ("mcp", wheel)):
            home = directory / extra
            bin_dir = home / "bin"
            tool_env = {**env, "UV_TOOL_DIR": str(home / "tools"), "UV_TOOL_BIN_DIR": str(bin_dir)}
            requirement = f"hungry-crab{'[mcp]' if extra == 'mcp' else ''} @ {package.as_uri()}"
            run(
                [uv, "tool", "install", "--python", sys.executable, requirement],
                cwd=directory,
                env=tool_env,
            )
            command = str(bin_dir / ("crab.exe" if os.name == "nt" else "crab"))
            assert (
                run([command, "--version"], cwd=directory, env=tool_env).strip()
                == f"crab {version}"
            )
            assert "report" in run([command, "--help"], cwd=directory, env=tool_env)
            digest = directory / f"{extra}-digest"
            run(
                [
                    command,
                    "digest",
                    str(workspace / "prey"),
                    "--out",
                    str(digest),
                    "--maw-license",
                    "MIT",
                    "--fail-on-miner-error",
                    "--fail-on-loss",
                ],
                cwd=directory,
                env=tool_env,
            )
            report = directory / f"{extra}-report.html"
            run([command, "report", str(digest), "--out", str(report)], cwd=directory, env=tool_env)
            assert "Miner health" in report.read_text(encoding="utf-8")
            check = run(
                [command, "mcp", "--check"],
                cwd=directory,
                env=tool_env,
                code=0 if extra == "mcp" else 2,
            )
            if extra == "mcp":
                assert json.loads(check)["tools"] == ["crab_digest", "crab_menu"]
                anyio.run(probe, command, workspace, directory / "mcp-cache")
            print(f"PASS: {extra} ({package.suffix}), installed CLI, digest and HTML")
        if args.skills:
            npx = shutil.which("npx.cmd" if os.name == "nt" else "npx")
            if npx is None:
                raise RuntimeError("npx is required for --skills")
            project = directory / "skills consumer"
            project.mkdir()
            run(
                [
                    npx,
                    "--yes",
                    "skills",
                    "add",
                    str(ROOT / "skills" / "eat"),
                    "--skill",
                    "eat",
                    "--agent",
                    "codex",
                    "--copy",
                    "--yes",
                ],
                cwd=project,
                env=env,
            )
            assert (project / ".agents" / "skills" / "eat" / "SKILL.md").is_file()
            print("PASS: npx skills add installs our portable eat skill in an isolated project")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
