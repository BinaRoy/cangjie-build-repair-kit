from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from driver.weekly_report import generate_weekly_comparison_report


class WeeklyReportTests(unittest.TestCase):
    def test_generate_weekly_report_contains_required_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root / "runs"
            run_a = runs / "20260304_100000_001_aaaaaa"
            run_b = runs / "20260304_110000_001_bbbbbb"
            run_a.mkdir(parents=True)
            run_b.mkdir(parents=True)
            (run_a / "summary.json").write_text(
                '{"run_id":"20260304_100000_001_aaaaaa","project_name":"p","iterations":2,"final_status":"success","stop_reason":"verify_passed"}',
                encoding="utf-8",
            )
            (run_b / "summary.json").write_text(
                '{"run_id":"20260304_110000_001_bbbbbb","project_name":"p","iterations":1,"final_status":"failed","stop_reason":"stop_strategy_direct_write_detected"}',
                encoding="utf-8",
            )
            (run_a / "iter_1.json").write_text(
                '{"iteration":1,"decision":"continue","model_route_decision":{"selected_model":"model-a"},"verify_duration_sec":0.5,"post_patch_verify_duration_sec":0.2}',
                encoding="utf-8",
            )
            (run_b / "iter_1.json").write_text(
                '{"iteration":1,"decision":"stop_strategy_direct_write_detected","model_route_decision":{"selected_model":"model-b"},"verify_duration_sec":0.4,"post_patch_verify_duration_sec":null}',
                encoding="utf-8",
            )

            out = root / "weekly_report.md"
            generate_weekly_comparison_report(runs_dir=runs, output_path=out, days=7)
            text = out.read_text(encoding="utf-8")

            self.assertIn("success_rate", text)
            self.assertIn("avg_iterations", text)
            self.assertIn("avg_duration_sec", text)
            self.assertIn("safety_events", text)
            self.assertIn("model-a", text)
            self.assertIn("model-b", text)


if __name__ == "__main__":
    unittest.main()
