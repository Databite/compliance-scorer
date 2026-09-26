import streamlit as st
from anthropic import Anthropic
import os
import pandas as pd
import io

try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
client = Anthropic(api_key=api_key)
MODEL = "claude-sonnet-5"

INPUT_COST_PER_1K = 0.003
OUTPUT_COST_PER_1K = 0.015

REQUIRED_ELEMENTS = [
    "purpose of the study",
    "right to withdraw",
    "confidentiality",
    "risks",
    "benefits",
    "contact information",
    "compensation"
]

def rule_based_check(text):
    flags = []
    lower_text = text.lower()
    for element in REQUIRED_ELEMENTS:
        if element not in lower_text:
            flags.append(f"Missing required element: '{element}'")
    return flags

def llm_check(text):
    prompt = f"""You are a clinical research compliance reviewer checking an informed consent form.
Review the following consent form text for:
1. Readability, is the risk and benefit language written in plain language a non-medical person could understand, or is it dense with jargon
2. Undue inducement, does any language overstate benefits or downplay risk in a way that could pressure someone to enroll
3. Ambiguous language, any risk or procedure description that is vague enough that a participant could not give truly informed consent

Consent form text:
\"\"\"
{text}
\"\"\"

Respond in exactly this format:
READABILITY: [Pass/Flag/Fail] - [one sentence reason]
UNDUE_INDUCEMENT: [Pass/Flag/Fail] - [one sentence reason]
AMBIGUOUS_LANGUAGE: [Pass/Flag/Fail] - [one sentence reason]
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens / 1000 * INPUT_COST_PER_1K) + (output_tokens / 1000 * OUTPUT_COST_PER_1K)

    text_blocks = [block.text for block in response.content if block.type == "text"]
    result_text = "\n".join(text_blocks)
    if response.stop_reason == "max_tokens":
        result_text += "\n\n[WARNING: Response was cut off before completion. Increase max_tokens.]"
    return result_text, cost

st.title("Informed Consent Compliance Scorer")
st.write("Check informed consent forms for missing required elements and readability risk, one at a time or in bulk.")

tab1, tab2 = st.tabs(["Single scan", "Batch mode"])

with tab1:
    if "total_cost" not in st.session_state:
        st.session_state.total_cost = 0.0
    if "scan_count" not in st.session_state:
        st.session_state.scan_count = 0

    text_input = st.text_area("Consent form text", height=200)

    if st.button("Scan"):
        if text_input.strip() == "":
            st.warning("Paste some consent form text first.")
        else:
            st.subheader("Required elements check")
            rule_flags = rule_based_check(text_input)
            if rule_flags:
                for flag in rule_flags:
                    st.error(flag)
            else:
                st.success("All required elements found.")

            st.subheader("Readability and risk language check")
            with st.spinner("Checking with Claude..."):
                llm_result, cost = llm_check(text_input)
            st.text(llm_result)

            st.session_state.total_cost += cost
            st.session_state.scan_count += 1

            st.subheader("Cost tracking")
            st.write(f"This scan cost approximately ${cost:.5f}")
            st.write(f"Total scans this session: {st.session_state.scan_count}")
            st.write(f"Total estimated cost this session: ${st.session_state.total_cost:.5f}")

with tab2:
    st.write("Upload a CSV file with one column named `consent_text`, one consent form per row.")
    uploaded_file = st.file_uploader("Upload CSV", type="csv")

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        if "consent_text" not in df.columns:
            st.error("Your CSV must have a column named 'consent_text'.")
        else:
            st.write(f"Found {len(df)} consent forms in this file.")
            if st.button("Run batch scan"):
                results = []
                total_batch_cost = 0.0
                progress = st.progress(0)

                for i, row in df.iterrows():
                    text = str(row["consent_text"])
                    rule_flags = rule_based_check(text)
                    llm_result, cost = llm_check(text)
                    total_batch_cost += cost
                    results.append({
                        "row": i + 1,
                        "missing_elements_count": len(rule_flags),
                        "missing_elements": "; ".join(rule_flags) if rule_flags else "none",
                        "readability_check": llm_result,
                        "cost": round(cost, 5)
                    })
                    progress.progress((i + 1) / len(df))

                results_df = pd.DataFrame(results)
                st.subheader("Batch results")
                st.dataframe(results_df)
                st.write(f"Total batch cost: ${total_batch_cost:.5f}")

                csv_buffer = io.StringIO()
                results_df.to_csv(csv_buffer, index=False)
                st.download_button(
                    "Download results as CSV",
                    csv_buffer.getvalue(),
                    "batch_results.csv",
                    "text/csv"
                )
