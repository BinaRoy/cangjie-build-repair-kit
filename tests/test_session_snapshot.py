from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from driver.session_snapshot import (
    extract_milestone_checklist,
    generate_snapshot_markdown,
    write_snapshot_file,
)


class SessionSnapshotTests(unittest.TestCase):
    def test_extract_milestone_checklist_reads_checkboxes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "guide.md"
            doc.write_text(
                "\n".join(
                    [
                        "# Demo",
                        "- [ ] A1. first item",
                        "- [x] A2. second item",
                        "not checklist",
                    ]
                ),
                encoding="utf-8",
            )
            checklist = extract_milestone_checklist(doc)
            self.assertEqual(
                checklist,
                [
                    (False, "A1. first item"),
                    (True, "A2. second item"),
                ],
            )

    def test_generate_snapshot_markdown_contains_core_sections(self) -> None:
        markdown = generate_snapshot_markdown(
            timestamp="2026-03-03T12:00:00Z",
            branch="main",
            status_short=" M docs/x.md\n?? scripts/y.py",
            latest_commit="abc123 feat: add snapshot",
            checklist=[(False, "A1. one"), (True, "A2. two")],
            source_doc=Path("docs/development_assessment_and_followup.md"),
        )
        self.assertIn("# Session Snapshot", markdown)
        self.assertIn("## Git", markdown)
        self.assertIn("## Milestone Checklist", markdown)
        self.assertIn("- [ ] A1. one", markdown)
        self.assertIn("- [x] A2. two", markdown)

    def test_write_snapshot_file_collects_git_and_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            doc = base / "docs" / "development_assessment_and_followup.md"
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text("- [ ] A1. test item\n", encoding="utf-8")
            out = base / "docs" / "session_snapshot.md"

            with patch(
                "driver.session_snapshot.run_command",
                side_effect=[
                    "main",
                    " M docs/development_assessment_and_followup.md",
                    "abc123 feat: demo",
                ],
            ):
                write_snapshot_file(base_dir=base, source_doc=doc, output_path=out)

            text = out.read_text(encoding="utf-8")
            self.assertIn("abc123 feat: demo", text)
            self.assertIn("- [ ] A1. test item", text)


if __name__ == "__main__":
    unittest.main()
