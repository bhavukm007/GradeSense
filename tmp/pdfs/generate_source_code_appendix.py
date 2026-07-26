from __future__ import annotations

import html
import re
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(r"Q:\Programs\GradeSense")
OUTPUT = ROOT / "Submission" / "Source_Code.pdf"

for name, path in [
    ("Arial", r"C:\Windows\Fonts\arial.ttf"),
    ("ArialBold", r"C:\Windows\Fonts\arialbd.ttf"),
    ("Consolas", r"C:\Windows\Fonts\consola.ttf"),
    ("ConsolasBold", r"C:\Windows\Fonts\consolab.ttf"),
]:
    pdfmetrics.registerFont(TTFont(name, path))

INK = colors.HexColor("#0F172A")
SLATE = colors.HexColor("#475569")
MUTED = colors.HexColor("#64748B")
RED = colors.HexColor("#E11B22")
CYAN = colors.HexColor("#06B6D4")
PALE = colors.HexColor("#F8FAFC")
CODE_BG = colors.HexColor("#111827")
CODE_TEXT = "#E5E7EB"
CODE_KEYWORD = "#F87171"
CODE_STRING = "#86EFAC"
CODE_COMMENT = "#94A3B8"
CODE_NUMBER = "#67E8F9"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverKicker", fontName="ArialBold", fontSize=8, leading=10, textColor=RED, tracking=1.5))
styles.add(ParagraphStyle(name="CoverTitle", fontName="ArialBold", fontSize=28, leading=33, textColor=INK, spaceAfter=10))
styles.add(ParagraphStyle(name="CoverSub", fontName="Arial", fontSize=12, leading=18, textColor=SLATE))
styles.add(ParagraphStyle(name="ModulePath", fontName="ConsolasBold", fontSize=8, leading=10, textColor=RED, spaceAfter=4))
styles.add(ParagraphStyle(name="ModuleTitle", fontName="ArialBold", fontSize=19, leading=23, textColor=INK, spaceAfter=9))
styles.add(ParagraphStyle(name="H2", fontName="ArialBold", fontSize=10, leading=13, textColor=INK, spaceBefore=7, spaceAfter=3))
styles.add(ParagraphStyle(name="Body", fontName="Arial", fontSize=8.7, leading=13, textColor=SLATE, spaceAfter=4))
styles.add(ParagraphStyle(name="Small", fontName="Arial", fontSize=7, leading=9.5, textColor=MUTED))
styles.add(ParagraphStyle(name="CodeX", fontName="Consolas", fontSize=6.7, leading=8.6, textColor=colors.HexColor(CODE_TEXT)))
styles.add(ParagraphStyle(name="Tree", fontName="Consolas", fontSize=8.2, leading=12, textColor=INK))
styles.add(ParagraphStyle(name="White", fontName="ArialBold", fontSize=9, leading=11, textColor=colors.white))


def safe(text: str) -> str:
    return html.escape(text, quote=False)


def highlight_line(line: str, language: str) -> str:
    escaped = safe(line).replace(" ", "&nbsp;")
    comment_at = escaped.find("#" if language == "python" else "//")
    comment = ""
    if comment_at >= 0:
        comment = escaped[comment_at:]
        escaped = escaped[:comment_at]

    string_pattern = r"(&quot;.*?&quot;|&#x27;.*?&#x27;|`.*?`)"
    escaped = re.sub(string_pattern, rf'<font color="{CODE_STRING}">\1</font>', escaped)
    keywords = (
        r"\b(async|await|class|def|return|if|else|elif|for|while|in|from|import|"
        r"with|as|raise|yield|try|except|finally|const|let|function|interface|"
        r"export|new|switch|case|break|continue|true|false|None|True|False)\b"
    )
    escaped = re.sub(keywords, rf'<font color="{CODE_KEYWORD}"><b>\1</b></font>', escaped)
    escaped = re.sub(r"\b(\d+(?:\.\d+)?)\b", rf'<font color="{CODE_NUMBER}">\1</font>', escaped)
    if comment:
        escaped += f'<font color="{CODE_COMMENT}">{comment}</font>'
    return escaped or "&nbsp;"


def code_block(code: str, language: str):
    lines = [highlight_line(line.rstrip(), language) for line in code.strip("\n").splitlines()]
    content = "<br/>".join(lines)
    return Table(
        [[Paragraph(content, styles["CodeX"])]],
        colWidths=[170 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#334155")),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        ),
    )


def pill(text: str):
    return Table(
        [[Paragraph(safe(text), styles["Small"])]],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        ),
    )


