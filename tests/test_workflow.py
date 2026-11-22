import unittest
from pathlib import Path

from support import RepoTestCase


class PlanGateTest(RepoTestCase):
    def test_approve_fails_when_no_gate_is_pending(self):
        self.ok("begin", "--task", "Greeting", "--branch", "feature/greeting")

        result = self.chisel("approve")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No gate is waiting", result.stderr)

    def test_commit_fails_without_an_approved_gate(self):
        self.ok("begin", "--task", "Greeting", "--branch", "feature/greeting")
        self.write("docs/IMPLEMENTATION.md", "# Plan\n")
        self.ok("request", "plan")

        result = self.chisel("commit", "--message", "Plan the greeting")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("rev-list", "--count", "HEAD"), "1")

    def test_approved_plan_is_committed_on_the_task_branch(self):
        self.ok("begin", "--task", "Greeting", "--branch", "feature/greeting")
        self.write("docs/IMPLEMENTATION.md", "# Plan\n")
        self.ok("request", "plan")
        self.approve_as_user()

        self.ok("commit", "--message", "Plan the greeting")

        self.assertEqual(self.git("branch", "--show-current"), "feature/greeting")
        self.assertEqual(self.git("log", "-1", "--format=%s"), "Plan the greeting")
        self.assertEqual(self.last_commit_files(), {"docs/IMPLEMENTATION.md"})

    def test_approved_plan_without_doc_changes_only_creates_the_branch(self):
        self.ok("begin", "--task", "Greeting", "--branch", "feature/greeting")
        self.ok("request", "plan")
        self.approve_as_user()

        self.ok("commit", "--message", "Plan the greeting")

        self.assertEqual(self.git("branch", "--show-current"), "feature/greeting")
        self.assertEqual(self.git("rev-list", "--count", "HEAD"), "1")

    def test_begin_fails_while_another_task_is_active(self):
        self.ok("begin", "--task", "Greeting", "--branch", "feature/greeting")

        result = self.chisel("begin", "--task", "Other", "--branch", "feature/other")

        self.assertNotEqual(result.returncode, 0)


class DocsConfigTest(RepoTestCase):
    def test_status_says_when_docs_are_not_configured(self):
        status = self.ok("status")

        self.assertIn("Docs: not configured", status)

    def test_status_shows_configured_docs(self):
        self.ok("config", "--docs", "docs/SPEC.md", "docs/IMPLEMENTATION.md")

        status = self.ok("status")

        self.assertIn("Docs: docs/SPEC.md, docs/IMPLEMENTATION.md", status)


class SliceGatesTest(RepoTestCase):
    def setUp(self):
        super().setUp()
        self.start_planned_task()
        self.ok("slice", "--id", "1")

    def approve_tests(self):
        self.write("tests/test_greet.py", "assert greet() == 'hi'\n")
        self.ok("request", "tests", "--test-files", "tests/test_greet.py")
        self.approve_as_user()

    def test_impl_gate_requires_approved_tests(self):
        self.write("tests/test_greet.py", "assert greet() == 'hi'\n")
        self.ok("request", "tests", "--test-files", "tests/test_greet.py")

        result = self.chisel("request", "impl")

        self.assertNotEqual(result.returncode, 0)

    def test_impl_gate_is_refused_when_an_approved_test_changed(self):
        self.approve_tests()
        self.write("tests/test_greet.py", "assert True\n")

        result = self.chisel("request", "impl")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tests/test_greet.py", result.stderr)

    def test_requesting_tests_again_withdraws_their_approval(self):
        self.approve_tests()
        self.ok("request", "tests", "--test-files", "tests/test_greet.py")
        self.approve_as_user()
        self.write("tests/test_greet.py", "assert greet() == 'hello'\n")
        self.ok("request", "tests", "--test-files", "tests/test_greet.py")

        result = self.chisel("request", "impl")

        self.assertNotEqual(result.returncode, 0)

    def test_approved_slice_is_one_commit_with_tests_and_implementation(self):
        self.approve_tests()
        self.write("src/greet.py", "def greet():\n    return 'hi'\n")
        self.ok("request", "impl")
        self.approve_as_user()

        self.ok("commit", "--message", "Greet the user")

        self.assertEqual(self.last_commit_files(), {"tests/test_greet.py", "src/greet.py"})
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_single_gate_slice_needs_no_test_approval(self):
        self.ok("slice", "--id", "1", "--single-gate")
        self.write("src/style.css", "body {}\n")

        self.ok("request", "impl")

    def test_diff_since_tests_shows_only_changes_after_test_approval(self):
        self.approve_tests()
        self.write("src/greet.py", "def greet():\n    return 'hi'\n")

        diff = self.ok("diff", "--since-tests", "--stat")

        self.assertIn("src/greet.py", diff)
        self.assertNotIn("tests/test_greet.py", diff)

    def test_slice_diff_includes_new_untracked_files(self):
        self.approve_tests()

        diff = self.ok("diff")

        self.assertIn("tests/test_greet.py", diff)

    def test_a_second_slice_cannot_start_before_the_first_is_committed(self):
        self.approve_tests()

        result = self.chisel("slice", "--id", "2")

        self.assertNotEqual(result.returncode, 0)


class PullRequestTest(RepoTestCase):
    def setUp(self):
        super().setUp()
        self.start_planned_task()
        self.ok("slice", "--id", "1", "--single-gate")
        self.write("src/greet.py", "x = 1\n")
        self.ok("request", "impl")
        self.approve_as_user()
        self.ok("commit", "--message", "Greet the user")
        self.session_start("clear")
        self.body = Path(self.tmp.name) / "pr.md"
        self.body.write_text("Body\n")

    def test_draft_pr_is_opened_only_after_push_approval(self):
        result = self.chisel("open-pr", "--title", "Greeting", "--body-file", str(self.body))

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.gh_log.exists())

    def test_approved_push_pushes_the_branch_and_opens_a_draft_pr(self):
        self.ok("request", "push")
        self.approve_as_user()

        self.ok("open-pr", "--title", "Greeting", "--body-file", str(self.body))

        self.assertIn("--draft", self.gh_log.read_text())
        self.assertNotEqual(self.git("ls-remote", "--heads", "origin", "feature/greeting"), "")
        self.assertIn("pull/7", self.ok("status"))

    def open_pr(self):
        self.ok("request", "push")
        self.approve_as_user()
        self.ok("open-pr", "--title", "Greeting", "--body-file", str(self.body))

    def test_approved_ready_commits_doc_updates_and_marks_the_pr_ready(self):
        self.open_pr()
        self.write("docs/IMPLEMENTATION.md", "# Plan\nPR: pull/7\n")
        self.ok("request", "ready")
        self.approve_as_user()

        self.ok("ready", "--message", "Link the greeting task to its PR")

        self.assertEqual(self.last_commit_files(), {"docs/IMPLEMENTATION.md"})
        self.assertIn("pr ready", self.gh_log.read_text())
        self.assertIn("No chisel task", self.ok("status"))

    def test_ready_refuses_changes_outside_the_docs(self):
        self.open_pr()
        self.write("src/greet.py", "x = 2\n")
        self.ok("request", "ready")
        self.approve_as_user()

        result = self.chisel("ready", "--message", "Link the greeting task to its PR")

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("pr ready", self.gh_log.read_text())


if __name__ == "__main__":
    unittest.main()
