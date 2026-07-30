# -*- coding: utf-8 -*-
"""
The Crucible — ileri düzey red team koşucu
==========================================
KOD GÜNCELLEME YOK. Sadece ölç, kır, raporla.

Kullanım:
    python tests/the_crucible_test.py
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot, ChatbotResponse  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPORTS = ROOT / "reports"
IN_JSON = FIXTURES / "the_crucible.json"
OUT_JSON = REPORTS / "the_crucible_sonuclari.json"
OUT_MD = REPORTS / "the_crucible_raporu.md"


class A:
    R = "\033[0m"
    B = "\033[1m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YEL = "\033[93m"
    CYAN = "\033[96m"
    GRY = "\033[90m"


@dataclass
class CaseResult:
    id: str
    vektor: str
    baslik: str
    girdi: str
    sektor: str
    mod: str
    skor: float
    yontem: str
    aciklama: str
    sure_ms: float
    ok: bool
    reasons: list[str] = field(default_factory=list)
    temiz_sorgu: str = ""
    rewrite_backend: str = ""


def _lst(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def evaluate(y: ChatbotResponse, case: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    bek = _lst(case.get("beklenen_sektor"))
    yasak = _lst(case.get("yasak_sektor"))

    if yasak and y.sektor in yasak:
        reasons.append(f"YASAK sektör kilitlenmesi: {y.sektor}")
    if bek and y.sektor not in bek:
        reasons.append(f"Beklenen {bek}, gelen '{y.sektor}'")
    # İroni/şart: yasaklı sektöre K1@1.0 özellikle ağır
    if yasak and y.sektor in yasak and y.yontem == "kural" and y.skor >= 0.95:
        reasons.append(f"K1 greedy zehir @{y.skor:.2f}")
    return len(reasons) == 0, reasons


def main() -> int:
    data = json.loads(IN_JSON.read_text(encoding="utf-8"))
    cases = data["senaryolar"]
    print(f"{A.CYAN}{A.B}THE CRUCIBLE{A.R} — {len(cases)} senaryo (zırh YOK, sadece ölçüm)\n")

    # Kanıt koşusu: API anahtarı olsa bile simüle rewriter (tekrarlanabilir log)
    bot = Chatbot(force_simulated_rewriter=True)
    print(
        f"Corpus={bot.corpus_boyutu()} | BGE={bot.bge_aktif_mi()} | "
        f"Rewriter={bot._rewriter.mode}\n"
    )

    results: list[CaseResult] = []
    for case in cases:
        t0 = time.perf_counter()
        y = bot.sor(case["girdi"])
        ms = (time.perf_counter() - t0) * 1000
        ok, reasons = evaluate(y, case)
        cr = CaseResult(
            id=case["id"],
            vektor=case["vektor"],
            baslik=case.get("baslik", case["id"]),
            girdi=case["girdi"],
            sektor=y.sektor,
            mod=y.mod,
            skor=y.skor,
            yontem=y.yontem,
            aciklama=y.aciklama,
            sure_ms=round(ms, 2),
            ok=ok,
            reasons=reasons,
            temiz_sorgu=getattr(y, "temiz_sorgu", ""),
            rewrite_backend=getattr(y, "rewrite_backend", ""),
        )
        results.append(cr)

        tag = f"{A.GRN}PASS{A.R}" if ok else f"{A.RED}{A.B}FAIL{A.R}"
        print(f"{tag} [{cr.id}] ({cr.vektor}) {cr.baslik}")
        print(f"  {A.GRY}{cr.girdi[:90]}{'…' if len(cr.girdi)>90 else ''}{A.R}")
        print(
            f"  → {cr.sektor}/{cr.mod} skor={cr.skor:.3f} yontem={cr.yontem} ({cr.sure_ms:.0f}ms)"
        )
        temiz = getattr(y, "temiz_sorgu", "")
        rb = getattr(y, "rewrite_backend", "")
        if temiz:
            print(f"  {A.CYAN}Rewriter[{rb}]: {temiz!r}{A.R}")
        if cr.aciklama:
            print(f"  {A.GRY}{cr.aciklama[:140]}{A.R}")
        for r in reasons:
            print(f"  {A.RED}💥 {r}{A.R}")
        print()

    n = len(results)
    n_ok = sum(1 for r in results if r.ok)
    n_fail = n - n_ok

    print("=" * 70)
    print(f"{A.B}ÖZET{A.R}: {n_ok}/{n} pass | {A.RED}{n_fail} FAIL{A.R} ({100*n_ok/n:.1f}%)")
    print("=" * 70)

    vektors = [
        "sarcasm",
        "conditional",
        "code_switch",
        "phonetic",
        "dilution",
        "temporal_shift",
    ]
    by_fail: dict[str, list[CaseResult]] = {v: [] for v in vektors}
    for r in results:
        items = [x for x in results if x.vektor == r.vektor]
        f = sum(1 for x in items if not x.ok)
        # print once per vector below
    for v in vektors:
        items = [r for r in results if r.vektor == v]
        f = sum(1 for r in items if not r.ok)
        col = A.RED if f else A.GRN
        print(f"  {v}: {col}{len(items)-f}/{len(items)}{A.R} (fail={f})")
        by_fail[v] = [r for r in items if not r.ok]

    print(f"\n{A.B}KIRILGANLIKLAR:{A.R}")
    fails = [r for r in results if not r.ok]
    if not fails:
        print("  (fail yok)")
    for r in fails:
        print(f"  {A.RED}• {r.id}{A.R} [{r.vektor}]: {'; '.join(r.reasons)}")

    # JSON + MD
    payload = {
        "meta": {
            **data.get("meta", {}),
            "toplam": n,
            "pass": n_ok,
            "fail": n_fail,
            "oran": round(100 * n_ok / n, 1),
        },
        "sonuclar": [
            {
                "id": r.id,
                "vektor": r.vektor,
                "baslik": r.baslik,
                "girdi": r.girdi,
                "sektor": r.sektor,
                "mod": r.mod,
                "skor": r.skor,
                "yontem": r.yontem,
                "aciklama": r.aciklama,
                "temiz_sorgu": r.temiz_sorgu,
                "rewrite_backend": r.rewrite_backend,
                "sure_ms": r.sure_ms,
                "ok": r.ok,
                "reasons": r.reasons,
            }
            for r in results
        ],
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# The Crucible Raporu",
        "",
        f"- Skor: **{n_ok}/{n}** ({100*n_ok/n:.1f}%) — FAIL **{n_fail}**",
        "",
        "## Vektör kırılımı",
        "",
    ]
    for v in vektors:
        items = [r for r in results if r.vektor == v]
        f = sum(1 for r in items if not r.ok)
        lines.append(f"- `{v}`: {len(items)-f}/{len(items)} pass — **{f} fail**")

    lines += ["", "## Fail detayları", ""]
    for r in fails:
        lines.append(f"### {r.id} — {r.baslik}")
        lines.append(f"- Vektör: `{r.vektor}`")
        lines.append(f"- Girdi: `{r.girdi}`")
        lines.append(
            f"- Çıktı: **{r.sektor}** / {r.mod} / {r.yontem} / skor={r.skor}"
        )
        lines.append(f"- Aciklama: {r.aciklama}")
        lines.append(f"- Neden: {', '.join(r.reasons)}")
        lines.append("")

    lines += [
        "## Mimari not",
        "",
        "- Akış: `Kullanıcı → LLMRewriter → K1 → K2` (söylem regex yok).",
        "- Rewriter sınıflandırmaz; temiz arama sorgusu üretir.",
        "- Bu koşu `force_simulated_rewriter=True` ile tekrarlanabilir kanıt üretir.",
        "",
        "## Gözlem özeti",
        "",
        "- İroni/şart/zaman kayması: rewriter asıl niyeti süzmeli; K1/K2 temiz sorguya bakmalı.",
        "- Code-switch: EN jargon (HR, PMS, EHR) regex sözlüğünde yoksa BGE'ye kalır.",
        "- Fonetik: leet/noktalı yazım K1'i deler; BGE kurtarabilir veya FB'ye düşer.",
        "- Dilution: uzun gürültü + sonda niyet; rewriter gürültüyü düşürmeli.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRapor: {OUT_MD}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
