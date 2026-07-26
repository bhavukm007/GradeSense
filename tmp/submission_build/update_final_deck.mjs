import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const source = "Q:/Programs/GradeSense/Submission/GradeSense_Presentation.pptx";
const output = "Q:/Programs/GradeSense/Submission/GradeSense_Final_Presentation.pptx";
const preview = "Q:/Programs/GradeSense/tmp/submission_build/final-revised-preview";
const shots = "Q:/Programs/GradeSense/Submission/screenshots";
await fs.mkdir(preview, { recursive: true });

const p = await PresentationFile.importPptx(await FileBlob.load(source));
const NONE = "#00000000";
const INK = "#111827";
const SLATE = "#475569";
const LIGHT = "#F8FAFC";
const RED = "#E11B22";
const CYAN = "#06B6D4";
const GREEN = "#10B981";
const AMBER = "#F59E0B";

function box(slide, x, y, w, h, fill, line = NONE, geometry = "roundRect") {
  return slide.shapes.add({
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: line === NONE ? 0 : 1 },
  });
}

function label(slide, value, x, y, w, h, size = 16, color = INK, bold = false, align = "left") {
  const s = box(slide, x, y, w, h, NONE, NONE, "rect");
  s.text = value;
  s.text.fontSize = size;
  s.text.color = color;
  s.text.bold = bold;
  s.text.typeface = "Arial";
  s.text.alignment = align;
  s.text.verticalAlignment = "middle";
  s.text.insets = { left: 4, right: 4, top: 2, bottom: 2 };
  return s;
}

function clean(slide) {
  box(slide, 42, 125, 1195, 475, "#FFFFFF", NONE, "rect");
}

function setTitle(slide, value) {
  const title = slide.shapes.items.find((item) => item.name === "Title 1");
  if (title) title.text = value;
}

function note(slide, lines) {
  slide.speakerNotes.textFrame.setText(`[Sources]\n${lines.join("\n")}`);
  slide.speakerNotes.setVisible(true);
}

async function image(slide, path, x, y, w, h, alt) {
  const b = await fs.readFile(path);
  slide.images.add({
    blob: b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength),
    contentType: "image/png",
    alt,
    fit: "contain",
    position: { left: x, top: y, width: w, height: h },
    geometry: "roundRect",
    borderRadius: "rounded-lg",
  });
}

{
  const s = p.slides.getItem(0);
  for (const item of s.shapes.items) {
    const value = String(item.text ?? "");
    if (value.includes("GradeSense Team")) {
      item.text = value.replace("GradeSense Team", "Bhavuk Mahajan | GradeSense");
    }
  }
}

// Slide 3: explicit approach choice and comparison.
{
  const s = p.slides.getItem(2);
  setTitle(s, "WHY GRADESENSE IS DIFFERENT");
  clean(s);
  label(s, "WHY THIS APPROACH", 65, 142, 420, 30, 17, RED, true);
  label(s, "Forecast the whole trajectory, then simulate only constraint-valid actions with the same active model.", 65, 180, 430, 100, 24, INK, true);
  label(s, "The result is earlier warning without recursive error accumulation - plus recommendations an operator can verify before acting.", 65, 292, 430, 90, 16, SLATE);
  label(s, "DESIGN ADVANTAGES", 65, 420, 380, 28, 17, RED, true);
  label(s, "• Windows never cross transitions\n• Empirical confidence bands\n• Safety gate before inference\n• Human approval + outcome audit", 65, 455, 430, 112, 16, INK, true);

  label(s, "APPROACH COMPARISON", 545, 142, 630, 30, 17, RED, true);
  const rows = [
    ["Reactive thresholds", "Late", "None", "Low"],
    ["Recursive forecast", "Early", "Error compounds", "Medium"],
    ["Black-box optimizer", "Early", "Needs external guardrails", "Low"],
    ["GradeSense", "Early + 12-step", "Pre-checked + simulated", "High"],
  ];
  [["METHOD",175],["WARNING",170],["ACTION QUALITY",205],["TRUST",80]].reduce((x,[t,w]) => {
    label(s,t,x,184,w,28,12,SLATE,true,t==="TRUST"?"center":"left"); return x+w;
  },555);
  rows.forEach((r,i) => {
    const y = 220 + i * 72;
    const active = i === 3;
    box(s, 545, y, 635, 58, active ? INK : LIGHT, active ? INK : "#E2E8F0");
    label(s,r[0],560,y+7,185,42,14,active?"#FFFFFF":INK,true);
    label(s,r[1],750,y+7,165,42,13,active?"#FFFFFF":SLATE);
    label(s,r[2],915,y+7,195,42,13,active?"#FFFFFF":SLATE);
    label(s,r[3],1110,y+7,58,42,13,active?GREEN:SLATE,true,"center");
  });
  note(s, ["Internal source: docs/MODEL_OVERVIEW.md and backend/app/services/forecasting.", "The comparison is qualitative; no external benchmark is claimed."]);
}

