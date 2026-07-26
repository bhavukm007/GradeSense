import fs from "node:fs/promises";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT = "Q:/Programs/GradeSense/Submission/GradeSense_Red_Beige_Presentation.pptx";
const PREVIEW = "Q:/Programs/GradeSense/tmp/submission_build/red-beige-preview";
await fs.mkdir(PREVIEW, { recursive: true });

const p = Presentation.create({ slideSize: { width: 1440, height: 810 } });
const CREAM = "#F5EFE6";
const RED = "#B80F36";
const DARK = "#181515";
const MUTED = "#6F625D";
const WHITE = "#FFFDF9";
const GREEN = "#17815D";
const NONE = "#00000000";
const SANS = "Arial";

function rect(slide, x, y, w, h, fill = NONE, line = NONE, radius = "roundRect", width = 1) {
  return slide.shapes.add({
    geometry: radius,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: line === NONE ? 0 : width },
  });
}

function txt(slide, value, x, y, w, h, size = 20, color = DARK, bold = false, align = "left") {
  const s = rect(slide, x, y, w, h, NONE, NONE, "rect");
  s.text = value;
  s.text.fontSize = size;
  s.text.color = color;
  s.text.bold = bold;
  s.text.typeface = SANS;
  s.text.alignment = align;
  s.text.verticalAlignment = "middle";
  s.text.insets = { left: 2, right: 2, top: 1, bottom: 1 };
  return s;
}

function rule(slide, x, y, w, color = RED, h = 3) {
  rect(slide, x, y, w, h, color, NONE, "rect");
}

function chrome(slide, page, section) {
  slide.background.fill = CREAM;
  txt(slide, "GRADESENSE", 54, 24, 180, 22, 11, RED, true);
  txt(slide, section.toUpperCase(), 580, 24, 280, 22, 10, MUTED, true, "center");
  txt(slide, `HONEYWELL HACKATHON  ·  0${page}`, 1135, 24, 250, 22, 10, RED, true, "right");
}

function title(slide, value, y = 68, size = 50, width = 1120) {
  return txt(slide, value, 62, y, width, 100, size, RED, true);
}

function bullet(slide, value, x, y, w, color = DARK, size = 18) {
  txt(slide, "•", x, y, 20, 28, size + 2, RED, true);
  txt(slide, value, x + 24, y, w - 24, 34, size, color, false);
}

function pill(slide, value, x, y, w) {
  rect(slide, x, y, w, 36, RED, RED, "roundRect");
  txt(slide, value, x + 6, y + 2, w - 12, 30, 13, WHITE, true, "center");
}

function arrow(slide, x1, y, x2) {
  rule(slide, x1, y, x2 - x1 - 10, RED, 2);
  rect(slide, x2 - 13, y - 6, 13, 13, RED, NONE, "chevron");
}

function notes(slide, lines) {
  slide.speakerNotes.textFrame.setText(`[Sources]\n${lines.join("\n")}`);
  slide.speakerNotes.setVisible(true);
}

async function addImage(slide, path, x, y, w, h, alt, fit = "contain") {
  const b = await fs.readFile(path);
  slide.images.add({
    blob: b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength),
    contentType: "image/png",
    alt,
    fit,
    position: { left: x, top: y, width: w, height: h },
    geometry: "roundRect",
    borderRadius: "rounded-lg",
  });
}

