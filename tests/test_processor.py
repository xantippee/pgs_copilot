import unittest
import pandas as pd
from pgs_copilot.processor import PGSProcessor, parse_ancestry_dist, get_ancestry_pct

class TestPGSProcessor(unittest.TestCase):
    def test_parse_ancestry_dist(self):
        dist = {"EUR": 95.0, "AFR": 5.0}
        result = parse_ancestry_dist(dist)
        self.assertEqual(result, "EUR: 95.0%, AFR: 5.0%")
        
        self.assertEqual(parse_ancestry_dist(None), "Unknown")
        self.assertEqual(parse_ancestry_dist({}), "None")

    def test_get_ancestry_pct(self):
        dist = {"EUR": 95.0, "AFR": 5.0}
        self.assertEqual(get_ancestry_pct(dist, "AFR"), 5.0)
        self.assertEqual(get_ancestry_pct(dist, "EAS"), 0.0)
        self.assertEqual(get_ancestry_pct(None, "AFR"), 0.0)

    def test_create_comparison_dataframe(self):
        # Create some mock scores
        scores = [
            {
                "id": "PGS000001",
                "name": "Score A",
                "variants_number": 100,
                "variants_genomebuild": "GRCh37",
                "method_name": "PRScs",
                "publication": {"firstauthor": "Author A", "date_publication": "2020-01-01"},
                "ancestry_distribution": {
                    "dev": {"dist": {"EUR": 100.0}},
                    "eval": {"dist": {"EUR": 100.0}}
                }
            },
            {
                "id": "PGS000002",
                "name": "Score B",
                "variants_number": 200,
                "variants_genomebuild": "GRCh38",
                "method_name": "LDpred2",
                "publication": {"firstauthor": "Author B", "date_publication": "2021-05-15"},
                "ancestry_distribution": {
                    "dev": {"dist": {"EUR": 90.0, "AFR": 10.0}},
                    "eval": {"dist": {"EUR": 80.0, "AFR": 20.0}}
                }
            }
        ]
        
        # We look for African ancestry comparison
        df = PGSProcessor.create_comparison_dataframe(scores, "African")
        
        self.assertEqual(len(df), 2)
        # Score B should be sorted first because it has AFR representation (High relevance)
        self.assertEqual(df.iloc[0]["PGS ID"], "PGS000002")
        self.assertEqual(df.iloc[0]["Relevance"], "High (Developed in Pop)")
        
        # Score A should be second with low relevance
        self.assertEqual(df.iloc[1]["PGS ID"], "PGS000001")
        self.assertEqual(df.iloc[1]["Relevance"], "Low (No Data)")

    def test_extract_relevant_performances(self):
        # Create a mock performance metrics list
        performance_list = [
            {
                "id": "PMP000001",
                "sampleset": {
                    "id": "PSS000001",
                    "samples": [
                        {
                            "ancestry_broad": "African American",
                            "sample_number": 500,
                            "sample_cases": 100,
                            "sample_controls": 400,
                            "cohorts": [{"name_short": "MOCK_COHORT"}]
                        }
                    ]
                },
                "performance_metrics": {
                    "class_acc": [{"name_short": "AUROC", "estimate": 0.65}],
                    "effect_sizes": [{"name_short": "OR", "estimate": 1.25}]
                },
                "publication": {"firstauthor": "Evaluator A", "date_publication": "2022-03-20"}
            },
            {
                "id": "PMP000002",
                "sampleset": {
                    "id": "PSS000002",
                    "samples": [
                        {
                            "ancestry_broad": "European",
                            "sample_number": 10000,
                            "cohorts": [{"name_short": "UKB"}]
                        }
                    ]
                },
                "performance_metrics": {
                    "class_acc": [{"name_short": "AUROC", "estimate": 0.80}]
                },
                "publication": {"firstauthor": "Evaluator B", "date_publication": "2023-01-01"}
            }
        ]

        relevant = PGSProcessor.extract_relevant_performances("PGS000001", performance_list, "African")
        

        # Only PMP000001 should be extracted since it contains African ancestry
        self.assertEqual(len(relevant), 1)
        self.assertEqual(relevant[0]["perf_id"], "PMP000001")
        self.assertEqual(relevant[0]["total_sample_size"], 500)
        self.assertEqual(relevant[0]["cases"], 100)
        self.assertEqual(relevant[0]["metrics"]["AUROC"], 0.65)
        self.assertEqual(relevant[0]["metrics"]["OR"], 1.25)
        self.assertEqual(relevant[0]["cohorts"], "MOCK_COHORT")

    def test_extract_relevant_performances_with_ci(self):
        performance_list = [
            {
                "id": "PMP000003",
                "sampleset": {
                    "id": "PSS000003",
                    "samples": [
                        {
                            "ancestry_broad": "African",
                            "sample_number": 1000,
                            "cohorts": [{"name_short": "AHA"}]
                        }
                    ]
                },
                "performance_metrics": {
                    "effect_sizes": [{"name_short": "OR", "estimate": 1.5, "ci_lower": 1.3, "ci_upper": 1.7}]
                },
                "publication": {"firstauthor": "Evaluator C", "date_publication": "2024-02-15"}
            }
        ]

        relevant = PGSProcessor.extract_relevant_performances("PGS000001", performance_list, "African")
        self.assertEqual(len(relevant), 1)
        self.assertEqual(relevant[0]["metrics"]["OR"], "1.5 (95% CI: 1.3 - 1.7)")

if __name__ == "__main__":
    unittest.main()
