# Honeywell Hackathon Demo Guide

## Recommended eight-minute flow

### 1. Establish the operating problem — 45 seconds

Open the Dashboard. Explain that grade transitions create a temporary but costly off-spec risk.
Point to the live Newsprint → CopyPaper transition, current sensors, quality/risk estimates, and
Basis Weight forecast.

### 2. Show prediction before failure — 60 seconds

Use a live forecast with a visible ±2.5% crossing. Highlight:

- the future trajectory and confidence interval;
- predicted crossing step/time;
- remaining safe operating time;
- forecast-driving variables.

### 3. Move from prediction to action — 90 seconds

Open the What-if Simulator. Use a recent persisted forecast and compare a feasible stock-flow or
machine-speed change. Show baseline/intervention trajectories, specification limits, confidence
bands, crossing markers, risk reduction, and peak-deviation reduction.

Generate ranked actions. Explain that every candidate is constraint-checked and reforecast; nothing
is a static rule or placeholder.

### 4. Demonstrate the operator workflow — 60 seconds

Accept the top recommendation or delay it for five minutes. Open Recommendation History and show
the persistent lifecycle state. Explain that modified values, reasons, delay, and notes are stored
as separate immutable decisions.

### 5. Close the learning loop — 45 seconds

Show Recommendation Effectiveness. Explain how future observations are compared with the predicted
intervention trajectory to measure avoided/delayed crossings, accuracy, deviation, and
stabilization.

### 6. Prove production governance — 90 seconds

Open Model Registry and identify the active snapshot and forecasting versions. Describe checksum,
schema, pipeline, and metric validation during promotion. Then open Health Dashboard/System Metrics
to show real CPU, memory, disk, database latency, request counts, error rate, WebSocket connections,
and latency trends.

### 7. Show traceability — 45 seconds

Open Audit Log and identify forecast, recommendation decision, configuration, and model lifecycle
events with request IDs. Open Export Center and download audit or recommendation history as CSV.

### 8. Finish with deployment — 25 seconds

Explain the three-container Compose stack, durable PostgreSQL, read-only data/models, health checks,
security middleware, and the path to a mill historian and identity-aware gateway.

## Sample scenario

Use the sequential dataset's live replay. A representative transition is:

- current grade: Newsprint;
- target grade: CopyPaper;
- target Basis Weight: use the active stream value;
- history: latest complete forecast window;
- intervention: a feasible machine-speed reduction and/or stock-flow correction returned by the
  ranked engine.

Do not promise a specific recommendation value in advance: candidates are determined from the
actual active forecast and constraints.

## Example operator workflow

1. Generate recommendations from the latest persisted forecast.
2. Review rank, confidence, before/after crossing probability, peak deviation, and risks.
3. Choose `accepted`, `modified`, `delayed`, `rejected`, or `applied`.
4. Provide a reason and optional notes.
5. After at least three aligned observations, submit the outcome.
6. Review effectiveness metrics and the audit record.

## Example audit trail

The demonstration naturally produces:

- `forecast_request`
- `recommendation_generation`
- `recommendation_decision`
- `recommendation_outcome` when observations are available
- `configuration_change` if stream speed is adjusted
- `export`

Each contains timestamp, actor, action, entity, details, and request ID.

## Example exports

Use Export Center to download:

- `recommendations.csv` for ranked actions and lifecycle states;
- `decisions.json` for operator reasons and modifications;
- `audit.csv` for the complete trace;
- `models.json` for registry evidence.

## Demo preparation checklist

- Docker Linux engine is running.
- `docker compose config --quiet` passes.
- All four data/model artifacts exist.
- `docker compose up --build -d` reports healthy database/backend/frontend.
- Dashboard WebSocket shows connected.
- At least one forecast has been persisted.
- Browser zoom is 100% and viewport is at least 1440×900.
- Keep OpenAPI and this guide available as fallback evidence.

