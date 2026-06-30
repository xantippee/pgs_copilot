import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Core trait mapping
TRAIT_MAP = {
    "Breast cancer": "MONDO_0004989",
    "Prostate carcinoma": "MONDO_0005159",
    "Colorectal cancer": "MONDO_0005575",
    "CAD": "MONDO_0005010",
    "BMI": "EFO_0004340",
    "Diabetes": "MONDO_0005015",
    "Pancreatic cancer": "MONDO_0005192"
}

# Core ancestry mapping (UI Label -> PGS Catalog Code)
ANCESTRY_MAP = {
    "European": "EUR",
    "African": "AFR",
    "East Asian": "EAS",
    "South Asian": "SAS",
    "Latino / Admixed": "AMR",
    "Greater Middle Eastern": "GME",
    "Oceanian": "OCE"
}

# Reverse mapping for display
ANCESTRY_CODE_TO_LABEL = {v: k for k, v in ANCESTRY_MAP.items()}

def parse_ancestry_dist(dist_dict):
    """
    Helper to format ancestry distribution dictionary into a clean string.
    Example: {"EUR": 95.0, "AFR": 5.0} -> "EUR: 95.0%, AFR: 5.0%"
    """
    if dist_dict is None or not isinstance(dist_dict, dict):
        return "Unknown"
    if not dist_dict:
        return "None"
    
    parts = []
    # Sort by percentage descending
    for code, pct in sorted(dist_dict.items(), key=lambda x: x[1], reverse=True):
        parts.append("{}: {}%".format(code, pct))
    return ", ".join(parts) if parts else "None"

def get_ancestry_pct(dist_dict, target_code):
    """
    Get percentage of target ancestry from distribution dict.
    """
    if not dist_dict or not isinstance(dist_dict, dict):
        return 0.0
    return float(dist_dict.get(target_code, 0.0))

