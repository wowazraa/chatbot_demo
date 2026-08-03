"""Geriye dönük uyumluluk — app.core.config kullanın."""

from app.core.config import (  # noqa: F401
    ROOT,
    active_paths,
    load_router_config,
    save_router_config,
)

__all__ = ["ROOT", "active_paths", "load_router_config", "save_router_config"]
