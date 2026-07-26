# API Reference

Interactive OpenAPI documentation is available at `/docs`; the machine-readable schema is
`/openapi.json`. All APIs are backward compatible with earlier project phases.

## Conventions

- JSON request and response bodies use snake_case.
- IDs are UUID strings.
- Timestamps are ISO 8601 UTC.
- Validation failures return HTTP 422.
- Missing resources return HTTP 404.
- Conflicting lifecycle operations return HTTP 409.
- Every HTTP response includes `X-Request-ID` and security headers.
- Errors use the common application error envelope where handled by FastAPI exception middleware.

## System

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Service identity |
| GET | `/health` | Lightweight liveness |
| GET | `/version` | Application version |

## Snapshot intelligence

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/predict` | Predict quality, off-spec risk, and stabilization |
| POST | `/recommend` | Legacy snapshot-model corrective actions |
| GET | `/correlations` | Snapshot correlation matrix and ranked pairs |
| GET | `/dataset/statistics` | Snapshot dataset profile |
| POST | `/dataset/regenerate` | Explicit legacy offline regeneration/training compatibility endpoint |
| GET | `/model/info` | Active snapshot model information |
| GET | `/history/predictions` | Paginated prediction history |
| GET | `/history/recommendations` | Paginated legacy recommendation history |

`/dataset/regenerate` is retained for compatibility but is not called by startup, deployment, demo,
or any automated runtime workflow.

## Forecasting and relationships

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/forecast` | Generate and persist a trajectory |
| GET | `/forecast/history` | Recent forecasts |
| GET | `/forecast/{forecast_id}` | One forecast |
| POST | `/forecast/simulate` | Constraint-valid manual intervention simulation |
| GET | `/relationships/discovery` | Lag, nonlinear, grade/stage, and interaction relationships |

Forecast history must contain ordered `SequencePoint` objects. Simulation supports one to four
changes and returns HTTP 422 for unsafe combinations.

## Forecast interventions

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/interventions/recommendations` | Generate forecast-backed ranked actions |
| GET | `/interventions/recommendations` | History, optionally filtered by state |
| GET | `/interventions/recommendations/{id}` | Recommendation detail |
| POST | `/interventions/recommendations/{id}/decisions` | Accept, reject, modify, delay, or apply |
| POST | `/interventions/recommendations/{id}/outcome` | Evaluate future observations |
| GET | `/interventions/effectiveness` | Aggregate observed effectiveness |

Lifecycle states are `proposed`, `accepted`, `rejected`, `modified`, `delayed`, `expired`,
`applied`, and `evaluated`.

## Real-time operations

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/alerts` | Alert history |
| POST | `/alerts/{id}/acknowledge` | Acknowledge an alert |
| GET | `/feedback` | Operator feedback history |
| POST | `/feedback` | Record feedback |
| GET | `/stream/status` | Worker and connection state |
| GET | `/stream/statistics` | Rolling windows |
| GET | `/metrics/live` | Latest live state |
| GET | `/metrics/rolling` | Rolling windows alias |
| GET | `/drift` | Current process/prediction drift |

## Model Registry

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/models` | All registered models |
| GET | `/models/active` | Active prediction and forecast models |
| GET | `/models/{id}` | One registry entry |
| POST | `/models/register` | Validate and register an immutable artifact |
| POST | `/models/promote` | Validate and activate a model |
| POST | `/models/archive` | Archive a non-active model |
| GET | `/admin/models` | Administrative alias |

Registration requires the artifact's SHA-256, dataset checksum, feature-schema checksum, metrics,
training parameters, timestamps, description, algorithm, version, name, kind, and path.

## Administration

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/admin/system` | Combined operational overview |
| GET | `/admin/metrics` | Live metrics and trends |
| GET | `/admin/config` | Runtime configuration |
| PUT | `/admin/config` | Validate, persist, and reload configuration |
| GET | `/admin/audit` | Immutable audit history |
| GET | `/admin/health` | Detailed dependency/resource health |
| GET | `/admin/exports` | Export catalog and row counts |
| POST | `/admin/export` | Download JSON or CSV |

Export resources: `forecasts`, `recommendations`, `decisions`, `outcomes`, `alerts`, `feedback`,
`metrics`, `models`, and `audit`.

## WebSockets

Connect to `/ws/live` or `/ws/dashboard`. Events share this envelope:

```json
{
  "event": "prediction",
  "timestamp": "2026-07-25T12:00:00Z",
  "data": {}
}
```

Event names:

- `system_status`
- `heartbeat`
- `sensor_update`
- `prediction`
- `recommendation`
- `alert`
- `drift`
- `basis_forecast`
- `recommendation_created`
- `recommendation_updated`
- `recommendation_decision`
- `recommendation_outcome`

