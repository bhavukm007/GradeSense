# Honeywell Round 2 — Three-Minute Judge Walkthrough

## Before the judge arrives

1. Start the Docker Compose stack and open `http://localhost:5173/honeywell-demo`.
2. Confirm that the forecast model and sequential dataset health checks are green.
3. Click **Populate Demo Mode** once. This runs existing inference and lifecycle services only; it
   does not regenerate data, retrain a model, or replace existing records.
4. Confirm the page reports at least three predictions, three recommendations, three decisions,
   and one evaluated outcome.

## Exact three-minute click order

### 0:00–0:25 — Current transition and future risk

Open **Honeywell Demo** from the first sidebar item. Point to:

- Step 1: current grade transition and live Basis Weight;
- Step 2: future Basis Weight trajectory and ±2.5% limits;
- Step 3: crossing probability, predicted crossing step, maximum deviation, and confidence.

Talking point: “The system predicts when Basis Weight will leave the allowed envelope before the
crossing occurs.”

Expected output: a persisted multi-horizon trajectory. If the live replay has not produced one,
click **Populate Demo Mode**.

### 0:25–0:50 — New relationships

Scroll to Step 4. Show lag, nonlinear, and interaction discoveries across early, middle, and late
transition stages. Read one generated sentence, such as “Steam Pressure leads Basis Weight by
approximately 3 timesteps during early transition.”

Talking point: “These relationships are calculated from transition histories; they are not a
hard-coded list.”

Expected output: five top discoveries on this page. Open **Correlations** for the complete Top 10
view and correlation heatmap.

### 0:50–1:35 — Recommendation and stabilization guidance

At Step 5, click **Generate ranked recommendations** if recommendations are not already populated.
Open the first evidence card and point to:

- suggested setpoint and rank;
- crossing-risk and stabilization improvement;
- forecast confidence;
- constraint validation and attributed recipe rule;
- inference-source badges;
- similar-transition count, acceptance rate, and historical effectiveness.

Scroll briefly to **Stabilization Guidance** to compare current and suggested values.

Talking point: “Every candidate is constraint-checked and reforecast. Historical evidence is
advisory and never retrains the model.”

### 1:35–2:10 — Operator decision and outcome

Click **Accept** or **Apply** on a proposed recommendation. Click **Evaluate Outcome** when the
button appears.

Talking point: “The operator remains in control. The response and observed trajectory are
persisted, then compared against the predicted intervention trajectory.”

Expected output: the recommendation becomes evaluated and Step 9 reports an evaluated outcome.

### 2:10–2:35 — Effectiveness and audit

Show Step 9 historical effectiveness and Step 10 audit history.

Talking point: “The system measures crossing avoidance, deviation improvement, stabilization
improvement, and recommendation accuracy rather than assuming its advice worked.”

### 2:35–3:00 — Requirement proof

Expand **How this satisfies the Honeywell Challenge** and read the seven mappings. Finish with:

“GradeSense predicts off-spec Basis Weight, discovers transition relationships, recommends
constraint-valid setpoints, explains every inference source, records operator decisions, and
measures the outcome.”

## Recovery instructions

- **No forecast:** click **Populate Demo Mode**; it creates a forecast from the supplied sequential
  dataset using the active artifact.
- **No recommendations:** click **Generate ranked recommendations**. If no candidate improves that
  forecast, click **Populate Demo Mode** to select a demonstrated transition.
- **Outcome button unavailable:** first click **Accept** or **Apply**.
- **Historical evidence is zero:** click **Populate Demo Mode** once more. The previous evaluated
  recommendation becomes supporting history for the next matching transition.
- **WebSocket disconnected:** the judge workflow still reads persisted REST data. Check the backend
  health page and reload the browser.
- **Backend unavailable:** run `docker compose up --build -d`, then confirm `/health`.
- **UI stale after an action:** refresh the Honeywell Demo page; all records are persistent.

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
