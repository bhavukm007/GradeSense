# Data Artifacts

The submission includes:

- `generated/paper_mill_transitions.csv`: snapshot transition observations for the legacy
  prediction/explainability path;
- `sequential/paper_mill_transition_sequences.csv`: ordered, transition-ID-bounded sequences for
  forecasting and live replay.

Production deployment mounts `data/` read-only and does not regenerate these files during startup
or the demo. Explicit regeneration remains available for controlled development and experimentation.
The synthetic data demonstrates process relationships and system behavior; it is not a substitute
for mill historian validation.
