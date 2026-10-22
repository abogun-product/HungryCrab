from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest


def test_action_resolves_local_paths_in_the_caller_and_preserves_literal_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "feeder_action.py"
    spec = importlib.util.spec_from_file_location("feeder_action_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    workspace = tmp_path / "maw with spaces"
    prey = workspace / "donor;literal"
    prey.mkdir(parents=True)
    outputs = tmp_path / "outputs"
    summary = tmp_path / "summary"
    env = {
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_WORKSPACE": str(workspace),
        "GITHUB_OUTPUT": str(outputs),
        "GITHUB_STEP_SUMMARY": str(summary),
        "CRAB_PREY": "donor;literal",
        "CRAB_MAW": ".",
        "CRAB_SINCE": "all",
        "CRAB_ISSUES": "0",
        "CRAB_TOP": "30",
        "CRAB_MAX_REPO_KB": "307200",
        "CRAB_DEPTH": "normal",
        "CRAB_SHALLOW": "true",
        "CRAB_WIKI": "false",
        "CRAB_ALLOW_LOSS": "false",
        "CRAB_ALLOW_PRIVATE_ARTIFACT": "true",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    calls: list[list[str]] = []

    def fake_main(args: list[str]) -> int:
        calls.append(args)
        print(json.dumps({"out_dir": str(tmp_path / "bundle"), "counts": {"total": 2}}))
        return 0

    monkeypatch.setattr(module, "main", fake_main)
    assert module.run() == 0
    assert calls[0][calls[0].index("eat") + 1] == str(prey.resolve())
    assert calls[0][calls[0].index("--maw") + 1] == str(workspace)
    assert "candidate-count=2" in outputs.read_text()
    assert "2 candidates" in summary.read_text()


def _action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    prey: str,
    event: dict[str, object] | None,
    allow: str = "false",
) -> tuple[Any, list[list[str]]]:
    script = Path(__file__).resolve().parents[1] / "scripts" / "feeder_action.py"
    spec = importlib.util.spec_from_file_location("feeder_action_exposure", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    workspace = tmp_path / "workspace"
    (workspace / "donor").mkdir(parents=True, exist_ok=True)
    env = {
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_WORKSPACE": str(workspace),
        "GITHUB_OUTPUT": str(tmp_path / "outputs"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        "CRAB_PREY": prey,
        "CRAB_MAW": ".",
        "CRAB_SINCE": "all",
        "CRAB_ISSUES": "0",
        "CRAB_TOP": "30",
        "CRAB_MAX_REPO_KB": "307200",
        "CRAB_DEPTH": "normal",
        "CRAB_SHALLOW": "true",
        "CRAB_WIKI": "false",
        "CRAB_ALLOW_LOSS": "false",
        "CRAB_ALLOW_PRIVATE_ARTIFACT": allow,
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    if event is None:
        monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    else:
        path = tmp_path / "event.json"
        path.write_text(json.dumps(event), encoding="utf-8")
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(path))
    calls: list[list[str]] = []

    def fake_main(args: list[str]) -> int:
        calls.append(args)
        print(json.dumps({"out_dir": str(tmp_path / "bundle"), "counts": {"total": 1}}))
        return 0

    monkeypatch.setattr(module, "main", fake_main)
    return module, calls


@pytest.mark.parametrize("event", [{"repository": {"private": False}}, {}, None])
def test_a_public_caller_never_uploads_an_unconfirmed_prey(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, event: dict[str, object] | None
) -> None:
    module, calls = _action(tmp_path, monkeypatch, prey="donor", event=event)
    assert module.run() == 2
    assert calls == [], "the refusal comes before any acquisition or digest"


def test_a_private_caller_or_an_explicit_opt_in_uploads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module, calls = _action(
        tmp_path, monkeypatch, prey="donor", event={"repository": {"visibility": "private"}}
    )
    assert module.run() == 0 and len(calls) == 1
    module, calls = _action(
        tmp_path, monkeypatch, prey="donor", event={"repository": {"private": False}}, allow="true"
    )
    assert module.run() == 0 and len(calls) == 1


@pytest.mark.parametrize(("private", "code"), [(False, 0), (True, 2)])
def test_the_forge_decides_whether_a_remote_prey_is_public(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, private: bool, code: int
) -> None:
    module, calls = _action(
        tmp_path, monkeypatch, prey="owner/repo", event={"repository": {"private": False}}
    )

    class Client:
        def repo(self, _: object) -> dict[str, object]:
            return {"private": private}

    monkeypatch.setattr(module, "client_for", lambda _: Client())
    assert module.run() == code
    assert len(calls) == (1 if code == 0 else 0)
