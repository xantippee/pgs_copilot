import streamlit as st
import pandas as pd
import json
import os
from pgs_copilot.api import PGSCatalogClient
from pgs_copilot.processor import TRAIT_MAP, ANCESTRY_MAP, PGSProcessor
from pgs_copilot.llm import ReportGenerator

# Page config
st.set_page_config(
    page_title="PGS Equity Copilot",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
<style>
    /* Premium visual styles */
    .main {
        background-color: #0f111a;
        color: #f0f2f6;
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    .stApp {
        background-color: #0f111a;
    }
    h1, h2, h3 {
        color: #00f2fe;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .report-title {
        background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .disclaimer-box {
        background-color: rgba(255, 75, 75, 0.1);
        border: 1px solid #ff4b4b;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 2rem;
        color: #ff9e9e;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    .disclaimer-title {
        color: #ff4b4b;
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .metric-card {
        background-color: #1a1d2e;
        border: 1px solid #2d3250;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: #00f2fe;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #00f2fe;
        margin-bottom: 0.2rem;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #a0aec0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .report-container {
        background-color: #151828;
        border: 1px solid #22263f;
        border-radius: 12px;
        padding: 2rem;
        margin-top: 1.5rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    /* Make all markdown text within report-container human-readable white/light-gray */
    .report-container, .report-container p, .report-container li, .report-container span, .report-container div {
        color: #f0f2f6 !important;
    }
    .report-container h1, .report-container h2, .report-container h3, .report-container h4, .report-container h5 {
        color: #00f2fe !important;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
    }
    .report-container strong {
        color: #ffffff !important;
    }
    
    /* Global overrides for the main body container to force readable light colors in dark mode */
    .main .stMarkdown p, 
    .main .stMarkdown li, 
    .main .stMarkdown span,
    .main .stMarkdown div,
    .main p,
    .main li,
    .main span {
        color: #f0f2f6 !important;
    }
    .main h1, .main h2, .main h3, .main h4, .main h5, .main h6,
    .main .stMarkdown h1, .main .stMarkdown h2, .main .stMarkdown h3, .main .stMarkdown h4, .main .stMarkdown h5 {
        color: #00f2fe !important;
    }
    .main strong, .main .stMarkdown strong {
        color: #ffffff !important;
    }
    .sidebar-api-key {
        font-size: 0.8rem;
        margin-top: -10px;
        margin-bottom: 10px;
        color: #718096;
    }
</style>
""", unsafe_allow_html=True)

# Clients instantiation
client = PGSCatalogClient()

# Caching functions for performance optimization
@st.cache_data(show_spinner="Querying PGS Catalog for scores...")
def cached_fetch_scores(efo_id):
    return client.get_scores_by_trait(efo_id)

@st.cache_data(show_spinner="Querying detailed evaluation performance metrics...")
def cached_fetch_performance(pgs_ids):
    # Fetch performance data concurrently
    return client.get_performance_metrics_bulk(pgs_ids)

# Header
st.markdown('<div class="report-title">🧬 PGS Equity Copilot</div>', unsafe_allow_html=True)
st.markdown('<p style="color:#a0aec0; font-size:1.1rem; margin-top:-10px;">Evaluating Ancestry Representation & Bias in Polygenic Risk Scores</p>', unsafe_allow_html=True)

# Prominent Medical Disclaimer Warning
st.markdown("""
<div class="disclaimer-box">
    <div class="disclaimer-title">⚠️ CLINICAL LIMITATION WARNING & DISCLAIMER</div>
    This software is a research evaluation tool that summarizes published scientific metadata from the public Polygenic Score (PGS) Catalog. 
    It <strong>does not calculate individual clinical risk</strong>, <strong>does not process individual genotypes</strong>, and <strong>does not provide medical advice or diagnostic recommendations</strong>. 
    The performance metrics summarized herein represent studies conducted on specific research cohorts and may not generalize. 
    Users must consult licensed healthcare providers for clinical genetic testing and medical decision-making.
</div>
""", unsafe_allow_html=True)

# Sidebar configurations
st.sidebar.markdown("### ⚙️ Engine Settings")
llm_backend = st.sidebar.selectbox(
    "Report LLM Backend",
    ["Offline Simulator", "Google Gemini", "OpenAI", "Ollama (Local)"],
    index=0,
    help="Choose the backend for report generation. Offline Simulator runs instantly without API keys."
)

api_key = ""
ollama_host = ""
ollama_model = ""

if llm_backend == "Google Gemini":
    api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Enter your Google AI Studio API key.")
    st.sidebar.markdown('<div class="sidebar-api-key">Saved in session memory only</div>', unsafe_allow_html=True)
elif llm_backend == "OpenAI":
    api_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Enter your OpenAI API key.")
    st.sidebar.markdown('<div class="sidebar-api-key">Saved in session memory only</div>', unsafe_allow_html=True)
elif llm_backend == "Ollama (Local)":
    ollama_host = st.sidebar.text_input("Ollama Host URL", value="http://localhost:11434")
    ollama_model = st.sidebar.text_input("Ollama Model", value="llama2")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 Query Selection")

# Trait Selection
selected_trait_label = st.sidebar.selectbox(
    "Select Target Trait",
    list(TRAIT_MAP.keys()),
    index=0
)
target_efo_id = TRAIT_MAP[selected_trait_label]

# Ancestry Selection
selected_ancestry_label = st.sidebar.selectbox(
    "Select Target Ancestry",
    list(ANCESTRY_MAP.keys()),
    index=1  # Default to African
)

# Fetch data triggers
st.sidebar.markdown("---")
run_analysis = st.sidebar.button("⚡ Generate Copilot Report", use_container_width=True)

# Primary Workflow
if target_efo_id:
    # 1. Fetch scores
    raw_scores = cached_fetch_scores(target_efo_id)
    
    if not raw_scores:
        st.error("No scores found for the trait '{}' ({}) in the PGS Catalog.".format(selected_trait_label, target_efo_id))
    else:
        # Create Comparative DataFrame
        df_comparison = PGSProcessor.create_comparison_dataframe(raw_scores, selected_ancestry_label)
        
        # Calculate statistics
        total_scores = len(df_comparison)
        high_relevance_count = len(df_comparison[df_comparison["Relevance"] == "High (Developed in Pop)"])
        med_relevance_count = len(df_comparison[df_comparison["Relevance"] == "Medium (Evaluated in Pop)"])
        represented_count = high_relevance_count + med_relevance_count
        
        # UI Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Total Scores Found</div>
            </div>
            """.format(total_scores), unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Developed in Target</div>
            </div>
            """.format(high_relevance_count), unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Evaluated in Target</div>
            </div>
            """.format(med_relevance_count), unsafe_allow_html=True)
        with col4:
            equity_ratio = (represented_count / total_scores * 100) if total_scores > 0 else 0
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">{:.1f}%</div>
                <div class="metric-label">Equity Data Ratio</div>
            </div>
            """.format(equity_ratio), unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Display Comparative Table
        st.subheader("📊 Comparative Score Catalog Matrix")
        st.markdown(
            "Below is the complete list of polygenic scores associated with **{}** (mapped ontology term `{}`), "
            "sorted by relevancy to **{}** ancestry."
            .format(selected_trait_label, target_efo_id, selected_ancestry_label)
        )
        
        # Format table for cleaner look (dropping columns used for sorting)
        display_columns = ["PGS ID", "Score Name", "Relevance", "Variants", "Genome Build", "Publication", "Dev Ancestry", "Eval Ancestry"]
        st.dataframe(df_comparison[display_columns], use_container_width=True)
        
        # Trigger analysis
        if run_analysis:
            st.markdown("---")
            st.markdown("### 🤖 LLM Copilot Report Generator")
            
            # 1. Fetch performances for top ranked scores to feed into RAG context
            # To avoid API overloading, we fetch detailed evaluations for the top 15 ranked scores
            top_scores_to_evaluate = df_comparison.head(15)["PGS ID"].tolist()
            raw_perf_data = cached_fetch_performance(tuple(top_scores_to_evaluate))
            
            # Process performance data to filter for target ancestry
            performance_context = {}
            for pid, perfs in raw_perf_data.items():
                relevant_evals = PGSProcessor.extract_relevant_performances(pid, perfs, selected_ancestry_label)
                performance_context[pid] = relevant_evals
                
            # 2. Build RAG prompt context
            # We construct a summary text block representing the scores, metadata, and evaluation results
            summary_context_list = []
            for _, row in df_comparison.head(10).iterrows():
                pid = row["PGS ID"]
                score_str = (
                    "Score: {}\n"
                    "- Name: {}\n"
                    "- Variants: {:,}\n"
                    "- Genome Build: {}\n"
                    "- Method: {}\n"
                    "- Development Ancestry: {}\n"
                    "- Evaluation Ancestry: {}\n"
                    "- Publication: {}\n"
                    .format(pid, row["Score Name"], row["Variants"], row["Genome Build"], row["Method"], row["Dev Ancestry"], row["Eval Ancestry"], row["Publication"])
                )
                
                # Append relevant evaluations
                evals = performance_context.get(pid, [])
                if evals:
                    evals_str = []
                    for ev in evals:
                        m_str = ", ".join("{}: {}".format(k, v) for k, v in ev["metrics"].items())
                        evals_str.append("  * Eval Cohort: {} (N={:,}, Cases={}, Controls={}), Metrics: [{}]"
                                         .format(ev["cohorts"], ev["total_sample_size"], ev["cases"], ev["controls"], m_str))
                    score_str += "- Performance evaluations in target population:\n" + "\n".join(evals_str) + "\n"
                else:
                    score_str += "- Performance evaluations in target population: None reported in catalog\n"
                    
                summary_context_list.append(score_str)
                
            scores_context_str = "\n=======================\n".join(summary_context_list)
            
            # 3. Generate Report
            with st.spinner("Generating equity copilot report via {}...".format(llm_backend)):
                report_text = ""
                
                if llm_backend == "Offline Simulator":
                    report_text = ReportGenerator.generate_offline_report(
                        selected_trait_label,
                        selected_ancestry_label,
                        df_comparison,
                        performance_context
                    )
                elif llm_backend == "Google Gemini":
                    if not api_key:
                        st.error("Please enter a Google Gemini API Key in the sidebar settings.")
                    else:
                        report_text = ReportGenerator.generate_with_gemini(
                            api_key,
                            selected_trait_label,
                            selected_ancestry_label,
                            scores_context_str
                        )
                elif llm_backend == "OpenAI":
                    if not api_key:
                        st.error("Please enter an OpenAI API Key in the sidebar settings.")
                    else:
                        report_text = ReportGenerator.generate_with_openai(
                            api_key,
                            selected_trait_label,
                            selected_ancestry_label,
                            scores_context_str
                        )
                elif llm_backend == "Ollama (Local)":
                    report_text = ReportGenerator.generate_with_ollama(
                        ollama_host,
                        ollama_model,
                        selected_trait_label,
                        selected_ancestry_label,
                        scores_context_str
                    )
                
                if report_text:
                    # Combine wrapper tags and report text in a single block so the class wrapper applies correctly
                    combined_report_html = '<div class="report-container">\n\n' + report_text + '\n\n</div>'
                    st.markdown(combined_report_html, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Download button
                    st.download_button(
                        label="📥 Download Report (Markdown)",
                        data=report_text,
                        file_name="PGS_Equity_Report_{}_{}.md".format(
                            selected_trait_label.replace(" ", "_"),
                            selected_ancestry_label.replace(" ", "_")
                        ),
                        mime="text/markdown",
                        use_container_width=True
                    )
        else:
            st.info("👈 Set your preferences in the sidebar and click 'Generate Copilot Report' to run the evaluation.")
else:
    st.warning("Please configure your selections in the sidebar.")
