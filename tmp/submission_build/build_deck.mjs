import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const workspace = "Q:/Programs/GradeSense/tmp/submission_build";
const starter = `${workspace}/template-starter.pptx`;
const finalPptx = "Q:/Programs/GradeSense/Submission/GradeSense_Final_Presentation.pptx";
const screenshots = "Q:/Programs/GradeSense/Submission/screenshots";
const previewDir = `${workspace}/final-preview`;
const layoutDir = `${workspace}/final-layout`;
await fs.mkdir(previewDir, { recursive: true });
await fs.mkdir(layoutDir, { recursive: true });

async function writeBlob(outputPath, blob) {
  await fs.writeFile(outputPath, new Uint8Array(await blob.arrayBuffer()));
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(starter));
const transparent = "#00000000";
const RED = "#E11B22";
const INK = "#111827";
const SLATE = "#475569";
const LIGHT = "#F8FAFC";
const CYAN = "#06B6D4";
const GREEN = "#10B981";
const AMBER = "#F59E0B";

function shape(slide, x, y, w, h, fill, radius = "roundRect", line = "#D1D5DB", name = "") {
  return slide.shapes.add({
    geometry: radius,
    name,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: line === transparent ? 0 : 1 },
  });
}

function text(slide, value, x, y, w, h, size = 20, color = INK, bold = false, align = "left", name = "") {
  const box = shape(slide, x, y, w, h, transparent, "rect", transparent, name);
  box.text = value;
  box.text.fontSize = size;
  box.text.color = color;
  box.text.bold = bold;
  box.text.typeface = "Arial";
  box.text.alignment = align;
  box.text.verticalAlignment = "middle";
  box.text.insets = { left: 4, right: 4, top: 2, bottom: 2 };
  return box;
}

function line(slide, x, y, w, h = 3, color = "#CBD5E1") {
  return shape(slide, x, y, w, h, color, "rect", transparent);
}

function arrow(slide, x1, y1, x2, y2, color = "#94A3B8") {
  const horizontal = Math.abs(y2 - y1) < Math.abs(x2 - x1);
  if (horizontal) {
    line(slide, Math.min(x1, x2), y1 - 1.5, Math.abs(x2 - x1), 3, color);
    shape(slide, x2 - 8, y2 - 7, 12, 14, color, "chevron", transparent);
  } else {
    line(slide, x1 - 1.5, Math.min(y1, y2), 3, Math.abs(y2 - y1), color);
    shape(slide, x2 - 7, y2 - 8, 14, 12, color, "chevron", transparent).rotation = 90;
  }
}

function node(slide, title, subtitle, x, y, w, h, accent = RED) {
  shape(slide, x, y, w, h, LIGHT, "roundRect", "#CBD5E1");
  shape(slide, x, y, 7, h, accent, "roundRect", transparent);
  text(slide, title, x + 18, y + 9, w - 26, 26, 17, INK, true);
  text(slide, subtitle, x + 18, y + 38, w - 26, h - 45, 11, SLATE, false);
}

function metric(slide, big, label, x, y, w, accent) {
  shape(slide, x, y, w, 112, LIGHT, "roundRect", "#E2E8F0");
  text(slide, big, x + 10, y + 13, w - 20, 48, 30, accent, true, "center");
  text(slide, label, x + 10, y + 64, w - 20, 33, 12, SLATE, true, "center");
}

async function addImage(slide, imagePath, x, y, w, h, alt) {
  const bytes = await fs.readFile(imagePath);
  slide.images.add({
    blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: "image/png",
    alt,
    fit: "contain",
    position: { left: x, top: y, width: w, height: h },
    geometry: "roundRect",
    borderRadius: "rounded-lg",
  });
}

function setSourceNotes(slide, lines) {
  slide.speakerNotes.textFrame.setText(`[Sources]\n${lines.join("\n")}`);
  slide.speakerNotes.setVisible(true);
}

function inherited(slide, name) {
  return slide.shapes.items.find((item) => item.name === name);
}

