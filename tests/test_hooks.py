import unittest

from support import RepoTestCase


class ApprovalGuardTest(RepoTestCase):
    def test_agent_cannot_run_approve_through_bash(self):
        decision = self.pre_tool_use("Bash", {"command": 'python3 "/x/scripts/chisel.py" approve'})

        self.assertEqual(decision["permissionDecision"], "deny")

    def test_agent_cannot_edit_the_workflow_state(self):
        decision = self.pre_tool_use("Write", {"file_path": str(self.repo / ".git" / "chisel" / "state.json")})

        self.assertEqual(decision["permissionDecision"], "deny")

    def test_agent_cannot_touch_the_workflow_state_from_bash(self):
        decision = self.pre_tool_use("Bash", {"command": "echo {} > .git/chisel/state.json"})

        self.assertEqual(decision["permissionDecision"], "deny")


class GitGuardTest(RepoTestCase):
    def test_raw_git_commit_is_allowed_without_an_active_task(self):
        decision = self.pre_tool_use("Bash", {"command": "git commit -m 'x'"})

        self.assertIsNone(decision)

    def test_raw_git_commit_is_denied_during_a_task(self):
        self.ok("begin", "--task", "Greeting", "--branch", "feature/greeting")

        decision = self.pre_tool_use("Bash", {"command": "git add -A && git -c user.name=x commit -m 'x'"})

        self.assertEqual(decision["permissionDecision"], "deny")

    def test_raw_push_and_pr_commands_are_denied_during_a_task(self):
        self.ok("begin", "--task", "Greeting", "--branch", "feature/greeting")

        for command in ["git push origin HEAD", "gh pr create --fill", "gh pr ready", "gh pr merge 7"]:
            with self.subTest(command=command):
                self.assertEqual(self.pre_tool_use("Bash", {"command": command})["permissionDecision"], "deny")

    def test_read_only_git_is_allowed_during_a_task(self):
        self.ok("begin", "--task", "Greeting", "--branch", "feature/greeting")

        decision = self.pre_tool_use("Bash", {"command": "git log --oneline -5"})

        self.assertIsNone(decision)

    def test_hook_does_nothing_outside_a_git_repository(self):
        self.repo = self.repo.parent

        decision = self.pre_tool_use("Bash", {"command": "git commit -m x"})

        self.assertIsNone(decision)


class SessionLockTest(RepoTestCase):
    def setUp(self):
        super().setUp()
        self.ok("begin", "--task", "Greeting", "--branch", "feature/greeting")
        self.ok("request", "plan")
        self.approve_as_user()
        self.ok("commit", "--message", "Plan the greeting")

    def test_edits_are_denied_after_a_commit_in_the_same_session(self):
        decision = self.pre_tool_use("Edit", {"file_path": str(self.repo / "src" / "greet.py")})

        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("/clear", decision["permissionDecisionReason"])

    def test_bash_is_denied_after_a_commit_except_status(self):
        self.assertEqual(self.pre_tool_use("Bash", {"command": "npm test"})["permissionDecision"], "deny")
        self.assertIsNone(self.pre_tool_use("Bash", {"command": 'python3 "/x/scripts/chisel.py" status'}))

    def test_clear_unlocks_the_session(self):
        self.session_start("clear")

        decision = self.pre_tool_use("Edit", {"file_path": str(self.repo / "src" / "greet.py")})

        self.assertIsNone(decision)

    def test_resume_keeps_the_session_locked(self):
        self.session_start("resume")

        decision = self.pre_tool_use("Edit", {"file_path": str(self.repo / "src" / "greet.py")})

        self.assertEqual(decision["permissionDecision"], "deny")


class SessionContextTest(RepoTestCase):
    def test_without_a_task_the_agent_is_told_to_offer_the_workflow(self):
        context = self.session_start("startup")

        self.assertIn("chisel:task", context)

    def test_with_an_active_task_the_agent_is_told_where_it_stands(self):
        self.ok("begin", "--task", "Greeting", "--branch", "feature/greeting")
        self.ok("request", "plan")

        context = self.session_start("clear")

        self.assertIn("Greeting", context)
        self.assertIn("plan", context)


if __name__ == "__main__":
    unittest.main()