// 1 - Title
{
  const s = p.slides.add();
  chrome(s, 1, "Industrial AI / Smart Manufacturing");
  txt(s, "AI-POWERED INTELLIGENT PROCESS OPTIMIZATION", 70, 70, 730, 34, 16, RED, true);
  txt(s, "GRADE\nSENSE", 70, 125, 700, 225, 82, RED, true);
  txt(s, "Predict quality. Explain risk. Recommend action.", 76, 370, 650, 50, 25, DARK, true);
  txt(s, "An AI-assisted manufacturing intelligence platform that predicts product quality in real time and recommends safe process adjustments before defects occur.", 76, 430, 620, 105, 19, MUTED);
  rect(s, 855, 96, 475, 535, RED, NONE, "roundRect");
  txt(s, "PREDICT", 930, 155, 320, 60, 34, WHITE, true, "center");
  txt(s, "↓", 980, 225, 220, 52, 35, WHITE, true, "center");
  txt(s, "EXPLAIN", 930, 285, 320, 60, 34, WHITE, true, "center");
  txt(s, "↓", 980, 355, 220, 52, 35, WHITE, true, "center");
  txt(s, "RECOMMEND", 900, 415, 380, 60, 34, WHITE, true, "center");
  txt(s, "HUMAN-IN-THE-LOOP · REAL-TIME · TRACEABLE", 895, 530, 395, 30, 12, CREAM, true, "center");
  rule(s, 76, 580, 620, RED, 2);
  txt(s, "BHAVUK MAHAJAN", 76, 605, 300, 32, 17, DARK, true);
  txt(s, "Candidate ID 20484629  ·  Category: Software", 76, 640, 520, 28, 14, MUTED);
  txt(s, "Honeywell Hackathon · Industrial AI / Smart Manufacturing", 76, 684, 680, 25, 12, RED, true);
  notes(s, ["Internal source: README.md.", "The official Honeywell problem-statement ID and exact title were not present in the supplied files; the slide flags this rather than inventing them."]);
}

// 2 - Problem and idea
{
  const s = p.slides.add();
  chrome(s, 2, "Problem + Idea");
  title(s, "Quality decisions arrive too late");
  txt(s, "CURRENT WORKFLOW", 66, 190, 300, 30, 16, RED, true);
  rect(s, 65, 230, 550, 310, WHITE, RED, "roundRect");
  const current = [
    ["1", "Watch hundreds of changing sensor values"],
    ["2", "Detect drift after quality moves off target"],
    ["3", "Rely on experience to choose an adjustment"],
    ["4", "Inspect output and absorb waste or rework"],
  ];
  current.forEach(([n,t],i) => {
    const y = 257 + i * 66;
    txt(s,n,88,y,40,38,24,RED,true,"center");
    txt(s,t,140,y,430,38,18,DARK,i===3);
  });
  txt(s, "GRADESENSE WORKFLOW", 755, 190, 360, 30, 16, RED, true);
  rect(s, 750, 230, 625, 310, RED, RED, "roundRect");
  const future = [
    ["SENSE", "Continuous process stream"],
    ["PREDICT", "Quality, risk, stabilization"],
    ["EXPLAIN", "Drivers, confidence, drift"],
    ["RECOMMEND", "Safe set-point changes"],
  ];
  future.forEach(([a,b],i) => {
    const y = 252 + i * 66;
    txt(s,a,785,y,175,38,19,WHITE,true);
    txt(s,b,970,y,350,38,17,CREAM);
  });
  txt(s, "WHY IT MATTERS", 65, 590, 250, 30, 16, RED, true);
  pill(s, "BEFORE DEFECTS", 65, 640, 220);
  pill(s, "ACTION, NOT ALERTS", 300, 640, 240);
  pill(s, "EXPLAINED DECISIONS", 555, 640, 260);
  pill(s, "CONTINUOUS LEARNING", 830, 640, 260);
  pill(s, "OPERATOR CONTROL", 1105, 640, 220);
  notes(s, ["Internal source: README.md and docs/DEMO_GUIDE.md.", "Benefits are capability statements, not quantified plant ROI claims."]);
}