function rewriteChrome(slide, titleValue, page) {
  const titleShape = inherited(slide, "Title 1");
  if (titleShape) {
    titleShape.text = titleValue;
    titleShape.position = { left: 19.21, top: 12, width: 1152, height: 92 };
  }
  const footer = slide.shapes.items.find((item) => item.name?.startsWith("Footer Placeholder"));
  if (footer) footer.text = "GradeSense | Honeywell Hackathon Final Submission";
  const number = slide.shapes.items.find((item) => item.name?.startsWith("Slide Number Placeholder"));
  if (number) number.text = String(page);
  const body = inherited(slide, "TextBox 8");
  if (body) body.text = [{ runs: [""] }];
  line(slide, 55, 112, 1170, 5, RED);
}

// Slide 1 - minimal title
{
  const slide = presentation.slides.getItem(0);
  inherited(slide, "Subtitle 3").text = "\nGRADESENSE";
  const body = inherited(slide, "TextBox 6");
  body.text = "Explainable AI for safer, faster paper grade transitions\n\nHoneywell Hackathon Final Submission\nIndustrial AI | Software Prototype\nBhavuk Mahajan | GradeSense";
  const footer = slide.shapes.items.find((item) => item.name?.startsWith("Footer Placeholder"));
  if (footer) footer.text = "GradeSense | Honeywell Hackathon Final Submission";
  const number = slide.shapes.items.find((item) => item.name?.startsWith("Slide Number Placeholder"));
  if (number) number.text = "1";
  shape(slide, 700, 165, 490, 370, INK, "roundRect", transparent);
  text(slide, "PREDICT", 740, 205, 410, 45, 27, "#FFFFFF", true, "center");
  arrow(slide, 945, 265, 945, 310, RED);
  text(slide, "EXPLAIN", 740, 315, 410, 45, 27, "#FFFFFF", true, "center");
  arrow(slide, 945, 375, 945, 420, RED);
  text(slide, "RECOMMEND", 740, 425, 410, 45, 27, "#FFFFFF", true, "center");
  text(slide, "Human-in-the-loop • Constraint-aware • Real-time", 735, 492, 420, 28, 12, "#CBD5E1", false, "center");
  setSourceNotes(slide, ["Internal source: GradeSense README.md", "No external claims or assets."]);
}

// Slide 2 - problem / solution
{
  const slide = presentation.slides.getItem(1);
  rewriteChrome(slide, "PREDICT BEFORE QUALITY DRIFTS", 2);
  text(slide, "THE PROBLEM", 70, 145, 350, 35, 18, RED, true);
  text(slide, "Grade transitions are multivariable, time-dependent, and costly when deviation is detected late.", 70, 185, 400, 92, 23, INK, true);
  text(slide, "Operators must connect changing sensor values, future basis-weight behavior, safety constraints, and past outcomes under time pressure.", 70, 295, 400, 120, 16, SLATE);
  text(slide, "THE GRADE SENSE LOOP", 535, 145, 630, 35, 18, RED, true);
  arrow(slide, 680, 242, 775, 242);
  arrow(slide, 910, 242, 1005, 242);
  node(slide, "Sense", "Live process state", 535, 195, 145, 95, CYAN);
  node(slide, "Predict", "Quality, risk, time", 775, 195, 145, 95, RED);
  node(slide, "Act", "Safe ranked guidance", 1005, 195, 160, 95, GREEN);
  arrow(slide, 1085, 315, 1085, 380);
  arrow(slide, 1005, 430, 920, 430);
  arrow(slide, 775, 430, 690, 430);
  node(slide, "Learn", "Decision + outcome", 535, 382, 155, 95, AMBER);
  node(slide, "Explain", "Drivers + confidence", 775, 382, 145, 95, CYAN);
  node(slide, "Simulate", "Forecast under action", 1005, 382, 160, 95, RED);
  text(slide, "One governed system connects detection, explanation, intervention, and measurable learning.", 535, 510, 630, 48, 18, INK, true, "center");
  setSourceNotes(slide, ["Internal source: README.md and docs/SYSTEM_ARCHITECTURE.md", "No external claims or assets."]);
}

