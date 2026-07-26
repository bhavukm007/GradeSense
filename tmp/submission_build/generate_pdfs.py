from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.request import urlopen

from PIL import Image
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    Flowable,
    Image as RLImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Submission"
SHOTS = OUT / "screenshots"
OUT.mkdir(exist_ok=True)

RED = colors.HexColor("#E11B22")
INK = colors.HexColor("#111827")
SLATE = colors.HexColor("#475569")
PALE = colors.HexColor("#F8FAFC")
CYAN = colors.HexColor("#06B6D4")
GREEN = colors.HexColor("#10B981")
AMBER = colors.HexColor("#F59E0B")

for name, path in [
    ("Inter", r"C:\Windows\Fonts\arial.ttf"),
    ("InterBold", r"C:\Windows\Fonts\arialbd.ttf"),
    ("Mono", r"C:\Windows\Fonts\consola.ttf"),
    ("MonoBold", r"C:\Windows\Fonts\consolab.ttf"),
]:
    if Path(path).exists():
        pdfmetrics.registerFont(TTFont(name, path))

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="DocTitle", fontName="InterBold", fontSize=28, leading=32, textColor=INK, spaceAfter=14))
styles.add(ParagraphStyle(name="DeckKicker", fontName="InterBold", fontSize=8, leading=10, textColor=RED, tracking=1.4, spaceAfter=6))
styles.add(ParagraphStyle(name="H1x", fontName="InterBold", fontSize=18, leading=22, textColor=INK, spaceBefore=14, spaceAfter=8))
styles.add(ParagraphStyle(name="H2x", fontName="InterBold", fontSize=12, leading=15, textColor=INK, spaceBefore=10, spaceAfter=5))
styles.add(ParagraphStyle(name="Bodyx", fontName="Inter", fontSize=9.4, leading=14, textColor=SLATE, spaceAfter=6))
styles.add(ParagraphStyle(name="Smallx", fontName="Inter", fontSize=7.4, leading=10, textColor=SLATE))
styles.add(ParagraphStyle(name="Whitex", fontName="InterBold", fontSize=10, leading=12, textColor=colors.white, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="Codex", fontName="Mono", fontSize=7.4, leading=10, textColor=colors.HexColor("#D8DEE9")))
styles.add(ParagraphStyle(name="Callout", fontName="InterBold", fontSize=12, leading=16, textColor=INK, leftIndent=8, borderColor=RED, borderWidth=0, borderPadding=8))