def bullet(text: str):
    return Paragraph(f'<font color="#E11B22">●</font>&nbsp;&nbsp;{safe(text)}', styles["Body"])


def module_page(module):
    story = [
        Paragraph(module["path"], styles["ModulePath"]),
        Paragraph(module["title"], styles["ModuleTitle"]),
        Table(
            [
                [
                    Paragraph("<b>PURPOSE</b><br/>" + safe(module["purpose"]), styles["Body"]),
                    Paragraph("<b>ARCHITECTURAL ROLE</b><br/>" + safe(module["role"]), styles["Body"]),
                ]
            ],
            colWidths=[84 * mm, 84 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PALE),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        ),
        Spacer(1, 4 * mm),
        Paragraph("Inputs", styles["H2"]),
    ]
    story += [bullet(value) for value in module["inputs"]]
    story += [Paragraph("Outputs", styles["H2"])]
    story += [bullet(value) for value in module["outputs"]]
    story += [Paragraph("Algorithms and control flow", styles["H2"])]
    story += [bullet(value) for value in module["algorithms"]]
    story += [Paragraph("Major functions", styles["H2"])]
    function_cells = [pill(value) for value in module["functions"]]
    story.append(Table([function_cells], colWidths=[170 * mm / len(function_cells)] * len(function_cells), style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2)])))
    story += [Spacer(1, 4 * mm), Paragraph("Representative implementation", styles["H2"]), code_block(module["code"], module["language"])]
    return story


