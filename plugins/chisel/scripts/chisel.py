#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
RESUME_HINT = "Tell the user to run /clear and then /chisel:task to continue in a fresh session."

GATE_NEXT_STEP = {
    "plan": "Run `chisel commit --message <subject>` to create the task branch and commit the plan.",
    "tests": "Write the implementation for this slice.",
    "impl": "Run `chisel commit --message <subject>` to commit the slice.",
    "push": "Run `chisel open-pr --title <title> --body-file <file>` to push and open the draft PR.",
    "ready": "Run `chisel ready --message <subject>` to commit the doc updates and mark the PR ready.",
}

APPROVE_COMMAND = re.compile(r"chisel\.py[\"']?\s+approve\b")
STATUS_COMMAND = re.compile(r"chisel\.py[\"']?\s+status\b")
STATE_PATH = re.compile(r"\.git/chisel/")
GUARDED_COMMANDS = [
    (re.compile(r"\bgit\b[^;&|\n]*\bcommit\b"), "commits"),
    (re.compile(r"\bgit\b[^;&|\n]*\bpush\b"), "pushes"),
    (re.compile(r"\bgh\s+pr\s+(create|ready|merge)\b"), "pull request changes"),
]
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


class ChiselError(Exception):
    pass


def git(repo, *args, env=None, check=True):
    result = subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise ChiselError(result.stderr.strip() or result.stdout.strip())
    return result


def run(repo, *args):
    result = subprocess.run(args, cwd=repo, capture_output=True, text=True)
    if result.returncode != 0:
        raise ChiselError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def find_git_dir(cwd):
    result = git(cwd, "rev-parse", "--absolute-git-dir", check=False)
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


