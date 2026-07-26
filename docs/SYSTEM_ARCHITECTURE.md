# GradeSenseAI System Architecture

## Overall architecture

```mermaid
flowchart TB
    Operator["Operator / process engineer"] --> Browser["React + TypeScript UI"]
    Browser -->|REST| Middleware["Request ID, limits, security, telemetry"]
    Browser <-->|WebSocket| StreamAPI["Live stream endpoints"]
    Middleware --> API["FastAPI routes"]
    API --> Intelligence["Snapshot intelligence"]
    API --> Forecasting["Sequential forecasting"]
    API --> Intervention["Intervention + constraints"]
    API --> Administration["Registry + config + audit + exports"]
    Intelligence --> Resolver["Active model resolver"]
    Forecasting --> Resolver
    Resolver --> Artifacts[("Read-only joblib artifacts")]
    API --> Persistence["SQLAlchemy session boundary"]
    Persistence --> Database[("PostgreSQL / SQLite")]
    StreamWorker["Streaming worker"] --> Intelligence
    StreamWorker --> Forecasting
    StreamWorker --> StreamAPI
```

## Backend services

```mermaid
flowchart LR
    Routes["Typed route handlers"] --> IntelligenceService
    Routes --> ForecastingService
    Routes --> InterventionEngine
    Routes --> AdminServices["Registry / operations / export"]
    IntelligenceService --> ModelService
    IntelligenceService --> Explainability
    IntelligenceService --> LegacyRecommendations
    ForecastingService --> ForecastArtifactService
    InterventionEngine --> ConstraintEngine
    InterventionEngine --> ForecastingService
    AdminServices --> MetricsService
    AdminServices --> AuditService
    AdminServices --> RuntimeConfigService
    AdminServices --> ModelRegistryService
```

Routes own HTTP semantics; services own behavior; schemas define public contracts; SQLAlchemy models
define persistence. Forecasting and intervention services remain isolated from administrative
concerns except for active artifact resolution.

## Forecast pipeline

```mermaid
flowchart LR
    Samples["Ordered transition samples"] --> Boundary["Transition boundary check"]
    Boundary --> Window["History window"]
    Window --> Features["Lags + rolling stats + rates + grade pair"]
    Features --> Horizon["Direct horizon regressors"]
    Features --> Crossing["Crossing classifier"]
    Horizon --> Residuals["Validation residual intervals"]
    Horizon --> Trajectory["Basis Weight trajectory"]
    Residuals --> Trajectory
    Crossing --> Specification["±2.5% crossing monitor"]
    Trajectory --> Specification
    Specification --> Persist["Forecast + crossing persistence"]
```

## Recommendation pipeline

```mermaid
flowchart LR
    Baseline["Persisted baseline forecast"] --> Candidates["Single + multi-variable candidates"]
    Candidates --> Constraints{"All constraints valid?"}
    Constraints -->|No| Reject["Discard"]
    Constraints -->|Yes| Simulate["Run active forecast model"]
    Simulate --> Compare["Compare crossing, peak deviation, stabilization"]
    Compare --> Positive{"Improves forecast?"}
    Positive -->|No| Reject
    Positive -->|Yes| Rank["Deterministic ranking"]
    Rank --> Recommendation["Persistent proposed recommendation"]
    Recommendation --> Decision["Operator decision"]
    Decision --> Outcome["Future observation evaluation"]
```

## Streaming architecture

```mermaid
sequenceDiagram
    participant Source as Sequential CSV replay
    participant Worker as Streaming worker
    participant AI as Intelligence services
    participant DB as Database
    participant WS as WebSocket clients

    Worker->>Source: Read next ordered sample
    Worker->>AI: Predict and evaluate alerts
    AI->>DB: Persist prediction and recommendation
    Worker->>WS: sensor_update / prediction / recommendation / alert / drift
    alt Complete forecast history window
        Worker->>AI: Forecast trajectory
        Worker->>WS: basis_forecast
    end
    Worker->>DB: Periodic rolling metric snapshots
```

The worker is single-process by design. Its queues are bounded. A transition-ID change clears the
forecast history, preventing windows from crossing grade-transition boundaries.

## Database schema

```mermaid
erDiagram
    MODEL_METADATA {}
    PREDICTION_HISTORY ||--o{ RECOMMENDATION_HISTORY : produces
    PREDICTION_HISTORY ||--o{ OPERATOR_FEEDBACK : receives
    PREDICTION_HISTORY ||--o{ ALERT_HISTORY : triggers
    FORECAST_HISTORY ||--o{ FORECAST_CROSSING_EVENTS : detects
    FORECAST_HISTORY ||--o{ INTERVENTION_SIMULATIONS : simulates
    FORECAST_HISTORY ||--o{ FORECAST_RECOMMENDATIONS : generates
    FORECAST_RECOMMENDATIONS ||--o{ RECOMMENDATION_DECISIONS : records
    FORECAST_RECOMMENDATIONS ||--o| RECOMMENDATION_OUTCOMES : evaluates
    REGISTERED_MODELS {}
    AUDIT_LOGS {}
    RUNTIME_CONFIGURATION {}
    ROLLING_METRIC_SNAPSHOTS {}
    STREAMING_SESSIONS {}
```

UUID primary keys and timestamps are consistent across operational tables. JSON columns retain
model-specific trajectory, metric, explanation, and input structures while indexed relational
columns support identity, state, time, and foreign-key access paths.

## Deployment architecture

```mermaid
flowchart TB
    Client["Mill browser"] --> Proxy["TLS / identity-aware reverse proxy"]
    Proxy --> Nginx["Nginx static frontend"]
    Proxy --> FastAPI["GradeSense FastAPI"]
    FastAPI --> PostgreSQL[("Durable PostgreSQL")]
    FastAPI --> Models["Read-only model mount"]
    FastAPI --> Data["Read-only dataset mount"]
    FastAPI --> Logs["JSON log collector"]
    FastAPI --> Metrics["External metrics collector (future multi-replica)"]
```

Docker Compose implements the single-node reference deployment. Production should provide TLS,
identity, secrets, backups, log retention, and network policy outside the application container.

## Key architectural decisions

- Direct horizon models avoid autoregressive error accumulation and keep inference explainable.
- Model and dataset artifacts are read-only at runtime; missing artifacts fail startup.
- Model versions are immutable and promotion is an atomic registry status change.
- Recommendations are simulated, constrained, explainable, persistent, and advisory.
- Existing snapshot APIs remain separate for backward compatibility.
- In-memory stream/metric buffers are bounded to prevent unbounded process growth.
- Audit persistence is append-only and cannot turn a successful domain response into a failure.
- Operational middleware is centralized so request IDs and security controls cover all HTTP APIs.

