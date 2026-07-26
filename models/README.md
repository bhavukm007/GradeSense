# Model Artifacts

The submission includes:

- `grade_transition_model.joblib`: preprocessor, multi-output Random Forest, baselines,
  importance, metrics, version, and dataset checksum;
- `basis_weight_forecast.joblib`: temporal schema, direct horizon regressors, crossing classifier,
  residual intervals, metrics, and version.

Production deployment mounts `models/` read-only and uses these pre-trained artifacts for the demo.
Runtime startup registers and validates artifacts without training or overwriting them. Explicit
development regeneration/retraining remains available through the compatibility endpoint and
offline scripts. See [MODEL_OVERVIEW.md](../docs/MODEL_OVERVIEW.md).
