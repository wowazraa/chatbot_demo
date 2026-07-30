"""
Simülatör — tests/fixtures/test_scenarios.json senaryolarını otomatik çalıştırır.

Çıktı: ANSI renkli terminal tablosu + özet metrik raporu
Bağımlılık: yalnızca standart kütüphane + proje içi src.chatbot
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Proje kökünü Python path'e ekle (pip install gerekmez)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot, ChatbotResponse  # noqa: E402

# ---------------------------------------------------------------------------
# ANSI Renk Kodları
# ---------------------------------------------------------------------------
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"

    # Renkler
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BLUE   = "\033[94m"
    MAGENTA= "\033[95m"
    WHITE  = "\033[97m"
    GRAY   = "\033[90m"

    @staticmethod
    def ok(text: str) -> str:   return f"{C.GREEN}{C.BOLD}{text}{C.RESET}"
    @staticmethod
    def fail(text: str) -> str: return f"{C.RED}{C.BOLD}{text}{C.RESET}"
    @staticmethod
    def warn(text: str) -> str: return f"{C.YELLOW}{text}{C.RESET}"
    @staticmethod
    def hi(text: str) -> str:   return f"{C.CYAN}{C.BOLD}{text}{C.RESET}"
    @staticmethod
    def dim(text: str) -> str:  return f"{C.GRAY}{text}{C.RESET}"


# ---------------------------------------------------------------------------
# Yardımcı çizim fonksiyonları
# ---------------------------------------------------------------------------
def _hr(char: str = "─", width: int = 80, color: str = C.DIM + C.WHITE) -> None:
    print(f"{color}{char * width}{C.RESET}")


def _banner(text: str) -> None:
    _hr("═")
    pad = (78 - len(text)) // 2
    print(f"{C.BLUE}{C.BOLD}{'═' * 1}{' ' * pad}{text}{' ' * pad}{'═' * 1}{C.RESET}")
    _hr("═")


def _truncate(s: str, n: int = 45) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


# ---------------------------------------------------------------------------
# Senaryo sonuç veri yapısı
# ---------------------------------------------------------------------------
@dataclass
class SenaryoSonucu:
    senaryo_id: str
    baslik: str
    zorluk: str
    girdi: str
    beklenen_sektor: str
    beklenen_mod: str
    tahmin_sektor: str
    tahmin_mod: str
    skor: float
    yontem: str
    sure_ms: float
    basarili: bool
    determinizm_ok: bool | None = None   # S12 için


# ---------------------------------------------------------------------------
# Değerlendirme yardımcıları
# ---------------------------------------------------------------------------
ZORLUK_RENK: dict[str, str] = {
    "kolay": C.GREEN,
    "orta":  C.YELLOW,
    "zor":   C.MAGENTA,
    "tuzak": C.RED,
}

def _zorluk_str(z: str) -> str:
    renk = ZORLUK_RENK.get(z, "")
    return f"{renk}{z:6}{C.RESET}"


def _mod_str(mod: str) -> str:
    return C.hi(mod) if mod in ("K2", "HAFIZA") else C.warn(mod)


def _skor_bar(skor: float, width: int = 12) -> str:
    filled = round(skor * width)
    bar = "█" * filled + "░" * (width - filled)
    color = C.GREEN if skor >= 0.7 else C.YELLOW if skor >= 0.4 else C.RED
    return f"{color}{bar}{C.RESET} {skor:.2f}"


# ---------------------------------------------------------------------------
# Tek senaryo çalıştır
# ---------------------------------------------------------------------------
def _calistir_senaryo(
    bot: Chatbot,
    s: dict,
    ikinci_kez: bool = False,
) -> SenaryoSonucu:
    girdi         = s.get("girdi", "")
    bkl_sektor    = s.get("beklenen_sektor", "belirsiz")
    bkl_mod       = s.get("beklenen_mod", s.get("beklened_mod", "K2"))

    t0 = time.perf_counter()
    yanit: ChatbotResponse = bot.sor(girdi)
    sure = (time.perf_counter() - t0) * 1000  # ms

    basarili = (
        yanit.sektor == bkl_sektor and
        yanit.mod    == bkl_mod
    )
    return SenaryoSonucu(
        senaryo_id      = s.get("id", "?"),
        baslik          = s.get("baslik", ""),
        zorluk          = s.get("zorluk", "?"),
        girdi           = girdi,
        beklenen_sektor = bkl_sektor,
        beklenen_mod    = bkl_mod,
        tahmin_sektor   = yanit.sektor,
        tahmin_mod      = yanit.mod,
        skor            = yanit.skor,
        yontem          = yanit.yontem,
        sure_ms         = sure,
        basarili        = basarili,
    )


# ---------------------------------------------------------------------------
# Tablo satırı yazdır
# ---------------------------------------------------------------------------
def _satir_yazdir(sonuc: SenaryoSonucu, idx: int) -> None:
    durum_ikon = C.ok(" ✔ PASS") if sonuc.basarili else C.fail(" ✘ FAIL")
    det_str = ""
    if sonuc.determinizm_ok is not None:
        det_str = C.ok(" [DET✔]") if sonuc.determinizm_ok else C.fail(" [DET✘]")

    print(
        f"  {C.BOLD}{C.WHITE}{idx:2}.{C.RESET} "
        f"{C.CYAN}{sonuc.senaryo_id:4}{C.RESET} "
        f"{_zorluk_str(sonuc.zorluk)} "
        f"{durum_ikon}"
        f"{det_str}"
    )
    print(
        f"      {C.DIM}Girdi  :{C.RESET} {_truncate(sonuc.girdi, 55)}"
    )
    print(
        f"      {C.DIM}Beklenen:{C.RESET} "
        f"{_mod_str(sonuc.beklenen_mod)}/{sonuc.beklenen_sektor:10} "
        f"{C.DIM}Tahmin :{C.RESET} "
        f"{_mod_str(sonuc.tahmin_mod)}/{sonuc.tahmin_sektor:10}"
    )
    print(
        f"      {C.DIM}Skor   :{C.RESET} {_skor_bar(sonuc.skor)}  "
        f"{C.DIM}Yöntem: {C.RESET}{C.BLUE}{sonuc.yontem:6}{C.RESET}  "
        f"{C.DIM}Süre:{C.RESET} {sonuc.sure_ms:5.1f}ms"
    )
    _hr("·", 78, C.DIM)


# ---------------------------------------------------------------------------
# Özet metrik kutusu
# ---------------------------------------------------------------------------
def _ozet_yazdir(sonuclar: list[SenaryoSonucu]) -> None:
    toplam    = len(sonuclar)
    basarili  = sum(1 for s in sonuclar if s.basarili)
    basarisiz = toplam - basarili
    ort_sure  = sum(s.sure_ms for s in sonuclar) / toplam if toplam else 0
    ort_skor  = sum(s.skor    for s in sonuclar) / toplam if toplam else 0

    # Zorluk bazlı başarı
    zorluk_sayac: dict[str, list[bool]] = {}
    for s in sonuclar:
        zorluk_sayac.setdefault(s.zorluk, []).append(s.basarili)

    _banner("SİMÜLASYON ÖZET RAPORU")

    print(f"  {C.BOLD}Toplam Senaryo  :{C.RESET} {C.WHITE}{toplam}{C.RESET}")
    print(f"  {C.BOLD}✔ Başarılı       :{C.RESET} {C.ok(str(basarili))}")
    print(f"  {C.BOLD}✘ Başarısız      :{C.RESET} {C.fail(str(basarisiz)) if basarisiz else C.dim(str(basarisiz))}")
    print()
    oran = basarili / toplam * 100 if toplam else 0
    bar_w = 50
    dolu  = round(oran / 100 * bar_w)
    bar   = (C.GREEN + "█" * dolu + C.RESET + C.DIM + "░" * (bar_w - dolu) + C.RESET)
    renk  = C.GREEN if oran >= 80 else C.YELLOW if oran >= 60 else C.RED
    print(f"  {C.BOLD}Başarı Oranı     :{C.RESET} {bar} {renk}{oran:.1f}%{C.RESET}")
    print()
    print(f"  {C.BOLD}Ort. Yanıt Süresi:{C.RESET} {C.CYAN}{ort_sure:.2f}ms{C.RESET}")
    print(f"  {C.BOLD}Ort. Güven Skoru :{C.RESET} {_skor_bar(ort_skor)}")
    print()

    # Zorluk dağılımı tablosu
    _hr("─")
    print(f"  {C.BOLD}{'Zorluk':8} {'Başarı':>8} {'Toplam':>8} {'Oran':>8}{C.RESET}")
    _hr("─")
    for zorluk, sonuclar_z in sorted(zorluk_sayac.items()):
        bas = sum(sonuclar_z)
        top = len(sonuclar_z)
        orn = bas / top * 100
        renk = ZORLUK_RENK.get(zorluk, "")
        print(
            f"  {renk}{zorluk:8}{C.RESET} "
            f"{C.ok(str(bas)):>16} "
            f"{top:>8} "
            f"{'%5.1f%%' % orn:>9}"
        )
    _hr("─")

    # Başarısız senaryolar
    hatalar = [s for s in sonuclar if not s.basarili]
    if hatalar:
        print()
        print(f"  {C.fail('✘ Başarısız Senaryolar:')}")
        for h in hatalar:
            print(
                f"    {C.RED}•{C.RESET} [{h.senaryo_id}] {h.baslik} — "
                f"beklenen={h.beklenen_mod}/{h.beklenen_sektor}, "
                f"tahmin={h.tahmin_mod}/{h.tahmin_sektor} "
                f"(skor={h.skor:.2f})"
            )
    else:
        print()
        print(f"  {C.ok('🎉 Tüm senaryolar başarıyla geçti!')}")

    _hr("═")


# ---------------------------------------------------------------------------
# Ana simülatör
# ---------------------------------------------------------------------------
def calistir(
    senaryo_dosyasi: Path | None = None,
    *,
    verbose: bool = True,
) -> list[SenaryoSonucu]:
    """
    Test senaryolarını yükle, chatbot'u çalıştır, sonuçları raporla.

    Returns:
        Tüm senaryo sonuçlarının listesi (programatik kullanım için)
    """
    senaryo_dosyasi = senaryo_dosyasi or (ROOT / "tests" / "fixtures" / "test_scenarios.json")
    if not senaryo_dosyasi.exists():
        print(C.fail(f"Senaryo dosyası bulunamadı: {senaryo_dosyasi}"))
        sys.exit(1)

    with senaryo_dosyasi.open(encoding="utf-8") as f:
        veri = json.load(f)

    senaryolar: list[dict] = veri.get("senaryolar", [])

    # Chatbot yükle
    try:
        bot = Chatbot()
    except FileNotFoundError as e:
        print(C.fail(str(e)))
        sys.exit(1)

    if verbose:
        _banner(f"CHATBOT SİMÜLATÖRÜ  •  {len(senaryolar)} senaryo  •  corpus={bot.corpus_boyutu()} kayıt")
        print()

    tum_sonuclar: list[SenaryoSonucu] = []

    for i, s in enumerate(senaryolar, start=1):
        sonuc = _calistir_senaryo(bot, s)

        # Determinizm senaryosu: ikinci kez çalıştır, sonuçları karşılaştır
        if s.get("determinizm"):
            sonuc2 = _calistir_senaryo(bot, s, ikinci_kez=True)
            sonuc.determinizm_ok = (
                sonuc.tahmin_sektor == sonuc2.tahmin_sektor and
                sonuc.skor          == sonuc2.skor
            )

        tum_sonuclar.append(sonuc)
        if verbose:
            _satir_yazdir(sonuc, i)

    if verbose:
        print()
        _ozet_yazdir(tum_sonuclar)

    return tum_sonuclar


# ---------------------------------------------------------------------------
# Doğrudan çalıştırma
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Windows terminali ANSI desteklemiyor olabilir; etkinleştir
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    calistir()
