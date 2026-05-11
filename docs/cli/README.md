# vocr CLI

`vocr` is the CLI-first entry point for VonishOCR. The CLI talks to the local
HTTP service started by `vocr serve`. If a command needs the service and it
is not running, the CLI starts it automatically.

## Install For Development

```bash
pip install -e .
```

On Windows, the repository also ships lightweight launchers:

```powershell
.\vocr.cmd --help
.\vonishocr.cmd --help
.\install-cli.ps1
```

`install-cli.ps1` creates `vocr.cmd` and `vonishocr.cmd` under
`%LOCALAPPDATA%\VonishOCR\bin` and adds that directory to the user PATH.

## Service

```bash
vocr serve --port 8000
vocr serve --foreground
vocr status
vocr stop
```

## Models

```bash
vocr list
vocr list --remote
vocr pull rapidocr-mobile-cn
vocr pull cnocr-standard --url https://example.com/model.onnx
vocr rm onnxtr-standard
vocr load cnocr-standard
```

## Language Packs

VonishOCR language packs use a two-level JSON index:

- `resources/langpacks/index.json` is the lightweight navigation index.
- `resources/langpacks/<model-family>/<lang>.json` is the full manifest with
  model files, SHA256, compatibility, license, and mirror URLs.

```bash
vocr lang list
vocr lang list --installed
vocr lang show ch
vocr lang pull ch --offline
vocr lang pull en --yes --mirror hf-mirror
vocr lang verify ch
vocr lang rm ch
```

Installed pack state is stored in SQLite under the CLI state directory. Pulling
`ch` currently registers the bundled `rapidocr-mobile-cn` ONNX files, verifies
SHA256, and copies them into `models/langpacks/pp-ocrv5/standard/ch`.

## OCR

```bash
vocr ocr invoice.jpg
vocr ocr scan.png --output result.md
vocr ocr book.pdf --model pro --format json
vocr batch ./invoices --model standard --output ./results
```

## Queue

```bash
vocr queue ls
vocr queue ls --watch
vocr queue cancel <task_id>
vocr queue logs <task_id>
vocr queue clear
```

## Vault

```bash
vocr vault ls
vocr vault search "2024 invoice"
vocr vault export <id> --format md
vocr vault rm <id>
```

## Config And Monitoring

```bash
vocr config get
vocr config set power_mode beast
vocr config reload
vocr metrics
vocr logs --follow
vocr doctor
```

External service APIs under `/api/v1/*` require `X-API-Key`. Local CLI commands
use the `/v1/*` loopback aliases so desktop and SSH workflows remain frictionless.

## Compatibility

`vonishocr` remains a compatibility command and maps to the same CLI entry point as `vocr`. New scripts should use `vocr`.