// 3 - Technical approach
{
  const s = p.slides.add();
  chrome(s, 3, "Technical Approach");
  title(s, "One governed path from sensor to action");
  const nodes = [
    ["SENSORS", "Live process data"],
    ["PIPELINE", "Validate + engineer"],
    ["PREDICT", "Snapshot + forecast"],
    ["EXPLAIN", "Drivers + confidence"],
    ["RECOMMEND", "Constrain + simulate"],
    ["DASHBOARD", "Decide + learn"],
  ];
  for (let i = 0; i < nodes.length - 1; i++) arrow(s, 105 + i * 215 + 150, 315, 105 + (i + 1) * 215 - 15);
  nodes.forEach(([a,b],i) => {
    const x = 65 + i * 215;
    rect(s,x,245,185,140,i===2||i===4?RED:WHITE,RED,"roundRect",2);
    txt(s,String(i+1).padStart(2,"0"),x+18,260,48,34,20,i===2||i===4?CREAM:RED,true);
    txt(s,a,x+18,300,150,34,17,i===2||i===4?WHITE:DARK,true);
    txt(s,b,x+18,340,150,30,13,i===2||i===4?CREAM:MUTED);
  });
  txt(s, "TECHNOLOGY STACK", 65, 455, 300, 30, 16, RED, true);
  const stacks = [
    ["FRONTEND", "React · TypeScript · Vite"],
    ["BACKEND", "FastAPI · Python · SQLAlchemy"],
    ["ML", "Scikit-learn · Pandas · NumPy"],
    ["REAL TIME", "REST APIs · WebSockets"],
    ["DEPLOY", "Docker · Render · PostgreSQL"],
  ];
  stacks.forEach(([a,b],i) => {
    const x=65+i*260;
    txt(s,a,x,505,230,28,15,RED,true);
    txt(s,b,x,538,230,48,15,DARK);
  });
  rule(s,65,615,1270,RED,2);
  txt(s,"LIVE MONITORING",65,635,220,32,15,RED,true);
  txt(s,"PREDICTIVE ANALYTICS",320,635,250,32,15,RED,true);
  txt(s,"EXPLAINABLE AI",605,635,220,32,15,RED,true);
  txt(s,"RANKED ACTIONS",860,635,220,32,15,RED,true);
  txt(s,"AUDIT + HISTORY",1115,635,220,32,15,RED,true);
  notes(s, ["Internal source: docs/SYSTEM_ARCHITECTURE.md, docs/MODEL_OVERVIEW.md, backend/app, and frontend/src."]);
}

// 4 - Demonstration
{
  const s = p.slides.add();
  chrome(s, 4, "Solution Demonstration");
  title(s, "The closed loop is already working");
  await addImage(s,"C:/Users/ASUS/Pictures/Screenshots/Screenshot 2026-07-26 220430.png",65,175,620,255,"GradeSense live transition command center");
  await addImage(s,"C:/Users/ASUS/Pictures/Screenshots/Screenshot 2026-07-26 220623.png",755,175,620,255,"GradeSense ranked recommendations");
  await addImage(s,"Q:/Programs/GradeSense/docs/screenshots/simulator.png",65,475,620,210,"GradeSense what-if simulator");
  await addImage(s,"Q:/Programs/GradeSense/docs/screenshots/model-registry.png",755,475,620,210,"GradeSense governed model registry");
  txt(s,"LIVE SIGNALS + EARLY RISK",80,425,300,30,15,RED,true);
  txt(s,"EXPLAINED, RANKED ACTIONS",770,425,340,30,15,RED,true);
  txt(s,"WHAT-IF BEFORE APPLYING",80,682,300,30,15,RED,true);
  txt(s,"VERSIONED + AUDITABLE",770,682,300,30,15,RED,true);
  notes(s, ["Internal assets: user-supplied GradeSense screenshots and docs/screenshots/simulator.png, docs/screenshots/model-registry.png.", "No external assets."]);
}

