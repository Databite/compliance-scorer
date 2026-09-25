# Informed Consent Compliance Scorer

A prototype tool that reviews clinical trial informed consent forms for two things: whether required disclosure elements are present, and whether the language is clear and free of undue pressure on participants.

## What it does

The tool runs two checks on a pasted consent form:

1. **Required elements check** — a rule-based pass that confirms the document mentions each of the standard disclosure elements (purpose of the study, right to withdraw, confidentiality, risks, benefits, contact information, compensation).
2. **Readability and risk language check** — an AI-powered pass using Claude that evaluates plain-language clarity, flags any language that could overstate benefits or downplay risk, and identifies ambiguous descriptions that could undermine informed consent.

Each scan also shows an estimated API cost, since running the AI check on every document at scale has a real, measurable cost that matters for a production version of this tool.

## Why two layers

Rule-based checks are cheap and deterministic, so they run first to catch anything a simple keyword match can find. The AI layer is slower and costs money per call, so it's reserved for judgment calls that keyword matching can't make, like tone and ambiguity. This mirrors a common pattern in production AI systems: use cheap deterministic logic wherever possible, and reserve model calls for genuinely hard judgment tasks.

## What this is not

This is a prototype built to demonstrate the interaction pattern and architecture, not a validated compliance tool. It has not been reviewed by legal or clinical research compliance experts, and it should not be used to approve or reject a real consent form.

## Tech stack

- Python
- Streamlit (interface)
- Anthropic API (Claude) for the language judgment layer

## Running it locally

```
python3 -m venv venv
source venv/bin/activate
pip install streamlit anthropic
export ANTHROPIC_API_KEY="your-key-here"
streamlit run app.py
```