def esc(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def bullet(text: str, color=RED) -> Paragraph:
    return Paragraph(f'<font color="{color.hexval()}">●</font>&nbsp;&nbsp;{esc(text)}', styles["Bodyx"])


class BrandHeader(Flowable):
    def __init__(self, title: str, width: float):
        super().__init__()
        self.title = title
        self.width = width
        self.height = 18 * mm

    def draw(self):
        c = self.canv
        c.setFillColor(INK)
        c.roundRect(0, 1 * mm, self.width, 14 * mm, 3 * mm, stroke=0, fill=1)
        c.setFillColor(RED)
        c.rect(0, 1 * mm, 5 * mm, 14 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("InterBold", 12)
        c.drawString(11 * mm, 6 * mm, self.title)
        c.setFont("Inter", 7)
        c.setFillColor(colors.HexColor("#CBD5E1"))
        c.drawRightString(self.width - 7 * mm, 6.2 * mm, "GradeSense | Honeywell Hackathon Submission")


class ArchitectureDiagram(Flowable):
    def __init__(self, nodes, edges, width=170 * mm, height=80 * mm, columns=4):
        super().__init__()
        self.nodes, self.edges, self.width, self.height, self.columns = nodes, edges, width, height, columns

    def draw(self):
        c = self.canv
        rows = (len(self.nodes) + self.columns - 1) // self.columns
        gap = 5 * mm
        bw = (self.width - gap * (self.columns - 1)) / self.columns
        bh = min(19 * mm, (self.height - gap * max(rows - 1, 0)) / max(rows, 1))
        pos = {}
        for idx, (key, label, subtitle, accent) in enumerate(self.nodes):
            row, col = divmod(idx, self.columns)
            x = col * (bw + gap)
            y = self.height - (row + 1) * bh - row * gap
            pos[key] = (x, y, bw, bh)
        c.setStrokeColor(colors.HexColor("#94A3B8"))
        c.setLineWidth(1)
        for src, dst, label in self.edges:
            if src not in pos or dst not in pos:
                continue
            sx, sy, sw, sh = pos[src]
            dx, dy, dw, dh = pos[dst]
            x1, y1 = sx + sw, sy + sh / 2
            x2, y2 = dx, dy + dh / 2
            if abs(y1 - y2) > 2:
                x1, y1 = sx + sw / 2, sy
                x2, y2 = dx + dw / 2, dy + dh
            c.line(x1, y1, x2, y2)
            ang = 3 * mm
            c.line(x2, y2, x2 - ang, y2 + ang / 2)
            c.line(x2, y2, x2 - ang, y2 - ang / 2)
            if label:
                c.setFont("Inter", 6)
                c.setFillColor(SLATE)
                c.drawCentredString((x1 + x2) / 2, (y1 + y2) / 2 + 2, label)
        for key, label, subtitle, accent in self.nodes:
            x, y, w, h = pos[key]
            c.setFillColor(PALE)
            c.setStrokeColor(colors.HexColor("#CBD5E1"))
            c.roundRect(x, y, w, h, 3 * mm, stroke=1, fill=1)
            c.setFillColor(accent)
            c.roundRect(x, y, 3 * mm, h, 1.5 * mm, stroke=0, fill=1)
            c.setFillColor(INK)
            c.setFont("InterBold", 8)
            c.drawString(x + 7 * mm, y + h - 7 * mm, label[:32])
            c.setFillColor(SLATE)
            c.setFont("Inter", 6.5)
            c.drawString(x + 7 * mm, y + 5 * mm, subtitle[:43])


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
    canvas.line(doc.leftMargin, 12 * mm, A4[0] - doc.rightMargin, 12 * mm)
    canvas.setFont("Inter", 7)
    canvas.setFillColor(SLATE)
    canvas.drawString(doc.leftMargin, 7.5 * mm, "GradeSenseAI - Industrial paper grade transition intelligence")
    canvas.drawRightString(A4[0] - doc.rightMargin, 7.5 * mm, f"{doc.page}")
    canvas.restoreState()


def build_pdf(filename: str, title: str, subtitle: str, story, pagesize=A4):
    path = OUT / filename
    doc = SimpleDocTemplate(
        str(path),
        pagesize=pagesize,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="GradeSense Team",
        subject=subtitle,
    )
    cover = [
        Spacer(1, 22 * mm),
        Paragraph("HONEYWELL HACKATHON | FINAL SUBMISSION", styles["DeckKicker"]),
        Paragraph(title, styles["DocTitle"]),
        Paragraph(subtitle, ParagraphStyle("sub", parent=styles["Bodyx"], fontSize=13, leading=18, textColor=SLATE)),
        Spacer(1, 12 * mm),
        Table(
            [[Paragraph("GRADE", styles["Whitex"]), Paragraph("SENSE", styles["Whitex"]), Paragraph("AI", styles["Whitex"])]],
            colWidths=[38 * mm] * 3,
            rowHeights=[20 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), RED),
                ("BACKGROUND", (1, 0), (1, 0), INK),
                ("BACKGROUND", (2, 0), (2, 0), CYAN),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0, colors.white),
            ]),
        ),
        Spacer(1, 14 * mm),
        Paragraph(
            "Explainable predictions, constraint-aware recommendations, and real-time operations for safer, faster paper grade transitions.",
            styles["Callout"],
        ),
        Spacer(1, 48 * mm),
        Paragraph("Prepared from the validated GradeSense v0.2.0 source repository and live application.", styles["Smallx"]),
        PageBreak(),
    ]
    doc.build(cover + story, onFirstPage=footer, onLaterPages=footer)
    return path


def section(title, paragraphs=(), bullets=()):
    body = [BrandHeader(title, 174 * mm), Spacer(1, 4 * mm)]
    body += [Paragraph(p, styles["Bodyx"]) for p in paragraphs]
    body += [bullet(b) for b in bullets]
    return body


