# FinGuard AI — Flagship Product Update

## Added
- Professional product information architecture: Overview, Transactions, Alerts, Investigations, Evaluation, URL Analysis, Models.
- Persisted alert lifecycle for Review and Automatic-case assessments.
- Analyst actions: acknowledge, dismiss, and escalate.
- Manual escalation from alert to investigation.
- Investigation status, notes, and resolution workflow.
- Held-out Evaluation workspace with labels hidden until explicit reveal.
- Transaction detail drawer with clear pre-analysis and post-analysis states.
- Threshold-aware evidence for Low assessments as well as escalated tiers.
- Transaction filters for assessed and unassessed records.

## Correctness changes
- Historical `is_fraud` labels are no longer returned by normal transaction list/detail endpoints.
- Ground truth is available only through the explicit Evaluation reveal endpoint.
- Removed stale High Risk / Critical product tiers from the UI.
- The only payment tiers are Low, Monitor, Review, and Automatic case.
- URL automated enforcement remains disabled.

## UI changes
- Removed portfolio slogans and defensive project explanations from operational screens.
- Replaced demo-oriented pages with analyst workflows and compact product copy.
- Reduced the production frontend bundle by removing the chart-heavy dashboard dependency from runtime use.

## Final engineering polish

- Alerts now preserve operational history with Open, Acknowledged, Escalated, Closed, and All filters plus counts.
- Evaluation sampling is fully server-side across the held-out period; the former 8,000-row pool cap is removed.
- Evaluation supports Random, Fraud, Legitimate, TP, TN, FP, and FN scenarios. Outcome-specific scenarios only use already-assessed held-out records, and the historical label remains hidden until explicit reveal.
- Added honest offline score-drift monitoring using PSI across chronological assessed-score halves. It reports insufficient data below 100 assessments and never claims live production monitoring.
- No model retraining, fabricated metrics, synthetic transactions, or fake streaming infrastructure were added.
