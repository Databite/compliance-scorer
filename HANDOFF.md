# Engineering Handoff: Informed Consent Compliance Scorer

## The problem this addresses

Clinical research teams need to confirm informed consent forms include all required disclosure elements and are written in language participants can actually understand, without pressure or ambiguity that could undermine informed consent. Today this review is manual and inconsistent across reviewers, and even once an issue is found, drafting a compliant fix is its own manual step.

## What this prototype proves

A layered system, cheap deterministic rules for required elements, one AI call for judgment-based flagging, a second AI call to draft a fix, and a third AI call to independently verify that fix, can not only catch compliance issues but attempt to resolve them, while being honest about when an automated fix doesn't actually work. This is meaningfully more than a single-call tool: it's a small agentic loop where the system's next action depends on what a previous step actually found, including whether to retry, and when to stop and defer to a human.

## What I deliberately did not solve

- No real document ingestion. This takes pasted plain text only. A production version needs to accept actual consent form files (PDF, Word), which means adding a text extraction step before this logic runs.
- No persistence. Nothing is saved. A real tool needs a record of what was scanned, what was auto-fixed, what still needs review, and who ultimately approved each fix.
- No human review workflow, only a flag. The tool identifies what needs human review, but there's no way for a reviewer to accept, edit, or reject a suggested fix within the tool itself, and no record of that decision.
- Fixes rewrite only the flagged sentence, not the document. The tool never assembles a fully revised consent form. A production version would need to apply accepted fixes back into the source document, which raises its own questions about version control and audit trail.
- Required elements list is not exhaustive. The seven elements checked here are a common baseline, not a complete regulatory list, and would need review against actual IRB or REB requirements for the relevant jurisdiction.

## Open questions for engineering

1. How many retry attempts is the right number? This caps at two attempts before deferring to a human. That number was chosen to bound cost and latency, not derived from real data on how often a second attempt actually succeeds versus a first. Worth measuring against real consent forms before treating two as the right default.
2. What happens to a fix that passes verification but a human later rejects? Right now, a resolved fix and an unresolved one are both just displayed. Neither is applied anywhere or tracked. If this becomes a real tool, every fix, whether auto-verified or human-reviewed, needs a clear approval and audit trail before it touches an actual document.
3. Cost at scale, with the fix loop included. A scan with no flags costs roughly what the original single-call version cost. A scan where every category gets flagged and needs two fix attempts each costs meaningfully more, since each attempt is two additional API calls (draft, then verify). Worth modeling the actual expected flag rate on real documents before assuming a fixed per-scan cost.
4. Where does the required elements list live? Right now it's hardcoded. A real version likely needs this configurable per study type or jurisdiction.

## Architecture note

This system has four layers, each with a distinct job:

1. Rules check for required elements, cheap and deterministic, no model call needed.
2. One model call flags readability and risk issues, judgment a keyword match can't make.
3. A second model call drafts a fix, but only runs for what was actually flagged, never wasted on content that already passed.
4. A third model call verifies the fix against the original issue, independently, rather than trusting the drafting call's own assessment of its work.

The retry logic matters here: a failed verification doesn't just stop, it feeds the specific failure back into a second drafting attempt with an explicit instruction to try differently, and if that also fails, the system stops and says so, rather than looping indefinitely or accepting an unverified result. This stop condition, admitting a limit rather than pretending success, is arguably the most important design decision in this whole loop.