def tech_documentation():
    story = []
    story += section("Executive Summary", [
        "GradeSenseAI is an operator-facing industrial intelligence platform for paper-mill grade transitions. It combines snapshot prediction, sequential basis-weight forecasting, explainable AI, safe intervention simulation, persistent recommendations, alerts, and operational governance in one deployable system.",
        "The platform is advisory by design: every action is constraint-checked, model-simulated, ranked by expected improvement, explained in operational language, and preserved for later effectiveness analysis."
    ], [
        "Decision support spans live sensing, inference, recommendation, operator action, and outcome learning.",
        "REST and WebSocket interfaces support both deliberate workflows and continuous streaming.",
        "Immutable model artifacts, audit logs, health checks, and registry controls support production readiness."
    ])
    story += section("Problem Statement", [
        "Paper grade transitions are multivariable, time-dependent processes. Operators must stabilize basis weight and quality while machine speed, moisture, stock flow, steam pressure, temperature, pulp consistency, and grade-specific targets change together.",
        "The objective is to reduce off-spec production and stabilization time without replacing operator authority."
    ])
    story += section("Existing Challenges", bullets=[
        "Delayed detection: conventional thresholds react after deviation is visible.",
        "Fragmented context: sensor trends, model confidence, and historical outcomes live in separate views.",
        "Unsafe optimization: an apparently beneficial set-point change can violate process constraints.",
        "Low trust: black-box predictions do not explain why risk changed or what to do next.",
        "Weak learning loop: accepted recommendations and observed outcomes are rarely measured together."
    ])
    story += section("Proposed Solution", [
        "GradeSense fuses typed FastAPI services, a React operations console, persisted operational history, and two model families. Snapshot intelligence estimates current transition quality, off-spec risk, and stabilization; sequential forecasting projects basis-weight trajectory and detects specification crossing."
    ], [
        "Generate only feasible intervention candidates.",
        "Simulate each candidate with the active forecast model.",
        "Rank improvements deterministically by crossing risk, peak deviation, and stabilization.",
        "Expose feature-level reasons and confidence instead of opaque scores.",
        "Stream predictions, alerts, drift, and recommendations to the dashboard."
    ])
    story += section("System Architecture")
    story.append(ArchitectureDiagram(
        [
            ("ui", "React UI", "Operations + admin console", CYAN),
            ("api", "FastAPI", "Typed REST + WebSocket", RED),
            ("svc", "Domain services", "Inference + intervention", AMBER),
            ("db", "SQL database", "History + governance", GREEN),
            ("stream", "Stream worker", "Bounded replay + events", CYAN),
            ("models", "Model artifacts", "Read-only joblib bundles", RED),
            ("registry", "Model registry", "Checksums + promotion", AMBER),
            ("ops", "Operations", "Metrics + audit + export", GREEN),
        ],
        [("ui", "api", "REST / WS"), ("api", "svc", ""), ("svc", "db", ""), ("stream", "svc", ""), ("svc", "models", ""), ("registry", "models", ""), ("api", "ops", "")],
        height=65 * mm,
    ))
    story += section("ML Pipeline", [
        "The snapshot pipeline validates and preprocesses a transition state, resolves the active model, produces quality/risk/stabilization outputs, and attaches feature-level explanations. The sequential pipeline enforces transition boundaries, builds lag/rolling/rate features, executes direct-horizon regressors, estimates residual intervals, and monitors the ±2.5% specification band."
    ], [
        "Direct-horizon forecasting avoids recursive error accumulation.",
        "Windows never cross transition IDs, protecting temporal validity.",
        "Validation residuals become prediction intervals.",
        "Model and feature-schema checksums make inference reproducible."
    ])
    story += section("Recommendation Engine", [
        "The intervention engine creates one-to-four-variable candidate adjustments from operationally meaningful ranges. A constraint engine rejects unsafe combinations before inference. Surviving candidates are simulated against a persisted baseline and ranked only when they improve the forecast."
    ], [
        "Candidate generation: single-variable and coordinated multivariable actions.",
        "Safety gate: bounds, change magnitude, and incompatible combinations.",
        "Benefit gate: crossing avoidance, lower peak deviation, or faster stabilization.",
        "Lifecycle: proposed, accepted, rejected, modified, delayed, applied, evaluated."
    ])
    story += section("Explainable AI", [
        "GradeSense turns model evidence into operator-facing reasoning. Snapshot explanations surface the most influential variables and their direction. Forecast recommendations state the proposed set-point changes, why they are safe, which risk measure improves, and the expected operational effect.",
        "Confidence, model version, data recency, and drift are visible so the operator can judge when the model should carry less weight."
    ])
    story += section("Dashboard", [
        "The responsive dashboard provides a transition command center, live charts, rolling metrics, alerts, prediction and recommendation workflows, analytics, searchable history, model registry, health, audit, configuration, and export controls."
    ])
    for name in ["Home", "Live_Dashboard", "Prediction", "Recommendation"]:
        path = SHOTS / f"{name}.png"
        if path.exists():
            with Image.open(path) as im:
                w, h = im.size
            story += [Paragraph(name.replace("_", " "), styles["H2x"]), RLImage(str(path), width=174 * mm, height=min(92 * mm, 174 * mm * h / w)), Spacer(1, 3 * mm)]
    story += section("Deployment Architecture")
    story.append(ArchitectureDiagram(
        [
            ("browser", "Mill browser", "Operator experience", CYAN),
            ("proxy", "TLS gateway", "Identity + routing", RED),
            ("front", "Nginx frontend", "Static React bundle", AMBER),
            ("back", "FastAPI/Uvicorn", "REST + WebSocket", RED),
            ("pg", "PostgreSQL", "Durable operations", GREEN),
            ("art", "Read-only artifacts", "Models + datasets", CYAN),
            ("tele", "Telemetry", "Logs + metrics", AMBER),
        ],
        [("browser", "proxy", "HTTPS"), ("proxy", "front", ""), ("proxy", "back", ""), ("back", "pg", ""), ("back", "art", ""), ("back", "tele", "")],
        height=62 * mm,
    ))
    story += section("API Overview", bullets=[
        "System: identity, health, version, OpenAPI.",
        "Intelligence: predict, recommend, correlations, dataset, model, history.",
        "Forecasting: trajectory, history, simulation, relationship discovery.",
        "Interventions: ranked actions, decisions, outcomes, effectiveness.",
        "Real time: alerts, feedback, stream state, rolling/live metrics, drift, WebSockets.",
        "Administration: registry, configuration, metrics, health, audit, exports."
    ])
    story += section("Technologies", bullets=[
        "Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic, Uvicorn.",
        "ML: scikit-learn-compatible joblib artifacts, feature engineering, direct-horizon regression.",
        "Frontend: React 19, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts, Zustand.",
        "Data and deployment: PostgreSQL/SQLite, Docker Compose, Nginx, Render blueprint.",
        "Quality: pytest, Vitest, Ruff, ESLint, health checks, structured logs."
    ])
    story += section("Results", [
        "The implemented submission demonstrates a complete inference-to-action loop rather than a standalone model. Automated test suites cover system APIs, real-time behavior, forecasting, recommendations, interventions, datasets, production readiness, and frontend workflows.",
        "Repository evidence supports the architectural and functional results; the package intentionally avoids inventing plant ROI or model-accuracy figures not present in validated artifacts."
    ])
    story += section("Future Scope", bullets=[
        "Pilot with live PLC/SCADA integration and plant-specific calibration.",
        "Add authenticated roles and an identity-aware gateway.",
        "Move streaming fan-out and rate limits to shared infrastructure for multi-replica scale.",
        "Introduce governed online learning after sufficient evaluated outcomes.",
        "Add fleet-level benchmarking, energy optimization, and prescriptive scheduling."
    ])
    return build_pdf("GradeSense_Technical_Documentation.pdf", "GradeSense Technical Documentation", "Architecture, intelligence workflows, explainability, deployment, and results", story)


