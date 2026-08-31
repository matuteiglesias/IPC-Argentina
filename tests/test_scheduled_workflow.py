import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "scheduled-price-candidate.yml"


class ScheduledWorkflowTests(unittest.TestCase):
    def test_scheduled_maturity_is_advisory_but_manual_gate_remains_strict(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        scheduled = workflow.split("- name: Assess scheduled candidate maturity", 1)[1]
        scheduled = scheduled.split("- name: Apply explicitly requested maturity gate", 1)[0]
        self.assertIn("if: github.event_name == 'schedule'", scheduled)
        self.assertIn("continue-on-error: true", scheduled)
        self.assertIn("run: make price-v2-approved-check", scheduled)

        explicit = workflow.split("- name: Apply explicitly requested maturity gate", 1)[1]
        explicit = explicit.split("- name: Summarize maintenance state", 1)[0]
        self.assertIn(
            "if: github.event_name == 'workflow_dispatch' && inputs.require_approved_latest",
            explicit,
        )
        self.assertNotIn("continue-on-error", explicit)
        self.assertIn("run: make price-v2-approved-check", explicit)


if __name__ == "__main__":
    unittest.main()
