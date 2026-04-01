# Deterministic Engine Rule-Depth And Validation Checklist

Use this checklist to deepen the deterministic Meta Ads audit engine before adding more presentation-layer work.

## Goal

Make the client-facing output feel like real analytics by improving:

- fixture coverage
- rule coverage
- recommendation quality
- score calibration
- validation against real account patterns

This work should strengthen the deterministic engine first. AI remains an explanation layer, not the analytics source.

---

## 1. Fixture Dataset Foundation

- [ ] Create a dedicated fixture dataset folder for audit-engine validation.
- [ ] Add fixture datasets for:
  - [ ] healthy baseline account
  - [ ] weak CTR
  - [ ] weak CVR / conversion leakage
  - [ ] high CPA
  - [ ] frequency fatigue
  - [ ] budget imbalance
  - [ ] aggregate-only export
- [ ] Decide which fixtures should exist as:
  - [ ] raw CSV/XLSX imports
  - [ ] normalized expected metric snapshots
  - [ ] both
- [ ] Keep fixture names explicit and scenario-based.

---

## 2. Expected Outcome Specs

- [ ] Define the intended diagnosis for each fixture before expanding rules.
- [ ] For every fixture, document:
  - [ ] expected findings
  - [ ] expected severities
  - [ ] expected categories
  - [ ] expected recommendation direction
  - [ ] expected confidence level
  - [ ] expected score range
- [ ] Add a healthy-account control case so the engine is not calibrated only around failure scenarios.

---

## 3. Deterministic Finding Tests

- [ ] Add tests that verify findings fire correctly for each fixture.
- [ ] Add tests that verify irrelevant rules do not fire.
- [ ] Add tests that verify aggregate-only exports suppress trend-only logic.
- [ ] Add tests that verify low-signal findings still appear when waste/uplift is `$0`.
- [ ] Add tests that verify finding confidence labels match fixture richness.

---

## 4. Weak CTR Rule Expansion

- [ ] Add rule coverage for weak CTR at campaign level.
- [ ] Add rule coverage for weak CTR at ad set level.
- [ ] Add rule coverage for low CTR under meaningful spend.
- [ ] Add rule coverage for low CTR relative to account baseline when possible.
- [ ] Ensure recommendations point to:
  - [ ] creative hook
  - [ ] audience-message fit
  - [ ] offer framing
  - [ ] placement mismatch

---

## 5. Weak CVR / Conversion Leakage Rule Expansion

- [ ] Add rule coverage for clicks without conversions.
- [ ] Add rule coverage for low click-to-conversion rate under meaningful click volume.
- [ ] Add rule coverage for high spend with weak conversion yield.
- [ ] Ensure recommendations point to:
  - [ ] landing page friction
  - [ ] checkout / lead flow friction
  - [ ] tracking integrity
  - [ ] offer mismatch

---

## 6. High CPA Rule Expansion

- [ ] Add rule coverage for CPA above threshold under meaningful spend.
- [ ] Add rule coverage for CPA inflation versus account baseline or prior period where possible.
- [ ] Add rule coverage for high CPA concentrated in one entity.
- [ ] Ensure recommendations point to:
  - [ ] budget reallocation
  - [ ] conversion-quality review
  - [ ] creative and audience efficiency review

---

## 7. Fatigue Rule Expansion

- [ ] Add rule coverage for high frequency under active spend.
- [ ] Add rule coverage for high frequency with weakening CTR or ROAS.
- [ ] Add rule coverage for repeated spend on likely-saturated entities.
- [ ] Ensure recommendations point to:
  - [ ] creative refresh
  - [ ] audience expansion
  - [ ] rotation strategy

---

## 8. Budget Imbalance Rule Expansion

- [ ] Add rule coverage for one entity consuming too much spend with poor outcome.
- [ ] Add rule coverage for sibling inefficiency within the same campaign.
- [ ] Add rule coverage for budget concentration without return concentration.
- [ ] Ensure recommendations point to:
  - [ ] shifting spend to better-performing siblings
  - [ ] reducing weak concentration
  - [ ] separating learning budget from scaling budget

---

## 9. Aggregate-Only Handling

- [ ] Add explicit rule and messaging support for aggregate-only report context.
- [ ] Ensure the engine distinguishes:
  - [ ] no issue found
  - [ ] issue found but trend logic unavailable
  - [ ] issue found but dollar modeling is low-confidence
- [ ] Ensure aggregate-only audits still feel useful and do not look broken.

---

## 10. Recommendation Quality

- [ ] Verify recommendation text is specific to each finding.
- [ ] Ensure recommendations include when available:
  - [ ] affected entity
  - [ ] actual metric
  - [ ] threshold
  - [ ] why it matters
  - [ ] next inspection target
- [ ] Remove any remaining generic filler recommendation wording.
- [ ] Ensure repeated issue types can still produce separate entity-level actions when useful.

---

## 11. Score Calibration

- [ ] Calibrate score behavior against the fixture scenarios.
- [ ] Define expected score bands for:
  - [ ] healthy baseline
  - [ ] weak CTR only
  - [ ] weak CVR under spend
  - [ ] high CPA
  - [ ] fatigue
  - [ ] budget imbalance
  - [ ] aggregate-only export
- [ ] Ensure high-spend serious issues hurt more than low-spend weak signals.
- [ ] Ensure one severe account-wide leak is not hidden by averaging.
- [ ] Ensure sparse data lowers confidence without erasing real issues.

---

## 12. Score Explanation Validation

- [ ] Verify each score pillar exposes:
  - [ ] findings count
  - [ ] strongest issue
  - [ ] understandable reasoning text
- [ ] Ensure score explanations sound business-relevant, not mechanical.

---

## 13. Rule Coverage Matrix

- [ ] Create a simple coverage matrix mapping:
  - [ ] scenario
  - [ ] available signals
  - [ ] rules expected to fire
  - [ ] rules that must not fire
  - [ ] score areas affected
- [ ] Keep this matrix updated as rules are added.

---

## 14. Regression And Validation

- [ ] Add regression tests for low-dollar findings so they still surface as useful diagnostics.
- [ ] Add regression tests for recommendation specificity.
- [ ] Add regression tests for confidence labels on weak datasets.
- [ ] Validate the engine against real uploaded exports after fixture tests pass.
- [ ] Compare output quality against the standard:
  - [ ] real diagnosis
  - [ ] believable prioritization
  - [ ] sensible score
  - [ ] concrete next steps

---

## 15. Recommended Execution Order

- [ ] Create fixture dataset structure.
- [ ] Write expected-outcome specs for each fixture.
- [ ] Add deterministic finding tests for current rule behavior.
- [ ] Expand weak CTR, weak CVR, and high CPA rules first.
- [ ] Expand fatigue, budget imbalance, and aggregate-only handling.
- [ ] Calibrate score ranges against fixtures.
- [ ] Improve recommendation wording per scenario.
- [ ] Validate with real uploads.

---

## Notes

- Do not treat AI as the analytics source.
- Do not add more UI complexity before the deterministic layer is strong enough.
- Prioritize rules that change real client decisions.
- Avoid vanity findings that do not materially help a marketer decide what to do next.
