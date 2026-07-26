# Model Artifacts

The submission includes:

- `grade_transition_model.joblib`: preprocessor, multi-output Random Forest, baselines,
  importance, metrics, version, and dataset checksum;
- `basis_weight_forecast.joblib`: temporal schema, direct horizon regressors, crossing classifier,
  residual intervals, metrics, and version.

Deployment mounts `models/` read-only. Runtime registers and validates artifacts but never trains or
overwrites them. See [MODEL_OVERVIEW.md](../docs/MODEL_OVERVIEW.md).

