from __future__ import annotations

import json
from dataclasses import dataclass, field
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .core import normalize_base_url, responses_url


@dataclass
class ProbeResult:
    ok: bool
    message: str
    protocol: str = ""
    status: int = 0
    models: list[str] = field(default_factory=list)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ProviderProbe:
    def __init__(self, base_url: str, api_key: str, timeout: float = 20):
        self.base_url = normalize_base_url(base_url)
        self.api_key = api_key
        self.timeout = timeout

    def _safe_message(self, value: object) -> str:
        return str(value).replace(self.api_key, "[REDACTED]") if self.api_key else str(value)

    def _request(self, url: str, *, method: str = "GET", payload: dict | None = None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            url,
            method=method,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "CodexProviderSwitcher/0.1",
            },
        )
        # Disable urllib's automatic redirects from the very first request.
        opener = build_opener(NoRedirect())
        for redirect_count in range(6):
            try:
                return opener.open(request, timeout=self.timeout)
            except HTTPError as exc:
                if exc.code not in {301, 302, 303, 307, 308} or not exc.headers.get("Location"):
                    exc.close()
                    raise
                target = urljoin(request.full_url, exc.headers["Location"])
                exc.close()
                validation = self.validate_redirect(target)
                if not validation.ok:
                    raise OSError(validation.message) from exc
                if redirect_count == 5:
                    raise OSError("重定向次数过多，已停止请求") from exc
                # A Responses POST must never silently become a GET.
                if method != "GET" and exc.code not in {307, 308}:
                    raise OSError("POST 请求仅允许 307/308 同源重定向") from exc
                request = Request(target, method=method, data=data, headers=dict(request.headers))

    def validate_redirect(self, target: str) -> ProbeResult:
        source = urlparse(self.base_url)
        destination = urlparse(target)
        def origin(parsed):
            port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
            return (parsed.scheme, parsed.hostname, port)
        try:
            same_origin = not (destination.username or destination.password) and origin(source) == origin(destination)
        except ValueError:
            same_origin = False
        if not same_origin:
            return ProbeResult(False, "已拒绝跨源重定向，防止 API 密钥泄露")
        return ProbeResult(True, "允许同源重定向")

    def list_models(self) -> ProbeResult:
        url = f"{self.base_url}/models"
        try:
            with self._request(url) as response:
                body = json.loads(response.read().decode("utf-8"))
                entries = body.get("data", []) if isinstance(body, dict) else []
                models = [str(entry.get("id")) for entry in entries if isinstance(entry, dict) and entry.get("id")]
                return ProbeResult(True, f"找到 {len(models)} 个模型", "models", response.status, models)
        except Exception as exc:
            return ProbeResult(False, self._safe_message(exc), "models")

    def test_responses(self, model: str) -> ProbeResult:
        payload = {
            "model": model,
            "input": "Reply with exactly: OK",
            "max_output_tokens": 32,
            "stream": False,
        }
        try:
            with self._request(responses_url(self.base_url), method="POST", payload=payload) as response:
                body = json.loads(response.read().decode("utf-8"))
                status = str(body.get("status", "")) if isinstance(body, dict) else ""
                ok = response.status == 200 and status in {"completed", "incomplete"}
                return ProbeResult(ok, f"HTTP {response.status}；响应状态：{status or '未知'}", "responses", response.status)
        except Exception as exc:
            return ProbeResult(False, self._safe_message(exc), "responses")
