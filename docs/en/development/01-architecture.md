# Architecture

VonishOCR is built on four layers. Each has a clear boundary. No layer pretends to be magic.

---

## Layer Diagram

```
┌─────────────────────────────────────┐
│  Desktop Shell (Tauri v2 + Rust)    │
│  Window management · System tray    │
│  Python sidecar lifecycle · IPC     │
├─────────────────────────────────────┤
│  Frontend (Vue 3.4 + Vite + Pinia)  │
│  Evidence desk UI · Toast/Dialog    │
│  Theme system · Fluid tokens        │
├─────────────────────────────────────┤
│  Backend (Python 3.12 + FastAPI)    │
│  OCR routes · Batch queue · WS     │
│  AI refiner · Config manager       │
├─────────────────────────────────────┤
│  Engine Layer                       │
│  ONNX Runtime (DirectML)            │
│  OpenCV preprocessing               │
│  Scene classifier (rule-based)      │
└─────────────────────────────────────┘
```

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Tauri over Electron | Smaller binary, lower memory, Rust safety |
| Python sidecar over Rust OCR | Ecosystem maturity; ONNX, OpenCV, RapidOCR |
| DirectML over CUDA | Cross-GPU (NVIDIA, AMD, Intel) |
| CSS Variables over Tailwind | Complete theme control; four-theme system |
| Pinia over Vuex | Smaller API, TypeScript-ready |

---

## Data Flow

1. User drops an image onto the evidence desk
2. Frontend sends base64-encoded image to backend via Tauri IPC or HTTP
3. Backend decodes, classifies scene, runs preprocessing pipeline
4. OCR engine recognizes text via ONNX Runtime (DirectML GPU)
5. AI refiner optionally post-processes low-confidence fields
6. Result returns to frontend with confidence scores, diff records, and scene metadata

---

> Architecture is not a diagram. It is a promise about where the light touches.
