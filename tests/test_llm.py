import unittest
import pandas as pd
from pgs_copilot.llm import ReportGenerator, _get_float_estimate

class TestLLM(unittest.TestCase):
    def test_get_float_estimate(self):
        self.assertEqual(_get_float_estimate(1.25), 1.25)
        self.assertEqual(_get_float_estimate("1.25 (95% CI: 1.1 - 1.4)"), 1.25)
        self.assertEqual(_get_float_estimate("0.85"), 0.85)
        self.assertIsNone(_get_float_estimate(None))
        self.assertIsNone(_get_float_estimate("invalid"))

    def test_generate_offline_report_no_error(self):
        # Create a mock comparative dataframe
        df_comparison = pd.DataFrame([
            {
                "PGS ID": "PGS000001",
                "Score Name": "Score A",
                "Variants": 1000,
                "Genome Build": "GRCh37",
                "Method": "PRScs",
                "Publication": "Author A (2020)",
                "Relevance": "High (Developed in Pop)",
                "Dev Ancestry": "AFR: 10.0%, EUR: 90.0%",
                "Eval Ancestry": "AFR: 100.0%",
                "GWAS Ancestry": "EUR: 100.0%",
                "dev_pct": 10.0,
                "eval_pct": 100.0,
                "gwas_pct": 0.0
            }
        ])

        # Create mock performance data containing metrics formatted with CIs (strings)
        performance_context = {
            "PGS000001": [
                {
                    "perf_id": "PMP000001",
                    "sampleset_id": "PSS000001",
                    "cohorts": "Mock Cohort",
                    "total_sample_size": 500,  # Trigger caution (size < 1000)
                    "cases": 100,
                    "controls": 400,
                    "metrics": {
                        "AUROC": "0.55 (95% CI: 0.50 - 0.60)",  # Trigger caution (auroc < 0.60)
                        "R2": "0.02 (95% CI: 0.01 - 0.03)"     # Trigger caution (r2 < 0.05)
                    },
                    "publication": "Author B (2021)"
                }
            ]
        }

        # This should execute successfully without any TypeError
        report = ReportGenerator.generate_offline_report(
            "CAD",
            "African",
            df_comparison,
            performance_context
        )

        self.assertIn("PGS000001", report)
        self.assertIn("Weak predictive accuracy", report)
        self.assertIn("0.55 (95% CI: 0.50 - 0.60)", report)
        self.assertIn("Low variance explained", report)
        self.assertIn("0.02 (95% CI: 0.01 - 0.03)", report)

if __name__ == "__main__":
    unittest.main()
