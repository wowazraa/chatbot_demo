# -*- coding: utf-8 -*-
"""
Singularity Test — 5 uçuk senaryo
=================================
Motor koduna DOKUNULMAZ. Sadece ölçüm.

Beklentiler:
  1) Mantık: "sağlık sigortası" + "lojistik firmasıyız" → sağlık elenmeli
  2) Entity: "askeri radar" + debug/kod niyeti → savunma elenmeli
  3) Güvenlik çemberi: elma/portakal vb. → FB / belirsiz (sektörel talep değil)

Kullanım:
    python tests/singularity_test.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot  # noqa: E402


@dataclass
class Case:
    id: str
    baslik: str
    girdi: str
    yasak: list[str] = field(default_factory=list)
    # beklenen_sektor: tam eşleşme listesi (boşsa sadece yasak kontrolü)
    beklenen: list[str] = field(default_factory=list)
    # True → mod FB veya sektör belirsiz olmalı
    fb_zorunlu: bool = False
    not_: str = ""


CASES: list[Case] = [
    Case(
        id="S01_lojistik_mantik",
        baslik="Mantık: lojistik firma + sağlık sigortası tuzağı",
        girdi=(
            "Biz bir lojistik firmasıyız; depo rota optimizasyonu bakıyoruz. "
            "Bu arada personel için sağlık sigortası paketi de konuşuldu ama "
            "asıl ihtiyacımız filomuzun sevkiyat yazılımı."
        ),
        yasak=["sağlık"],
        beklenen=["belirsiz", "ik_kurumsal"],  # lojistik taksonomide yok; sağlık YASAK
        not_="sağlık sigortası geçse bile lojistik niyet sağlık'ı elemmeli",
    ),
    Case(
        id="S02_radar_debug",
        baslik="Entity: askeri radar kelimesi + kod/debug niyeti",
        girdi=(
            "Askeri radar verisini parse eden Python scriptimde "
            "NullReferenceException alıyorum, stack trace'i debug etmek "
            "ve unit test yazmak için yardım lazım."
        ),
        yasak=["savunma"],
        beklenen=["belirsiz", "bilişim"],
        not_="askeri radar entity'si savunma kilitlememeli; debug/kod öncelikli",
    ),
    Case(
        id="S03_elma_portakal",
        baslik="Güvenlik çemberi: sektörel olmayan elma/portakal",
        girdi="Sence elma mı daha sağlıklı portakal mı? Hangisini kahvaltıda yemeliyim?",
        yasak=["sağlık", "turizm", "finans", "eğitim", "savunma", "e_ticaret"],
        beklenen=["belirsiz"],
        fb_zorunlu=True,
        not_="sektörel talep değil → FB/belirsiz",
    ),
    Case(
        id="S04_sarkastik_hastane",
        baslik="İroni + yanlış sektör: hastane övgüsü, asıl HR bordro",
        girdi=(
            "Hastane yazılımınız muhteşemmiş (!) keşke işimize yarasaydı. "
            "Biz fabrikada personel bordro ve performans CRM kuracağız."
        ),
        yasak=["sağlık"],
        beklenen=["ik_kurumsal", "belirsiz"],
        not_="hastane entity'si ironide; asıl niyet IK",
    ),
    Case(
        id="S05_havadis_futbol",
        baslik="Güvenlik çemberi: futbol skoru / sohbet",
        girdi="Dün akşamki maç kaç kaç bitti, Galatasaray mı yendi Fener mi?",
        yasak=["sağlık", "turizm", "savunma", "eğitim", "finans", "e_ticaret", "bilişim"],
        beklenen=["belirsiz"],
        fb_zorunlu=True,
        not_="sektörel talep değil → FB/belirsiz",
    ),
]


def evaluate(bot_resp, case: Case) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if case.yasak and bot_resp.sektor in case.yasak:
        reasons.append(f"YASAK sektör: {bot_resp.sektor}")
    if case.beklenen and bot_resp.sektor not in case.beklenen:
        reasons.append(f"Beklenen {case.beklenen}, gelen '{bot_resp.sektor}'")
    if case.fb_zorunlu:
        if bot_resp.sektor != "belirsiz" and bot_resp.mod != "FB":
            reasons.append(
                f"FB zorunlu ama sektor={bot_resp.sektor} mod={bot_resp.mod}"
            )
    return len(reasons) == 0, reasons


def main() -> int:
    bot = Chatbot(force_simulated_rewriter=True)
    print("=" * 72)
    print("SINGULARITY TEST — 5 uçuk senaryo (motor koduna dokunulmadi)")
    print(f"Rewriter={bot._rewriter.mode} | Corpus={bot.corpus_boyutu()}")
    print("=" * 72)

    results = []
    for case in CASES:
        y = bot.sor(case.girdi)
        ok, reasons = evaluate(y, case)
        results.append((case, y, ok, reasons))

        tag = "PASS" if ok else "FAIL"
        print(f"\n[{tag}] {case.id} — {case.baslik}")
        print(f"  girdi : {case.girdi[:110]}{'…' if len(case.girdi) > 110 else ''}")
        print(f"  clean : {y.temiz_sorgu!r}")
        print(f"  sonuc : {y.sektor} / {y.mod} / {y.yontem} @ {y.skor:.3f}")
        print(f"  not   : {case.not_}")
        if "sektörel" in (y.aciklama or "").lower() or "fallback" in (y.aciklama or "").lower():
            print(f"  msg   : {y.aciklama[:120]}")
        else:
            print(f"  acik  : {(y.aciklama or '')[:140]}")
        for r in reasons:
            print(f"  !! {r}")

    n_ok = sum(1 for *_, ok, __ in results if ok)
    n = len(results)
    print("\n" + "=" * 72)
    print(f"OZET: {n_ok}/{n} pass ({100 * n_ok / n:.0f}%)")
    if n_ok == n:
        print("VERDICT: SINGULARITY esigi — mantik/entity/guvenlik cemberi OK")
    elif n_ok >= 3:
        print("VERDICT: KISMI — bazi senaryolar genelliyor, bazilari halusinasyon")
    else:
        print("VERDICT: HALUSINASYON / ezber — Singularity yok")
    print("=" * 72)

    # Kısa tablo
    print("\n| ID | Sektor | Mod | Yontem | OK |")
    print("|----|--------|-----|--------|----|")
    for case, y, ok, _ in results:
        print(
            f"| {case.id} | {y.sektor} | {y.mod} | {y.yontem} | "
            f"{'✓' if ok else '✗'} |"
        )

    return 0 if n_ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
