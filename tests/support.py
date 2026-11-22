import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "plugins" / "chisel" / "scripts" / "chisel.py"

FAKE_GH = """#!/bin/sh
echo "$@" >> "$GH_LOG"
if [ "$1 $2" = "pr create" ]; then echo "https://github.com/example/repo/pull/7"; fi
"""


class RepoTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        self.remote = root / "remote.git"
        bin_dir = root / "bin"
        bin_dir.mkdir()
        gh = bin_dir / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        self.gh_log = root / "gh.log"
        self.env = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "GH_LOG": str(self.gh_log),
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
        subprocess.run(["git", "init", "-q", "--bare", str(self.remote)], check=True)
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("remote", "add", "origin", str(self.remote))
        self.write("README.md", "hello\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "Initial commit")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.repo, env=self.env, check=True, capture_output=True, text=True
        ).stdout.strip()

    def write(self, path, content):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def chisel(self, *args, stdin=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.repo,
            env=self.env,
            input=stdin,
            capture_output=True,
            text=True,
        )

    def ok(self, *args):
        result = self.chisel(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def pre_tool_use(self, tool_name, tool_input):
        payload = {"hook_event_name": "PreToolUse", "cwd": str(self.repo), "tool_name": tool_name, "tool_input": tool_input}
        result = self.chisel("hook", "pre-tool-use", stdin=json.dumps(payload))
        self.assertEqual(result.returncode, 0, result.stderr)
        if not result.stdout.strip():
            return None
        return json.loads(result.stdout)["hookSpecificOutput"]

    def session_start(self, source):
        payload = {"hook_event_name": "SessionStart", "cwd": str(self.repo), "source": source}
        result = self.chisel("hook", "session-start", stdin=json.dumps(payload))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def approve_as_user(self):
        return self.ok("approve")

    def start_planned_task(self, branch="feature/greeting"):
        self.ok("config", "--docs", "docs/SPEC.md", "docs/IMPLEMENTATION.md")
        self.ok("begin", "--task", "Greeting", "--branch", branch)
        self.write("docs/IMPLEMENTATION.md", "# Plan\n")
        self.ok("request", "plan")
        self.approve_as_user()
        self.ok("commit", "--message", "Plan the greeting")
        self.session_start("clear")

    def last_commit_files(self):
        return set(self.git("show", "--name-only", "--format=", "HEAD").splitlines())
