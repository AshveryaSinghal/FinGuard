# Model governance

## Payment V3 — accepted for historical replay
Source: IEEE-CIS Fraud Detection. Evaluation: untouched chronological partition created from the labelled training data, not Kaggle's hidden competition test labels.

Operating thresholds are loaded only from `artifacts/metadata.json`:
- Monitor
- Review
- Automatic case

The UI must not invent intermediate thresholds. Probability, operational tier, prediction/action, hidden ground truth, and TP/TN/FP/FN outcome are separate concepts.

## URL V2/V3 — rejected for automated decisions
The lexical URL artifacts achieved strong in-dataset metrics but failed independent legitimate-domain stress testing, including severe false positives on major bare-apex domains. A curated allowlist was removed as a model-quality patch. FinGuard exposes only a research score if an artifact is installed and never converts it into an automated allow/block verdict.

A future URL artifact may be accepted only after domain-disjoint evaluation, independent benign-domain stress testing, broad bare-apex coverage, feature ablation, token-safe feature engineering, and explicit automatic rejection gates.
