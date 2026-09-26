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

FRIENDLY_NAMES = {
    "READABILITY": "Readability",
    "UNDUE_INDUCEMENT": "Undue Inducement Risk",
    "AMBIGUOUS_LANGUAGE": "Ambiguous Language"
}

def rule_based_check(text):
    flags = []
    lower_text = text.lower()
    for element in REQUIRED_ELEMENTS:
        if element not in lower_text:
            flags.append(f"Missing required element: '{element}'")
    return flags

def call_claude(prompt, max_tokens):
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens / 1000 * INPUT_COST_PER_1K) + (output_tokens / 1000 * OUTPUT_COST_PER_1K)
    text_blocks = [block.text for block in response.content if block.type == "text"]
    result_text = "\n".join(text_blocks)
    truncated = response.stop_reason == "max_tokens"
    return result_text, cost, truncated

def readability_check_prompt(text):
    return f"""You are a clinical research compliance reviewer checking an informed consent form.
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

def parse_readability_result(result_text):
    categories = {}
    for line in result_text.splitlines():
        for cat in ["READABILITY", "UNDUE_INDUCEMENT", "AMBIGUOUS_LANGUAGE"]:
            if line.startswith(cat):
                status = "Pass" if "Pass" in line.split("-")[0] else ("Fail" if "Fail" in line.split("-")[0] else "Flag")
                reason = line.split("-", 1)[1].strip() if "-" in line else ""
                categories[cat] = {
                    "status": status,
                    "line": line,
                    "friendly_name": FRIENDLY_NAMES[cat],
                    "reason": reason
                }
    return categories

def draft_fix_prompt(original_text, category, reason, attempt_number, previous_attempt=None):
    retry_note = ""
    if attempt_number > 1:
        retry_note = f"\nYour previous attempt did not resolve the issue: \"{previous_attempt}\"\nTry a meaningfully different approach this time, don't just reword the same sentence slightly."
    return f"""You are helping revise an informed consent form. The following text was flagged for this issue:

Issue category: {category}
Reason flagged: {reason}

Original text:
\"\"\"
{original_text}
\"\"\"
{retry_note}

Rewrite ONLY the specific problematic phrase or sentence to resolve this issue, in plain, clear language appropriate for a consent form. Respond with ONLY the rewritten text, no explanation, no quotes, no preamble.
"""

def recheck_fix_prompt(rewritten_text, category, reason):
    return f"""You are a clinical research compliance reviewer. A sentence was previously flagged for this issue:

Issue category: {category}
Original reason flagged: {reason}

Here is a rewritten version of that sentence:
\"\"\"
{rewritten_text}
\"\"\"