class Workflow:
    def __init__(self, repo, git_dir):
        self.repo = Path(repo)
        self.git_dir = git_dir
        self.path = git_dir / "chisel" / "state.json"
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {}

    @classmethod
    def open(cls, cwd):
        git_dir = find_git_dir(cwd)
        if git_dir is None:
            raise ChiselError("Not inside a git repository.")
        top = git(cwd, "rev-parse", "--show-toplevel").stdout.strip()
        return cls(top, git_dir)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=2) + "\n")

    @property
    def task(self):
        return self.state.get("task")

    @property
    def docs(self):
        return self.state.get("docs", [])

    def require_task(self):
        if self.task is None:
            raise ChiselError("No chisel task is active. Start one with /chisel:task.")
        return self.task

    def worktree_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index"
            real_index = self.git_dir / "index"
            if real_index.exists():
                shutil.copy(real_index, index)
            env = {**os.environ, "GIT_INDEX_FILE": str(index)}
            git(self.repo, "add", "-A", env=env)
            return git(self.repo, "write-tree", env=env).stdout.strip()

    def head_tree(self):
        result = git(self.repo, "rev-parse", "--verify", "-q", "HEAD^{tree}", check=False)
        return result.stdout.strip() if result.returncode == 0 else EMPTY_TREE

    def changed_paths(self):
        return git(self.repo, "diff", "--name-only", self.head_tree(), self.worktree_tree()).stdout.split()

    def begin(self, title, branch):
        if self.task is not None:
            raise ChiselError(f"Task '{self.task['title']}' is still active.")
        self.state["task"] = {
            "title": title,
            "branch": branch,
            "planned": False,
            "slice": None,
            "single_gate": False,
            "pending": None,
            "approved": [],
            "tests_tree": None,
            "test_files": [],
            "pr_url": None,
            "locked": False,
        }
        self.save()
        return f"Task '{title}' started. Branch {branch} is created when the plan is approved."

    def configure(self, docs):
        self.state["docs"] = docs
        self.save()
        return "Docs: " + ", ".join(docs)

    def start_slice(self, slice_id, single_gate):
        task = self.require_task()
        if not task["planned"]:
            raise ChiselError("The plan is not committed yet.")
        if task["slice"] is not None and task["approved"]:
            raise ChiselError(f"Slice {task['slice']} has approvals and is not committed yet.")
        task.update(slice=slice_id, single_gate=single_gate, pending=None, approved=[], tests_tree=None, test_files=[])
        self.save()
        gates = "one gate (impl)" if single_gate else "two gates (tests, impl)"
        return f"Slice {slice_id} started with {gates}."

    def request(self, gate, test_files):
        task = self.require_task()
        if task["pending"] not in (None, gate):
            raise ChiselError(f"Gate '{task['pending']}' is still waiting for the user.")
        self.check_request(task, gate)
        if gate == "tests":
            task["approved"] = []
            task["test_files"] = test_files
        task["pending"] = gate
        self.save()
        return f"Gate '{gate}' is waiting. Present the report and ask the user to run /chisel:approve."

    def check_request(self, task, gate):
        if gate == "plan" and task["planned"]:
            raise ChiselError("The plan is already committed.")
        if gate in ("tests", "impl") and task["slice"] is None:
            raise ChiselError("No slice is in progress. Start one with `chisel slice --id <id>`.")
        if gate == "tests" and task["single_gate"]:
            raise ChiselError("This slice has a single gate: request 'impl'.")
        if gate == "impl" and not task["single_gate"]:
            if "tests" not in task["approved"]:
                raise ChiselError("The tests of this slice are not approved yet.")
            changed = self.changed_test_files(task)
            if changed:
                raise ChiselError(
                    "Approved tests changed: " + ", ".join(changed)
                    + ". Stop and ask the user before changing approved tests."
                )
        if gate == "push" and (not task["planned"] or task["slice"] is not None or task["pr_url"]):
            raise ChiselError("Push needs a committed plan, no slice in progress and no open PR.")
        if gate == "ready" and not task["pr_url"]:
            raise ChiselError("No pull request is open yet.")

    def changed_test_files(self, task):
        if not task["test_files"]:
            return []
        result = git(self.repo, "diff", "--name-only", task["tests_tree"], self.worktree_tree(), "--", *task["test_files"])
        return result.stdout.split()

    def approve(self):
        task = self.require_task()
        gate = task["pending"]
        if gate is None:
            raise ChiselError("No gate is waiting for approval.")
        task["approved"].append(gate)
        task["pending"] = None
        if gate == "tests":
            task["tests_tree"] = self.worktree_tree()
        self.save()
        return f"The user approved gate '{gate}'. {GATE_NEXT_STEP[gate]}"

    def commit(self, message):
        task = self.require_task()
        if "plan" in task["approved"]:
            return self.commit_plan(task, message)
        if "impl" in task["approved"]:
            return self.commit_slice(task, message)
        raise ChiselError("Nothing is approved for a commit.")

    def commit_plan(self, task, message):
        exists = git(self.repo, "rev-parse", "--verify", "-q", f"refs/heads/{task['branch']}", check=False).returncode == 0
        git(self.repo, "switch", *([] if exists else ["-c"]), task["branch"])
        committed = self.commit_all(message, allow_empty=True)
        task.update(planned=True, approved=[], locked=True)
        self.save()
        done = f"Committed the plan on {task['branch']}." if committed else f"On branch {task['branch']}, no doc changes to commit."
        return f"{done} {RESUME_HINT}"

    def commit_slice(self, task, message):
        self.commit_all(message, allow_empty=False)
        done = task["slice"]
        task.update(slice=None, single_gate=False, approved=[], tests_tree=None, test_files=[], locked=True)
        self.save()
        return f"Committed slice {done}. {RESUME_HINT}"

    def commit_all(self, message, allow_empty):
        if not self.changed_paths():
            if allow_empty:
                return False
            raise ChiselError("There are no changes to commit.")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", message)
        return True

    def open_pr(self, title, body_file):
        task = self.require_task()
        if "push" not in task["approved"]:
            raise ChiselError("Push is not approved.")
        git(self.repo, "push", "-u", "origin", task["branch"])
        url = run(self.repo, "gh", "pr", "create", "--draft", "--head", task["branch"], "--title", title, "--body-file", body_file)
        task.update(pr_url=url.splitlines()[-1], approved=[])
        self.save()
        return f"Opened draft PR {task['pr_url']}. Run the pr-reviewer next."

    def push(self):
        task = self.require_task()
        if not task["pr_url"]:
            raise ChiselError("No pull request is open yet: request the 'push' gate.")
        git(self.repo, "push", "origin", task["branch"])
        return f"Pushed {task['branch']}."

    def ready(self, message):
        task = self.require_task()
        if "ready" not in task["approved"]:
            raise ChiselError("Marking the PR ready is not approved.")
        outside = [path for path in self.changed_paths() if path not in self.docs]
        if outside:
            raise ChiselError("Only doc updates can be committed here, found: " + ", ".join(outside))
        self.commit_all(message, allow_empty=True)
        git(self.repo, "push", "origin", task["branch"])
        run(self.repo, "gh", "pr", "ready", task["pr_url"])
        self.state["task"] = None
        self.save()
        return f"PR {task['pr_url']} is ready for review. The chisel task is finished."

    def diff(self, since_tests, stat):
        task = self.require_task()
        if since_tests and not task["tests_tree"]:
            raise ChiselError("The tests of this slice are not approved yet.")
        base = task["tests_tree"] if since_tests else self.head_tree()
        return git(self.repo, "diff", *(["--stat"] if stat else []), base, self.worktree_tree()).stdout

    def status(self):
        docs = f"Docs: {', '.join(self.docs) or 'not configured'}"
        task = self.task
        if task is None:
            return f"No chisel task is active.\n{docs}"
        lines = [
            f"Task: {task['title']}",
            f"Branch: {task['branch']}",
            f"Plan committed: {'yes' if task['planned'] else 'no'}",
            f"Slice: {task['slice'] or '-'}{' (single gate)' if task['single_gate'] else ''}",
            f"Waiting for approval: {task['pending'] or '-'}",
            f"Approved: {', '.join(task['approved']) or '-'}",
            f"PR: {task['pr_url'] or '-'}",
            docs,
        ]
        if task["locked"]:
            lines.append(f"Session locked. {RESUME_HINT}")
        return "\n".join(lines)

    def unlock(self):
        if self.task is not None and self.task["locked"]:
            self.task["locked"] = False
            self.save()


