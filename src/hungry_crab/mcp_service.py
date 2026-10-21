"""Operator-scoped deterministic operations exposed by MCP, without publication authority."""

from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any, Literal

from .artifact_read import MAX_PAGE_BYTES, markdown_pages, read_bytes, read_object
from .cache import Slug, Target
from .compare import compare_for_maw
from .digest import DigestOptions, incomplete_miners, run_digest
from .digest_integrity import digest_integrity_errors
from .errors import CrabError, UsageError
from .fetch.catch import CatchOptions
from .nutrients import CATEGORIES


class AnalysisService:
    def __init__(self, roots: list[Path], cache: Path, *, allow_network: bool = False) -> None:
        if not roots:
            raise UsageError("MCP needs at least one operator-approved --root")
        self.roots = [root.expanduser().resolve() for root in roots]
        if any(not root.is_dir() for root in self.roots):
            raise UsageError("every MCP root must be an existing directory")
        self.cache = cache.expanduser().resolve()
        if any(self.cache.is_relative_to(root) for root in self.roots):
            raise UsageError("MCP cache must be outside the approved source roots")
        self.allow_network = allow_network
        # The CLI cache is shared mutable state; serialize this server's own requests.
        self.lock = threading.Lock()

    def local(self, value: str) -> Path:
        if not value.strip() or "\x00" in value:
            raise UsageError("a local repository path is required")
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.roots[0] / path
        path = path.resolve()
        if not any(path.is_relative_to(root) for root in self.roots) or path.is_relative_to(
            self.cache
        ):
            raise UsageError("repository is outside the operator-approved MCP roots")
        if not path.is_dir():
            raise UsageError("repository must be an existing local directory")
        return path

    def prey(self, value: str) -> Target:
        if not value.strip() or "\x00" in value:
            raise UsageError("prey must not be empty")
        explicit = value.startswith((".", "/", "\\", "~")) or re.match(r"^[A-Za-z]:", value)
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = self.roots[0] / candidate
        if explicit or candidate.exists():
            return Target(path=self.local(value))
        slug = Slug.parse(value)
        if not self.allow_network:
            raise UsageError("remote prey requires the operator's --allow-network option")
        return Target(slug=slug)

    def options(self, depth: Literal["normal", "deep"]) -> DigestOptions:
        if depth not in {"normal", "deep"}:
            raise UsageError("depth must be normal or deep")
        return DigestOptions(
            depth=depth,
            cache_root=self.cache,
            catch_options=CatchOptions(shallow=True, since="90d", issues=0, wiki=False),
        )

    def digest(
        self, prey: str, depth: Literal["normal", "deep"] = "normal", page: str | None = None
    ) -> dict[str, Any]:
        with self.lock:
            target = self.prey(prey)
            result = run_digest(target, self.options(depth))
            errors = digest_integrity_errors(result.out_dir, result.manifest)
            if (
                errors
                or incomplete_miners(result.manifest)
                or result.manifest.get("coverage", {}).get("healthy") is not True
            ):
                raise CrabError("MCP refuses incomplete or damaged digest evidence")
            pages = markdown_pages(result.out_dir, result.manifest)
            payload: dict[str, Any] = {
                "schema": "hungry-crab.mcp-digest/1",
                "untrusted_data": True,
                "manifest": result.manifest,
                "digest_dir": str(result.out_dir),
                "pages": pages,
                "side_effects": {
                    "scope": "cache only",
                    "ledger_written": False,
                    "published": False,
                },
            }
            if page is not None:
                if page not in pages:
                    raise UsageError("page must be one of the listed digest Markdown artifacts")
                payload["page"] = {
                    "name": page,
                    "text": read_bytes(result.out_dir / page, MAX_PAGE_BYTES).decode(
                        "utf-8", errors="replace"
                    ),
                }
            return payload

    def menu(
        self, prey: str, maw: str, offset: int = 0, limit: int = 15, category: str | None = None
    ) -> dict[str, Any]:
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise UsageError("offset must be non-negative and limit must be in 1..100")
        if category is not None and category not in CATEGORIES:
            raise UsageError("unknown nutrient category")
        with self.lock:
            target, root = self.prey(prey), self.local(maw)
            result, _, _, _ = compare_for_maw(
                target,
                root,
                digest_options=self.options("normal"),
                record_ledger=False,
                issue_lookup=None,
            )
            for directory in (result.prey_dir, result.maw_dir):
                if directory is None:
                    raise CrabError("MCP menu is missing its source digest")
                manifest = read_object(directory / "manifest.json")
                if (
                    incomplete_miners(manifest)
                    or digest_integrity_errors(directory, manifest)
                    or manifest.get("coverage", {}).get("healthy") is not True
                ):
                    raise CrabError("MCP refuses incomplete menu source evidence")
            rows = result.menu["candidates"]
            if category is not None:
                rows = [row for row in rows if row["category"] == category]
            selected = rows[offset : offset + limit]
            return {
                "schema": "hungry-crab.mcp-menu/1",
                "untrusted_data": True,
                "prey": result.menu["prey"],
                "maw": result.menu["maw"],
                "verdict": result.menu["verdict"],
                "meal_dir": str(result.meal_dir),
                "candidates": selected,
                "total": len(rows),
                "offset": offset,
                "next_offset": offset + len(selected)
                if offset + len(selected) < len(rows)
                else None,
                "hidden_count": len(result.hidden),
                "side_effects": {
                    "scope": "cache only",
                    "ledger_written": False,
                    "published": False,
                },
            }
