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

## Known limitations

Two real issues surfaced during development, both fixed here but worth naming for anyone extending this:

1. **Response parsing broke on a specific Claude output format.** The initial implementation assumed the API always returns a single text block, but Claude can return a separate internal reasoning block alongside the final answer. The code now explicitly filters for text-type blocks only, but this is a good reminder that API response shapes shouldn't be assumed without checking the actual response structure.

2. **Truncated responses at low token limits.** The original `max_tokens` setting was occasionally too low to let Claude complete all three readability check lines, resulting in a cut-off response the user would see as an incomplete answer rather than an error. Raising the limit resolved it for the cases tested here, but a production version should validate that the response actually reached a natural stopping point, rather than assuming any returned text is complete.

Neither issue is caught automatically today, both were found through manual testing. A production version would want automated tests covering both cases, a multi-block response and a response near the token limit, rather than relying on someone noticing a cut-off answer during a demo.

## Tech stack

- Python
- Streamlit (interface)
- Anthropic API (Claude) for the language judgment layer

## Live Demo

https://compliance-scorer-c8krr3htfin6ogvqdmzzvq.streamlit.app/


See [HANDOFF.md](HANDOFF.md) for engineering handoff notes, open questions, and what this prototype deliberately doesn't solve.
