# Editions

VonishOCR ships in three forms. One codebase. Three ways to hold the light.

---

## Desktop Edition

The flagship. A Tauri + Vue desktop application for Windows, macOS, and Linux.

- OCR runs locally on DirectML GPU or CPU
- Models managed on-disk, switched at will
- System tray, batch queue, AI polish — all built in
- Files never leave the device

## Web Edition

No install required. Open a browser tab and start recognizing.

- GPU acceleration via Web backend
- 5-10× faster than local CPU inference
- Same preprocessing pipeline and scene classifier
- Ideal for quick jobs and demonstration

## Official API

RESTful, 7×24, unlimited basic recognition calls.

- `POST /v1/ocr` for single images
- `POST /v1/ocr/batch/json` for batch processing
- WebSocket progress for long-running queues
- One line of Python to integrate into your toolchain

---

> Three forms. One promise: the light stays in your hand.