// Slide 3 - architecture + AI workflow
{
  const slide = presentation.slides.getItem(2);
  rewriteChrome(slide, "PRODUCTION-READY AI ARCHITECTURE", 3);
  text(slide, "SYSTEM ARCHITECTURE", 70, 142, 500, 30, 17, RED, true);
  arrow(slide, 285, 250, 360, 250);
  arrow(slide, 575, 250, 650, 250);
  arrow(slide, 865, 250, 940, 250);
  node(slide, "React UI", "Operations + governance", 70, 195, 215, 110, CYAN);
  node(slide, "FastAPI", "REST + WebSocket", 360, 195, 215, 110, RED);
  node(slide, "Domain services", "Inference + intervention", 650, 195, 215, 110, AMBER);
  node(slide, "SQL + artifacts", "History + immutable models", 940, 195, 225, 110, GREEN);
  text(slide, "AI WORKFLOW", 70, 345, 500, 30, 17, RED, true);
  const stages = [
    ["1", "Validate", "Typed process state"],
    ["2", "Forecast", "Direct horizon"],
    ["3", "Explain", "Drivers + confidence"],
    ["4", "Constrain", "Safety gate"],
    ["5", "Recommend", "Ranked benefit"],
  ];
  stages.forEach(([n, t, s], i) => {
    const x = 70 + i * 224;
    if (i < stages.length - 1) arrow(slide, x + 186, 458, x + 218, 458, RED);
    shape(slide, x, 395, 186, 128, i === 4 ? INK : LIGHT, "roundRect", i === 4 ? INK : "#CBD5E1");
    text(slide, n, x + 12, 405, 35, 35, 21, i === 4 ? RED : RED, true, "center");
    text(slide, t, x + 42, 406, 128, 35, 18, i === 4 ? "#FFFFFF" : INK, true);
    text(slide, s, x + 16, 453, 154, 44, 12, i === 4 ? "#CBD5E1" : SLATE, false, "center");
  });
  text(slide, "Python • FastAPI • SQLAlchemy • scikit-learn • React • TypeScript • PostgreSQL • Docker", 110, 548, 1060, 30, 15, SLATE, true, "center");
  setSourceNotes(slide, ["Internal source: docs/SYSTEM_ARCHITECTURE.md, backend/app, frontend/src", "No external claims or assets."]);
}

// Slide 4 - XAI / recommendations / impact
{
  const slide = presentation.slides.getItem(3);
  rewriteChrome(slide, "EXPLAINABILITY, SAFETY, AND OUTCOMES", 4);
  text(slide, "EXPLAINABLE AI", 70, 145, 335, 30, 17, RED, true);
  shape(slide, 70, 188, 330, 305, LIGHT, "roundRect", "#CBD5E1");
  text(slide, "Why did risk change?", 92, 208, 285, 34, 20, INK, true);
  [["Moisture", 0.84, RED], ["Steam pressure", 0.68, AMBER], ["Machine speed", 0.52, CYAN]].forEach(([label, score, color], i) => {
    const y = 265 + i * 58;
    text(slide, label, 92, y, 145, 24, 13, SLATE, true);
    line(slide, 235, y + 9, 130, 12, "#E2E8F0");
    line(slide, 235, y + 9, 130 * score, 12, color);
  });
  text(slide, "Feature direction • model version • confidence • drift", 92, 443, 285, 34, 11, SLATE, false, "center");
  text(slide, "RECOMMENDATION ENGINE", 455, 145, 365, 30, 17, RED, true);
  arrow(slide, 565, 258, 620, 258);
  arrow(slide, 730, 258, 785, 258);
  node(slide, "Generate", "1-4 variable actions", 455, 205, 110, 105, CYAN);
  node(slide, "Gate", "Reject unsafe sets", 620, 205, 110, 105, RED);
  node(slide, "Simulate", "Compare to baseline", 785, 205, 125, 105, GREEN);
  text(slide, "Only positive, constraint-valid improvements are ranked for the operator.", 460, 340, 445, 88, 19, INK, true, "center");
  text(slide, "BUSINESS IMPACT", 955, 145, 240, 30, 17, RED, true);
  metric(slide, "EARLIER", "risk detection", 955, 195, 230, RED);
  metric(slide, "SAFER", "set-point guidance", 955, 325, 230, GREEN);
  metric(slide, "TRACEABLE", "decision-to-outcome loop", 955, 455, 230, CYAN);
  text(slide, "Advisory by design: the operator remains in control.", 70, 530, 840, 42, 17, SLATE, true, "center");
  setSourceNotes(slide, ["Internal source: backend/app/services/explainability.py, recommendation.py, intervention.py", "Business-impact wording is directional; no unvalidated ROI figures are claimed."]);
}

