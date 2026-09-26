# Engineering Handoff: Informed Consent Compliance Scorer

## The problem this addresses

Clinical research teams need to confirm informed consent forms include all required disclosure elements and are written in language participants can actually understand, without pressure or ambiguity that could undermine informed consent. Today this review is manual and inconsistent across reviewers.

## What this prototype proves

A two-layer check, cheap deterministic rules for required elements, an LLM judgment call for readability and risk language, can catch both kinds of issues in a single pass, at a rough cost of $0.005 to $0.01 per document scanned.

## What I deliberately did not solve

- **No real document ingestion.** This takes pasted plain text only. A production version needs to accept actual consent form files (PDF, Word), which means adding a text extraction step before this logic runs.
- **No persistence.** Nothing is saved. A real tool needs a record of what was scanned, when, its results, and who reviewed it, both for audit purposes and to track whether flagged issues get resolved.
- **No human review workflow.** Right now a flag is just text on a screen. A production version needs a way for a compliance reviewer to accept, override, or dismiss each flag, and a record of that decision.
- **Required elements list is not exhaustive.** The seven elements checked here are the common baseline, not a complete regulatory list. This needs review against actual IRB or REB requirements for whatever jurisdictions this would be used in, likely with legal or compliance input, not just engineering judgment.

## Open questions for engineering

1. **Response reliability at scale.** During testing, this hit two real issues: a Claude response format assumption that broke silently, and truncated responses at low token limits (both documented in the README's Known Limitations section). At scale, what's the right retry and validation strategy so a malformed or incomplete model response never gets treated as a clean result?
2. **Cost at scale.** Based on actual per-scan costs observed during testing (roughly $0.009 per scan), here's what real volume looks like:

   | Monthly volume | Estimated monthly cost |
   |---|---|
   | 100 scans | ~$0.90 |
   | 1,000 scans | ~$9 |
   | 10,000 scans | ~$90 |
   | 100,000 scans | ~$900 |

   At any realistic volume for a single research institution, this is a trivial line item, not a cost driver. The number worth watching isn't per-scan cost, it's what happens if scope expands: checking ancillary documents (assent forms, translated versions) multiplies volume, and moving to a more capable or more expensive model changes the per-call rate. Neither breaks this cost model, but both should be revisited if either changes materially. Worth deciding now whether cost tracking needs to be a first-class, persisted feature (so a compliance team can see cost by study, by reviewer, by month) rather than the current in-session-only display, which resets if the browser tab closes.
3. **Where does the required elements list live?** Right now it's hardcoded in the script. If this becomes a real tool, that list likely needs to be configurable per study type or jurisdiction, which is a data modeling decision, not just a code change.

## Architecture note

Rules run first, deterministic and free. The LLM call only runs after, and only handles judgment a keyword match can't make. This ordering matters: reversing it, running the expensive call first, would cost more with no accuracy benefit, since the rule-based check doesn't need the LLM's help.