def deployment_guide():
    story = []
    story += section("Deployment Overview", [
        "The reference system supports local developer startup, Docker Compose, and a Render blueprint. Production operation requires externally managed TLS, identity, secrets, backups, and telemetry retention."
    ])
    story += section("Backend Setup", bullets=[
        "Create a Python 3.11+ virtual environment inside backend/.",
        "Install the project: python -m pip install -e .",
        "Copy backend/.env.example to backend/.env and set environment-specific values.",
        "Run migrations: alembic upgrade head",
        "Start: uvicorn app.main:app --host 0.0.0.0 --port 8000",
        "Verify: GET /health and GET /admin/health"
    ])
    story += section("Frontend Setup", bullets=[
        "Install Node.js 20+ and run npm install in frontend/.",
        "Set VITE_API_URL=http://localhost:8000 and VITE_WS_URL=ws://localhost:8000.",
        "Development: npm run dev -- --host 0.0.0.0 --port 5173",
        "Production build: npm run build; serve frontend/dist through Nginx."
    ])
    story += section("Docker", [
        "Docker Compose starts PostgreSQL, the FastAPI backend, and the Nginx-served frontend. Model and dataset directories are mounted read-only and PostgreSQL uses a durable named volume."
    ], [
        "Validate: docker compose config --quiet",
        "Start: docker compose up --build -d",
        "Observe: docker compose ps; docker compose logs -f backend",
        "Stop: docker compose down",
        "Do not add --volumes unless database history should be intentionally deleted."
    ])
    story += section("Render Deployment", [
        "The repository render.yaml defines the deployment blueprint. Connect the repository in Render, create services from the blueprint, provision the database, and set all secret variables in the Render dashboard.",
        "Use the backend public URL for VITE_API_URL and the corresponding wss:// URL for VITE_WS_URL. Confirm CORS contains the exact frontend origin."
    ], [
        "Backend build installs the Python project and applies Alembic migrations before serving.",
        "Frontend build compiles the Vite bundle.",
        "Health checks must target /health for the API and /healthz for Nginx."
    ])
    story += section("Environment Variables")
    rows = [["Variable", "Purpose"]] + [
        ["GRADESENSE_ENVIRONMENT", "development, test, staging, production"],
        ["GRADESENSE_DATABASE_URL", "SQLAlchemy database URL"],
        ["GRADESENSE_CORS_ORIGINS", "JSON list of allowed origins"],
        ["GRADESENSE_DATASET_PATH", "Snapshot dataset path"],
        ["GRADESENSE_SEQUENTIAL_DATASET_PATH", "Ordered transition dataset"],
        ["GRADESENSE_MODEL_PATH", "Snapshot model artifact"],
        ["GRADESENSE_FORECAST_MODEL_PATH", "Forecast model artifact"],
        ["GRADESENSE_STREAM_INTERVAL_SECONDS", "Replay cadence"],
        ["GRADESENSE_LOG_LEVEL", "Structured logging level"],
        ["VITE_API_URL", "Browser-visible REST base URL"],
        ["VITE_WS_URL", "Browser-visible WebSocket base URL"],
    ]
    story.append(Table(rows, colWidths=[70 * mm, 100 * mm], repeatRows=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "InterBold"), ("FONTNAME", (0, 1), (-1, -1), "Inter"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("GRID", (0, 0), (-1, -1), .5, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ])))
    story += section("WebSocket Architecture")
    story.append(ArchitectureDiagram(
        [
            ("src", "Sequential source", "Ordered transition samples", CYAN),
            ("worker", "Streaming worker", "Bounded queues", RED),
            ("ai", "AI services", "Predict + forecast", AMBER),
            ("ws", "WebSocket hub", "Event fan-out", GREEN),
            ("ui", "Live dashboard", "Charts + alerts", CYAN),
            ("db", "Database", "History + metrics", GREEN),
        ],
        [("src", "worker", ""), ("worker", "ai", ""), ("ai", "ws", ""), ("ws", "ui", ""), ("ai", "db", "")],
        height=55 * mm, columns=3,
    ))
    story += [Paragraph("WebSocket event envelope", styles["H2x"]), Paragraph('<font face="Mono">{ "event": "prediction", "timestamp": "ISO-8601", "data": { ... } }</font>', styles["Bodyx"])]
    story += section("API Endpoints", bullets=[
        "REST documentation: /docs, /redoc, /openapi.json",
        "Live sockets: /ws/live and /ws/dashboard",
        "Liveness: /health",
        "Deep health: /admin/health",
        "Current stream: /stream/status, /metrics/live, /metrics/rolling",
        "Core inference: /predict, /forecast, /forecast/simulate, /interventions/recommendations"
    ])
    story += section("Reverse Proxy and Scaling", bullets=[
        "Preserve Upgrade and Connection headers for WebSockets.",
        "Use idle timeouts longer than the heartbeat interval.",
        "A single backend replica is the reference because stream state is process-local.",
        "Multi-replica operation requires a shared broker, coordinated ingestion, centralized metrics/rate limiting, and WebSocket fan-out or sticky sessions."
    ])
    story += section("Verification Checklist", bullets=[
        "All four model/data artifacts exist and are readable.",
        "Database migrations are at head.",
        "/health and /admin/health return healthy.",
        "Frontend can call the API with no CORS error.",
        "A browser receives heartbeat and prediction WebSocket events.",
        "Model registry shows active snapshot and forecast artifacts.",
        "Backups, TLS, identity, logs, and secrets are configured before production traffic."
    ])
    return build_pdf("GradeSense_Deployment_Guide.pdf", "GradeSense Deployment Guide", "Local, Docker, Render, WebSocket, and operational deployment", story)


