"""PyTorch CPU mikro-optimizasyonları — ortak ayarlar."""

from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def configure_torch_threads(preferred: int = 4) -> int:
    """
    CPU thread bütçesi — aşırı thread thrashing'i keser.
    preferred varsayılan 4; çekirdek sayısından fazla açılmaz.
    """
    import torch

    n = max(1, min(int(preferred), int(os.cpu_count() or preferred)))
    torch.set_num_threads(n)
    # interop düşük tut — tek sorguluk latency için daha iyi
    try:
        torch.set_num_interop_threads(min(2, n))
    except RuntimeError:
        # process içinde bir kez set edilebilir
        pass
    return n
