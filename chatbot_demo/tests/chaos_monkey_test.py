# -*- coding: utf-8 -*-
"""
Chaos Monkey / Red Team koşucu
==============================
Amacı: sistemi PASS'e boğmak değil — kırıldığı yerleri kırmızı raporlamak.

Kullanım:
    python tests/chaos_monkey_test.py
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot, ChatbotResponse  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPORTS = ROOT / "reports"
CHAOS_JSON = FIXTURES / "chaos_monkey.json"
OUT_JSON = REPORTS / "chaos_monkey_sonuclari.json"
OUT_MD = REPORTS / "chaos_monkey_raporu.md"


class Ansi:
    R = "\033[0m"
    B = "\033[1m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YEL = "\033[93m"
    CYAN = "\033[96m"
    GRY = "\033[90m"


@dataclass
class TurnResult:
    girdi: str
    sektor: str
    mod: str
    skor: float
    yontem: str
    aciklama: str
    sure_ms: float
    ok: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class CaseResult:
    id: str
    vektor: str
    baslik: str
    ok: bool
    turns: list[TurnResult]
    vulnerability: str = ""


def _as_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def evaluate_turn(yanit: ChatbotResponse, kural: dict) -> tuple[bool, list[str]]:
    """Kabul edilebilir mi? Kandırıldı mı?"""
    reasons: list[str] = []
    sektor = yanit.sektor
    yontem = yanit.yontem
    skor = float(yanit.skor)
    mod = yanit.mod

    beklenen = _as_list(kural.get("beklenen_sektor"))
    yasak = _as_list(kural.get("yasak_sektor"))
    yasak_yontem = _as_list(kural.get("yasak_yontem"))

    if yasak and sektor in yasak:
        reasons.append(f"YASAK sektör: {sektor}")

    if yasak_yontem and yontem in yasak_yontem:
        reasons.append(f"YASAK yöntem: {yontem} (hafıza/kural zehri)")

    # K1 tek sektör %~1.00 ile agresif kilitleme
    if kural.get("k1_tek_sektor_yasak") and yontem == "kural" and skor >= 0.99:
        reasons.append(f"K1 greedy lock: {sektor} @{skor:.2f}")

    yasak_k1 = _as_list(kural.get("yasak_k1_tek_sektor"))
    if yasak_k1 and yontem == "kural" and sektor in yasak_k1 and skor >= 0.9:
        reasons.append(f"K1 yanlış tek-sektör kilidi: {sektor}")

    ysk = kural.get("yasak_yontem_skor") or {}
    if ysk:
        if yontem == ysk.get("yontem") and skor >= float(ysk.get("min_skor", 0.99)):
            reasons.append(f"Yasak skor profili: {yontem}/{skor}")

    if beklenen and sektor not in beklenen:
        # beklenen varsa ve tutmazsa — yasak yoksa bile sapma = fail
        reasons.append(f"Beklenen {beklenen}, gelen {sektor}")

    # Çok yüksek güven + belirsiz olmaması gereken OVV
    if kural.get("vektor") == "ovv_absurd" or (
        # parent vektor turn'de yok; runner set eder
        False
    ):
        pass

    return (len(reasons) == 0), reasons


def run_case(bot: Chatbot, case: dict) -> CaseResult:
    vektor = case["vektor"]
    sid = f"chaos-{case['id']}-{uuid.uuid4().hex[:8]}" if case.get("session") else None
    # Her session case temiz oturum
    if sid and sid in bot._sessions:
        bot._sessions.pop(sid, None)

    turn_results: list[TurnResult] = []
    turns = case.get("turns")
    if not turns:
        turns = [case]

    all_ok = True
    vulns: list[str] = []

    for t in turns:
        girdi = t["girdi"]
        # vektör bilgisini turn kuralına işle
        kural = {**t, "vektor": vektor}
        t0 = time.perf_counter()
        yanit = bot.sor(girdi, session_id=sid)
        ms = (time.perf_counter() - t0) * 1000

        ok, reasons = evaluate_turn(yanit, kural)

        # OVV ekstra: yüksek güvenle sektör uydurma
        if vektor == "ovv_absurd" and yanit.sektor != "belirsiz" and yanit.skor >= 0.75:
            if "beklenen_sektor" in t and "belirsiz" in _as_list(t.get("beklenen_sektor")):
                if yanit.sektor not in _as_list(t.get("beklenen_sektor")):
                    ok = False
                    reasons.append(f"OVV yüksek güven false-positive: {yanit.sektor}@{yanit.skor}")

        if not ok:
            all_ok = False
            vulns.extend(reasons)

        turn_results.append(
            TurnResult(
                girdi=girdi,
                sektor=yanit.sektor,
                mod=yanit.mod,
                skor=yanit.skor,
                yontem=yanit.yontem,
                aciklama=yanit.aciklama,
                sure_ms=round(ms, 2),
                ok=ok,
                reasons=reasons,
            )
        )

    return CaseResult(
        id=case["id"],
        vektor=vektor,
        baslik=case.get("baslik", case["id"]),
        ok=all_ok,
        turns=turn_results,
        vulnerability="; ".join(dict.fromkeys(vulns)),
    )


def print_case(cr: CaseResult) -> None:
    tag = f"{Ansi.GRN}PASS{Ansi.R}" if cr.ok else f"{Ansi.RED}{Ansi.B}FAIL{Ansi.R}"
    print(f"\n{tag} [{cr.id}] ({cr.vektor}) {cr.baslik}")
    for i, tr in enumerate(cr.turns, 1):
        col = Ansi.GRN if tr.ok else Ansi.RED
        print(
            f"  {col}T{i}{Ansi.R} {tr.girdi[:70]!r}"
            f"\n     → {tr.sektor}/{tr.mod} skor={tr.skor:.3f} yontem={tr.yontem} ({tr.sure_ms:.0f}ms)"
        )
        if tr.aciklama:
            print(f"     {Ansi.GRY}{tr.aciklama[:120]}{Ansi.R}")
        for r in tr.reasons:
            print(f"     {Ansi.RED}💥 {r}{Ansi.R}")


def write_reports(results: list[CaseResult], meta: dict) -> None:
    payload = {
        "meta": {
            **meta,
            "toplam": len(results),
            "pass": sum(1 for r in results if r.ok),
            "fail": sum(1 for r in results if not r.ok),
        },
        "sonuclar": [
            {
                "id": r.id,
                "vektor": r.vektor,
                "baslik": r.baslik,
                "ok": r.ok,
                "vulnerability": r.vulnerability,
                "turns": [
                    {
                        "girdi": t.girdi,
                        "sektor": t.sektor,
                        "mod": t.mod,
                        "skor": t.skor,
                        "yontem": t.yontem,
                        "aciklama": t.aciklama,
                        "sure_ms": t.sure_ms,
                        "ok": t.ok,
                        "reasons": t.reasons,
                    }
                    for t in r.turns
                ],
            }
            for r in results
        ],
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    fails = [r for r in results if not r.ok]
    by_v: dict[str, list[CaseResult]] = {}
    for r in results:
        by_v.setdefault(r.vektor, []).append(r)

    lines = [
        "# Chaos Monkey / Red Team Raporu",
        "",
        f"- Toplam senaryo: **{len(results)}**",
        f"- PASS: **{sum(1 for r in results if r.ok)}**",
        f"- FAIL (kırıldı/kandırıldı): **{len(fails)}**",
        f"- Başarı oranı: **{100 * sum(1 for r in results if r.ok) / len(results):.1f}%**",
        "",
        "## Vektör kırılımı",
        "",
    ]
    for v, items in by_v.items():
        f = sum(1 for x in items if not x.ok)
        lines.append(f"- `{v}`: {len(items) - f}/{len(items)} pass — **{f} fail**")

    lines += ["", "## 🔴 Açıklar (Failures)", ""]
    if not fails:
        lines.append("_Bu koşuda fail yok — yine de OVV/edge case’leri elle yokla._")
    for r in fails:
        lines.append(f"### {r.id} — {r.baslik}")
        lines.append(f"- Vektör: `{r.vektor}`")
        lines.append(f"- Vulnerability: {r.vulnerability or '(turn reasons)'}")
        for i, t in enumerate(r.turns, 1):
            if t.ok:
                continue
            lines.append(
                f"- T{i}: `{t.girdi}` → **{t.sektor}** ({t.yontem}, {t.skor}) — {', '.join(t.reasons)}"
            )
        lines.append("")

    lines += [
        "## 🟡 Gözlem notları",
        "",
        "- Hafıza mirası `fiyat/lisans/ücret` sinyali + `belirsiz` kombinasyonunda eski sektöre yapışabilir.",
        "- K1 çelişki sonrası BGE yine tek sektöre yüksek güvenle gidebilir (α=0.9).",
        "- OVV mecazları (otel konforu, savcılık savunma) embedding uzayında sektör komşusu olabilir.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    data = json.loads(CHAOS_JSON.read_text(encoding="utf-8"))
    cases = data["senaryolar"]
    print(f"{Ansi.CYAN}{Ansi.B}CHAOS MONKEY{Ansi.R} — {len(cases)} senaryo yükleniyor…")
    print("Chatbot motoru + BGE indeksi hazırlanıyor (ilk çağrı yavaş olabilir).\n")

    bot = Chatbot()
    print(f"Corpus={bot.corpus_boyutu()} | BGE={bot.bge_aktif_mi()}\n")

    results: list[CaseResult] = []
    for case in cases:
        cr = run_case(bot, case)
        results.append(cr)
        print_case(cr)

    n = len(results)
    n_ok = sum(1 for r in results if r.ok)
    n_fail = n - n_ok

    print("\n" + "=" * 70)
    print(f"{Ansi.B}ÖZET{Ansi.R}: {n_ok}/{n} pass | {Ansi.RED}{n_fail} FAIL{Ansi.R}")
    print("=" * 70)

    # Vektör fail özeti
    for v in ("memory_poison", "k1_evasion", "semantic_collision", "ovv_absurd"):
        items = [r for r in results if r.vektor == v]
        if not items:
            continue
        f = sum(1 for r in items if not r.ok)
        print(f"  {v}: {Ansi.RED if f else Ansi.GRN}{len(items)-f}/{len(items)}{Ansi.R} (fail={f})")

    print(f"\n{Ansi.B}KIRILGANLIKLAR:{Ansi.R}")
    fails = [r for r in results if not r.ok]
    if not fails:
        print("  (bu koşuda kırmızı yok — şüpheci kal)")
    for r in fails:
        print(f"  {Ansi.RED}• {r.id}{Ansi.R}: {r.vulnerability or r.baslik}")

    write_reports(results, data.get("meta", {}))
    print(f"\nRapor: {OUT_MD}")
    print(f"JSON : {OUT_JSON}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
