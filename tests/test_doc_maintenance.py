from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from driver.doc_maintenance import append_update_entry


class DocMaintenanceTests(unittest.TestCase):
    def test_append_update_entry_appends_expected_template_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "development.md"
            doc.write_text("# Guide\n", encoding="utf-8")

            append_update_entry(
                doc_path=doc,
                date_text="2026-03-03",
                change="新增会话快照脚本",
                modules=["driver/session_snapshot.py", "driver/main.py"],
                verify_command="python3 -m unittest tests/test_session_snapshot.py -q",
                result="PASS",
                risk="全量测试仍有历史失败用例待处理",
            )

            text = doc.read_text(encoding="utf-8")
            self.assertIn("### Update 2026-03-03", text)
            self.assertIn("- 变更: 新增会话快照脚本", text)
            self.assertIn("- 影响模块: driver/session_snapshot.py, driver/main.py", text)
            self.assertIn("- 验证命令: python3 -m unittest tests/test_session_snapshot.py -q", text)
            self.assertIn("- 结果: PASS", text)
            self.assertIn("- 风险/待办: 全量测试仍有历史失败用例待处理", text)


if __name__ == "__main__":
    unittest.main()
