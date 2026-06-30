import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PGSCatalogClient:
    BASE_URL = "https://www.pgscatalog.org/rest"
    
    def __init__(self, timeout=15):
        self.timeout = timeout
        
    def get_trait(self, efo_id):
        """
        Fetch trait metadata from /rest/trait/{efo_id}
        """
        # Replace colons with underscores for the API URL compatibility
        clean_id = efo_id.replace(":", "_")
        url = "{}/trait/{}".format(self.BASE_URL, clean_id)
        logger.info("Fetching trait: {}".format(url))
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error("Failed to fetch trait {}: Status {}".format(efo_id, resp.status_code))
                return None
        except Exception as e:
            logger.error("Exception fetching trait {}: {}".format(efo_id, e))
            return None

    def get_scores_by_trait(self, efo_id, max_pages=5):
        """
        Query paginated scores from /rest/score/search?trait_id={efo_id}
        """
        clean_id = efo_id.replace(":", "_")
        url = "{}/score/search?trait_id={}".format(self.BASE_URL, clean_id)
        logger.info("Searching scores for trait: {}".format(url))
        scores = []
        
        try:
            page = 1
            while url and page <= max_pages:
                logger.info("Fetching page {} for trait {}".format(page, efo_id))
                resp = requests.get(url, timeout=self.timeout)
                if resp.status_code != 200:
                    logger.error("Error fetching scores page {}: Status {}".format(page, resp.status_code))
                    break
                
                data = resp.json()
                results = data.get("results", [])
                scores.extend(results)
                
                # Check next page link in HATEOAS structure
                url = data.get("next")
                page += 1
                
        except Exception as e:
            logger.error("Exception fetching scores for trait {}: {}".format(efo_id, e))
            
        logger.info("Found {} scores for trait {}".format(len(scores), efo_id))
        return scores

    def get_performance_metrics(self, pgs_id):
        """
        Fetch performance metrics for a single score from /rest/performance/search?pgs_id={pgs_id}
        """
        url = "{}/performance/search?pgs_id={}".format(self.BASE_URL, pgs_id)
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("results", [])
            else:
                logger.error("Failed to fetch performance for {}: Status {}".format(pgs_id, resp.status_code))
                return []
        except Exception as e:
            logger.error("Exception fetching performance for {}: {}".format(pgs_id, e))
            return []

    def get_performance_metrics_bulk(self, pgs_ids, max_workers=15):
        """
        Fetch performance metrics for multiple score IDs concurrently.
        """
        results_map = {}
        if not pgs_ids:
            return results_map
            
        logger.info("Fetching performance metrics concurrently for {} scores...".format(len(pgs_ids)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {executor.submit(self.get_performance_metrics, pid): pid for pid in pgs_ids}
            for future in as_completed(future_to_id):
                pid = future_to_id[future]
                try:
                    perf_data = future.result()
                    results_map[pid] = perf_data
                except Exception as e:
                    logger.error("Error retrieving thread result for {}: {}".format(pid, e))
                    results_map[pid] = []
                    
        return results_map
