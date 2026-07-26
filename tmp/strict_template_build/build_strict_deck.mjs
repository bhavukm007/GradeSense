import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const workspace = "Q:/Programs/GradeSense/tmp/strict_template_build";
const starter = `${workspace}/template-starter.pptx`;
const output = "Q:/Programs/GradeSense/Submission/Presentation.pptx";
const previewDir = `${workspace}/final-preview`;
const layoutDir = `${workspace}/final-layout`;

await fs.mkdir(previewDir, { recursive: true });
await fs.mkdir(layoutDir, { recursive: true });

const presentation = await PresentationFile.importPptx(await FileBlob.load(starter));

function find(slide, exactName) {
  const result = slide.shapes.items.find((item) => item.name === exactName);
  if (!result) throw new Error(`Missing inherited element: ${exactName}`);
  return result;
}

function chrome(slide, page) {
  const footer = slide.shapes.items.find((item) => item.name?.startsWith("Footer Placeholder"));
  const number = slide.shapes.items.find((item) => item.name?.startsWith("Slide Number Placeholder"));
  if (!footer || !number) throw new Error(`Missing footer or slide number on slide ${page}`);
  footer.text = "GradeSense Final Submission";
  number.text = String(page);
}

function notes(slide, sources) {
  slide.speakerNotes.textFrame.setText(`[Sources]\n${sources.join("\n")}`);
  slide.speakerNotes.setVisible(true);
}

// Slide 1 - Title
{
  const slide = presentation.slides.getItem(0);
  find(slide, "Subtitle 3").text = "\nGRADESENSE";
  find(slide, "TextBox 6").text =
    "\nExplainable AI for Paper Grade Transitions\n" +
    "Early prediction of off-spec risk\n" +
    "Safe, explainable operator guidance\n" +
    "Honeywell Hackathon | GradeSense Team";
  chrome(slide, 1);
  notes(slide, ["Internal source: README.md", "No external assets or claims."]);
}

// Slide 2 - Problem Statement
{
  const slide = presentation.slides.getItem(1);
  find(slide, "Title 1").text = "\nPROBLEM STATEMENT";
  find(slide, "TextBox 8").text =
    "Paper grade transitions are difficult to stabilize because quality depends on interacting variables over time.\n" +
    "Off-spec behavior is often detected after material has already been produced.\n" +
    "Sensor trends, confidence, alerts, and historical outcomes are fragmented.\n" +
    "Black-box predictions do not explain why risk changed or which action is safe.\n" +
    "GradeSense must predict early, explain clearly, recommend safely, and keep operators in control.";
  chrome(slide, 2);
  notes(slide, ["Internal source: README.md and docs/MODEL_OVERVIEW.md", "No external assets or claims."]);
}

// Slide 3 - Technical Architecture
{
  const slide = presentation.slides.getItem(2);
  find(slide, "Title 1").text = "TECHNICAL ARCHITECTURE";
  find(slide, "TextBox 8").text =
    "React + TypeScript dashboard -> FastAPI REST and WebSocket layer -> domain services\n" +
    "Snapshot ML + direct-horizon forecasting -> explainability + constraint-aware recommendation engine\n" +
    "SQLAlchemy + PostgreSQL/SQLite persist predictions, alerts, decisions, outcomes, audit, and model registry\n" +
    "Docker, Nginx, Alembic, health checks, and read-only model artifacts support deployment";
  chrome(slide, 3);
  notes(slide, ["Internal source: docs/SYSTEM_ARCHITECTURE.md, docker-compose.yml, backend/app, frontend/src", "No external assets or claims."]);
}

// Slide 4 - Dashboard + AI Pipeline
{
  const slide = presentation.slides.getItem(3);
  find(slide, "Title 1").text = "DASHBOARD + AI PIPELINE";
  find(slide, "TextBox 8").text =
    "Dashboard: live trends, off-spec risk, alerts, recommendations, analytics, history, and system health\n" +
    "AI pipeline: validate -> engineer features -> predict/forecast -> explain -> constrain -> simulate -> rank\n" +
    "WebSocket events keep sensor updates, predictions, drift, alerts, and recommendations synchronized";
  chrome(slide, 4);
  notes(slide, ["Internal source: frontend/src/pages, frontend/src/components/live, backend/app/services/streaming.py", "No external assets or claims."]);
}

// Slide 5 - Business Impact + Innovation
{
  const slide = presentation.slides.getItem(4);
  find(slide, "Title 1").text = "BUSINESS IMPACT + INNOVATION";
  find(slide, "TextBox 8").text =
    "Earlier risk visibility supports intervention before quality drift becomes avoidable waste.\n" +
    "Direct-horizon forecasting projects the transition without recursive error accumulation.\n" +
    "Recommendations are constraint-checked and simulated against a persisted baseline.\n" +
    "Explanations, operator decisions, and observed outcomes create an auditable learning loop.";
  chrome(slide, 5);
  notes(slide, ["Internal source: docs/SYSTEM_ARCHITECTURE.md and backend/app/services", "Impact wording is directional; no unvalidated ROI figures are claimed."]);
}

// Slide 6 - Research + References
{
  const slide = presentation.slides.getItem(5);
  find(slide, "Title 1").text = "RESEARCH AND REFERENCES";
  find(slide, "TextBox 8").text =
    "GradeSense repository: README.md | docs/SYSTEM_ARCHITECTURE.md | docs/MODEL_OVERVIEW.md | docs/API_REFERENCE.md | docs/DEPLOYMENT.md | backend/app | frontend/src";
  chrome(slide, 6);
  notes(slide, [
    "Internal source: README.md",
    "Internal source: docs/SYSTEM_ARCHITECTURE.md",
    "Internal source: docs/MODEL_OVERVIEW.md",
    "Internal source: docs/API_REFERENCE.md",
    "Internal source: docs/DEPLOYMENT.md",
    "No external assets or claims.",
  ]);
}

for (let index = 0; index < presentation.slides.items.length; index += 1) {
  const slide = presentation.slides.getItem(index);
  const png = await presentation.export({ slide, format: "png", scale: 2 });
  await fs.writeFile(`${previewDir}/slide-${index + 1}.png`, new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${layoutDir}/slide-${index + 1}.json`, await layout.text(), "utf8");
}

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(output);
console.log(output);
