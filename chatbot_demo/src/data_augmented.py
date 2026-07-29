"""
Profesyonel veri artirma — Regex + On Ek / Son Ek + ASCII ikizler.

Amac:
  Ham veri setindeki semantik bosluklari (saglik / turizm / savunma kokleri)
  prefix x kok x suffix kombinasyonlariyla zenginlestirmek.
  Her cumlenin hem Turkce karakterli hem ASCII (test-uyumlu) halini basmak.

Akis:
  1) data/raw/chatbot_dataset.json oku (orijinal kayitlar korunur)
  2) Hedef kok ifadeleri icin prefix/suffix kombinasyonlari uret
  3) Her cumle icin ASCII ikiz (+ ugra san tipi yazim varyantlari) ekle
  4) Ham JSON + processed (indeks) guncelle

Calistirma:
    python src/data_augmented.py
"""

from __future__ import annotations

import json
import re
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "chatbot_dataset.json"
PROCESSED_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

# ---------------------------------------------------------------------------
# 1) Prefix / Suffix paleti
# ---------------------------------------------------------------------------
PREFIXES: tuple[str, ...] = (
    "lütfen",
    "acil olarak",
    "şirketimiz için",
    "kurumsal düzeyde",
    "bize",
    "hızlıca",
    "yeni bir",
)

SUFFIXES: tuple[str, ...] = (
    "entegrasyonu istiyoruz",
    "yazılımı gerekiyor",
    "çözümüne ihtiyacımız var",
    "sistemi lazım",
    "altyapısı kurulacak",
    "hizmeti almak istiyoruz",
)

# ---------------------------------------------------------------------------
# 2) Hedef kok ifadeler -> sektor
# ---------------------------------------------------------------------------
AUGMENTATION_TARGETS: dict[str, tuple[str, ...]] = {
    "sağlık": (
        "hekim takvimi",
        "muayene yönetim sistemi",
        "tele-tıp çözümleri",
        "uzaktan sağlık asistanı",
        "klinik randevu otomasyonu",
        "poliklinik yazılımı",
        "hasta takip sistemi",
        "HBYS",
        "enabiz",
        "AHBS",
    ),
    "turizm": (
        "travel agency booking",
        "check-in çözümü",
        "turizmle uğraşan işletmeler için otomasyon",
        "otel rezervasyon yazılımı",
        "tatil köyü otomasyonu",
        "acentelik yazılımı",
        "otel",
        "pnr",
        "bilet",
    ),
    "savunma": (
        "NATO standartlarında güvenli mesajlaşma",
        "birlikler arası kriptolu haberleşme",
        "siber savunma ağ çözümleri",
        "askeri taktik siber güvenlik",
        "komuta kontrol sistemi",
        "radar veri analiz yazılımı",
        "savunma sanayi yerli yazılım",
        "TSK",
        "ASELSAN",
        "KKK",
    ),
    "eğitim": (
        "öğrenci bilgi sistemi",
        "üniversite otomasyonu",
        "kampüs yönetim sistemi",
        "OBS",
        "LMS",
        "ÖBYS",
    ),
}

# Chatbot ile aynı kurumsal kısaltma sözlüğü (veri üretimi için)
KISALTMALAR: dict[str, str] = {
    "obs": "eğitim",
    "lms": "eğitim",
    "öbys": "eğitim",
    "hbys": "sağlık",
    "enabiz": "sağlık",
    "ahbs": "sağlık",
    # tsk archived
    # aselsan archived
    # kkk archived
    "bilet": "turizm",
    "pnr": "turizm",
    "otel": "turizm",
}

_WS = re.compile(r"\s+")
_TR_TO_ASCII = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
_OUR_ZORLUKLAR = frozenset(
    {
        "augmented_prefix_suffix",
        "augmented_prefix_suffix_ascii",
    }
)


def to_ascii(text: str) -> str:
    """Turkce karakterleri ASCII karsiliklarina cevir (g, i, s, c, o, u)."""
    return (text or "").translate(_TR_TO_ASCII)


def _normalize(text: str) -> str:
    return _WS.sub(" ", (text or "").strip())


def _detect_lang(text: str) -> str:
    if re.search(r"[çğıöşüÇĞİÖŞÜ]", text):
        return "tr"
    if re.search(
        r"\b(travel|agency|booking|check-?in|nato|software|system)\b",
        text,
        re.I,
    ):
        return "en"
    return "tr"


