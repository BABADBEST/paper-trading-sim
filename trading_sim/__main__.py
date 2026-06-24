"""Allow running the live server with ``python -m trading_sim``."""

try:
    from .server import main
except ImportError as e:
    raise SystemExit(
        f"Missing dependency: {e.name}\n"
        "Run:  pip install -r requirements.txt"
    ) from e

main()