Does this rewrite resolve the issue? Respond in exactly this format:
STATUS: [Pass/Fail]
REASON: [one sentence explanation]
"""

def attempt_fix_with_retry(original_text, category, reason, max_attempts=2):
    total_cost = 0.0
    attempts_log = []
    previous_attempt = None

    for attempt_number in range(1, max_attempts + 1):
        fix_prompt = draft_fix_prompt(original_text, category, reason, attempt_number, previous_attempt)
        fix_result, fix_cost, _ = call_claude(fix_prompt, 300)
        total_cost += fix_cost

        recheck_prompt = recheck_fix_prompt(fix_result, category, reason)
        recheck_result, recheck_cost, _ = call_claude(recheck_prompt, 200)
        total_cost += recheck_cost

        resolved = "STATUS: Pass" in recheck_result

        attempts_log.append({
            "attempt": attempt_number,
            "rewritten_text": fix_result,
            "recheck_result": recheck_result,
            "resolved": resolved
        })

        if resolved:
            return True, fix_result, attempts_log, total_cost

        previous_attempt = fix_result

    return False, None, attempts_log, total_cost

st.title("Informed Consent Compliance Scorer")
st.write("Checks consent forms for missing required elements and readability risk, and attempts to automatically fix flagged language, verifying its own fixes before accepting them.")

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
            session_cost = 0.0

            st.subheader("Required elements check")
            rule_flags = rule_based_check(text_input)
            if rule_flags:
                for flag in rule_flags:
                    st.error(flag)
            else:
                st.success("All required elements found.")

            st.subheader("Readability and risk language check")
            with st.spinner("Running readability check..."):
                initial_result, initial_cost, initial_truncated = call_claude(readability_check_prompt(text_input), 500)
            session_cost += initial_cost
            categories = parse_readability_result(initial_result)

            flagged_categories = {cat: info for cat, info in categories.items() if info["status"] != "Pass"}

            if not flagged_categories:
                st.success("All readability checks passed. No fixes needed.")
                for cat, info in categories.items():
                    st.write(f"Pass — **{info['friendly_name']}**: {info['reason']}")
            else:
                for cat, info in categories.items():
                    label = "Pass" if info["status"] == "Pass" else "Flagged"
                    st.write(f"{label} — **{info['friendly_name']}**: {info['reason']}")

                st.subheader("Automatic fix attempts")
                for cat, info in flagged_categories.items():
                    reason = info["reason"]
                    with st.spinner(f"Attempting to fix: {info['friendly_name']}..."):
                        resolved, fix_text, attempts_log, fix_cost = attempt_fix_with_retry(text_input, cat, reason)
                    session_cost += fix_cost

                    status_label = "Resolved automatically" if resolved else "Needs human review"
                    with st.expander(f"{info['friendly_name']} — {status_label}"):
                        for a in attempts_log:
                            recheck_passed = "STATUS: Pass" in a["recheck_result"]
                            recheck_reason = a["recheck_result"].split("REASON:")[-1].strip() if "REASON:" in a["recheck_result"] else a["recheck_result"]
                            st.markdown(f"**Suggested rewrite (attempt {a['attempt']}):**")
                            st.write(a["rewritten_text"])
                            check_label = "Fixed" if recheck_passed else "Still an issue"
                            st.markdown(f"**Did this fix work?** {check_label} — {recheck_reason}")
                            st.markdown("---")
                        if resolved:
                            st.success("This fix passed the re-check and can be applied.")
                        else:
                            st.warning("Automatic fix attempts did not resolve this issue. This needs human review.")

            st.session_state.total_cost += session_cost
            st.session_state.scan_count += 1

            st.subheader("Cost tracking")
            st.write(f"This scan (including fix attempts) cost approximately \\${session_cost:.5f}")
            st.write(f"Total scans this session: {st.session_state.scan_count}")
            st.write(f"Total estimated cost this session: \\${st.session_state.total_cost:.5f}")

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
                    row_cost = 0.0

                    rule_flags = rule_based_check(text)
                    initial_result, initial_cost, _ = call_claude(readability_check_prompt(text), 500)
                    row_cost += initial_cost
                    categories = parse_readability_result(initial_result)
                    flagged_categories = {cat: info for cat, info in categories.items() if info["status"] != "Pass"}

                    resolved_count = 0
                    needs_review_count = 0

                    for cat, info in flagged_categories.items():
                        reason = info["reason"]
                        resolved, fix_text, attempts_log, fix_cost = attempt_fix_with_retry(text, cat, reason)
                        row_cost += fix_cost
                        if resolved:
                            resolved_count += 1
                        else:
                            needs_review_count += 1

                    total_batch_cost += row_cost
                    results.append({
                        "row": i + 1,
                        "missing_elements_count": len(rule_flags),
                        "missing_elements": "; ".join(rule_flags) if rule_flags else "none",
                        "flags_found": len(flagged_categories),
                        "auto_resolved": resolved_count,
                        "needs_human_review": needs_review_count,
                        "cost": round(row_cost, 5)
                    })
                    progress.progress((i + 1) / len(df))

                results_df = pd.DataFrame(results)
                st.subheader("Batch results")
                st.dataframe(results_df, use_container_width=True)
                st.write(f"Total batch cost: \\${total_batch_cost:.5f}")

                csv_buffer = io.StringIO()
                results_df.to_csv(csv_buffer, index=False)
                st.download_button(
                    "Download results as CSV",
                    csv_buffer.getvalue(),
                    "batch_results.csv",
                    "text/csv"
                )
