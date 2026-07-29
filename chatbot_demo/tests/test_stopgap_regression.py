"""
tests/test_stopgap_regression.py
=================================
Aşama 2 stopgap'inin (commit 9d2edf1) düzelttiği 5 K1/bilişim yanlış-pozitif vakası
ve F2 K1-stopgap kontrolü için kalıcı regresyon testi.

Bu testler çalıştığı sürece şu davranışlar güvence altındadır:
  - A2, A3, A5, B6, D2 → artık K1/bilisim DÖNDÜRMEZ
  - F2 → K1/bilisim DÖNDÜRMEZ (K2/bilisim veya FB kabul edilebilir)

Çalıştır: pytest tests/test_stopgap_regression.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.chatbot import Chatbot

# Bir kere yükle — tüm testler paylaşır
@pytest.fixture(scope="module")
def bot():
    return Chatbot()


# ─── Stopgap Grubu 1: Artık K1/bilisim döndürmemeli ───────────────────────
# Bu 5 cümle, B2B_MODIFIERS ve SECTOR_ANCHORS daraltması öncesinde
# K1/bilisim layer=kisaltma, skor=0.99 ile yanlış sınıflandırılıyordu.
# Stopgap (9d2edf1) sonrası FB veya doğru sektöre yönlendirilmeli.

@pytest.mark.parametrize("cid,girdi,beklenen_sektor", [
    ("A2", "Sagligimiz icin bir sistem ariyoruz.",          "belirsiz"),
    ("A3", "Saglikla ilgili bir yazilim istiyoruz.",        "belirsiz"),
    ("A5", "Klinigimiz icin hasta takip yazilimi lazim.",   "saglik"),
    ("B6", "Otel yonetim yazilimi teklifi almak istiyoruz.", "turizm"),
    ("D2", "Uzaktan egitim platformu ariyoruz.",            "egitim"),
])
def test_no_k1_bilisim_false_positive(bot, cid, girdi, beklenen_sektor):
    """Stopgap: bu vakalar K1/bilisim döndürmemeli."""
    yanit = bot.sor(girdi)
    assert not (yanit.mod == "K1" and yanit.sektor == "bilisim"), (
        f"[{cid}] Regresyon: '{girdi}' hâlâ K1/bilisim döndürüyor "
        f"(layer={getattr(yanit, 'yontem', '?')}, skor={yanit.skor}). "
        f"Stopgap geri alındı mı? SECTOR_ANCHORS/B2B_MODIFIERS/STRICT_SECTOR_REGEX "
        f"jenerik kelimelerini kontrol edin."
    )


# ─── Stopgap Grubu 2: F2 K1-stopgap kontrolü ────────────────────────────
# F2 stopgap öncesi K1/bilisim döndürüyordu.
# Sonrası K2/bilisim (BGE yoluyla) veya FB kabul edilebilir;
# K1/bilisim OLMAMALI.

def test_f2_no_k1_bilisim(bot):
    """F2: 'yazilim hizmetleriniz' sorgusunda K1/bilisim yasak."""
    girdi = "Yazilim hizmetleriniz hakkinda bilgi alabilir miyim?"
    yanit = bot.sor(girdi)
    assert not (yanit.mod == "K1" and yanit.sektor == "bilisim"), (
        f"[F2] Regresyon: '{girdi}' K1/bilisim döndürüyor. "
        f"Beklenen: K2/bilisim veya FB/belirsiz. "
        f"Alınan: {yanit.mod}/{yanit.sektor} (layer={getattr(yanit, 'yontem', '?')})"
    )


# ─── Akıllı Negasyon Maskesi (Aşama 3): Yön testi ───────────────────────
# "X var ama Y arıyoruz" → Y-tarafı kazanmalı (post-conj + REQUEST bonus)
# "X yapıyoruz ama Y vermiyoruz" → X-tarafı kazanmalı (post-conj, REQUEST yok)

def test_negation_mask_post_conj_request_wins(bot):
    """Negasyon maskesi: 'ama + arıyoruz' → sonraki kısım niyet."""
    girdi = "Turistik bir bolgede ofisimiz var ama yazilim ariyoruz"
    yanit = bot.sor(girdi)
    # Beklenti: rewriter 'yazilim ariyoruz' kısmını seçeceği için sektör turizm olmamalı, bilisim veya belirsiz olmalıdır
    assert yanit.sektor in ("bilisim", "belirsiz"), (
        f"Negasyon maskesi başarısız: '{girdi}' → {yanit.mod}/{yanit.sektor} (skor={yanit.skor}). "
        f"Sektörün turizm olmaması, bilisim veya belirsiz olması gerekiyordu."
    )


# ─── Alt Problem 2 Domain Vakaları (Aşama 3): A7, A8, D3 ───────────────────
# Tele-tıp (A7), Klinik Otomasyon (A8) ve Okul Kayıt Sistemleri (D3)
# BGE-M3 aramasında doğrudan doğru sektöre yönlenmeli.

@pytest.mark.parametrize("cid,girdi,beklenen_sektor", [
    ("A7", "Poliklinigimiz icin tele-tip altyapisi ariyoruz", "saglik"),
    ("A8", "Saglik sektorunde otomasyon projeleri gelistiri...", "saglik"),
    ("D3", "Okulumuz icin kayit sistemi lazim.", "egitim"),
])
def test_alt_problem_2_domain_targets(bot, cid, girdi, beklenen_sektor):
    """Alt Problem 2: A7, A8, D3 vakaları doğru sektöre yüksek skorla yönlenmeli."""
    yanit = bot.sor(girdi)
    assert yanit.sektor == beklenen_sektor, (
        f"[{cid}] Regresyon: '{girdi}' → beklenen={beklenen_sektor}, "
        f"alınan={yanit.sektor} (mod={yanit.mod}, skor={yanit.skor})"
    )
    assert yanit.skor >= 0.80, (
        f"[{cid}] Skor Düşüklüğü: '{girdi}' → skor={yanit.skor} (<0.80). "
        f"Corpus embedding indeksini kontrol edin."
    )

