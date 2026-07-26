import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const source = "Q:/Programs/GradeSense/Submission/Presentation.pptx";
const output = "Q:/Programs/GradeSense/Submission/Presentation.pptx";
const strip = "Q:/Programs/GradeSense/Submission/deployed_screenshots/Presentation_Screenshot_Strip.png";
const previewDir = "Q:/Programs/GradeSense/tmp/deployed_capture_build/presentation-preview";

await fs.mkdir(previewDir, { recursive: true });
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const slide = presentation.slides.getItem(3);
const body = slide.shapes.items.find((item) => item.name === "TextBox 8");
if (!body) throw new Error("Slide 4 content frame was not found.");

body.text =
  "DEPLOYED APPLICATION · HOME · PREDICTION · RECOMMENDATION · ALERTS · ANALYTICS · HISTORY · SETTINGS";

const bytes = await fs.readFile(strip);
const added = slide.images.add({
  blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
  contentType: "image/png",
  alt: "Seven deployed GradeSense application views: Home, Prediction, Recommendation, Alerts, Analytics, History, and Settings",
  fit: "contain",
  position: { left: 64, top: 307, width: 985.33, height: 105 },
});
if (added) added.name = "Deployed Application Screenshots";

slide.speakerNotes.textFrame.setText(
  "[Sources]\n" +
  "Production deployment: https://gradesense-4weh.onrender.com\n" +
  "Captured routes: /dashboard, /prediction, /recommendations, /analytics, /history/predictions, /admin/config\n" +
  "Captured 2026-07-26."
);
slide.speakerNotes.setVisible(true);

for (let i = 0; i < presentation.slides.items.length; i += 1) {
  const current = presentation.slides.getItem(i);
  const png = await presentation.export({ slide: current, format: "png", scale: 2 });
  await fs.writeFile(
    `${previewDir}/slide-${i + 1}.png`,
    new Uint8Array(await png.arrayBuffer())
  );
}

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(output);
console.log(output);
