import uuid

from starlette.types import ASGIApp, Receive, Scope, Send

from src.infrastructure.logging import trace_id_var


class TraceIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        trace_id = None
        headers = scope.get("headers", [])
        for key, value in headers:
            if key == b"x-trace-id":
                trace_id = value.decode("utf-8")
                break

        if not trace_id:
            trace_id = str(uuid.uuid4())

        token = trace_id_var.set(trace_id)

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-trace-id", trace_id.encode("utf-8")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            trace_id_var.reset(token)