def deny(reason):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}


def pre_tool_use(payload):
    cwd = payload.get("cwd") or os.getcwd()
    git_dir = find_git_dir(cwd)
    if git_dir is None:
        return None
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    task = Workflow(cwd, git_dir).task
    if tool == "Bash":
        return check_bash(tool_input.get("command", ""), task)
    if tool in EDIT_TOOLS:
        return check_edit(tool_input.get("file_path") or tool_input.get("notebook_path") or "", task)
    return None


def check_bash(command, task):
    if APPROVE_COMMAND.search(command):
        return deny("Only the user approves a gate, with /chisel:approve.")
    if STATE_PATH.search(command):
        return deny("The chisel state is changed only through chisel.py.")
    if task is None:
        return None
    if task["locked"] and not STATUS_COMMAND.search(command):
        return deny(f"This session already committed a step of the chisel task. {RESUME_HINT}")
    for pattern, what in GUARDED_COMMANDS:
        if pattern.search(command):
            return deny(f"During a chisel task, {what} go through chisel.py after the user approves the gate.")
    return None


def check_edit(path, task):
    if STATE_PATH.search(path):
        return deny("The chisel state is changed only through chisel.py.")
    if task is not None and task["locked"]:
        return deny(f"This session already committed a step of the chisel task. {RESUME_HINT}")
    return None


def session_start(payload):
    cwd = payload.get("cwd") or os.getcwd()
    git_dir = find_git_dir(cwd)
    if git_dir is None:
        return ""
    workflow = Workflow(cwd, git_dir)
    if payload.get("source") in ("startup", "clear"):
        workflow.unlock()
    if workflow.task is None:
        return (
            "This repository uses the chisel workflow. When the user describes a new development task "
            "(feature, bug fix, refactor), ask in their language whether to run it as a chisel task; "
            "on yes, invoke the chisel:task skill with the description. Answer questions and small requests directly."
        )
    return f"A chisel task is in progress; the user continues it with /chisel:task.\n{workflow.status()}"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="chisel.py")
    commands = parser.add_subparsers(dest="command", required=True)
    begin = commands.add_parser("begin")
    begin.add_argument("--task", required=True)
    begin.add_argument("--branch", required=True)
    config = commands.add_parser("config")
    config.add_argument("--docs", nargs="+", required=True)
    slice_ = commands.add_parser("slice")
    slice_.add_argument("--id", required=True)
    slice_.add_argument("--single-gate", action="store_true")
    request = commands.add_parser("request")
    request.add_argument("gate", choices=list(GATE_NEXT_STEP))
    request.add_argument("--test-files", nargs="*", default=[])
    commands.add_parser("approve")
    commit = commands.add_parser("commit")
    commit.add_argument("--message", required=True)
    open_pr = commands.add_parser("open-pr")
    open_pr.add_argument("--title", required=True)
    open_pr.add_argument("--body-file", required=True)
    commands.add_parser("push")
    ready = commands.add_parser("ready")
    ready.add_argument("--message", required=True)
    diff = commands.add_parser("diff")
    diff.add_argument("--since-tests", action="store_true")
    diff.add_argument("--stat", action="store_true")
    commands.add_parser("status")
    hook = commands.add_parser("hook")
    hook.add_argument("event", choices=["pre-tool-use", "session-start"])
    args = parser.parse_args(argv)

    if args.command == "hook":
        payload = json.load(sys.stdin)
        if args.event == "pre-tool-use":
            decision = pre_tool_use(payload)
            if decision:
                print(json.dumps(decision))
        else:
            print(session_start(payload))
        return 0

    try:
        workflow = Workflow.open(os.getcwd())
        actions = {
            "begin": lambda: workflow.begin(args.task, args.branch),
            "config": lambda: workflow.configure(args.docs),
            "slice": lambda: workflow.start_slice(args.id, args.single_gate),
            "request": lambda: workflow.request(args.gate, args.test_files),
            "approve": workflow.approve,
            "commit": lambda: workflow.commit(args.message),
            "open-pr": lambda: workflow.open_pr(args.title, args.body_file),
            "push": workflow.push,
            "ready": lambda: workflow.ready(args.message),
            "diff": lambda: workflow.diff(args.since_tests, args.stat),
            "status": workflow.status,
        }
        print(actions[args.command]())
        return 0
    except ChiselError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
