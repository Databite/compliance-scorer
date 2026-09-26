import streamlit as st
from anthropic import Anthropic
import os

api_key = st.secrets.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY"))
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
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens / 1000 * INPUT_COST_PER_1K) + (output_tokens / 1000 * OUTPUT_COST_PER_1K)
    text_blocks = [block.text for block in response.content if block.type == "text"]
    result_text = "\n".join(text_blocks)
    return result_text, cost

st.title("Informed Consent Compliance Scorer")
st.write("Paste informed consent form text below to check it for missing required elements and readability risk.")

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

