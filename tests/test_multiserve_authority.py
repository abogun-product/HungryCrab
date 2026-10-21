from __future__ import annotations

import json
from pathlib import Path

import pytest
from fixture_builder import git
from test_multifeed import fake_eat
from test_serve import FakeIssues

from hungry_crab.cache import Target
from hungry_crab.errors import CrabError
from hungry_crab.feeder import EatOptions, EatResult
from hungry_crab.ledger import Ledger
from hungry_crab.maw import MawConfig
from hungry_crab.multifeed import eat_many
from hungry_crab.multiserve import serve_many
from hungry_crab.serve import ServeOptions


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("mode", ["issue", "pr-branch"])
def test_routing_ids_do_not_authorize_automatic_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, explicit: bool
) -> None:
    maw = tmp_path / "maw"
    maw.mkdir()
    git(maw, "init", "-b", "main")
    git(maw, "remote", "add", "origin", "https://github.com/example/maw.git")
    prey = [tmp_path / "a", tmp_path / "b"]
    for path in prey:
        path.mkdir()

    def feed(prey: Target, maw: Path, options: EatOptions, **kwargs: object) -> EatResult:
        result = fake_eat(prey, maw, options, **kwargs)
        if mode == "pr-branch":
            path = result.out_dir / "menu.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["candidates"][0]["serve_as"] = "pr"
            path.write_text(json.dumps(data), encoding="utf-8")
        return result

    monkeypatch.setattr("hungry_crab.multifeed.eat", feed)
    bundle = eat_many(
        [Target(path=path) for path in prey], maw, EatOptions(out=tmp_path / "bundle")
    )
    config = MawConfig.load(maw)
    config.hunger["ci"] = "ideas-only" if mode == "issue" else "auto"
    config.serve.prs = "ask"
    client = FakeIssues()
    ledger = Ledger.load(None, maw="maw")
    # Receipt transport is inert; policy and per-source serving remain real.
    monkeypatch.setattr("hungry_crab.multiserve.decode_receipt_stream", lambda _: "unused")
    monkeypatch.setattr("hungry_crab.multiserve.load_cleanroom_receipts", lambda _: {})
    options = ServeOptions(
        mode=mode, ids=["crab:ci:ci.cache"] if explicit else [], top=None if explicit else 1
    )
    if mode == "pr-branch" and not explicit:
        with pytest.raises(CrabError, match=r"serve\.prs is ask"):
            serve_many(bundle.out_dir, maw, options, config=config, ledger=ledger, client=client)
    else:
        report = serve_many(
            bundle.out_dir, maw, options, config=config, ledger=ledger, client=client
        )
        if mode == "issue":
            assert bool(report.served) is explicit
            assert len(client.created) == int(explicit)
            if not explicit:
                assert any(row["reason"] == "serve_as: idea" for row in report.skipped)
        else:
            assert any("receipt" in row["reason"] for row in report.skipped)
    if not (explicit and mode == "issue"):
        assert not client.created and not client.labels and not ledger.entries
