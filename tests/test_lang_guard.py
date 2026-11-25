import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "claude/hooks/lang-guard.py"
SPEC = importlib.util.spec_from_file_location("lang_guard", SCRIPT)
LG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LG)

ZH_PROMPT = "帮我看一下这个接口为什么变慢了，然后修好"
EN_UPDATE = "Now checking how the cache layer handles expired entries before writing the fix for this endpoint."
EN_PROMPT = "Please look into why this endpoint got slow and fix it for me today"
ZH_UPDATE = "正在看缓存层怎么处理过期条目，然后再写修复。"


class LangTests(unittest.TestCase):
    def test_classifies_plain_text(self):
        self.assertEqual(LG.lang(ZH_UPDATE), "zh")
        self.assertEqual(LG.lang(EN_UPDATE), "en")
        self.assertIsNone(LG.lang("OK, done."))

    def test_ignores_code_and_paths(self):
        text = (
            "已修好。\n```python\nfor item in items: print(item.name, item.value, item.size)\n```\n见 /src/app/cache.py"
        )
        self.assertEqual(LG.lang(text), "zh")

    def test_short_chinese_prompt(self):
        self.assertEqual(LG.lang("好的，继续", min_cjk=2), "zh")


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ, LKI_LANG_GUARD_DIR=self.tmp.name, CLAUDE_CODE_ENTRYPOINT="cli")

    def tearDown(self):
        self.tmp.cleanup()

    def run_hook(self, event, **extra):
        payload = {"hook_event_name": event, "session_id": "s1", "transcript_path": "/nonexistent.jsonl"}
        payload.update(extra)
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)], input=json.dumps(payload), capture_output=True, text=True, env=self.env
        )
        self.assertEqual(proc.returncode, 0)
        return json.loads(proc.stdout) if proc.stdout else None

    def tool_calls(self, n, **extra):
        return [self.run_hook("PostToolUse", tool_name="Bash", **extra) for _ in range(n)]

    def test_nudges_every_few_tool_calls(self):
        self.run_hook("UserPromptSubmit", prompt=ZH_PROMPT)
        outs = self.tool_calls(LG.NUDGE_EVERY)
        self.assertEqual(outs[:-1], [None] * (LG.NUDGE_EVERY - 1))
        self.assertEqual(outs[-1]["hookSpecificOutput"]["additionalContext"], LG.NUDGE)
        self.run_hook("UserPromptSubmit", prompt="继续")  # a new turn restarts the count
        self.assertEqual(self.tool_calls(LG.NUDGE_EVERY - 1), [None] * (LG.NUDGE_EVERY - 1))

    def test_silent_for_english_or_unknown_prompts(self):
        self.assertEqual(self.tool_calls(LG.NUDGE_EVERY), [None] * LG.NUDGE_EVERY)
        self.run_hook("UserPromptSubmit", prompt=EN_PROMPT)
        self.assertEqual(self.tool_calls(LG.NUDGE_EVERY), [None] * LG.NUDGE_EVERY)

    def test_short_prompt_keeps_previous_language(self):
        self.run_hook("UserPromptSubmit", prompt=ZH_PROMPT)
        self.run_hook("UserPromptSubmit", prompt="ok go")
        self.assertIsNotNone(self.tool_calls(LG.NUDGE_EVERY)[-1])

    def test_chinese_prompt_with_pasted_english_log(self):
        log = "Traceback (most recent call last): " + "File app.py line 12 in handler raise TimeoutError " * 20
        self.assertEqual(LG.prompt_lang("看下这个报错 " + log), "zh")

    def test_ignores_subagents(self):
        self.run_hook("UserPromptSubmit", prompt=ZH_PROMPT)
        self.assertEqual(self.tool_calls(LG.NUDGE_EVERY, agent_id="sub-1"), [None] * LG.NUDGE_EVERY)

    def test_stop_blocks_english_final_once(self):
        self.run_hook("UserPromptSubmit", prompt=ZH_PROMPT)
        out = self.run_hook("Stop", last_assistant_message=EN_UPDATE, stop_hook_active=False)
        self.assertEqual(out["decision"], "block")
        self.assertIsNone(self.run_hook("Stop", last_assistant_message=EN_UPDATE, stop_hook_active=True))
        self.assertIsNone(self.run_hook("Stop", last_assistant_message=ZH_UPDATE, stop_hook_active=False))

    def test_stop_skipped_for_headless_runs(self):
        self.run_hook("UserPromptSubmit", prompt=ZH_PROMPT)
        self.env["CLAUDE_CODE_ENTRYPOINT"] = "sdk-cli"
        self.assertIsNone(self.run_hook("Stop", last_assistant_message=EN_UPDATE, stop_hook_active=False))

    def test_stop_allows_english_for_english_prompt(self):
        self.run_hook("UserPromptSubmit", prompt=EN_PROMPT)
        self.assertIsNone(self.run_hook("Stop", last_assistant_message=EN_UPDATE, stop_hook_active=False))

    def test_session_end_removes_state(self):
        self.run_hook("UserPromptSubmit", prompt=ZH_PROMPT)
        self.assertTrue(any(Path(self.tmp.name).iterdir()))
        self.run_hook("SessionEnd")
        self.assertFalse(any(Path(self.tmp.name).iterdir()))

    def test_fails_open(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)], input="not json", capture_output=True, text=True, env=self.env
        )
        self.assertEqual((proc.returncode, proc.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