def openapi_schema():
    with urlopen("http://127.0.0.1:8000/openapi.json", timeout=10) as response:
        return json.load(response)


def example_from_schema(schema, components, depth=0):
    if depth > 4:
        return "..."
    if not schema:
        return None
    if "$ref" in schema:
        target = schema["$ref"].split("/")[-1]
        return example_from_schema(components.get(target, {}), components, depth + 1)
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if "enum" in schema:
        return schema["enum"][0]
    for branch in ("anyOf", "oneOf", "allOf"):
        if branch in schema and schema[branch]:
            if branch == "allOf":
                merged = {}
                for child in schema[branch]:
                    val = example_from_schema(child, components, depth + 1)
                    if isinstance(val, dict):
                        merged.update(val)
                return merged
            return example_from_schema(schema[branch][0], components, depth + 1)
    typ = schema.get("type")
    if typ == "object" or "properties" in schema:
        return {k: example_from_schema(v, components, depth + 1) for k, v in list(schema.get("properties", {}).items())[:12]}
    if typ == "array":
        return [example_from_schema(schema.get("items", {}), components, depth + 1)]
    if typ == "integer":
        return 1
    if typ == "number":
        return 0.5
    if typ == "boolean":
        return True
    fmt = schema.get("format")
    if fmt == "date-time":
        return "2026-07-26T12:00:00Z"
    if fmt == "uuid":
        return "00000000-0000-4000-8000-000000000001"
    return "string"