def ascii_typo_variants(text_ascii: str) -> list[str]:
    """
    Test dinamikleriyle uyumlu ekstra ASCII yazim varyantlari.
    Ornek: ugrasan -> ugra san (B2), tele-tip zaten to_ascii ile gelir.
    """
    base = _normalize(text_ascii)
    out = [base]
    if "ugrasan" in base:
        spaced = base.replace("ugrasan", "ugra san")
        if spaced not in out:
            out.append(spaced)
    # tele tip / teletip -> tele-tip
    alt = re.sub(r"\btele[\s]?tip\b", "tele-tip", base, flags=re.I)
    if alt not in out:
        out.append(alt)
    return out


def load_raw(path: Path = RAW_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Ham veri bulunamadi: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "kayitlar" not in data:
        raise ValueError("Beklenen format: { meta, kayitlar: [...] }")
    return data


def _max_numeric_id(records: list[dict[str, Any]]) -> int:
    mx = 0
    for r in records:
        rid = r.get("id")
        if isinstance(rid, int):
            mx = max(mx, rid)
        elif isinstance(rid, str) and rid.isdigit():
            mx = max(mx, int(rid))
        elif isinstance(rid, str):
            m = re.search(r"(\d+)$", rid)
            if m:
                mx = max(mx, int(m.group(1)))
    return mx


def _compose(prefix: str | None, root: str, suffix: str | None) -> str:
    parts: list[str] = []
    if prefix:
        parts.append(prefix)
    parts.append(root)
    if suffix:
        parts.append(suffix)
    return _normalize(" ".join(parts))


def _make_record(
    *,
    next_id: int,
    mesaj: str,
    sektor: str,
    root: str,
    varyant: str,
    prefix: str,
    suffix: str,
    zorluk: str,
    ascii_twin: bool,
) -> dict[str, Any]:
    return {
        "id": next_id,
        "mesaj": mesaj,
        "lang": _detect_lang(mesaj),
        "beklenen_sektor": sektor,
        "beklenen_mod": "K2",
        "zorluk": zorluk,
        "kaynak_kok": root,
        "varyant": varyant,
        "prefix": prefix,
        "suffix": suffix,
        "ascii_twin": ascii_twin,
    }


def generate_root_variants(
    root: str,
    sektor: str,
    start_id: int,
    *,
    prefixes: tuple[str, ...] = PREFIXES,
    suffixes: tuple[str, ...] = SUFFIXES,
) -> list[dict[str, Any]]:
    """
    Her kok icin TR cumleler + ASCII ikizler (+ ugra san tipi typo).
    """
    out: list[dict[str, Any]] = []
    next_id = start_id
    seen: set[str] = set()

    candidates: list[tuple[str | None, str | None]] = [(None, None)]
    candidates += [(p, None) for p in prefixes]
    candidates += [(None, s) for s in suffixes]
    candidates += list(product(prefixes, suffixes))

    for prefix, suffix in candidates:
        mesaj_tr = _compose(prefix, root, suffix)
        key_tr = mesaj_tr.casefold()
        if key_tr in seen:
            continue
        seen.add(key_tr)

        if prefix and suffix:
            varyant = "prefix_suffix"
        elif prefix:
            varyant = "prefix"
        elif suffix:
            varyant = "suffix"
        else:
            varyant = "duz"

        out.append(
            _make_record(
                next_id=next_id,
                mesaj=mesaj_tr,
                sektor=sektor,
                root=root,
                varyant=varyant,
                prefix=prefix or "",
                suffix=suffix or "",
                zorluk="augmented_prefix_suffix",
                ascii_twin=False,
            )
        )
        next_id += 1

        # ASCII ikizler (test girdileriyle birebir hizalama)
        ascii_base = to_ascii(mesaj_tr)
        for mesaj_ascii in ascii_typo_variants(ascii_base):
            key_a = mesaj_ascii.casefold()
            if key_a in seen:
                continue
            seen.add(key_a)
            out.append(
                _make_record(
                    next_id=next_id,
                    mesaj=mesaj_ascii,
                    sektor=sektor,
                    root=root,
                    varyant=f"{varyant}_ascii",
                    prefix=to_ascii(prefix or ""),
                    suffix=to_ascii(suffix or ""),
                    zorluk="augmented_prefix_suffix_ascii",
                    ascii_twin=True,
                )
            )
            next_id += 1

    return out


def _load_processed_base() -> list[dict[str, Any]]:
    if not PROCESSED_PATH.exists():
        return []
    with PROCESSED_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    recs = data.get("kayitlar", data) if isinstance(data, dict) else data
    return list(recs) if isinstance(recs, list) else []


def _is_our_augment(rec: dict[str, Any]) -> bool:
    return rec.get("zorluk") in _OUR_ZORLUKLAR


def augment_dataset(
    raw_path: Path = RAW_PATH,
    *,
    update_raw: bool = True,
    write_processed: bool = True,
) -> dict[str, Any]:
    data = load_raw(raw_path)
    raw_records: list[dict[str, Any]] = list(data.get("kayitlar") or [])

    raw_base = [r for r in raw_records if not _is_our_augment(r)]
    processed_base = [r for r in _load_processed_base() if not _is_our_augment(r)]

    corpus_base = processed_base if len(processed_base) >= len(raw_base) else raw_base
    next_id = max(_max_numeric_id(corpus_base), _max_numeric_id(raw_base)) + 1

    existing_msgs = {
        _normalize(str(r.get("mesaj", ""))).casefold()
        for r in corpus_base
        if r.get("mesaj")
    }
    for r in raw_base:
        msg = r.get("mesaj")
        if msg:
            existing_msgs.add(_normalize(str(msg)).casefold())

    generated: list[dict[str, Any]] = []
    for sektor, roots in AUGMENTATION_TARGETS.items():
        for root in roots:
            batch = generate_root_variants(root, sektor, next_id)
            for rec in batch:
                key = _normalize(rec["mesaj"]).casefold()
                if key in existing_msgs:
                    continue
                existing_msgs.add(key)
                rec["id"] = next_id
                next_id += 1
                generated.append(rec)

    raw_merged = raw_base + generated
    processed_merged = list(corpus_base) + generated

    n_ascii = sum(1 for r in generated if r.get("ascii_twin"))
    n_tr = len(generated) - n_ascii

    meta = dict(data.get("meta") or {})
    meta.update(
        {
            "kaynak": "Chatbot Bilgi Merkezi - ham + prefix/suffix + ASCII artirma",
            "artirma": {
                "yontem": "prefix_suffix_regex_ascii",
                "prefixes": list(PREFIXES),
                "suffixes": list(SUFFIXES),
                "hedefler": {k: list(v) for k, v in AUGMENTATION_TARGETS.items()},
                "ham_taban": len(raw_base),
                "corpus_taban": len(corpus_base),
                "yeni_kayit": len(generated),
                "yeni_tr": n_tr,
                "yeni_ascii": n_ascii,
                "ham_toplam": len(raw_merged),
                "processed_toplam": len(processed_merged),
            },
        }
    )

    raw_doc = {"meta": meta, "kayitlar": raw_merged}
    processed_doc = {
        "meta": {
            **meta,
            "kaynak": "src/data_augmented.py",
            "ham_dosya": raw_path.name,
            "kayit_sayisi": len(processed_merged),
            "yontemler": [
                "prefix_suffix",
                "hedef_kok_zenginlestirme",
                "ascii_twin",
            ],
        },
        "kayitlar": processed_merged,
    }

    if update_raw:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        with raw_path.open("w", encoding="utf-8") as f:
            json.dump(raw_doc, f, ensure_ascii=False, indent=2)
        print(f"[OK] Ham veri guncellendi: {raw_path} ({len(raw_merged)} kayit)")

    if write_processed:
        PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
        with PROCESSED_PATH.open("w", encoding="utf-8") as f:
            json.dump(processed_doc, f, ensure_ascii=False, indent=2)
        print(f"[OK] Processed yazildi: {PROCESSED_PATH} ({len(processed_merged)} kayit)")

    print(
        f"[i] Ozet: ham_taban={len(raw_base)} | corpus_taban={len(corpus_base)} "
        f"| yeni={len(generated)} (tr={n_tr}, ascii={n_ascii}) "
        f"| processed_toplam={len(processed_merged)}"
    )
    for sektor, roots in AUGMENTATION_TARGETS.items():
        n = sum(1 for r in generated if r["beklenen_sektor"] == sektor)
        print(f"    - {sektor}: {n} yeni kayit ({len(roots)} kok)")

    return processed_doc if write_processed else raw_doc


def run() -> None:
    print("=" * 60)
    print("  Veri Artirma - Prefix/Suffix + ASCII Ikizler")
    print("=" * 60)
    augment_dataset()
    print("=" * 60)
    print("  Bitti. Indeksi yenilemek icin:")
    print("    python scripts/build_index.py")
    print("=" * 60)


if __name__ == "__main__":
    run()
