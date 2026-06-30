import unittest
from unittest.mock import patch, MagicMock
from pgs_copilot.api import PGSCatalogClient

class TestPGSCatalogClient(unittest.TestCase):
    def setUp(self):
        self.client = PGSCatalogClient(timeout=5)

    @patch("pgs_copilot.api.requests.get")
    def test_get_trait_success(self, mock_get):
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "EFO_0004340", "label": "body mass index"}
        mock_get.return_value = mock_response

        result = self.client.get_trait("EFO:0004340")
        
        # Verify URL conversion and call
        mock_get.assert_called_once_with("https://www.pgscatalog.org/rest/trait/EFO_0004340", timeout=5)
        self.assertEqual(result["id"], "EFO_0004340")
        self.assertEqual(result["label"], "body mass index")

    @patch("pgs_copilot.api.requests.get")
    def test_get_trait_failure(self, mock_get):
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.client.get_trait("EFO:0004340")
        self.assertIsNone(result)

    @patch("pgs_copilot.api.requests.get")
    def test_get_scores_by_trait_pagination(self, mock_get):
        # Mock page 1 and page 2 responses
        response1 = MagicMock()
        response1.status_code = 200
        response1.json.return_value = {
            "results": [{"id": "PGS000001", "name": "Score 1"}],
            "next": "https://www.pgscatalog.org/rest/score/search?trait_id=EFO_0004340&offset=1"
        }
        
        response2 = MagicMock()
        response2.status_code = 200
        response2.json.return_value = {
            "results": [{"id": "PGS000002", "name": "Score 2"}],
            "next": None
        }
        
        # side_effect returns response1 on first call, response2 on second
        mock_get.side_effect = [response1, response2]

        results = self.client.get_scores_by_trait("EFO:0004340")
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], "PGS000001")
        self.assertEqual(results[1]["id"], "PGS000002")
        self.assertEqual(mock_get.call_count, 2)

    @patch("pgs_copilot.api.requests.get")
    def test_get_performance_metrics_bulk(self, mock_get):
        # Mock response for single score
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"id": "PMP000001", "associated_pgs_id": "PGS000001"}]
        }
        mock_get.return_value = mock_response

        pgs_ids = ["PGS000001", "PGS000002"]
        results = self.client.get_performance_metrics_bulk(pgs_ids, max_workers=2)
        
        self.assertEqual(len(results), 2)
        self.assertIn("PGS000001", results)
        self.assertIn("PGS000002", results)
        self.assertEqual(len(results["PGS000001"]), 1)
        self.assertEqual(results["PGS000001"][0]["id"], "PMP000001")

if __name__ == "__main__":
    unittest.main()
