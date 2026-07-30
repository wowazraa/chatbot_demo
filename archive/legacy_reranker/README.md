# Legacy reranker scripts (archived)

These standalone eval/benchmark scripts imported `src.models.reranker`,
`src.smart_gate`, or `src.score_fusion`, which were removed when the
routing architecture was unified on `src/k1_guardrails.py`
(K1 regex fast-path → raw BGE-M3 cosine ≥ 0.65 → reject; no
cross-encoder / reranker / fusion step).

They are kept here for reference only and will not run as-is.

- `benchmark_v2.py`
- `evaluate_reranker_impact.py`
- `evaluate_thresholds_hybrid_1000.py`
- `evaluate_thresholds_reranker_only_1000.py`
- `test_reranker_pipeline.py`
