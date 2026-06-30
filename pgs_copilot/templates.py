"""
Prompt templates and fallback templates for the PGS Equity Copilot report generator.
"""

SYSTEM_PROMPT = """
You are an advanced medical genomics AI agent specializing in evaluating polygenic scores (PGS) for diverse populations.
Your role is to summarize published PGS evidence and highlight ancestry-related evidence gaps.

CRITICAL WARNINGS:
1. You MUST NOT calculate clinical risk for any individual.
2. You MUST NOT provide medical advice or clinical recommendations.
3. You must use only the public metadata provided in the context.
4. You must include clear scientific limitations in all generated reports.

You will be given structured metadata representing available polygenic scores for a specific trait and a target ancestry group.
Analyze this data and produce a structured, professional report following the requested markdown format.
"""

REPORT_PROMPT_TEMPLATE = """
Analyze the available Polygenic Scores (PGS) for the trait '{trait}' when applied to the target ancestry '{ancestry}'.

Here is the comparative metadata for the available scores:
{scores_context}

Based on this data, generate an equity-focused evaluation report.
Your output MUST follow this exact structure and include these headers:

# PGS Equity Copilot Report: {trait} ({ancestry} Ancestry Focus)

> **[IMPORTANT] Warning & Disclaimer**
> This tool summarizes published polygenic score (PGS) research metadata for evaluation purposes. It does not calculate individual clinical risk, provide medical advice, or recommend clinical interventions. Polygenic scores are research tools and may have limited predictive accuracy, particularly in populations underrepresented in genomic studies.

## 1. Best-Supported PGS for this Population
Identify which score(s) have the strongest scientific evidence for the '{ancestry}' ancestry group.
- State the score ID (e.g., PGS000123) and name.
- Explain the evidence supporting this score (e.g., inclusion of '{ancestry}' individuals in the development/GWAS sample, or evaluation in '{ancestry}' cohorts).
- Mention the key publication metadata (author, journal, year).
- If no score has development or evaluation evidence for this ancestry, state: "No score is directly supported by development or evaluation data for this population. See 'Not enough evidence' below."

## 2. Evidence Gaps
Quantitatively analyze the representation gaps for the target ancestry across the available scores.
- Discuss how the development (GWAS/training) samples compare to the evaluation samples for this ancestry.
- Detail the typical percentage of target ancestry representation (e.g., "While score X has a large development cohort, it is 99% European, with only 1% representation for the target population").
- Highlight the discrepancy between the most researched ancestry (usually European) and the target ancestry.

## 3. Use with Caution
Identify scores that are evaluated in the target ancestry but have critical caveats:
- Small evaluation sample sizes (less than 1,000 cases/controls or individuals).
- Weak performance metrics (e.g., low AUROC, C-index, or R²).
- Potential issues due to genome build compatibility (e.g., hg19 vs hg38) or score transferability across cohorts.
- Specific performance estimates if available (e.g., "PGS000XXX reported an AUROC of only 0.55 in the target population").

## 4. Not Enough Evidence
List scores that have ZERO representation, training, or evaluation data for the target ancestry.
- State clearly that these scores have not been validated in the '{ancestry}' population and should not be assumed transferable.
- Emphasize the risks of applying non-validated scores to underrepresented populations.

## 5. PRS Distribution & Cohort Effect Sizes
Provide a clear scientific explanation of the score distribution in the population:
- Explain that raw polygenic scores (PRS) are arbitrary sums of genetic weights and do not have a universal absolute range.
- Detail that in any target population, scores are typically standardized to Z-scores (mean = 0, standard deviation = 1), meaning 95% of the population falls within the range of **-1.96 to +1.96**.
- Summarize the actual **reported validation effect sizes (e.g. Odds Ratio or Beta per standard deviation) and their 95% Confidence Intervals (CI)** for the target ancestry, showing the strength of association in validation cohorts (e.g., "OR = 1.41 [95% CI: 1.35 - 1.47]"). Use the actual CI values provided in the context.

## 6. Summary Table & Key Recommendations
Provide a clean summary of the findings, outlining key limitations of the current literature, and what data is needed to close the equity gaps.
"""

# Deterministic rules-based report generator for offline simulator
MOCK_REPORT_TEMPLATE = """# PGS Equity Copilot Report: {trait} ({ancestry} Ancestry Focus)

> **[IMPORTANT] Warning & Disclaimer**
> This tool summarizes published polygenic score (PGS) research metadata for evaluation purposes. It does not calculate individual clinical risk, provide medical advice, or recommend clinical interventions. Polygenic scores are research tools and may have limited predictive accuracy, particularly in populations underrepresented in genomic studies.

## 1. Best-Supported PGS for this Population
{best_supported_content}

## 2. Evidence Gaps
{evidence_gaps_content}

## 3. Use with Caution
{use_with_caution_content}

## 4. Not Enough Evidence
{not_enough_evidence_content}

## 5. PRS Distribution & Cohort Effect Sizes
{prs_distribution_content}

## 6. Summary Table & Key Recommendations
### Core Comparative Summary
* **Selected Trait**: {trait}
* **Target Ancestry**: {ancestry}
* **Total Evaluated Scores**: {total_scores}
* **Scores with Target Ancestry Data**: {scores_with_data_count}

### Recommendations for Closing Equity Gaps
1. **Diverse Cohort Recruitment**: Funding and resources must be allocated to establish biobanks and cohorts representing {ancestry} individuals to enable score development.
2. **Standardized Reporting**: Researchers should publish ancestry-specific performance metrics (AUROC, R²) for all evaluated cohorts to allow comparison.
3. **Cross-Population Transferability Research**: Support research into multi-ancestry risk scoring methods (e.g., PRS-CSx) that incorporate diverse GWAS weights to improve score accuracy across populations.
"""