def json_block(obj):
    text = json.dumps(obj, indent=2, ensure_ascii=True)
    if len(text) > 1800:
        text = text[:1750] + "\n  \"...\": \"truncated for readability\"\n}"
    colored = esc(text)
    colored = re.sub(r'(&quot;[^&]+?&quot;)(?=\s*:)', r'<font color="#88C0D0">\1</font>', colored)
    colored = re.sub(r'\b(true|false|null)\b', r'<font color="#A3BE8C">\1</font>', colored)
    return Table([[Paragraph(colored.replace("\n", "<br/>"), styles["Codex"])]], colWidths=[170 * mm], style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#18212F")),
        ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#334155")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))


def api_documentation():
    schema = openapi_schema()
    components = schema.get("components", {}).get("schemas", {})
    story = section("API Conventions", bullets=[
        "Base URL: deployment-specific; local reference http://localhost:8000.",
        "JSON fields use snake_case; timestamps are ISO 8601 UTC; IDs are UUID strings.",
        "Validation failures return 422, missing resources 404, and invalid lifecycle conflicts 409.",
        "Every HTTP response carries X-Request-ID and security headers.",
        "Interactive documentation is available at /docs and /redoc."
    ])
    paths = schema.get("paths", {})
    methods = {"get", "post", "put", "patch", "delete"}
    endpoint_count = 0
    for path, operations in paths.items():
        for method, op in operations.items():
            if method.lower() not in methods:
                continue
            endpoint_count += 1
            story += [BrandHeader(f"{method.upper()} {path}", 174 * mm), Spacer(1, 3 * mm)]
            story.append(Paragraph(esc(op.get("summary") or op.get("operationId") or "Endpoint"), styles["H2x"]))
            if op.get("description"):
                story.append(Paragraph(esc(op["description"]), styles["Bodyx"]))
            params = []
            for p in op.get("parameters", []):
                params.append([p.get("name"), p.get("in"), "yes" if p.get("required") else "no", p.get("description") or p.get("schema", {}).get("type", "")])
            if params:
                story.append(Table([["Parameter", "Location", "Required", "Description"]] + params, colWidths=[38 * mm, 24 * mm, 22 * mm, 86 * mm], repeatRows=1, style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "InterBold"), ("FONTNAME", (0, 1), (-1, -1), "Inter"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7), ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ])))
                story.append(Spacer(1, 3 * mm))
            body = op.get("requestBody", {}).get("content", {}).get("application/json", {})
            if body:
                req = example_from_schema(body.get("schema", {}), components)
                story += [Paragraph("Request example", styles["H2x"]), json_block(req)]
            responses = op.get("responses", {})
            success_code = next((k for k in responses if str(k).startswith("2")), next(iter(responses), "200"))
            response_json = responses.get(success_code, {}).get("content", {}).get("application/json", {})
            resp = example_from_schema(response_json.get("schema", {}), components) if response_json else {"status": success_code}
            story += [Paragraph(f"Response example - HTTP {success_code}", styles["H2x"]), json_block(resp), Spacer(1, 5 * mm)]
    story += [BrandHeader("WebSocket Endpoints", 174 * mm), Spacer(1, 3 * mm)]
    story += [Paragraph("WS /ws/live and WS /ws/dashboard", styles["H2x"]), Paragraph("Both sockets publish the same typed event envelope. The dashboard alias exists for compatibility.", styles["Bodyx"]), json_block({"event": "prediction", "timestamp": "2026-07-26T12:00:00Z", "data": {"quality_score": 0.94, "off_spec_risk": 0.08}})]
    story += [Paragraph("Event names", styles["H2x"])] + [bullet(x) for x in ["system_status, heartbeat, sensor_update, prediction", "recommendation, alert, drift, basis_forecast", "recommendation_created, recommendation_updated, recommendation_decision, recommendation_outcome"]]
    story.insert(0, Paragraph(f"Generated from the live OpenAPI 3 schema. HTTP endpoints documented: {endpoint_count}.", styles["Callout"]))
    return build_pdf("GradeSense_API_Documentation.pdf", "GradeSense API Documentation", "Complete REST and WebSocket reference with generated request/response examples", story)


def architecture_pdf():
    story = []
    diagrams = [
        ("Frontend", [
            ("browser", "Browser", "Responsive operator UI", CYAN), ("router", "React Router", "Lazy route boundaries", RED),
            ("query", "TanStack Query", "Server state + cache", AMBER), ("stores", "Zustand", "Theme + process state", GREEN),
            ("pages", "Workflow pages", "Prediction to governance", CYAN), ("charts", "Recharts", "Trends + correlations", RED),
        ], [("browser", "router", ""), ("router", "pages", ""), ("pages", "query", ""), ("pages", "stores", ""), ("pages", "charts", "")], 3),
        ("Backend", [
            ("mid", "Middleware", "Request ID + security", RED), ("routes", "FastAPI routes", "Typed HTTP contracts", CYAN),
            ("services", "Domain services", "Behavior + orchestration", AMBER), ("schemas", "Pydantic schemas", "Validation + response", GREEN),
            ("orm", "SQLAlchemy", "Persistence boundary", RED), ("audit", "Operations layer", "Audit + metrics + export", CYAN),
        ], [("mid", "routes", ""), ("routes", "services", ""), ("routes", "schemas", ""), ("services", "orm", ""), ("services", "audit", "")], 3),
        ("ML Engine", [
            ("input", "Transition state", "Validated process values", CYAN), ("prep", "Preprocessor", "Schema + features", RED),
            ("model", "Active model", "Resolved immutable artifact", AMBER), ("pred", "Prediction", "Quality + risk + time", GREEN),
            ("xai", "Explainability", "Drivers + direction", CYAN), ("persist", "History", "Inputs + outputs + version", RED),
        ], [("input", "prep", ""), ("prep", "model", ""), ("model", "pred", ""), ("pred", "xai", ""), ("pred", "persist", "")], 3),
        ("Recommendation Engine", [
            ("base", "Baseline forecast", "Persisted trajectory", CYAN), ("cand", "Candidate builder", "1-4 variable actions", RED),
            ("safe", "Constraint gate", "Bounds + combinations", AMBER), ("sim", "Forecast simulation", "Active model", GREEN),
            ("rank", "Benefit ranking", "Crossing + peak + time", CYAN), ("life", "Lifecycle", "Decision + outcome", RED),
        ], [("base", "cand", ""), ("cand", "safe", ""), ("safe", "sim", ""), ("sim", "rank", ""), ("rank", "life", "")], 3),
        ("WebSocket", [
            ("source", "Sequential source", "Ordered replay", CYAN), ("worker", "Streaming worker", "Bounded single writer", RED),
            ("infer", "Inference services", "Predict + forecast", AMBER), ("hub", "Connection manager", "Bounded fan-out", GREEN),
            ("client", "Dashboard clients", "Live charts + alerts", CYAN), ("metrics", "Rolling metrics", "Periodic snapshots", RED),
        ], [("source", "worker", ""), ("worker", "infer", ""), ("infer", "hub", ""), ("hub", "client", ""), ("worker", "metrics", "")], 3),
        ("Database", [
            ("pred", "Prediction history", "Inputs + XAI + model", CYAN), ("rec", "Recommendations", "Actions + rationale", RED),
            ("feedback", "Feedback / alerts", "Operator + events", AMBER), ("forecast", "Forecast history", "Trajectory + crossing", GREEN),
            ("interv", "Interventions", "Simulation + lifecycle", CYAN), ("gov", "Governance", "Models + audit + config", RED),
        ], [("pred", "rec", ""), ("pred", "feedback", ""), ("forecast", "interv", ""), ("rec", "interv", ""), ("interv", "gov", "")], 3),
        ("Inference Flow", [
            ("sample", "Sensor sample", "Current transition", CYAN), ("validate", "Validate", "Types + limits", RED),
            ("feature", "Engineer features", "Snapshot / sequential", AMBER), ("resolve", "Resolve model", "Active checksum", GREEN),
            ("infer", "Infer", "Score + trajectory", CYAN), ("explain", "Explain", "Drivers + confidence", RED),
            ("act", "Recommend", "Constrain + simulate", AMBER), ("stream", "Persist + stream", "UI + history", GREEN),
        ], [("sample", "validate", ""), ("validate", "feature", ""), ("feature", "resolve", ""), ("resolve", "infer", ""), ("infer", "explain", ""), ("explain", "act", ""), ("act", "stream", "")], 4),
    ]
    for idx, (name, nodes, edges, cols) in enumerate(diagrams):
        story += section(name)
        story.append(ArchitectureDiagram(nodes, edges, width=174 * mm, height=72 * mm, columns=cols))
        explanations = {
            "Frontend": "Presentation, routing, server state, local state, and visualization are separated so each workflow stays testable.",
            "Backend": "Routes own transport semantics; services own behavior; schemas and ORM models define explicit contracts.",
            "ML Engine": "Inference is versioned, reproducible, explainable, and persisted with its input context.",
            "Recommendation Engine": "No action reaches an operator until it passes constraints and improves a model-simulated baseline.",
            "WebSocket": "A bounded worker prevents unbounded memory growth and broadcasts typed events to connected clients.",
            "Database": "Operational outcomes remain linked to the predictions and recommendations that produced them.",
            "Inference Flow": "The same governed flow connects a raw process observation to an explainable, advisory action."
        }
        story += [Spacer(1, 5 * mm), Paragraph(explanations[name], styles["Callout"])]
        if idx < len(diagrams) - 1:
            story.append(PageBreak())
    return build_pdf("GradeSense_System_Architecture.pdf", "GradeSense System Architecture", "Seven professional architecture views across UI, services, ML, data, and inference", story)


