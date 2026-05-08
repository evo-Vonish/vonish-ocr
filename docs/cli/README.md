# VonishOCR CLI

VonishOCR is moving to a CLI-first architecture. The CLI talks to the local
HTTP service started by `vonishocr serve`. If a command needs the service and it
is not running, the CLI starts it automatically.

## Install For Development

```bash
pip install -e .
```

## Service

```bash
vonishocr serve --port 8000
vonishocr serve --foreground
vonishocr status
vonishocr stop
```

## Models

```bash
vonishocr list
vonishocr list --remote
vonishocr pull rapidocr-mobile-cn
vonishocr pull cnocr-standard --url https://example.com/model.onnx
vonishocr rm onnxtr-standard
vonishocr load cnocr-standard
```

## OCR

```bash
vonishocr ocr invoice.jpg
vonishocr ocr scan.png --output result.md
vonishocr ocr book.pdf --model pro --format json
vonishocr batch ./invoices --model standard --output ./results
```

## Queue

```bash
vonishocr queue ls
vonishocr queue ls --watch
vonishocr queue cancel <task_id>
vonishocr queue logs <task_id>
vonishocr queue clear
```

## Vault

```bash
vonishocr vault ls
vonishocr vault search "2024发票"
vonishocr vault export <id> --format md
vonishocr vault rm <id>
```

## Config And Monitoring

```bash
vonishocr config get
vonishocr config set power_mode beast
vonishocr config reload
vonishocr metrics
vonishocr logs --follow
vonishocr doctor
```

External service APIs under `/api/v1/*` require `X-API-Key`. Local CLI commands
use the `/v1/*` loopback aliases so desktop and SSH workflows remain frictionless.
