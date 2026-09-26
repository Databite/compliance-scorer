# Informed Consent Compliance Scorer

**Live demo:** https://compliance-scorer-c8krr3htfin6ogvqdmzzvq.streamlit.app/

A prototype tool that reviews clinical trial informed consent forms for missing required disclosure elements, readability risk, and undue pressure language, and attempts to automatically fix flagged issues, verifying its own fixes before accepting them.

## What it does

The tool runs several checks on a pasted consent form:

1. Required elements check, a rule-based pass that confirms the document mentions each of the standard disclosure elements (purpose of the study, right to withdraw, confidentiality, risks, benefits, contact information, compensation).
2. Readability and risk language check, an AI-powered pass using Claude that evaluates plain-language clarity, flags any language that could overstate benefits or downplay risk, and identifies ambiguous descriptions that could undermine informed consent.
3. Automatic fix and re-check loop, for anything flagged in step 2, a separate Claude call drafts a specific rewrite of the problematic sentence, and a third call independently re-checks whether that rewrite actually resolves the original issue. If the first attempt doesn't pass the re-check, it tries once more with an explicit instruction to take a different approach. If neither attempt resolves it, the tool says so plainly and flags it for human review, rather than presenting an unverified fix as if it worked.

Each scan shows an estimated API cost, since running multiple AI calls per flagged issue has a real, measurable cost that matters for a production version of this tool.

## Batch mode

Upload a CSV with a consent_text column to process multiple consent forms at once. Results show a compact summary table (missing elements, flags found, how many were auto-resolved vs. need human review, cost) with a downloadable CSV of the full output.

## Why this architecture

This is a layered system, not a single AI call:

- Rules run first, cheap and deterministic, to catch missing required elements a keyword match can find reliably.
- One AI call flags issues, reserved for judgment a keyword match can't make, like tone and ambiguity.
- A second AI call drafts a fix, only for what was actually flagged, never for content that already passed.
- A third AI call independently verifies the fix, rather than trusting the second call's output at face value. This is the key design choice: an automated fix that isn't checked against the original problem is just an assumption dressed up as a solution.
- A retry with explicit feedback, if the first fix attempt fails the check, the system doesn't just give up or retry blindly, it tells the model specifically that the first attempt didn't work and to try a meaningfully different approach.
- An honest stop condition. After two failed attempts, the tool stops and says this needs a human, rather than looping indefinitely or silently accepting a fix that didn't actually pass its own verification.

This is a small example of an agentic pattern: later steps make decisions based on what earlier steps actually found, rather than following a fixed script regardless of outcome.

## What this is not

This is a prototype built to demonstrate the interaction pattern and architecture, not a validated compliance tool. It has not been reviewed by legal or clinical research compliance experts, and it should not be used to approve or reject a real consent form or its automated rewrites without qualified human review.

## Known limitations

Two real issues surfaced during development, both fixed here but worth naming for anyone extending this:

1. Response parsing broke on a specific Claude output format. The initial implementation assumed the API always returns a single text block, but Claude can return a separate internal reasoning block alongside the final answer. The code now explicitly filters for text-type blocks only.
2. Truncated responses at low token limits. Longer responses occasionally got cut off before completion. The code now checks the API's stop_reason explicitly and can flag a truncated result rather than silently treating a cut-off response as complete.

## Tech stack

- Python
- Streamlit (interface)
- Anthropic API (Claude) for the readability check, fix drafting, and fix verification layers

See HANDOFF.md for engineering handoff notes, open questions, and what this prototype deliberately doesn't solve.
