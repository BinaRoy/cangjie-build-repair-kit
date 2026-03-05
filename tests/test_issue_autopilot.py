from __future__ import annotations

import unittest

from driver.issue_autopilot import (
    IssueContext,
    build_branch_name,
    build_pr_body,
    build_tracking_markdown,
    slugify,
)


class IssueAutopilotTests(unittest.TestCase):
    def test_slugify_and_branch_name(self) -> None:
        self.assertEqual(slugify("Fix MCP timeout on Windows"), "fix-mcp-timeout-on-windows")
        self.assertEqual(build_branch_name(123, "Fix MCP timeout on Windows"), "issue/123-fix-mcp-timeout-on-windows")

    def test_tracking_markdown_contains_core_fields(self) -> None:
        issue = IssueContext(
            number=42,
            title="Improve issue workflow",
            body="Need full automation from issue to PR.",
            url="https://github.com/acme/repo/issues/42",
            labels=["enhancement", "workflow"],
        )
        text = build_tracking_markdown(
            issue=issue,
            branch_name="issue/42-improve-issue-workflow",
            base_branch="main",
            test_command="python3 -m unittest discover -s tests -q",
        )
        self.assertIn("Issue #42", text)
        self.assertIn("https://github.com/acme/repo/issues/42", text)
        self.assertIn("issue/42-improve-issue-workflow", text)
        self.assertIn("enhancement, workflow", text)

    def test_pr_body_links_issue_and_tracking_file(self) -> None:
        issue = IssueContext(
            number=88,
            title="Repair parser edge case",
            body="",
            url="https://github.com/acme/repo/issues/88",
            labels=[],
        )
        body = build_pr_body(
            issue=issue,
            test_command="python3 -m unittest discover -s tests -q",
            tracking_file="docs/dev-tracking/issue-88-repair-parser-edge-case.md",
        )
        self.assertIn("Closes #88", body)
        self.assertIn("docs/dev-tracking/issue-88-repair-parser-edge-case.md", body)
        self.assertIn("python3 -m unittest discover -s tests -q", body)


if __name__ == "__main__":
    unittest.main()
