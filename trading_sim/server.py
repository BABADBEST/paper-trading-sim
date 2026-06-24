"""Flask web application – live paper-trading interface."""

from __future__ import annotations

import json
import os
import queue
import threading

from flask import Flask, Response, jsonify, render_template, request

from .live import LiveTradingEngine

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
)

engine = LiveTradingEngine(tick_interval=1.0)


# ---------- SSE price stream ----------
_subscribers: list[queue.Queue[str]] = []
_sub_lock = threading.Lock()


def _broadcast(price: float) -> None:
    snap = engine.snapshot()
    data = json.dumps({"price": round(price, 4), **snap})
    with _sub_lock:
        dead: list[queue.Queue[str]] = []
        for q in _subscribers:
            try:
                q.put_nowait(data)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _subscribers.remove(q)


engine.subscribe(_broadcast)


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/stream")
def stream() -> Response:
    q: queue.Queue[str] = queue.Queue(maxsize=64)
    with _sub_lock:
        _subscribers.append(q)

    def generate():  # type: ignore[override]
        try:
            while True:
                data = q.get()
                yield f"data: {data}\n\n"
        except GeneratorExit:
            with _sub_lock:
                if q in _subscribers:
                    _subscribers.remove(q)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/order", methods=["POST"])
def order() -> tuple[Response, int]:
    body = request.get_json(force=True)
    side = body.get("side")
    qty = int(body.get("qty", 1))
    if side not in ("buy", "sell"):
        return jsonify({"error": "side must be buy or sell"}), 400
    trade = engine.place_order(side, qty)
    if trade is None:
        return jsonify({"error": "order rejected (risk limit or no position)"}), 400
    return jsonify(
        {"side": trade.side, "qty": trade.qty, "price": round(trade.price, 4), "pnl": round(trade.pnl, 4)}
    ), 200


@app.route("/snapshot")
def snapshot() -> tuple[Response, int]:
    return jsonify(engine.snapshot()), 200


@app.route("/reset", methods=["POST"])
def reset() -> tuple[Response, int]:
    engine.stop()
    engine.start(seed_price=100.0)
    return jsonify({"status": "reset"}), 200


def main() -> None:
    engine.start(seed_price=100.0)
    try:
        app.run(host="0.0.0.0", port=5000, threaded=True)
    finally:
        engine.stop()


if __name__ == "__main__":
    main()
