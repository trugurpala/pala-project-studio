import unittest
from unittest.mock import patch
from pathlib import Path
from pala_github import GitHubRouter, GitHubReadPolicy, external_conflict

class GitHubReadOnlyTests(unittest.TestCase):
    def test_slug_redacts_and_no_remote_write_route(self):
        router=GitHubRouter(gh_path=None)
        self.assertEqual(router._repo_slug("https://github.com/acme/demo.git"),"acme/demo")
        with patch.object(router,"_remote",return_value="https://github.com/acme/demo.git"):
            result=router.read_only_snapshot(Path("."))
        self.assertEqual(result["status"],"not-run"); self.assertEqual(result["write_capability"],"none")
    def test_gh_snapshot_uses_only_api_reads(self):
        router=GitHubRouter(gh_path="gh")
        with patch.object(router,"_remote",return_value="git@github.com:acme/demo.git"), patch.object(router,"_gh_json",return_value=(0,[])) as call:
            result=router.read_only_snapshot(Path("."))
        self.assertEqual(result["status"],"passed"); self.assertEqual(call.call_count,4)
        self.assertTrue(all("write" not in str(item.args).lower() for item in call.call_args_list))

    def test_allowlist_rejects_github_writes_and_conflict_is_typed(self):
        self.assertTrue(GitHubReadPolicy.allowed("gh", ["api", "repos/acme/demo/issues"]))
        self.assertFalse(GitHubReadPolicy.allowed("gh", ["pr", "merge", "1"]))
        self.assertFalse(GitHubReadPolicy.allowed("git", ["push", "origin", "main"]))
        conflict = external_conflict("ci_failed_local_verified", local_basis={"sha": "a"}, remote_basis={"run": "failed"})
        self.assertEqual(conflict["type"], "ci_failed_local_verified")
        self.assertEqual(conflict["resolution"], "needs_decision")

    def test_allowlist_rejects_gh_api_write_flags_and_git_mutations(self):
        for argv in (
            ["api", "repos/acme/demo/issues", "--method", "POST"],
            ["api", "repos/acme/demo/issues", "-X", "POST"],
            ["api", "repos/acme/demo/issues", "--raw-field", "title=unsafe"],
            ["api", "repos/acme/demo/issues", "--input", "payload.json"],
        ):
            self.assertFalse(GitHubReadPolicy.allowed("gh", argv), argv)
        for argv in (
            ["branch", "-D", "main"],
            ["branch", "--delete", "main"],
            ["remote", "set-url", "origin", "https://github.com/acme/demo.git"],
        ):
            self.assertFalse(GitHubReadPolicy.allowed("git", argv), argv)

if __name__ == "__main__": unittest.main()