// 5 - Feasibility and impact
{
  const s = p.slides.add();
  chrome(s, 5, "Feasibility + Impact");
  title(s, "Built to deploy - designed to earn trust");
  const metrics = [
    ["0.920", "Crossing ROC-AUC"],
    ["1.388", "Trajectory MAE"],
    ["0.962", "Stabilization R²"],
    ["2,544", "Held-out windows"],
  ];
  metrics.forEach(([v,l],i) => {
    const x=65+i*330;
    txt(s,v,x,185,275,70,44,RED,true);
    txt(s,l,x,250,275,34,16,DARK,true);
    rule(s,x,292,275,RED,2);
  });
  txt(s,"TECHNICALLY FEASIBLE",65,350,330,34,19,RED,true);
  const tech=["Cloud deployed","API-driven modules","Real-time WebSockets","Dockerized services","Versioned model registry"];
  tech.forEach((t,i)=>bullet(s,t,65,400+i*42,390,DARK,17));
  txt(s,"BUSINESS VALUE",520,350,300,34,19,RED,true);
  const val=["Earlier intervention","Faster operator decisions","Lower rejection opportunity","Improved process stability","Higher trust through XAI"];
  val.forEach((t,i)=>bullet(s,t,520,400+i*42,350,DARK,17));
  rect(s,930,345,400,265,RED,RED,"roundRect");
  txt(s,"WHY GRADESENSE?",965,375,325,38,22,WHITE,true);
  txt(s,"PREDICT\n↓\nEXPLAIN\n↓\nRECOMMEND\n↓\nOPTIMIZE",965,425,325,155,23,CREAM,true,"center");
  txt(s,"One unified industrial decision-support platform.",945,625,380,48,17,RED,true,"center");
  notes(s, [
    "Internal source: models/grade_transition_model.joblib and models/basis_weight_forecast.joblib.",
    "Validated metrics: crossing ROC-AUC 0.920313; mean trajectory MAE 1.388263; stabilization R2 0.9622; 2,544 validation windows.",
    "Business benefits are directional opportunities; no plant ROI has been claimed.",
  ]);
}

// 6 - References
{
  const s = p.slides.add();
  chrome(s, 6, "References");
  title(s, "Explore the working submission");
  const refs = [
    ["GITHUB REPOSITORY","https://github.com/bhavukm007/GradeSense"],
    ["LIVE DEPLOYMENT","https://gradesense-4weh.onrender.com/"],
    ["DEMO VIDEO","https://drive.google.com/file/d/1rCr3CzuCit0O029VzyxIhHoR1lv9E93E/view?usp=sharing"],
  ];
  refs.forEach(([a,b],i) => {
    const y=190+i*105;
    rect(s,65,y,915,80,i===0?RED:WHITE,RED,"roundRect",2);
    txt(s,a,90,y+12,260,52,17,i===0?WHITE:RED,true);
    txt(s,b,360,y+12,590,52,15,i===0?CREAM:DARK);
  });
  txt(s,"TECHNOLOGY REFERENCES",1040,190,310,34,18,RED,true);
  ["React","FastAPI","Scikit-learn","Docker","Render","Pandas + NumPy"].forEach((t,i)=>pill(s,t,1040,245+i*48,265));
  rect(s,65,555,1265,105,RED,RED,"roundRect");
  txt(s,"GRADESENSE",95,575,330,55,34,WHITE,true);
  txt(s,"AI-powered intelligent process optimization platform",435,575,820,55,23,CREAM,true);
  txt(s,"Honeywell Hackathon Submission  ·  Bhavuk Mahajan  ·  Candidate ID 20484629",65,690,1265,34,15,MUTED,true,"center");
  notes(s, refs.map(([a,b]) => `${a}: ${b}`).concat(["Technology references are the official project names used in the repository."]));
}

for (let i=0;i<p.slides.items.length;i++) {
  const s=p.slides.getItem(i);
  const png=await p.export({slide:s,format:"png",scale:1.5});
  await fs.writeFile(`${PREVIEW}/slide-${i+1}.png`,new Uint8Array(await png.arrayBuffer()));
  const layout=await s.export({format:"layout"});
  await fs.writeFile(`${PREVIEW}/slide-${i+1}.layout.json`,await layout.text());
}
const deck=await PresentationFile.exportPptx(p);
await deck.save(OUT);
console.log(OUT);
