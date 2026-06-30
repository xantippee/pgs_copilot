import os
import requests
import json
import logging
from .templates import SYSTEM_PROMPT, REPORT_PROMPT_TEMPLATE, MOCK_REPORT_TEMPLATE

logger = logging.getLogger(__name__)

def _get_float_estimate(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        parts = val.split()
        if parts:
            try:
                return float(parts[0])
            except ValueError:
                pass
    return None

class ReportGenerator:
    @staticmethod
    def generate_with_gemini(api_key, trait, ancestry, scores_context):
        """
        Generate report using Google Gemini API
        """
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # Use gemini-1.5-flash as default, or gemini-1.5-pro if desired
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT
            )
            
            prompt = REPORT_PROMPT_TEMPLATE.format(
                trait=trait,
                ancestry=ancestry,
                scores_context=scores_context
            )
            
            logger.info("Sending request to Gemini API...")
            response = model.generate_content(prompt)
            return response.text
        except ImportError:
            return "Error: `google-generativeai` package is not installed. Please install it to use Gemini."
        except Exception as e:
            return "Error calling Gemini API: {}".format(e)

    @staticmethod
    def generate_with_openai(api_key, trait, ancestry, scores_context):
        """
        Generate report using OpenAI API
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            prompt = REPORT_PROMPT_TEMPLATE.format(
                trait=trait,
                ancestry=ancestry,
                scores_context=scores_context
            )
            
            logger.info("Sending request to OpenAI API...")
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            return completion.choices[0].message.content
        except ImportError:
            return "Error: `openai` package is not installed. Please install it to use OpenAI."
        except Exception as e:
            return "Error calling OpenAI API: {}".format(e)

    @staticmethod
    def generate_with_ollama(host, model_name, trait, ancestry, scores_context):
        """
        Generate report using local Ollama instance
        """
        url = "{}/api/chat".format(host.rstrip("/"))
        prompt = REPORT_PROMPT_TEMPLATE.format(
            trait=trait,
            ancestry=ancestry,
            scores_context=scores_context
        )
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        
        logger.info("Sending request to local Ollama at {}...".format(url))
        try:
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "No content returned.")
            else:
                return "Error calling Ollama API (Status {}): {}".format(resp.status_code, resp.text)
        except Exception as e:
            return "Error connecting to Ollama: {}".format(e)

    @staticmethod
    def generate_offline_report(trait, ancestry, df_comparison, performance_data):
        """
        Deterministic rules-based RAG simulator.
        Generates a highly-detailed, context-aware report without requiring an API key.
        """
        total_scores = len(df_comparison)
        
        # 1. Best Supported Scores
        best_supported = []
        scores_with_data_count = 0
        
        # High relevance (developed in population)
        high_rel = df_comparison[df_comparison["Relevance"] == "High (Developed in Pop)"]
        # Medium relevance (evaluated in population)
        med_rel = df_comparison[df_comparison["Relevance"] == "Medium (Evaluated in Pop)"]
        
        scores_with_data_count = len(high_rel) + len(med_rel)
        
        if not high_rel.empty:
            for _, row in high_rel.iterrows():
                pid = row["PGS ID"]
                name = row["Score Name"]
                pub = row["Publication"]
                dev_anc = row["Dev Ancestry"]
                eval_anc = row["Eval Ancestry"]
                var_count = row["Variants"]
                
                # Fetch performance metrics details
                perf_list = performance_data.get(pid, [])
                metrics_summary = []
                for p in perf_list:
                    m = p.get("metrics", {})
                    metrics_str = ", ".join("{}: {}".format(k, v) for k, v in m.items())
                    metrics_summary.append("- Cohort: **{}** (Size: {}), Metrics: [{}]".format(p.get("cohorts"), p.get("total_sample_size"), metrics_str))
                metrics_block = "\n".join(metrics_summary) if metrics_summary else "- No detailed performance estimates available in catalog."
                
                best_supported.append(
                    "### **{}** (Score Name: {})\n"
                    "- **Development Ancestry**: {}\n"
                    "- **Evaluation Ancestry**: {}\n"
                    "- **Variant Count**: {:,} (Build: {})\n"
                    "- **Publication**: {}\n"
                    "- **Reported Performance in target ancestry**:\n{}"
                    .format(pid, name, dev_anc, eval_anc, var_count, row["Genome Build"], pub, metrics_block)
                )
        
        if not med_rel.empty:
            best_supported.append("\n*The following scores were developed in other populations (typically European) but evaluated in the target ancestry:*\n")
            for _, row in med_rel.iterrows():
                pid = row["PGS ID"]
                name = row["Score Name"]
                pub = row["Publication"]
                dev_anc = row["Dev Ancestry"]
                eval_anc = row["Eval Ancestry"]
                var_count = row["Variants"]
                
                perf_list = performance_data.get(pid, [])
                metrics_summary = []
                for p in perf_list:
                    m = p.get("metrics", {})
                    metrics_str = ", ".join("{}: {}".format(k, v) for k, v in m.items())
                    metrics_summary.append("- Cohort: **{}** (Size: {}), Metrics: [{}]".format(p.get("cohorts"), p.get("total_sample_size"), metrics_str))
                metrics_block = "\n".join(metrics_summary) if metrics_summary else "- No detailed performance estimates available in catalog."
                
                best_supported.append(
                    "### **{}** (Score Name: {})\n"
                    "- **Development Ancestry**: {} (Underrepresented target population)\n"
                    "- **Evaluation Ancestry**: {}\n"
                    "- **Variant Count**: {:,} (Build: {})\n"
                    "- **Publication**: {}\n"
                    "- **Reported Performance in target ancestry**:\n{}"
                    .format(pid, name, dev_anc, eval_anc, var_count, row["Genome Build"], pub, metrics_block)
                )
                
        if not best_supported:
            best_supported_content = (
                "**No scores are directly supported by development or evaluation data for this population.**\n\n"
                "All identified scores for this trait were developed and evaluated in other ancestries (mostly European). "
                "Applying these scores to **{}** ancestry is highly speculative and is not recommended for clinical purposes."
            ).format(ancestry)
        else:
            best_supported_content = "\n\n".join(best_supported)

        # 2. Evidence Gaps
        eur_only_count = len(df_comparison[df_comparison["Relevance"] == "Low (No Data)"])
        pct_eur_only = (eur_only_count / total_scores * 100) if total_scores > 0 else 0
        
        evidence_gaps_content = (
            "An analysis of the **{total_scores}** scores for **{trait}** shows a massive disparity in ancestry representation:\n\n"
            "- **European Dominance**: **{eur_only_count} out of {total_scores} ({pct_eur_only:.1f}%)** of the scores have zero development or evaluation data in the target '{ancestry}' population.\n"
            "- **Incomplete Training**: Even for scores that evaluate in the target population, the underlying GWAS weights are almost exclusively derived from European biobanks (e.g. UK Biobank). This creates a 'transferability gap' because causal variants or linkage disequilibrium structures vary across ancestry groups.\n"
            "- **Evaluation Gaps**: Only **{scores_with_data_count}** scores have any validation data in cohorts containing {ancestry} individuals."
        ).format(
            total_scores=total_scores,
            trait=trait,
            eur_only_count=eur_only_count,
            pct_eur_only=pct_eur_only,
            ancestry=ancestry,
            scores_with_data_count=scores_with_data_count
        )

        # 3. Use with Caution
        caution_items = []
        for pid, perfs in performance_data.items():
            for p in perfs:
                size = p.get("total_sample_size", 0)
                metrics = p.get("metrics", {})
                
                # Check for caution criteria
                reasons = []
                if size < 1000:
                    reasons.append("Small evaluation size (N = {:,} individuals)".format(size))
                
                # Check for low AUROC/C-Index (if available)
                auroc_raw = metrics.get("AUROC") or metrics.get("C-index")
                auroc_val = _get_float_estimate(auroc_raw)
                if auroc_val is not None and auroc_val < 0.60:
                    reasons.append("Weak predictive accuracy (AUROC/C-index = {})".format(auroc_raw))
                
                # Check for low R2 (if available)
                r2_raw = metrics.get("R²") or metrics.get("R2")
                r2_val = _get_float_estimate(r2_raw)
                if r2_val is not None and r2_val < 0.05:
                    reasons.append("Low variance explained (R² = {})".format(r2_raw))
                    
                if reasons:
                    caution_items.append(
                        "- **{}** (Cohort: *{}*):\n"
                        "  - Caution: {}\n"
                        "  - Publication: {}\n"
                        "  - Sample size: {:,} (Cases: {}, Controls: {})"
                        .format(pid, p.get("cohorts"), "; ".join(reasons), p.get("publication"), size, p.get("cases", "N/A"), p.get("controls", "N/A"))
                    )
                    
        if caution_items:
            use_with_caution_content = (
                "The following scores have validation records in the target ancestry but exhibit limitations that warrant extreme caution:\n\n" + 
                "\n".join(caution_items)
            )
        else:
            use_with_caution_content = (
                "No scores with target validation data were flagged for small sample sizes or low performance metrics. "
                "However, general limitations of transferring scores across populations still apply."
            )

        # 4. Not Enough Evidence
        low_rel = df_comparison[df_comparison["Relevance"] == "Low (No Data)"]
        if not low_rel.empty:
            no_evidence_list = []
            # List top 10
            for _, row in low_rel.head(10).iterrows():
                no_evidence_list.append("- **{}** (Score Name: {}) - Developed: {}; Evaluated: {}"
                                       .format(row["PGS ID"], row["Score Name"], row["Dev Ancestry"], row["Eval Ancestry"]))
            
            suffix = ""
            if len(low_rel) > 10:
                suffix = "\n- *...and {} more scores with zero representation data.*".format(len(low_rel) - 10)
                
            not_enough_evidence_content = (
                "The following scores have **ZERO** representation, training, or evaluation data in the target '{ancestry}' population:\n\n"
                "{list_str}{suffix}\n\n"
                "**Risk Warning**: Applying these scores to a person of '{ancestry}' ancestry is highly discouraged as their performance is completely unvalidated, and they may lead to misclassification of genetic risk (either false reassurance or false alarm)."
            ).format(ancestry=ancestry, list_str="\n".join(no_evidence_list), suffix=suffix)
        else:
            not_enough_evidence_content = "All identified scores for this trait contain at least some training or evaluation data in the target ancestry."

        # 5. PRS Distribution & Cohort Effect Sizes
        prs_distribution_list = [
            "### Raw PRS Range vs. Population Z-Scores\n"
            "Polygenic Risk Scores (PRS) are calculated by summing the products of risk allele dosages and their "
            "respective effect weights. Because scores depend on the variant count (which varies from a few dozen to "
            "millions) and the statistical weights of a specific model, **raw PRS values are arbitrary and do not "
            "have a standard biological or absolute range** (e.g., a score of 150.0 is not inherently high or low).\n\n"
            "To make scores clinically interpretable, researchers typically standardize them relative to a reference "
            "population. The standardized score (Z-score) represents the number of standard deviations an individual's "
            "score lies from the population mean:\n"
            "- **Population Mean**: 0\n"
            "- **Standard Deviation (SD)**: 1\n"
            "- **Standard Population Range (95% CI)**: **-1.96 to +1.96** (95% of the population falls within this interval).\n"
            "- **High Risk Threshold**: Typically defined as Z-score > 1.64 (top 5% of the distribution) or Z-score > 2.33 (top 1%).\n"
        ]
        
        # Pull cohort validation metrics (OR, HR, Beta) with 95% CIs from the performance data
        cohort_metrics = []
        for pid, perfs in performance_data.items():
            for p in perfs:
                metrics = p.get("metrics", {})
                # Look for metrics that contain "(95% CI:"
                ci_metrics = {k: v for k, v in metrics.items() if isinstance(v, str) and "(95% CI:" in v}
                if ci_metrics:
                    ci_str = ", ".join("**{}**: {}".format(k, v) for k, v in ci_metrics.items())
                    cohort_metrics.append(
                        "- **{}** (Cohort: *{}*): {} (reported in publication: *{}*)"
                        .format(pid, p.get("cohorts"), ci_str, p.get("publication"))
                    )
                    
        if cohort_metrics:
            prs_distribution_list.append(
                "### Reported Validation Effect Sizes (with 95% CIs) in target population:\n"
                "The following scores have published association strength statistics (like Odds Ratio per SD or Hazard Ratio per SD) "
                "with 95% Confidence Intervals (CIs) validated in cohorts containing **{}** ancestry individuals:\n\n"
                "{}"
                .format(ancestry, "\n".join(cohort_metrics))
            )
        else:
            prs_distribution_list.append(
                "### Reported Validation Effect Sizes (with 95% CIs):\n"
                "**No scores have published validation effect sizes with 95% Confidence Intervals (CIs) reported in the catalog "
                "for the '{}' population.** This highlights a critical research gap: while a score might be evaluated, "
                "the precise statistical confidence intervals and association strengths (e.g. OR per SD) remain unquantified "
                "in this population.".format(ancestry)
            )
            
        prs_distribution_content = "\n\n".join(prs_distribution_list)

        return MOCK_REPORT_TEMPLATE.format(
            trait=trait,
            ancestry=ancestry,
            best_supported_content=best_supported_content,
            evidence_gaps_content=evidence_gaps_content,
            use_with_caution_content=use_with_caution_content,
            not_enough_evidence_content=not_enough_evidence_content,
            prs_distribution_content=prs_distribution_content,
            total_scores=total_scores,
            scores_with_data_count=scores_with_data_count
        )
