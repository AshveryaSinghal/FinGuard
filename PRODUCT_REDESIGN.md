# FinGuard AI product redesign

The application is organized as an operational fraud workspace rather than a portfolio explainer.

- Overview: monitoring activity, open alerts, cases, and recent scores.
- Transactions: inspect a transaction before assessment, run V3 inference, review evidence, and optionally reveal the historical label for evaluation.
- Alerts: Review and Automatic case tiers only.
- Investigations: cases created only by the artifact-defined Automatic case tier.
- URL Analysis: experimental inspection only; automated enforcement remains disabled.
- Models: compact model status, metrics, thresholds, validation scope, and limitations.

The payment UI never exposes ground truth before explicit reveal. Payment inference remains historical replay against the exact saved V3 feature store and is not represented as live raw-transaction scoring.
