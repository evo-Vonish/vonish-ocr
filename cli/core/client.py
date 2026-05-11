import json
import time
from pathlib import Path
from urllib import error, parse, request


class ClientError(RuntimeError):
    pass


class VonishOCRClient:
    def __init__(self, base_url="http://127.0.0.1:8000", api_key=None, timeout=60):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        # urllib 会读取 Windows 系统代理；本 CLI 只访问 localhost，
        # 显式禁用代理，避免本地请求被转发后得到 503/timeout。
        self._opener = request.build_opener(request.ProxyHandler({}))

    def _headers(self, extra=None):
        headers = dict(extra or {})
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def request(self, method, path, *, json_body=None, data=None, headers=None, timeout=None):
        body = data
        req_headers = self._headers(headers)
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        url = self.base_url + path
        req = request.Request(url, data=body, method=method.upper(), headers=req_headers)
        try:
            with self._opener.open(req, timeout=timeout or self.timeout) as resp:
                raw = resp.read()
                ctype = resp.headers.get("content-type", "")
                if "application/json" in ctype:
                    return json.loads(raw.decode("utf-8") or "{}")
                return raw.decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ClientError(f"HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise ClientError(str(exc.reason)) from exc

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def health(self):
        return self.get("/health", timeout=1)

    def submit_ocr(self, file_path, model_tier="auto", priority=0):
        file_path = Path(file_path)
        boundary = f"----vocr-{int(time.time() * 1000)}"
        parts = []

        def add_field(name, value):
            parts.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n".encode("utf-8")
            )

        add_field("model_tier", model_tier)
        add_field("priority", str(priority))
        file_header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
        body = b"".join(parts) + file_header + file_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")
        return self.post("/v1/queue/submit", data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})

    def task(self, task_id):
        return self.get(f"/v1/queue/status/{parse.quote(task_id)}")

    def tasks(self, limit=100):
        return self.get(f"/v1/queue/tasks?limit={int(limit)}")

    def cancel_task(self, task_id):
        return self.post(f"/v1/queue/cancel/{parse.quote(task_id)}")

    def retry_task(self, task_id):
        return self.post(f"/v1/queue/retry/{parse.quote(task_id)}")

    def models(self):
        return self.get("/v1/models")

    def local_models(self):
        return self.get("/v1/models/local")

    def pull_model(self, name, url=None, sha256=None):
        if url:
            qs = parse.urlencode({"name": name, "url": url, **({"sha256": sha256} if sha256 else {})})
            return self.post(f"/v1/models/pull?{qs}", timeout=3600)
        return self.post(f"/v1/models/{parse.quote(name)}/pull", timeout=3600)

    def config(self):
        return self.get("/v1/config")

    def save_config(self, cfg):
        return self.post("/v1/config", json_body=cfg)

    def reload_config(self):
        return self.post("/v1/admin/config/reload")

    def metrics(self):
        return self.get("/metrics")

    def vault_list(self, limit=50, scene=None, search=None):
        params = {"limit": limit}
        if scene:
            params["scene_type"] = scene
        if search:
            params["search"] = search
        return self.get("/vault/evidences?" + parse.urlencode(params))

    def vault_get(self, evidence_id):
        return self.get(f"/vault/evidences/{parse.quote(str(evidence_id))}")

    def vault_delete(self, evidence_id):
        return self.delete(f"/vault/evidences/{parse.quote(str(evidence_id))}")