class PGSProcessor:
    @staticmethod
    def create_comparison_dataframe(scores_list, target_ancestry_label):
        """
        Creates a clean, structured pandas DataFrame comparing available scores.
        """
        target_code = ANCESTRY_MAP.get(target_ancestry_label, "EUR")
        rows = []
        
        for score in scores_list:
            score_id = score.get("id")
            name = score.get("name", "N/A")
            variants = score.get("variants_number", 0)
            build = score.get("variants_genomebuild", "N/A") or "N/A"
            method = score.get("method_name", "N/A")
            
            # Extract publication
            pub = score.get("publication", {})
            author = pub.get("firstauthor", "N/A")
            year = pub.get("date_publication", "N/A")
            if year != "N/A" and len(year) >= 4:
                year = year[:4]
            pub_str = "{} ({})".format(author, year)
            
            # Ancestry distribution
            anc_dist = score.get("ancestry_distribution", {})
            gwas_dist = anc_dist.get("gwas", {}).get("dist", {})
            dev_dist = anc_dist.get("dev", {}).get("dist", {})
            eval_dist = anc_dist.get("eval", {}).get("dist", {})
            
            # Get target representation percentages
            gwas_target_pct = get_ancestry_pct(gwas_dist, target_code)
            dev_target_pct = get_ancestry_pct(dev_dist, target_code)
            eval_target_pct = get_ancestry_pct(eval_dist, target_code)
            
            # Format distributions for display
            gwas_display = parse_ancestry_dist(gwas_dist)
            dev_display = parse_ancestry_dist(dev_dist)
            eval_display = parse_ancestry_dist(eval_dist)
            
            # Simple relevance categorization
            relevance = "Low (No Data)"
            if dev_target_pct > 0 or gwas_target_pct > 0:
                relevance = "High (Developed in Pop)"
            elif eval_target_pct > 0:
                relevance = "Medium (Evaluated in Pop)"
            
            rows.append({
                "PGS ID": score_id,
                "Score Name": name,
                "Variants": variants,
                "Genome Build": build,
                "Method": method,
                "Publication": pub_str,
                "Relevance": relevance,
                "Dev Ancestry": dev_display,
                "Eval Ancestry": eval_display,
                "GWAS Ancestry": gwas_display,
                "dev_pct": dev_target_pct,
                "eval_pct": eval_target_pct,
                "gwas_pct": gwas_target_pct
            })
            
        df = pd.DataFrame(rows)
        if not df.empty:
            # Sort by relevance and target ancestry percentage
            relevance_order = {
                "High (Developed in Pop)": 0,
                "Medium (Evaluated in Pop)": 1,
                "Low (No Data)": 2
            }
            df["relevance_rank"] = df["Relevance"].map(relevance_order)
            df["max_pct"] = df[["dev_pct", "eval_pct", "gwas_pct"]].max(axis=1)
            df = df.sort_values(by=["relevance_rank", "max_pct"], ascending=[True, False]).drop(["relevance_rank", "max_pct"], axis=1)
            
        return df

    @staticmethod
    def extract_relevant_performances(pgs_id, performance_list, target_ancestry_label):
        """
        Extract and summarize evaluation studies matching target ancestry.
        """
        target_code = ANCESTRY_MAP.get(target_ancestry_label, "EUR")
        relevant_evals = []
        
        for perf in performance_list:
            sampleset = perf.get("sampleset", {})
            samples = sampleset.get("samples", [])
            
            # Check if any sample in the set has the target ancestry
            is_relevant = False
            sample_details = []
            
            for s in samples:
                broad_anc = s.get("ancestry_broad", "")
                # Map broad ancestry label to code if necessary, or do substring check
                # PGS Catalog uses broad labels like "European", "African", "East Asian", etc.
                if target_ancestry_label.lower() in broad_anc.lower():
                    is_relevant = True
                    
                cohorts_list = s.get("cohorts", [])
                cohort_names = [c.get("name_short") for c in cohorts_list if c.get("name_short")]
                cohort_str = ", ".join(cohort_names) if cohort_names else "Unknown Cohort"
                
                sample_details.append({
                    "ancestry": broad_anc,
                    "cohorts": cohort_str,
                    "size": s.get("sample_number", 0) or 0,
                    "cases": s.get("sample_cases", None),
                    "controls": s.get("sample_controls", None)
                })
            
            if is_relevant:
                # Extract metrics
                metrics_dict = perf.get("performance_metrics", {})
                effect_sizes = metrics_dict.get("effect_sizes", [])
                class_acc = metrics_dict.get("class_acc", [])
                other_metrics = metrics_dict.get("othermetrics", [])
                
                extracted_metrics = {}
                
                def format_metric(m_obj):
                    name = m_obj.get("name_short", "")
                    est = m_obj.get("estimate", None)
                    if name and est is not None:
                        ci_l = m_obj.get("ci_lower", None)
                        ci_u = m_obj.get("ci_upper", None)
                        if ci_l is not None and ci_u is not None:
                            return "{} (95% CI: {} - {})".format(est, ci_l, ci_u)
                        return est
                    return None
                
                # Check for classification accuracy (like AUROC / C-Index)
                for c in class_acc:
                    val = format_metric(c)
                    if val is not None:
                        extracted_metrics[c.get("name_short")] = val
                        
                # Check for effect size (Beta, OR, HR)
                for e in effect_sizes:
                    val = format_metric(e)
                    if val is not None:
                        extracted_metrics[e.get("name_short")] = val
                        
                # Check for other metrics (like R2)
                for o in other_metrics:
                    val = format_metric(o)
                    if val is not None:
                        extracted_metrics[o.get("name_short")] = val
                
                # Publication details
                pub = perf.get("publication", {})
                author = pub.get("firstauthor", "Unknown")
                year = pub.get("date_publication", "N/A")
                if year != "N/A" and len(year) >= 4:
                    year = year[:4]
                pub_str = "{} ({})".format(author, year)
                
                relevant_evals.append({
                    "perf_id": perf.get("id"),
                    "sampleset_id": sampleset.get("id"),
                    "cohorts": "; ".join(set(s["cohorts"] for s in sample_details)),
                    "total_sample_size": sum(s["size"] for s in sample_details),
                    "cases": sum(s["cases"] for s in sample_details if s["cases"] is not None),
                    "controls": sum(s["controls"] for s in sample_details if s["controls"] is not None),
                    "metrics": extracted_metrics,
                    "publication": pub_str
                })
                
        return relevant_evals
