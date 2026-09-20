"""HTTP routes for the initial application shell."""

from __future__ import annotations

import time
import uuid
from typing import Any

from flask import Flask, Response, current_app, jsonify, render_template, request, g

from .repositories import NotFound, Repository, RevisionConflict


def register_routes(app: Flask) -> None:
    def repository() -> Repository:
        return current_app.extensions["repository"]

    def payload() -> dict[str, Any]:
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def actor(data: dict[str, Any]) -> str:
        value = data.get("actor") or data.get("creator")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("actor is required")
        return value.strip()

    @app.errorhandler(NotFound)
    def handle_not_found(error: NotFound) -> tuple[Response, int]:
        return jsonify(error="not_found", message=str(error)), 404

    @app.errorhandler(RevisionConflict)
    def handle_conflict(error: RevisionConflict) -> tuple[Response, int]:
        return jsonify(error="conflict", object_type=error.object_type,
                       object_id=error.object_id, current=error.current), 409

    @app.errorhandler(ValueError)
    def handle_bad_request(error: ValueError) -> tuple[Response, int]:
        return jsonify(error="invalid_request", message=str(error)), 400

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

    @app.get("/dashboard")
    def dashboard() -> str:
        return render_template("index.html", app_name=current_app.config["APP_NAME"])

    @app.get("/healthz")
    def healthz() -> Response:
        return jsonify(status="ok")

    @app.get("/api/shortcuts")
    def shortcuts() -> Response:
        return jsonify(shortcuts=current_app.config["SHORTCUTS"])

    @app.get("/api/bundles")
    def list_bundles() -> Response:
        return jsonify(bundles=repository().list_bundles())

    @app.post("/api/bundles")
    def create_bundle() -> tuple[Response, int]:
        data = payload()
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name is required")
        result = repository().create_bundle(
            name=name.strip(), description=data.get("description", ""), creator=actor(data),
            bundle_id=data.get("id"),
        )
        return jsonify(bundle=result), 201

    @app.get("/api/bundles/<bundle_id>")
    def get_bundle(bundle_id: str) -> Response:
        return jsonify(bundle=repository().get_bundle(bundle_id))

    @app.get("/api/bundles/<bundle_id>/streams")
    def list_streams(bundle_id: str) -> Response:
        include_closed = request.args.get("include_closed", "true").lower() not in {"0", "false", "no"}
        streams = repository().list_streams(bundle_id, include_closed=include_closed)
        for stream in streams:
            stream["comments"] = repository().list_comments(stream["id"])
        return jsonify(streams=streams)

    @app.post("/api/bundles/<bundle_id>/streams")
    def create_stream(bundle_id: str) -> tuple[Response, int]:
        data = payload()
        summary = data.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("summary is required")
        result = repository().create_stream(
            bundle_id=bundle_id, summary=summary.strip(), creator=actor(data),
            description=data.get("description", ""), owners=data.get("owners", []),
            priority=data.get("priority"), parent_stream_id=data.get("parent_stream_id"),
            deadline=data.get("deadline"), snooze_until=data.get("snooze_until"),
            tags=data.get("tags", []), stream_id=data.get("id"),
            anchor_stream_id=data.get("anchor_stream_id"), placement=data.get("placement"),
            root_stream_id=data.get("root_stream_id"),
        )
        return jsonify(stream=result), 201

    @app.get("/api/streams/<stream_id>")
    def get_stream(stream_id: str) -> Response:
        stream = repository().get_stream(stream_id)
        stream["comments"] = repository().list_comments(stream_id)
        return jsonify(stream=stream)

    @app.patch("/api/streams/<stream_id>")
    def update_stream(stream_id: str) -> Response:
        data = payload()
        expected_revision = data.get("revision")
        if not isinstance(expected_revision, int):
            raise ValueError("revision is required")
        changes = data.get("changes")
        if not isinstance(changes, dict):
            raise ValueError("changes must be an object")
        return jsonify(stream=repository().update_stream(
            stream_id, expected_revision, actor(data), changes
        ))

    @app.delete("/api/streams/<stream_id>")
    def delete_stream(stream_id: str) -> Response:
        data = payload()
        expected_revision = data.get("revision")
        if not isinstance(expected_revision, int):
            raise ValueError("revision is required")
        return jsonify(deleted_stream=repository().delete_stream(
            stream_id, expected_revision, actor(data)
        ))

    @app.get("/api/streams/<stream_id>/comments")
    def list_comments(stream_id: str) -> Response:
        repository().get_stream(stream_id)
        return jsonify(comments=repository().list_comments(stream_id))

    @app.post("/api/streams/<stream_id>/comments")
    def add_comment(stream_id: str) -> tuple[Response, int]:
        data = payload()
        body = data.get("body")
        if not isinstance(body, str) or not body.strip():
            raise ValueError("body is required")
        result = repository().add_comment(
            stream_id, body, actor(data), comment_id=data.get("id"),
            sticky_note=data.get("sticky_note", False),
        )
        return jsonify(comment=result), 201

    @app.patch("/api/comments/<comment_id>")
    def update_comment(comment_id: str) -> Response:
        data = payload()
        expected_revision = data.get("revision")
        body = data.get("body")
        if not isinstance(expected_revision, int) or not isinstance(body, str):
            raise ValueError("revision and body are required")
        return jsonify(comment=repository().update_comment(
            comment_id, expected_revision, actor(data), body,
            sticky_note=data.get("sticky_note"),
        ))

    @app.delete("/api/comments/<comment_id>")
    def delete_comment(comment_id: str) -> Response:
        data = payload()
        expected_revision = data.get("revision")
        if not isinstance(expected_revision, int):
            raise ValueError("revision is required")
        return jsonify(deleted_comment=repository().delete_comment(
            comment_id, expected_revision, actor(data)
        ))