MODULES = [
    {
        "path": "backend/app/main.py",
        "title": "Application bootstrap and lifecycle",
        "purpose": "Creates the FastAPI application, registers cross-cutting middleware, verifies required intelligence artifacts, and owns startup/shutdown of the streaming worker.",
        "role": "Composition root. It is deliberately thin so transport configuration and lifecycle coordination remain separate from domain behavior.",
        "inputs": ["Validated Settings object loaded from environment.", "Database session factory and model/data artifact paths.", "FastAPI lifespan events."],
        "outputs": ["Configured FastAPI application.", "Startup and shutdown audit events.", "Running and cleanly stopped streaming service."],
        "algorithms": ["Fail-fast readiness check prevents implicit training during startup.", "Bootstrap immutable model registry entries before accepting traffic.", "Dispose database engine only after the stream worker is stopped."],
        "functions": ["lifespan()", "create_application()", "app"],
        "language": "python",
        "code": """@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with SessionFactory() as session:
        IntelligenceService(settings, session).ensure_ready()
        ModelRegistryService().bootstrap_existing(session, settings)
        AuditService().record(session, "application_startup", "application")
    stream = get_streaming_service(settings)
    await stream.start()
    yield
    await stream.stop()
    dispose_engine()""",
    },
    {
        "path": "backend/app/api/router.py",
        "title": "API route composition",
        "purpose": "Combines system, intelligence, forecasting, intervention, real-time, and administration route groups into one public API surface.",
        "role": "Transport boundary. Route modules own HTTP semantics while services own behavior.",
        "inputs": ["Typed APIRouter instances from six bounded route modules."],
        "outputs": ["One api_router attached to the FastAPI application."],
        "algorithms": ["Deterministic router registration keeps endpoint ownership explicit.", "No business logic is executed in the composition layer."],
        "functions": ["include_router()", "api_router"],
        "language": "python",
        "code": """api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(intelligence_router)
api_router.include_router(realtime_router)
api_router.include_router(forecasting_router)
api_router.include_router(intervention_router)
api_router.include_router(administration_router)""",
    },
    {
        "path": "backend/app/services/intelligence.py",
        "title": "Snapshot intelligence orchestration",
        "purpose": "Coordinates prediction, explanation, recommendation, dataset analytics, and persistence for the current transition state.",
        "role": "Application service linking typed process inputs to model inference and durable history.",
        "inputs": ["ProcessInput containing current and target grades plus process variables.", "Active snapshot model artifact.", "SQLAlchemy session."],
        "outputs": ["PredictionResponse and RecommendationResponse.", "Persisted prediction/recommendation history.", "Correlation, model, and dataset summaries."],
        "algorithms": ["Convert validated schema to feature dictionary.", "Infer, explain, persist, then round only at the response boundary.", "Use a lock only for explicit offline regeneration/training."],
        "functions": ["ensure_ready()", "predict()", "recommend()", "correlations()", "prediction_history()"],
        "language": "python",
        "code": """def predict(self, process_input: ProcessInput) -> PredictionResponse:
    values = process_input.model_dump()
    prediction = self.model_service.predict(values)
    explanation = self.explainability_service.explain(values, prediction)
    artifact = self.model_service.load()
    history = PredictionHistory(
        model_version=artifact["version"],
        input_data=values,
        quality_score=prediction.quality_score,
        explanation=explanation.model_dump(mode="json"),
    )
    self.session.add(history)
    self.session.commit()
    return PredictionResponse(prediction_id=history.id, explanation=explanation)""",
    },
    {
        "path": "backend/app/services/model.py",
        "title": "Snapshot model artifact service",
        "purpose": "Loads, caches, trains, validates, and executes the snapshot model pipeline for quality, off-spec probability, and stabilization time.",
        "role": "Model boundary isolating joblib artifacts and scikit-learn details from application services.",
        "inputs": ["Process feature dictionary.", "Persisted joblib pipeline and metadata.", "Training dataframe for explicit offline regeneration."],
        "outputs": ["ModelPrediction with three operational targets.", "Versioned artifact metadata and checksums."],
        "algorithms": ["Resolve a cached artifact under a re-entrant lock.", "Transform categorical and numeric process features through one pipeline.", "Use immutable metadata to trace dataset checksum, metrics, and version."],
        "functions": ["load()", "predict()", "train()", "latest_metadata()"],
        "language": "python",
        "code": """def predict(self, values: dict[str, Any]) -> ModelPrediction:
    artifact = self.load()
    frame = pd.DataFrame([values], columns=artifact["feature_columns"])
    prediction = artifact["pipeline"].predict(frame)[0]
    return ModelPrediction(
        quality_score=float(prediction[0]),
        off_spec_probability=float(np.clip(prediction[1], 0.0, 1.0)),
        stabilization_time=max(0.0, float(prediction[2])),
    )""",
    },
    {
        "path": "backend/app/services/explainability.py",
        "title": "Explainable AI service",
        "purpose": "Converts model feature evidence into ranked, operator-readable drivers with direction and contextual interpretation.",
        "role": "Trust layer between numerical inference and human decision support.",
        "inputs": ["Validated process values.", "ModelPrediction.", "Model feature importances and baseline statistics."],
        "outputs": ["Structured explanation with influential variables, direction, magnitude, and narrative."],
        "algorithms": ["Compare normalized feature deviation against artifact baselines.", "Weight deviation by model importance.", "Rank by absolute contribution and retain the most relevant drivers."],
        "functions": ["explain()", "_feature_contributions()", "_narrative()"],
        "language": "python",
        "code": """contributions = []
for feature, value in numeric_values.items():
    baseline = artifact["baselines"][feature]
    scale = max(abs(baseline["std"]), 1e-6)
    deviation = (float(value) - baseline["mean"]) / scale
    contribution = deviation * importances.get(feature, 0.0)
    contributions.append((feature, contribution))

ranked = sorted(contributions, key=lambda item: abs(item[1]), reverse=True)""",
    },
    {
        "path": "backend/app/services/recommendation.py",
        "title": "Snapshot recommendation search",
        "purpose": "Evaluates targeted process adjustments against the active snapshot model and retains only candidates that improve the multi-objective baseline.",
        "role": "Advisory search engine for immediate, explainable operator guidance.",
        "inputs": ["Current process state.", "Baseline model prediction.", "Candidate deltas and valid operating bounds."],
        "outputs": ["Ranked Recommendation objects with confidence, expected improvement, variables, and inference sources."],
        "algorithms": ["Generate controlled single-variable candidates.", "Re-run model inference for each candidate.", "Score quality gain, risk reduction, and stabilization improvement.", "Reject non-positive candidates; deterministically rank survivors."],
        "functions": ["recommend()", "_candidate_changes()", "_objective()", "_text()"],
        "language": "python",
        "code": """for variable, delta in self._candidate_changes(values):
    candidate = dict(values)
    candidate[variable] = candidate[variable] + delta
    prediction = self.model_service.predict(candidate)
    improvement = self._objective(prediction) - self._objective(baseline)
    if improvement <= 0:
        continue
    recommendations.append(
        Recommendation(expected_improvement=improvement,
                       affected_variables=[variable])
    )""",
    },
    {
        "path": "backend/app/services/forecasting/features.py",
        "title": "Sequential feature engineering",
        "purpose": "Builds leakage-safe temporal features for direct-horizon basis-weight forecasting.",
        "role": "Pure feature layer shared by training and inference.",
        "inputs": ["Ordered SequencePoint history from one transition.", "Configured history window and forecast horizon."],
        "outputs": ["Lag values, rolling statistics, rates of change, grade-pair encoding, and transition-stage features."],
        "algorithms": ["Reject windows crossing transition boundaries.", "Compute lags and rolling aggregates over recent values.", "Calculate time-aware first differences.", "Attach categorical transition context."],
        "functions": ["build_feature_row()", "validate_transition_window()", "feature_names()"],
        "language": "python",
        "code": """transition_ids = {point.transition_id for point in history}
if len(transition_ids) != 1:
    raise ValueError("Forecast windows cannot cross transition boundaries.")

for lag in range(1, history_window + 1):
    row[f"basis_weight_lag_{lag}"] = basis[-lag]
row["basis_weight_mean"] = float(np.mean(basis))
row["basis_weight_std"] = float(np.std(basis))
row["basis_weight_rate"] = (basis[-1] - basis[-2]) / elapsed_minutes""",
    },
    {
        "path": "backend/app/services/forecasting/service.py",
        "title": "Direct-horizon forecasting service",
        "purpose": "Generates and persists a future basis-weight trajectory, uncertainty intervals, and specification-crossing state.",
        "role": "Sequential inference orchestrator used by APIs, streaming, and intervention simulation.",
        "inputs": ["Ordered history window.", "Active forecast artifact.", "Target basis weight and specification tolerance."],
        "outputs": ["ForecastResponse containing horizon points, intervals, crossing status, and artifact version."],
        "algorithms": ["Build one feature vector from the bounded history.", "Execute independent horizon regressors to avoid recursive error accumulation.", "Attach residual-based intervals.", "Detect the first point entering the target band."],
        "functions": ["forecast()", "simulate()", "_crossing_event()", "_persist()"],
        "language": "python",
        "code": """features = build_feature_row(history, artifact.history_window)
predicted = [
    model.predict(features)[0]
    for model in artifact.horizon_models
]
trajectory = [
    ForecastPoint(step=step, basis_weight=value,
                  lower=value - residual, upper=value + residual)
    for step, (value, residual) in enumerate(
        zip(predicted, artifact.residual_intervals), start=1
    )
]""",
    },
    {
        "path": "backend/app/services/constraints.py",
        "title": "Operational constraint engine",
        "purpose": "Validates intervention proposals against per-variable limits, change magnitudes, and unsafe combinations before model simulation.",
        "role": "Safety gate separating candidate generation from recommendation ranking.",
        "inputs": ["Baseline process state.", "Proposed one-to-four-variable changes.", "Runtime constraint configuration."],
        "outputs": ["Validated candidate or explicit constraint violations."],
        "algorithms": ["Apply absolute bounds.", "Apply maximum delta from baseline.", "Evaluate coordinated-change rules.", "Fail with structured reasons instead of silently clipping values."],
        "functions": ["validate()", "apply_changes()", "describe_violations()"],
        "language": "python",
        "code": """for variable, proposed in candidate.items():
    rule = self.rules[variable]
    if not rule.minimum <= proposed <= rule.maximum:
        violations.append(f"{variable} outside safe range")
    baseline_value = baseline[variable]
    if abs(proposed - baseline_value) > rule.max_delta:
        violations.append(f"{variable} change exceeds maximum delta")

if violations:
    raise ConstraintViolation(violations)""",
    },
    {
        "path": "backend/app/services/intervention.py",
        "title": "Forecast-backed intervention engine",
        "purpose": "Generates multi-variable interventions, passes them through safety constraints, simulates future outcomes, and persists the recommendation lifecycle.",
        "role": "Primary prescriptive intelligence layer for GradeSense.",
        "inputs": ["Persisted baseline forecast.", "Current process state.", "Constraint configuration and active forecast model."],
        "outputs": ["Ranked proposed interventions.", "Operator decisions, modified actions, and evaluated outcomes."],
        "algorithms": ["Generate single and coordinated candidates.", "Discard unsafe proposals before inference.", "Compare crossing, peak deviation, and stabilization against baseline.", "Retain only strict improvements with deterministic tie-breaking."],
        "functions": ["generate_recommendations()", "record_decision()", "evaluate_outcome()", "effectiveness()"],
        "language": "python",
        "code": """for candidate in self._candidate_sets(process_state):
    validation = self.constraints.validate(process_state, candidate)
    if not validation.valid:
        continue
    simulated = self.forecasting.simulate(history, candidate)
    benefit = self._compare(simulated, baseline)
    if benefit.is_positive:
        accepted.append((candidate, simulated, benefit))

accepted.sort(key=self._ranking_key)""",
    },
    {
        "path": "backend/app/services/streaming.py",
        "title": "Bounded real-time streaming engine",
        "purpose": "Replays ordered process samples, triggers intelligence workflows, maintains bounded operational state, and broadcasts typed WebSocket events.",
        "role": "Single-writer real-time backbone for the live dashboard.",
        "inputs": ["Sequential dataset sample.", "Streaming interval configuration.", "Intelligence, forecasting, alert, and drift services."],
        "outputs": ["sensor_update, prediction, recommendation, alert, drift, basis_forecast, heartbeat, and system_status events."],
        "algorithms": ["Use one asynchronous worker to preserve sample order.", "Clear forecast history when transition ID changes.", "Bound client queues and trend buffers.", "Persist rolling metric snapshots periodically."],
        "functions": ["start()", "stop()", "_run()", "_process_sample()", "broadcast()"],
        "language": "python",
        "code": """async def _run(self) -> None:
    while self._running:
        sample = self.source.next()
        if sample.transition_id != self._active_transition:
            self._history.clear()
            self._active_transition = sample.transition_id
        events = await self._process_sample(sample)
        for event in events:
            await self.connection_manager.broadcast(event)
        await asyncio.sleep(self.interval_seconds)""",
    },
    {
        "path": "backend/app/services/registry.py",
        "title": "Immutable model registry",
        "purpose": "Registers, validates, promotes, resolves, and archives model artifacts with checksum and schema evidence.",
        "role": "Governance boundary controlling which artifact is active for each model kind.",
        "inputs": ["Artifact path and SHA-256.", "Dataset and feature-schema checksums.", "Metrics, algorithm, version, and training metadata."],
        "outputs": ["Registered model records and one active model per kind.", "Audit-friendly promotion/archive history."],
        "algorithms": ["Validate artifact existence and checksum before registration.", "Treat model versions as immutable.", "Promote atomically by retiring the previous active entry.", "Never archive the active model."],
        "functions": ["bootstrap_existing()", "register()", "promote()", "archive()", "resolve_active()"],
        "language": "python",
        "code": """def promote(self, session: Session, model_id: UUID) -> RegisteredModel:
    model = self.get(session, model_id)
    self._validate_artifact(model)
    session.execute(
        update(RegisteredModel)
        .where(RegisteredModel.kind == model.kind)
        .values(status="registered")
    )
    model.status = "active"
    session.commit()
    return model""",
    },
    {
        "path": "backend/app/database/session.py",
        "title": "Database session boundary",
        "purpose": "Centralizes engine creation, transaction-scoped sessions, SQLite compatibility, and deterministic disposal.",
        "role": "Infrastructure adapter used by API dependencies, lifecycle services, tests, and background workers.",
        "inputs": ["GRADESENSE_DATABASE_URL and pool configuration."],
        "outputs": ["SQLAlchemy engine and SessionFactory.", "Yielded request/session dependency."],
        "algorithms": ["Create one configured engine.", "Yield a session and always close it.", "Keep commit ownership inside services so transaction boundaries remain explicit."],
        "functions": ["engine", "SessionFactory", "get_session()", "dispose_engine()"],
        "language": "python",
        "code": """engine = create_engine(settings.database_url, **engine_options)
SessionFactory = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

def get_session() -> Iterator[Session]:
    with SessionFactory() as session:
        yield session

def dispose_engine() -> None:
    engine.dispose()""",
    },
    {
        "path": "frontend/src/api/client.ts",
        "title": "Typed REST and WebSocket client",
        "purpose": "Provides one validated browser-facing API surface for every GradeSense workflow and derives the correct WebSocket endpoint.",
        "role": "Frontend transport adapter shared by pages, hooks, and administration workflows.",
        "inputs": ["VITE_API_URL.", "Typed request bodies and query parameters.", "Fetch responses and structured error envelopes."],
        "outputs": ["Typed Promise results.", "Downloaded export files.", "ws:// or wss:// dashboard URL."],
        "algorithms": ["Reject startup when the API URL is absent.", "Normalize error handling in one request helper.", "Derive secure WebSocket protocol from the REST URL."],
        "functions": ["request<T>()", "api.predict()", "api.forecast()", "api.recommend()", "websocketUrl()"],
        "language": "typescript",
        "code": """async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!response.ok) throw await ApiError.fromResponse(response)
  return response.json() as Promise<T>
}

export const websocketUrl = () => {
  const url = new URL(API_URL)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = '/ws/dashboard'
  return url.toString()
}""",
    },
    {
        "path": "frontend/src/hooks/useLiveStream.ts",
        "title": "Live event reducer and reconnect hook",
        "purpose": "Hydrates the initial live state, connects to WebSocket events, reduces typed messages into UI state, and maintains bounded trend history.",
        "role": "Real-time state adapter feeding the operational dashboard.",
        "inputs": ["REST live metrics and stream status.", "Typed WebSocket event envelope.", "Current sensor sample held in a ref."],
        "outputs": ["Connection state, live metrics, stream status, 30-point trends, and basis forecast."],
        "algorithms": ["Hydrate before socket events arrive.", "Reconnect two seconds after an unexpected close.", "Reduce each event type into the smallest relevant state slice.", "Keep only the latest 30 trend points and 20 alerts."],
        "functions": ["useLiveStream()", "hydrate()", "connect()", "socket.onmessage"],
        "language": "typescript",
        "code": """socket.onmessage = (message) => {
  const event = JSON.parse(message.data) as { event: string; data: unknown }
  if (event.event === 'sensor_update') {
    sensor.current = event.data as ProcessInput
    setLive((current) => ({ ...current, sensor: sensor.current }))
  } else if (event.event === 'prediction') {
    const prediction = event.data as Prediction
    setLive((current) => ({ ...current, prediction }))
    setTrends((current) => [...current.slice(-29), point])
  } else if (event.event === 'alert') {
    setLive((current) => ({
      ...current,
      alerts: [event.data as Alert, ...current.alerts].slice(0, 20),
    }))
  }
}""",
    },
    {
        "path": "frontend/src/app/App.tsx",
        "title": "Route-level application composition",
        "purpose": "Defines lazy-loaded operational, intelligence, history, and platform routes inside one shared application shell.",
        "role": "Frontend composition root and code-splitting boundary.",
        "inputs": ["Browser location and React Router context."],
        "outputs": ["Selected workflow page with shared navigation and suspense fallback."],
        "algorithms": ["Lazy-load each page module.", "Redirect the root to the command center.", "Render one skeleton fallback while route chunks load."],
        "functions": ["App()", "lazy()", "Routes", "Navigate"],
        "language": "typescript",
        "code": """const DashboardPage = lazy(() =>
  import('../pages/DashboardPage').then((module) => ({
    default: module.DashboardPage,
  })),
)

export function App() {
  return (
    <Suspense fallback={<SkeletonGrid />}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/prediction" element={<PredictionPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}""",
    },
    {
        "path": "frontend/src/pages/DashboardPage.tsx",
        "title": "Operational command center",
        "purpose": "Combines real-time monitoring with model, dataset, health, prediction, and recommendation summaries.",
        "role": "Primary operator landing page.",
        "inputs": ["Live WebSocket hook.", "TanStack Query results for model, dataset, health, history, and recommendations."],
        "outputs": ["Live trends, status cards, aggregate metrics, latest prediction, and recent actions."],
        "algorithms": ["Refresh operational queries on independent cadences.", "Calculate averages only over available records.", "Separate loading, error, empty, and success states."],
        "functions": ["DashboardPage()", "average()", "useQuery()"],
        "language": "typescript",
        "code": """const predictions = useQuery({
  queryKey: ['prediction-history', 1, 50],
  queryFn: () => api.predictionHistory(1, 50),
  refetchInterval: 30_000,
})

const rows = predictions.data?.items ?? []
const average = (selector: (row: PredictionHistoryItem) => number) =>
  rows.length
    ? rows.reduce((sum, row) => sum + selector(row), 0) / rows.length
    : 0

return (
  <>
    <LiveMonitoring />
    <MetricCard label="Average Quality" value={average(row => row.quality_score)} />
  </>
)""",
    },
    {
        "path": "frontend/src/pages/PredictionPage.tsx",
        "title": "Prediction workflow",
        "purpose": "Captures process conditions, submits a typed prediction mutation, preserves the submitted baseline, and renders the explanation-aware result.",
        "role": "Operator workflow for deliberate snapshot inference.",
        "inputs": ["ProcessInput state from Zustand.", "Process form submission.", "Prediction API response."],
        "outputs": ["Persisted baseline, invalidated history cache, and visible PredictionResult."],
        "algorithms": ["Keep the form controlled through the shared process store.", "Mutate only on explicit submit.", "Invalidate prediction history after success."],
        "functions": ["PredictionPage()", "useMutation()", "prediction.mutate()"],
        "language": "typescript",
        "code": """const prediction = useMutation({
  mutationFn: api.predict,
  onSuccess: (_, submitted) => {
    setBaseline(submitted)
    setResultVisible(true)
    void queryClient.invalidateQueries({
      queryKey: ['prediction-history'],
    })
  },
})

<ProcessForm
  values={values}
  onChange={setValues}
  onSubmit={(event) => {
    event.preventDefault()
    prediction.mutate(values)
  }}
/>""",
    },
    {
        "path": "frontend/src/pages/RecommendationsPage.tsx",
        "title": "Recommendation workflow",
        "purpose": "Submits current process conditions for model-evaluated intervention search and presents ranked, explainable actions.",
        "role": "Human-in-the-loop decision-support screen.",
        "inputs": ["Current ProcessInput.", "Recommendation API response containing confidence, improvement, variables, and inference sources."],
        "outputs": ["Prioritized recommendation cards and refreshed prediction/recommendation history."],
        "algorithms": ["Convert confidence and expected improvement into display priority.", "Explain why each candidate survived model evaluation.", "Show a positive empty state when no beneficial intervention exists."],
        "functions": ["priority()", "RecommendationsPage()", "useMutation()"],
        "language": "typescript",
        "code": """function priority(item: Recommendation) {
  if (item.confidence >= 0.8 || item.expected_improvement >= 5)
    return 'High'
  if (item.confidence >= 0.65 || item.expected_improvement >= 2)
    return 'Medium'
  return 'Low'
}

const mutation = useMutation({
  mutationFn: api.recommend,
  onSuccess: () => {
    void queryClient.invalidateQueries({
      queryKey: ['recommendation-history'],
    })
  },
})""",
    },
]


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
    canvas.line(doc.leftMargin, 12 * mm, A4[0] - doc.rightMargin, 12 * mm)
    canvas.setFont("Arial", 6.8)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 7.5 * mm, "GradeSense Source Code Technical Appendix")
    canvas.drawRightString(A4[0] - doc.rightMargin, 7.5 * mm, f"{doc.page}")
    canvas.restoreState()


