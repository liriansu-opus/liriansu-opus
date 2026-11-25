#!/usr/bin/env python3
"""Measure how often Claude answers in English while I write Chinese.

Reads main-thread Claude Code transcripts modified in the last N days (default
7) and reports the English share of assistant text blocks written while my
latest prompt was Chinese, split by context size and by final vs. progress
messages. Uses the classifier from claude/hooks/lang-guard.py so numbers stay
comparable across changes to the hook.

    python3 scripts/lang-drift.py [days]
    python3 scripts/lang-drift.py --since 2026-11-16T09:45   # UTC, per record
"""

import collections
import glob
import importlib.util
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "claude/hooks/lang-guard.py"
SPEC = importlib.util.spec_from_file_location("lang_guard", HOOK)
LG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LG)


def blocks(path, since=""):
    """(final, context_tokens, lang) per assistant text block under a zh prompt."""
    user, ctx, out = None, 0, []
    with open(path, errors="ignore") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("isSidechain"):
                continue
            text = LG.human_text(r)
            if text is not None:
                user = LG.prompt_lang(text) or user
                if out:
                    out[-1][0] = True
                continue
            if r.get("type") != "assistant" or r.get("timestamp", "") < since:
                continue
            m = r.get("message") or {}
            u = m.get("usage") or {}
            ctx = (
                sum(u.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
                or ctx
            )
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "text" and user == "zh":
                    found = LG.lang(b["text"])
                    if found:
                        out.append([False, ctx, found])
    if out:
        out[-1][0] = True
    return out


def rate(c):
    n = c["zh"] + c["en"]
    return f"{c['en']:5}/{n:<5} {c['en'] / n:6.1%}" if n else "    -"


def main():
    args = sys.argv[1:]
    since = args[1] if args[:1] == ["--since"] else ""
    if since:
        cut = datetime.fromisoformat(since[:16]).replace(tzinfo=UTC).timestamp()
        days = (time.time() - cut) / 86400
    else:
        days = float(args[0]) if args else 7
        cut = time.time() - days * 86400
    total, kind, size = (
        collections.Counter(),
        collections.defaultdict(collections.Counter),
        collections.defaultdict(collections.Counter),
    )
    sessions = drifted = 0
    for path in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")):
        if os.path.getmtime(path) < cut:
            continue
        found = blocks(path, since)
        if not found:
            continue
        sessions += 1
        drifted += any(b[2] == "en" for b in found)
        for final, ctx, lang in found:
            total[lang] += 1
            kind["final reply" if final else "progress update"][lang] += 1
            size[min(ctx // 100_000, 4)][lang] += 1
    print(f"since {since} UTC:" if since else f"last {days:g} days:", end=" ")
    print(f"{sessions} sessions with Chinese prompts, {drifted} drifted to English")
    print(f"  all text blocks      {rate(total)}")
    for k, c in sorted(kind.items()):
        print(f"  {k:<20} {rate(c)}")
    for k in sorted(size):
        label = f"context {k * 100}k+" if k < 4 else "context 400k+"
        print(f"  {label:<20} {rate(size[k])}")


if __name__ == "__main__":
    main()