def code_panel(title, lines):
    colored = []
    keywords = {"class", "def", "async", "await", "return", "if", "for", "in", "from", "import", "raise", "with"}
    for line in lines:
        safe = esc(line)
        for word in keywords:
            safe = re.sub(rf"\b{word}\b", f'<font color="#BF616A"><b>{word}</b></font>', safe)
        safe = re.sub(r'(&quot;.*?&quot;)', r'<font color="#A3BE8C">\1</font>', safe)
        colored.append(safe)
    return KeepTogether([
        Paragraph(title, styles["H2x"]),
        Table([[Paragraph("<br/>".join(colored), styles["Codex"])]], colWidths=[170 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#18212F")),
            ("BOX", (0, 0), (-1, -1), .6, colors.HexColor("#334155")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])),
    ])


def source_documentation():
    story = []
    readme = (ROOT / "README.md").read_text(encoding="utf-8", errors="replace")
    intro = re.sub(r"[#*_`]", "", "\n".join(readme.splitlines()[:18])).strip()
    story += section("README and Product Intent", [
        intro[:1450],
        "This document summarizes the important implementation contracts and selected algorithmic patterns. It intentionally avoids a raw source dump."
    ])
    story += section("Backend Structure", bullets=[
        "app/api/routes: system, intelligence, real-time, forecasting, interventions, and administration.",
        "app/services: behavior for model inference, explainability, recommendations, forecasting, streaming, registry, operations, and constraints.",
        "app/schemas: versioned public request and response contracts.",
        "app/models and app/database: SQLAlchemy entities, sessions, and shared mixins.",
        "alembic: ordered database migrations through operational governance."
    ])
    story.append(code_panel("Service boundary pattern", [
        "route request -> validate schema",
        "resolve dependency -> domain service",
        "service -> active model + persistence boundary",
        "return typed response with request ID",
    ]))
    story += section("Frontend Structure", bullets=[
        "app/App.tsx: lazy route composition inside the shared application shell.",
        "pages/: workflow screens for operations, intelligence, history, and platform administration.",
        "components/: reusable live monitoring, process forms, prediction result, layout, forecast, and UI states.",
        "api/: typed client and shared contracts; hooks/: WebSocket subscription.",
        "stores/: focused Zustand stores for process inputs and theme."
    ])
    story.append(code_panel("Client data flow", [
        "Route -> page component",
        "page -> TanStack query or mutation",
        "typed API client -> REST endpoint",
        "useLiveStream -> WebSocket event reducer",
        "result -> charts, status, explanation, action",
    ]))
    story += section("Major Modules", bullets=[
        "IntelligenceService: readiness, prediction, recommendation, persistence.",
        "ForecastingService: history window, feature construction, direct-horizon trajectory.",
        "InterventionEngine: candidate generation, constraint checks, simulation, ranking, lifecycle.",
        "StreamingService: single-writer replay, bounded queues, typed broadcast, rolling metrics.",
        "ModelRegistryService: immutable registration, checksum validation, promotion, archive.",
        "Operations services: audit, runtime configuration, health, metrics, and export."
    ])
    story += section("Important Algorithms")
    story.append(code_panel("Snapshot inference", [
        "validate(process_state)",
        "features = preprocessor.transform(process_state)",
        "model = registry.resolve_active(kind=\"snapshot\")",
        "prediction = model.predict(features)",
        "explanation = explainability.describe(model, features)",
        "persist(inputs, prediction, explanation, model.version)",
    ]))
    story.append(Spacer(1, 5 * mm))
    story.append(code_panel("Specification crossing", [
        "target_band = target_basis_weight * 0.025",
        "for point in forecast_trajectory:",
        "    deviation = abs(point.basis_weight - target_basis_weight)",
        "    if deviation <= target_band:",
        "        return first_crossing_time",
        "return not_crossed_within_horizon",
    ]))
    story += section("ML Pipeline", bullets=[
        "Snapshot features represent the current grade transition state.",
        "Sequential features add lags, rolling statistics, rates of change, grade pair, and transition stage.",
        "Direct horizon regressors predict each future point without autoregressive feedback.",
        "A crossing classifier and validation residual intervals quantify operational risk.",
        "Transition-ID boundaries reset history so training and inference windows remain valid."
    ])
    story.append(code_panel("Sequential feature window", [
        "assert samples are ordered",
        "assert one transition_id per history window",
        "lags = values[t-k : t]",
        "rolling = mean/std/min/max(lags)",
        "rates = diff(lags) / delta_time",
        "features = concat(lags, rolling, rates, grade_pair, stage)",
    ]))
    story += section("Recommendation Engine", bullets=[
        "Generate meaningful set-point deltas for controllable variables.",
        "Reject out-of-range and incompatible combinations before model execution.",
        "Simulate each safe candidate using the active forecast artifact.",
        "Require a measurable improvement over the persisted baseline.",
        "Rank deterministically and retain the rationale, constraints, model version, decision, and outcome."
    ])
    story.append(code_panel("Constraint-aware ranking", [
        "for candidate in generate_candidates(baseline):",
        "    if not constraints.valid(candidate): continue",
        "    simulated = forecast.simulate(candidate)",
        "    benefit = compare(simulated, baseline)",
        "    if benefit.positive: accepted.append((candidate, benefit))",
        "return sorted(accepted, key=deterministic_priority)",
    ]))
    story += section("Streaming Engine", bullets=[
        "A single background worker reads the next ordered sample at a configurable cadence.",
        "Prediction, recommendation, alert, drift, and basis-forecast events share one envelope.",
        "Client queues and rolling buffers are bounded.",
        "Transition changes clear forecast history to prevent invalid cross-transition windows.",
        "Rolling metrics are periodically persisted for operations and audit."
    ])
    story.append(code_panel("Streaming loop", [
        "while running:",
        "    sample = source.next()",
        "    events = intelligence.evaluate(sample)",
        "    await websocket.broadcast(events)",
        "    rolling.update(sample, events)",
        "    if rolling.snapshot_due: persist(rolling.snapshot())",
    ]))
    story += section("Testing and Maintainability", bullets=[
        "Backend pytest suites cover system, intelligence, real-time, forecasting, recommendations, interventions, datasets, and production readiness.",
        "Frontend Vitest suites cover live monitoring and end-to-end workflow states.",
        "Typed schemas and API client types reduce contract drift.",
        "Services isolate behavior from HTTP details, making algorithm tests deterministic.",
        "Immutable artifacts and audit persistence make operational behavior traceable."
    ])
    return build_pdf("GradeSense_Source_Code_Documentation.pdf", "GradeSense Source Code Documentation", "Curated architecture and syntax-highlighted algorithm documentation", story)


def validate(paths):
    summary = []
    for path in paths:
        reader = PdfReader(str(path))
        if not reader.pages:
            raise RuntimeError(f"No pages: {path}")
        extracted = "".join((page.extract_text() or "") for page in reader.pages)
        if len(extracted) < 250:
            raise RuntimeError(f"Insufficient extractable content: {path}")
        summary.append({"file": path.name, "pages": len(reader.pages), "text_chars": len(extracted), "bytes": path.stat().st_size})
    (OUT / "validation_report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main():
    paths = [
        tech_documentation(),
        deployment_guide(),
        api_documentation(),
        architecture_pdf(),
        source_documentation(),
    ]
    print(json.dumps(validate(paths), indent=2))


if __name__ == "__main__":
    main()
