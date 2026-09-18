"""HTTP routes for the initial application shell."""

from __future__ import annotations

import time
import uuid

from flask import Flask, Response, current_app, jsonify, render_template, request, g


def register_routes(app: Flask) -> None:
    @app.before_request
    def assign_request_context() -> None:
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        g.request_started = time.perf_counter()

    @app.after_request
    def log_request(response: Response) -> Response:
        elapsed_ms = (time.perf_counter() - g.request_started) * 1000
        current_app.logger.info(
            "request completed",
            extra={
                "request_id": g.request_id,
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round(elapsed_ms, 2),
            },
        )
        response.headers["X-Request-ID"] = g.request_id
        return response

    @app.get("/")
    def index() -> str:
        return render_template("index.html", app_name=current_app.config["APP_NAME"])

    @app.get("/healthz")
    def healthz() -> Response:
        return jsonify(status="ok")

