# Scenarios

VonishOCR is not a general-purpose image tool. It is built for the real world — where paper is creased, ink has faded, and scanners introduce artifacts.

---

## Where It Excels

| Scenario | Why VonishOCR |
|----------|---------------|
| Printed documents | Clean text extraction with layout preservation |
| Handwritten notes | Scene classifier adapts preprocessing for pen strokes |
| Screenshots | Recognized as-is — no unnecessary processing |
| ID cards | Perspective correction + focused ROI cropping |
| Table forms | Line enhancement + structure-aware recognition |
| Outdoor photos | Shadow removal + contrast recovery |
| Low-quality scans | Non-local means denoising + sharpening |
| Exam papers | Line removal to isolate answer text |

---

## Where It Is Honest

VonishOCR marks what it cannot be certain about. Low-confidence predictions appear with a soft cyan border. AI refinement may add a diff record. You always know what the machine saw and what it guessed.

---

> Not every input is clean. That is not a bug. That is the real world.
