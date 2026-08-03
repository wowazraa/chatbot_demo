"""Geriye dönük uyumluluk — app.services.pipeline_service kullanın."""

from app.services.pipeline_service import (  # noqa: F401
    V2IntentPipeline,
    V2PipelineResult,
)

__all__ = ["V2IntentPipeline", "V2PipelineResult"]