// Slide 5 - screenshots
{
  const slide = presentation.slides.getItem(4);
  rewriteChrome(slide, "WORKING DASHBOARD: THE CLOSED LOOP", 5);
  await addImage(slide, `${screenshots}/Home.png`, 55, 140, 565, 200, "GradeSense transition command center");
  await addImage(slide, `${screenshots}/Prediction.png`, 660, 140, 565, 200, "GradeSense prediction center");
  await addImage(slide, `${screenshots}/Recommendation.png`, 55, 365, 565, 200, "GradeSense recommendation center");
  await addImage(slide, `${screenshots}/Analytics.png`, 660, 365, 565, 200, "GradeSense dataset analytics");
  text(slide, "LIVE OPERATIONS", 74, 318, 240, 28, 14, RED, true);
  text(slide, "EXPLAINABLE PREDICTION", 680, 318, 300, 28, 14, RED, true);
  text(slide, "CONSTRAINT-AWARE ACTION", 74, 543, 320, 28, 14, RED, true);
  text(slide, "ANALYTICS + GOVERNANCE", 680, 543, 320, 28, 14, RED, true);
  setSourceNotes(slide, ["Internal source: live local GradeSense application captured 2026-07-26", "Screenshots: Submission/screenshots/Home.png, Prediction.png, Recommendation.png, Analytics.png"]);
}

// Slide 6 - deployment + close
{
  const slide = presentation.slides.getItem(5);
  rewriteChrome(slide, "DEPLOYABLE TODAY; PILOT-READY NEXT", 6);
  text(slide, "DEPLOYMENT ARCHITECTURE", 70, 142, 500, 30, 17, RED, true);
  arrow(slide, 280, 245, 350, 245);
  arrow(slide, 560, 245, 630, 245);
  arrow(slide, 840, 245, 910, 245);
  node(slide, "Mill browser", "Operator experience", 70, 190, 210, 110, CYAN);
  node(slide, "TLS gateway", "Identity + routing", 350, 190, 210, 110, RED);
  node(slide, "React + FastAPI", "Nginx, REST, WebSocket", 630, 190, 210, 110, AMBER);
  node(slide, "PostgreSQL", "Durable history + audit", 910, 190, 230, 110, GREEN);
  line(slide, 70, 340, 1070, 2, "#CBD5E1");
  text(slide, "REFERENCE DELIVERY", 70, 365, 320, 28, 17, RED, true);
  text(slide, "Docker Compose • Render blueprint • Alembic migrations • health checks • read-only model mounts", 70, 405, 480, 92, 17, INK, true);
  text(slide, "PILOT NEXT", 650, 365, 260, 28, 17, RED, true);
  text(slide, "Connect PLC/SCADA data\nCalibrate on plant history\nEnable SSO and governed roles\nMeasure off-spec and stabilization outcomes", 650, 405, 490, 120, 17, INK, true);
  shape(slide, 70, 535, 1070, 42, INK, "roundRect", transparent);
  text(slide, "GradeSense turns model output into safe, explainable, measurable operator action.", 88, 539, 1034, 34, 20, "#FFFFFF", true, "center");
  setSourceNotes(slide, ["Internal source: docker-compose.yml, render.yaml, docs/DEPLOYMENT.md", "No external claims or assets."]);
}

for (let index = 0; index < presentation.slides.items.length; index += 1) {
  const slide = presentation.slides.getItem(index);
  const png = await presentation.export({ slide, format: "png", scale: 2 });
  await writeBlob(`${previewDir}/slide-${index + 1}.png`, png);
  const layout = await slide.export({ format: "layout" });
  await writeBlob(`${layoutDir}/slide-${index + 1}.json`, layout);
}
const montage = await presentation.export({ format: "png", montage: true, scale: 1 });
await writeBlob(`${workspace}/final-montage.png`, montage);
const deck = await PresentationFile.exportPptx(presentation);
await deck.save(finalPptx);
console.log(finalPptx);
