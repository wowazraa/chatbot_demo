"""
B2B Intent Router — Live Dashboard
Çalıştırmak için:  streamlit run app.py

Bu arayüz hiçbir ML/NLP modeli yüklemez veya yerel çıkarım yapmaz.
Tüm karar http://localhost:8001/route üzerindeki canlı FastAPI router'dan
gelir (src/router_server.py — K1 Regex Fast-Path -> OOD Guardrail ->
BGE-M3 raw cosine >= 0.65).
"""

from __future__ import annotations

import time
from typing import Any

import requests
import streamlit as st

ROUTER_URL = "http://localhost:8001/route"
REQUEST_TIMEOUT_S = 10

st.set_page_config(page_title="B2B Intent Router Dashboard", page_icon="🚀", layout="wide")

EXAMPLES: dict[str, str] = {
    "🏥 Sağlık (HL7 Fast-Path)": "HL7 FHIR entegrasyonu",
    "💻 Bilişim (API Fast-Path)": "kurumsal API entegrasyonu ve bulut veri yedekleme",
    "🎬 Eğlence (OTT Fast-Path)": "OTT streaming platformu medya yayın lisansı",
    "🎓 Eğitim (Vektör Eşleşmesi)": "Üniversiteler için LMS ve öğrenci bilgi sistemi",
    "🏨 Turizm (Vektör Eşleşmesi)": "deniz kenarı otel ve tatil konaklama rezervasyonu",
    "🚫 OOD / Red (Hava Durumu)": "bugün hava nasıl",
}


def _init_state() -> None:
    if "query_input" not in st.session_state:
        st.session_state.query_input = "HL7 FHIR entegrasyonu"


def _render_sidebar() -> None:
    st.sidebar.header("🧪 Hızlı Test Senaryoları")
    for label, query in EXAMPLES.items():
        if st.sidebar.button(label, use_container_width=True):
            st.session_state.query_input = query
    st.sidebar.divider()
    st.sidebar.caption(f"Router endpoint:\n\n`{ROUTER_URL}`")


def call_router(query: str) -> tuple[dict[str, Any] | None, float, str | None]:
    """Router'a POST atar. (response_json, roundtrip_ms, error_message) döner."""
    t0 = time.perf_counter()
    try:
        res = requests.post(
            ROUTER_URL,
            json={"query": query},
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=REQUEST_TIMEOUT_S,
        )
    except requests.exceptions.ConnectionError:
        return (
            None,
            0.0,
            f"Router'a bağlanılamadı ({ROUTER_URL}). Sunucu açık mı?\n\n"
            f"`python src/router_server.py`",
        )
    except requests.exceptions.Timeout:
        return None, 0.0, f"Router yanıt vermedi ({REQUEST_TIMEOUT_S}s timeout)."
    except requests.exceptions.RequestException as exc:
        return None, 0.0, f"İstek hatası: {exc}"

    roundtrip_ms = round((time.perf_counter() - t0) * 1000, 2)
    if res.status_code != 200:
        return None, roundtrip_ms, f"Router hatası: {res.status_code} — {res.text}"
    return res.json(), roundtrip_ms, None


def _decision_layer_label(data: dict[str, Any]) -> tuple[str, str]:
    """(etiket, streamlit_render_fn_adı) döner."""
    if data.get("regex_matched"):
        return "⚡ K1 Regex Fast-Path", "info"
    if data.get("accepted"):
        return "🤖 BGE-M3 Similarity", "info"
    return "🛡️ OOD Guardrail", "warning"


def render_result(data: dict[str, Any], roundtrip_ms: float) -> None:
    col1, col2, col3 = st.columns(3)

    if data.get("accepted"):
        col1.success(
            f"**Durum:** KABUL EDİLDİ\n\n"
            f"**Sektör:** {str(data.get('predicted_sector') or '').upper()}"
        )
    else:
        col1.error(
            f"**Durum:** REDDEDİLDİ\n\n"
            f"**Sebep:** {data.get('decision_reason', 'Bilinmiyor')}"
        )

    label, kind = _decision_layer_label(data)
    getattr(col2, kind)(f"**Katman:** {label}")

    server_lat = data.get("latency_ms", 0.0)
    col3.metric(
        label="Server Latency",
        value=f"{server_lat} ms",
        delta=f"Network total: {roundtrip_ms} ms",
        delta_color="off",
    )

    st.divider()
    with st.expander("🔍 API Ham JSON Yanıtı"):
        st.json(data)


def main() -> None:
    st.title("🚀 B2B Intent Router Live Dashboard")
    st.caption(
        "K1 Regex Fast-Path | OOD Guardrail | BGE-M3 Similarity Engine — "
        "model burada değil, router'da çalışır"
    )

    _init_state()
    _render_sidebar()

    st.text_input("Test Cümlesi Giriniz:", key="query_input")

    if st.button("Sorgula ve Yönlendir", type="primary"):
        query = st.session_state.query_input.strip()
        if not query:
            st.warning("Lütfen bir sorgu girin.")
            return
        data, roundtrip_ms, error = call_router(query)
        if error:
            st.error(error)
            return
        render_result(data, roundtrip_ms)


main()