// Slide 5: validated metrics and authentic UI evidence.
{
  const s = p.slides.getItem(4);
  setTitle(s, "VALIDATED ANALYTICS + WORKING PRODUCT");
  clean(s);
  const metrics = [
    ["0.920", "Crossing ROC-AUC", RED],
    ["1.388", "Trajectory MAE", CYAN],
    ["0.962", "Stabilization R²", GREEN],
    ["20,000", "Snapshot records", AMBER],
    ["2,544", "Held-out windows", RED],
  ];
  metrics.forEach(([v,t,c],i) => {
    const x = 55 + i * 225;
    box(s,x,145,210,108,LIGHT,"#E2E8F0");
    label(s,v,x+8,156,194,48,29,c,true,"center");
    label(s,t,x+8,207,194,30,12,SLATE,true,"center");
  });
  label(s,"Validation is grouped by complete transitions: 192 train / 48 held out. Windows never cross transition boundaries.",70,266,1090,42,17,INK,true,"center");
  await image(s,"C:/Users/ASUS/Pictures/Screenshots/Screenshot 2026-07-26 220430.png",55,330,545,210,"GradeSense transition command center");
  await image(s,"C:/Users/ASUS/Pictures/Screenshots/Screenshot 2026-07-26 220623.png",635,330,545,210,"GradeSense ranked recommendation workflow");
  label(s,"REAL-TIME RISK + DRIFT",75,538,300,28,14,RED,true);
  label(s,"RANKED, EXPLAINED ACTIONS",655,538,330,28,14,RED,true);
  note(s, [
    "Internal source: models/grade_transition_model.joblib and models/basis_weight_forecast.joblib.",
    "Metrics: crossing ROC-AUC 0.920313; mean trajectory MAE 1.388263; stabilization R2 0.9622; 20,000 snapshot records; 2,544 validation windows; 192/48 transition split.",
    "Screenshots: Submission/screenshots/Home.png and Recommendation.png.",
  ]);
}

// Slide 6: references and direct access links.
{
  const s = p.slides.getItem(5);
  setTitle(s, "TRY IT, REVIEW IT, BUILD ON IT");
  clean(s);
  label(s,"GradeSense turns model output into safe, explainable, measurable operator action.",75,145,1080,55,24,INK,true,"center");
  const links = [
    ["LIVE PRODUCT","https://gradesense-4weh.onrender.com/",CYAN],
    ["SOURCE CODE","https://github.com/bhavukm007/GradeSense",RED],
    ["API DOCUMENTATION","https://gradesense-api.onrender.com/docs",GREEN],
    ["DEMO VIDEO","https://drive.google.com/file/d/1rCr3CzuCit0O029VzyxIhHoR1lv9E93E/view?usp=sharing",AMBER],
  ];
  links.forEach(([name,url,c],i) => {
    const y = 225 + i * 72;
    box(s,115,y,1025,56,i===0?INK:LIGHT,i===0?INK:"#D7DEE8");
    label(s,name,140,y+7,235,42,15,c,true);
    label(s,url,385,y+7,725,42,14,i===0?"#FFFFFF":INK);
  });
  label(s,"Pilot next: historian integration, mill-specific calibration, identity controls, and measured avoided off-spec production.",105,530,1050,42,16,SLATE,true,"center");
  note(s,links.map(([name,url]) => `${name}: ${url}`));
}

for (let i = 0; i < p.slides.items.length; i += 1) {
  const s = p.slides.getItem(i);
  const png = await p.export({ slide: s, format: "png", scale: 2 });
  await fs.writeFile(`${preview}/slide-${i+1}.png`, new Uint8Array(await png.arrayBuffer()));
}
const montage = await p.export({ format: "png", montage: true, scale: 1 });
await fs.writeFile(`${preview}/montage.png`, new Uint8Array(await montage.arrayBuffer()));
const deck = await PresentationFile.exportPptx(p);
await deck.save(output);
console.log(output);