def build():
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="GradeSense Source Code Technical Appendix",
        author="GradeSense Team",
        subject="Curated source code documentation",
    )
    story = [
        Spacer(1, 20 * mm),
        Paragraph("HONEYWELL HACKATHON | TECHNICAL APPENDIX", styles["CoverKicker"]),
        Spacer(1, 4 * mm),
        Paragraph("GradeSense<br/>Source Code Appendix", styles["CoverTitle"]),
        Paragraph(
            "A curated guide to the architecture, contracts, algorithms, major functions, and representative implementation of the GradeSense industrial AI platform.",
            styles["CoverSub"],
        ),
        Spacer(1, 12 * mm),
        Table(
            [[Paragraph("NOT A RAW DUMP", styles["White"]), Paragraph("IMPORTANT MODULES ONLY", styles["White"]), Paragraph("SYNTAX HIGHLIGHTED", styles["White"])]],
            colWidths=[56 * mm] * 3,
            rowHeights=[18 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), RED),
                    ("BACKGROUND", (1, 0), (1, 0), INK),
                    ("BACKGROUND", (2, 0), (2, 0), CYAN),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ]
            ),
        ),
        Spacer(1, 12 * mm),
        Paragraph(
            f"Coverage: {len(MODULES)} core modules across application bootstrap, APIs, machine learning, forecasting, explainability, recommendations, streaming, persistence, and the React frontend.",
            styles["Body"],
        ),
        Paragraph(
            "Snippets are intentionally limited to the lines that best explain each module's design. Ellipses and surrounding boilerplate are omitted.",
            styles["Body"],
        ),
        PageBreak(),
        Paragraph("Repository Structure", styles["ModuleTitle"]),
        Paragraph(
            "The repository follows clear backend, frontend, model, data, documentation, and deployment boundaries.",
            styles["Body"],
        ),
        Spacer(1, 4 * mm),
        Table(
            [[Paragraph(
                """GradeSense/<br/>
├── backend/<br/>
│   ├── app/<br/>
│   │   ├── api/routes/........ HTTP and WebSocket contracts<br/>
│   │   ├── config/............ environment settings<br/>
│   │   ├── database/.......... engine and sessions<br/>
│   │   ├── models/............ SQLAlchemy entities<br/>
│   │   ├── schemas/........... Pydantic contracts<br/>
│   │   └── services/.......... domain and ML behavior<br/>
│   ├── alembic/............... database migrations<br/>
│   └── tests/................. backend verification<br/>
├── frontend/<br/>
│   └── src/<br/>
│       ├── api/............... typed HTTP contracts<br/>
│       ├── app/............... route composition<br/>
│       ├── components/........ reusable UI and live views<br/>
│       ├── hooks/............. WebSocket state<br/>
│       ├── pages/............. operator workflows<br/>
│       └── stores/............ local process state<br/>
├── models/.................... immutable joblib artifacts<br/>
├── data/...................... snapshot and sequential datasets<br/>
├── docs/...................... architecture, API, deployment<br/>
├── scripts/................... explicit offline training<br/>
├── docker-compose.yml<br/>
└── render.yaml""",
                styles["Tree"],
            )]],
            colWidths=[170 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PALE),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ]
            ),
        ),
        Spacer(1, 6 * mm),
        Paragraph("Architectural rule", styles["H2"]),
        bullet("Routes own HTTP semantics; services own behavior; schemas define contracts; models define persistence."),
        bullet("Runtime model and dataset artifacts are read-only; training remains an explicit offline action."),
        bullet("Recommendations are advisory, constraint-checked, explainable, persistent, and measurable."),
        PageBreak(),
    ]

    for index, module in enumerate(MODULES):
        story.extend(module_page(module))
        if index < len(MODULES) - 1:
            story.append(PageBreak())

    story += [
        PageBreak(),
        Paragraph("Cross-Module Execution Flow", styles["ModuleTitle"]),
        Paragraph("The most important runtime path from operator input to persisted, explainable guidance:", styles["Body"]),
        Spacer(1, 5 * mm),
        code_block(
            """React ProcessForm
  -> typed API client
  -> FastAPI route + Pydantic validation
  -> IntelligenceService / ForecastingService
  -> active immutable model artifact
  -> ExplainabilityService
  -> ConstraintEngine
  -> Recommendation / Intervention engine
  -> SQLAlchemy persistence
  -> REST response + WebSocket broadcast
  -> dashboard, history, audit, and outcome evaluation""",
            "text",
        ),
        Spacer(1, 8 * mm),
        Paragraph("Design properties", styles["H2"]),
        bullet("Deterministic: identical model artifact and input schema produce traceable results."),
        bullet("Bounded: stream queues, rolling windows, and dashboard trends cannot grow without limit."),
        bullet("Explainable: influential variables and recommendation rationale accompany numerical output."),
        bullet("Safe: proposed interventions pass explicit constraints before forecast simulation."),
        bullet("Human-controlled: the operator accepts, rejects, modifies, delays, or applies each action."),
        bullet("Observable: health, metrics, audit, model registry, and export endpoints expose operational state."),
        Spacer(1, 8 * mm),
        Paragraph("Document basis", styles["H2"]),
        Paragraph(
            "Generated from the GradeSense source tree in Q:\\Programs\\GradeSense. The appendix summarizes implementation current as of the generated artifact date and does not introduce external code.",
            styles["Body"],
        ),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    reader = PdfReader(str(OUTPUT))
    text_chars = sum(len(page.extract_text() or "") for page in reader.pages)
    if len(reader.pages) < 10 or text_chars < 10000:
        raise RuntimeError(f"Validation failed: pages={len(reader.pages)}, text={text_chars}")
    print({"file": str(OUTPUT), "pages": len(reader.pages), "text_chars": text_chars, "bytes": OUTPUT.stat().st_size})


if __name__ == "__main__":
    build()
