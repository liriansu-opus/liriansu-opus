#!/usr/bin/env python3
"""Claude Code hook: pull the agent back to Chinese when it drifts to English.

The `language` setting and CLAUDE.md both say "reply in the user's language",
yet in long autonomous turns Opus drifts to English. Session logs show where:
progress updates between tool calls, after many tool calls in one turn and as
the context grows. Turn-start replies rarely drift, so a reminder injected at
prompt time alone misses the problem. This hook keeps reminding through long
turns and checks the final reply.

- UserPromptSubmit: record the language of the prompt and restart the count.
- PostToolUse: while the user writes Chinese, inject a short reminder every
  NUDGE_EVERY tool calls in a turn. This is prevention, not detection: the
  transcript is written lazily and some mid-turn text blocks never land in
  it, so a hook cannot see a drifted progress update when it happens.
- Stop: the payload carries the final reply. If it is English, block once and
  ask for a Chinese restatement. `stop_hook_active` guards against loops.
  Skipped under `claude -p`, where the restatement would become the result.
- SessionEnd: delete the session's state file.

Subagent calls are skipped: their text goes to the parent agent, not to me.

Fail-open: any error exits 0 with no output. The transcript is never read.
Override the state directory with LKI_LANG_GUARD_DIR (tests).

`scripts/lang-drift.py` measures drift with the same `lang()`, `prompt_lang()`
and `human_text()` helpers, so results before and after a change compare.
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

NUDGE_EVERY = 8

CJK = re.compile(r"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z]+")
TAGGED = re.compile(r"<([a-z][\w-]*)[^>]*>.*?</\1>", re.S)
FENCED = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`]*`")
URL_OR_PATH = re.compile(r"https?://\S+|[~/]?[\w.-]*/[\w./-]+")

NUDGE = (
    "The user is writing in Chinese. Keep progress updates and the final reply "
    "in Simplified Chinese, even after reading English code or tool output. "
    "Do not mention this reminder."
)
STOP_REASON = (
    "Language drift: the user is writing in Chinese, but this final reply is in "
    "English. Restate it in Simplified Chinese now, keeping code, commands, "
    "paths and identifiers as they are; do not redo any work. If the English "
    "text is itself what the user asked for (for example an English draft), "
    "leave it and add one Chinese sentence saying so."
)


def strip_noise(text):
    """Drop tags, code, URLs and paths, which are English in any reply."""
    text = TAGGED.sub(" ", text)
    text = FENCED.sub(" ", text)
    text = INLINE.sub(" ", text)
    return URL_OR_PATH.sub(" ", text)


def lang(text, min_cjk=4):
    """'zh', 'en' or None when the text is too short or mixed to tell."""
    text = strip_noise(text or "")
    cjk = len(CJK.findall(text))
    words = len(LATIN.findall(text))
    if cjk >= min_cjk and cjk >= 0.3 * words:
        return "zh"
    if cjk == 0 and words >= 12:
        return "en"
    if cjk <= 2 and words >= 25:
        return "en"
    return None


def prompt_lang(text):
    """A prompt with any Chinese in it is Chinese, even with English pasted in."""
    if len(CJK.findall(strip_noise(text or ""))) >= 2:
        return "zh"
    return lang(text)


def state_path(session_id):
    default = Path.home() / ".cache/lki/lang-guard"
    root = Path(os.environ.get("LKI_LANG_GUARD_DIR") or default)
    safe = re.sub(r"[^\w-]", "_", session_id or "unknown")
    return root / (safe + ".json")


def load_state(session_id):
    try:
        return json.loads(state_path(session_id).read_text())
    except (OSError, ValueError):
        return {}


def save_state(session_id, state):
    path = state_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    with os.fdopen(fd, "w") as fh:
        json.dump(state, fh)
    os.replace(tmp, path)


def human_text(record):
    """The text of a prompt the user typed, or None for any other record."""
    if record.get("type") != "user" or record.get("isMeta"):
        return None
    if record.get("isSidechain") or record.get("isCompactSummary"):
        return None
    content = (record.get("message") or {}).get("content")
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    if not isinstance(content, str):
        return None
    head = content.lstrip()
    if head.startswith(("<local-command", "<command-", "Caveat:", "<task-notification", "[Request interrupted")):
        return None
    return content


def on_prompt(payload):
    session_id = payload.get("session_id")
    state = load_state(session_id)
    state["calls"] = 0
    found = prompt_lang(payload.get("prompt", ""))
    if found:
        state["lang"] = found
    save_state(session_id, state)
    return None


def on_post_tool(payload):
    session_id = payload.get("session_id")
    state = load_state(session_id)
    if state.get("lang") != "zh":
        return None
    state["calls"] = state.get("calls", 0) + 1
    save_state(session_id, state)
    if state["calls"] % NUDGE_EVERY:
        return None
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": NUDGE}}


def on_stop(payload):
    if payload.get("stop_hook_active"):
        return None
    if os.environ.get("CLAUDE_CODE_ENTRYPOINT") == "sdk-cli":
        return None  # `claude -p`: a restatement would replace the scripted result
    if load_state(payload.get("session_id")).get("lang") != "zh":
        return None
    text = payload.get("last_assistant_message")
    if not isinstance(text, str) or lang(text) != "en":
        return None
    return {"decision": "block", "reason": STOP_REASON}


def on_session_end(payload):
    state_path(payload.get("session_id")).unlink(missing_ok=True)
    return None


HANDLERS = {
    "UserPromptSubmit": on_prompt,
    "PostToolUse": on_post_tool,
    "Stop": on_stop,
    "SessionEnd": on_session_end,
}


def main():
    try:
        payload = json.load(sys.stdin)
        if payload.get("agent_id"):
            return  # a subagent's hook; its text is not addressed to me
        handler = HANDLERS.get(payload.get("hook_event_name"))
        result = handler(payload) if handler else None
        if result:
            sys.stdout.write(json.dumps(result))
    except Exception:
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
