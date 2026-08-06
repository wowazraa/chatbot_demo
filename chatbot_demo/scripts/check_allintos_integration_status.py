"""
Allintos DB entegrasyon durumu — manuel kontrol.

Kullanim:
    python scripts/check_allintos_integration_status.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.config import active_paths, load_dotenv as _ld
from app.core.record_types import KAYIT_TIPI_KURUMSAL
from app.db.allintos_db import (
    get_allintos_readonly_url,
    get_allintos_write_url,
    fetch_readonly,
    is_allintos_readonly_configured,
    mask_db_url,
    refresh_intent_id_cache,
)
from app.core.config import get_allintos_retrieval_mode, get_k0_data_source, use_allintos_chat_db, allintos_local_fallback_enabled

_ld()

SERVICE_SECTORS = ("turizm", "saglik", "egitim", "bilisim", "eglence")


def main() -> int:
    print("=== ALLINTOS ENTEGRASYON DURUMU ===\n")

    write_url = get_allintos_write_url()
    ro_url = get_allintos_readonly_url()
    mode = get_allintos_retrieval_mode()
    k0_source = get_k0_data_source()
    chat_db = "allintos" if use_allintos_chat_db() else "local"
    fallback = allintos_local_fallback_enabled()

    print(f"ALLINTOS_RETRIEVAL_MODE : {mode}")
    print(f"ALLINTOS_K0_SOURCE      : {k0_source}")
    print(f"ALLINTOS_CHAT_DB        : {chat_db}")
    print(f"ALLINTOS_LOCAL_FALLBACK : {fallback}")
    print(f"ALLINTOS_DB_URL         : {mask_db_url(write_url) if write_url else 'YOK'}")
    print(f"ALLINTOS_READONLY_DB_URL: {mask_db_url(ro_url) if ro_url else 'YOK'}")
    print(f"Readonly yapilandirildi : {is_allintos_readonly_configured()}")

    if not write_url and not ro_url:
        print("\n[!] Allintos DB URL yok — .env kontrol edin.")
        return 1

    try:
        qa = fetch_readonly("SELECT COUNT(*) FROM qa_embeddings")[0][0]
        kd = fetch_readonly("SELECT COUNT(*) FROM knowledge_documents")[0][0]
        ke = fetch_readonly("SELECT COUNT(*) FROM knowledge_document_embeddings")[0][0]
        intents = fetch_readonly("SELECT intent_code, COUNT(*) FROM qa_embeddings q JOIN intents i ON q.intent_id=i.id GROUP BY intent_code ORDER BY 1")
    except Exception as exc:
        print(f"\n[!] DB baglanti hatasi: {exc}")
        return 1

    print(f"\n--- Sinem DB ---")
    print(f"qa_embeddings                  : {qa}")
    print(f"knowledge_documents            : {kd}")
    print(f"knowledge_document_embeddings  : {ke}")
    if intents:
        print("qa_embeddings / intent:")
        for code, cnt in intents:
            print(f"  {code}: {cnt}")
    else:
        print("qa_embeddings / intent: (bos)")

    paths = active_paths()
    local_service = 0
    local_kurumsal = 0
    if paths["vectors"].exists() and paths["metadata"].exists():
        import numpy as np

        vectors = np.load(paths["vectors"])["vectors"]
        meta = json.loads(paths["metadata"].read_text(encoding="utf-8"))["meta"]
        for m in meta:
            if m.get("kayit_tipi") == KAYIT_TIPI_KURUMSAL or m.get("intent_code") == "corporate_info":
                local_kurumsal += 1
            elif m.get("beklenen_sektor") in SERVICE_SECTORS:
                local_service += 1
        print(f"\n--- Yerel index ---")
        print(f"NPZ satir                     : {vectors.shape[0]}")
        print(f"Hizmet (5 sektor)             : {local_service}")
        print(f"Kurumsal                      : {local_kurumsal}")
    else:
        print("\n[!] Yerel NPZ/meta bulunamadi")

    print(f"\n--- Parite ---")
    ok_qa = qa >= local_service if local_service else qa > 0
    ok_kd = kd >= 168
    print(f"qa_embeddings >= hizmet kayit : {'OK' if ok_qa else f'EKSIK ({qa}/{local_service})'}")
    print(f"knowledge_documents >= 168    : {'OK' if ok_kd else f'EKSIK ({kd}/168)'}")

    try:
        cache = refresh_intent_id_cache()
        print(f"\nintent_id cache ({len(cache)} kod): {sorted(cache.keys())}")
    except Exception as exc:
        print(f"\n[!] intent cache yuklenemedi: {exc}")
        return 1

    if not ok_qa:
        print("\n[!] Sonraki adim: python scripts/backfill_allintos_qa_embeddings.py --dry-run")
        return 2
    if mode == "local":
        print("\n[i] Veri hazir; cutover icin .env: ALLINTOS_RETRIEVAL_MODE=primary")
    elif mode == "primary":
        print("\n[OK] Canli retrieval Allintos DB uzerinden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
