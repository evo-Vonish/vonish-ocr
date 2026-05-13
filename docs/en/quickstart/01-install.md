# Install & Start

Get VonishOCR running on your machine in under three minutes.

---

## Requirements

| Component | Minimum |
|-----------|---------|
| OS | Windows 10/11, macOS 12+, Linux |
| Python | 3.12+ |
| Node.js | 20+ |
| Rust | 1.75+ (desktop edition) |
| GPU | Optional — DirectML for acceleration |

## Installation

### Desktop Edition (Tauri)

```powershell
# Clone
git clone https://github.com/evo-Vonish/vonish-ocr.git
cd VonishOCR

# Install dependencies
scripts/setup_dev.ps1

# Start Vite dev server
node node_modules/vite/bin/vite.js

# In another terminal, start Tauri
cd src-tauri
cargo run
```

### Backend Only (API / Web)

```bash
cd VonishOCR/backend
pip install -r requirements.txt
python main.py
```

The API will be available at `http://127.0.0.1:8000`.

---

## Verify Installation

- [ ] `http://127.0.0.1:1420` shows the evidence desk interface
- [ ] `POST http://127.0.0.1:8000/v1/ocr` returns a recognition result
- [ ] Drag a test image onto the desk — result appears within 3 seconds

If anything fails, see [Troubleshooting](../operations/02-troubleshooting).

---

> Setup is not onboarding. Setup is handing you the lantern. You decide where to point it.
