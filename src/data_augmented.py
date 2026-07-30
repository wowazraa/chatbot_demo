"""
Profesyonel veri artirma — Regex + On Ek / Son Ek + ASCII ikizler.

Amac:
  Ham veri setindeki semantik bosluklari (saglik / turizm / savunma / egitim /
  bilisim / eglence kokleri) prefix x kok x suffix kombinasyonlariyla
  zenginlestirmek.
  Her cumlenin hem Turkce karakterli hem ASCII (test-uyumlu) halini basmak.

Akis:
  1) data/raw/chatbot_dataset.json oku (orijinal kayitlar korunur)
  2) OOD mislabeling duzelt: sektore ait geçerli kayitlari geri rota et
  3) Hedef kok ifadeleri icin prefix/suffix kombinasyonlari uret
  4) Her cumle icin ASCII ikiz (+ ugra san tipi yazim varyantlari) ekle
  5) Sinif dengesizligi düzelt: asiri genislemis sektorlere downsample uygula
  6) Ham JSON + processed (indeks) guncelle

Calistirma:
    python src/data_augmented.py
"""

from __future__ import annotations

import json
import random
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
#    ÖNEMLİ: Anahtar adlar raw dataset'teki "beklenen_sektor" değerleriyle
#    birebir eşleşmelidir (ASCII, Türkçe karakter yok).
# ---------------------------------------------------------------------------
AUGMENTATION_TARGETS: dict[str, tuple[str, ...]] = {
    "saglik": (
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
    "egitim": (
        "öğrenci bilgi sistemi",
        "üniversite otomasyonu",
        "kampüs yönetim sistemi",
        "OBS",
        "LMS",
        "ÖBYS",
        "okul kayıt yazılımı",
        "eğitim portalı altyapısı",
        "uzaktan eğitim platformu",
        "sınıf yoklama otomasyonu",
    ),
    "bilisim": (
        "ERP entegrasyonu",
        "API geliştirme platformu",
        "ESB middleware orchestration",
        "kurumsal yazılım çözümleri",
        "bulut altyapısı kurulumu",
        "sunucu barındırma hizmeti",
        "ağ güvenliği izleme",
        "veri merkezi otomasyonu",
        "bilişim sistemleri danışmanlığı",
    ),
    "eglence": (
        "OTT streaming platformu",
        "oyun motoru entegrasyonu",
        "dijital medya yayın hakları yönetimi",
        "kurumsal etkinlik biletleme sistemi",
        "içerik dağıtım ağı",
        "video on demand altyapısı",
        "sinema gişe otomasyonu",
        "tema park geçiş sistemi",
        "canlı yayın aktarım yazılımı",
    ),
}

# Chatbot ile aynı kurumsal kısaltma sözlüğü (veri üretimi için)
KISALTMALAR: dict[str, str] = {
    "obs": "egitim",
    "lms": "egitim",
    "öbys": "egitim",
    "hbys": "saglik",
    "enabiz": "saglik",
    "ahbs": "saglik",
    "bilet": "turizm",
    "pnr": "turizm",
    "otel": "turizm",
}

# ---------------------------------------------------------------------------
# 3) OOD Mislabeling Düzeltme Tablosu
#    Anahtar: ham mesajın normalize/lower versiyonu
#    Değer: doğru sektör etiketi
#
#    Bu tablo, raw dataset'teki yanlış "ood" etiketli kayıtları
#    doğru sektörlerine yönlendirir. Kayıt ID yerine mesaj içeriğine
#    dayalı eşleme yapılır; böylece veri seti güncellendikçe sağlamlığı
#    korunur.
# ---------------------------------------------------------------------------
_OOD_RELABEL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # ── Sağlık ──────────────────────────────────────────────────────────────
    (re.compile(r"\belectronik\s+re[çc]ete\b|elektronik\s+re[çc]ete", re.I), "saglik"),
    (re.compile(r"\bmuayene\s+y[oö]netim\b", re.I),                          "saglik"),
    (re.compile(r"\bdoktor\s+[çc]al[iı][şs]ma\s+takvimi\b", re.I),           "saglik"),
    (re.compile(r"\bhasta\s+dosyas[iı]\s+y[oö]netimi\b", re.I),              "saglik"),
    # ── Turizm ──────────────────────────────────────────────────────────────
    (re.compile(r"\btatil\s+paketi\s+sat[iı][şs]\b", re.I),                  "turizm"),
    (re.compile(r"\btatil\s+k[oö]y[uü]\b", re.I),                           "turizm"),
    (re.compile(r"\bonline\s+rezervasyon\b", re.I),                           "turizm"),
    (re.compile(r"\bcheck-?in\s+ve\s+oda\s+y[oö]netim\b", re.I),            "turizm"),
    (re.compile(r"\bkonaklama\s+y[oö]netim\b", re.I),                        "turizm"),
    # ── Eğitim ──────────────────────────────────────────────────────────────
    (re.compile(r"\baskeri\s+personele\b.*\be[gğ]itim\b", re.I),             "egitim"),
    (re.compile(r"\bpros[eé]d[uü]r\s+e[gğ]itimi\b", re.I),                  "egitim"),
    # ── Bilişim ─────────────────────────────────────────────────────────────
    (re.compile(r"\bthird.party\s+platform\s+integration\b", re.I),           "bilisim"),
    (re.compile(r"\bESB\s+middleware\b", re.I),                               "bilisim"),
    (re.compile(r"\bworkflow\s+orchestration\b", re.I),                       "bilisim"),
]

# ---------------------------------------------------------------------------
# 4) Sınıf Dengeleme Ayarları
#    Downsample eşiği: bir sektörün augmented kayıt sayısı bu değeri
#    aşarsa, rastgele örnekleme ile bu sayıya indirilir.
#    None = sınırlama yok
# ---------------------------------------------------------------------------
CLASS_BALANCE_CAP: dict[str, int | None] = {
    "turizm":   947,
    "saglik":   947,
    "bilisim":  947,
    "egitim":   947,
    "eglence":  947,
    "ood":      None,
}

# Downsample için sabit seed (tekrarlanabilirlik)
_BALANCE_SEED = 42

_WS = re.compile(r"\s+")
_TR_TO_ASCII = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
_OUR_ZORLUKLAR = frozenset(
    {
        "augmented_prefix_suffix",
        "augmented_prefix_suffix_ascii",
    }
)


def to_ascii(text: str) -> str:
    """Türkçe karakterleri ASCII karşılıklarına çevir (ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u)."""
    return (text or "").translate(_TR_TO_ASCII)


def _normalize(text: str) -> str:
    return _WS.sub(" ", (text or "").strip())


def _detect_lang(text: str) -> str:
    if re.search(r"[çğıöşüÇĞİÖŞÜ]", text):
        return "tr"
    if re.search(
        r"\b(travel|agency|booking|check-?in|nato|software|system|military|secure|radar|cybersecurity)\b",
        text,
        re.I,
    ):
        return "en"
    return "tr"


def ascii_typo_variants(text_ascii: str) -> list[str]:
    """
    Test dinamikleriyle uyumlu ekstra ASCII yazım varyantları.
    Örnek: ugrasan → ugra san (B2), tele-tip zaten to_ascii ile gelir.
    """
    base = _normalize(text_ascii)
    out = [base]
    if "ugrasan" in base:
        spaced = base.replace("ugrasan", "ugra san")
        if spaced not in out:
            out.append(spaced)
    # tele tip / teletip → tele-tip
    alt = re.sub(r"\btele[\s]?tip\b", "tele-tip", base, flags=re.I)
    if alt not in out:
        out.append(alt)
    return out


def relabel_ood_record(rec: dict[str, Any]) -> dict[str, Any]:
    """
    Tek bir kaydın "ood" etiketini mesaj içeriğine göre doğru sektörle
    değiştirir. Gerçek OOD (selamlama, genel soru vb.) kayıtları değişmez.

    UTF-8 güvenlidir: giriş/çıkış encoding'i değiştirilmez.
    """
    current = rec.get("beklened_sektor", rec.get("beklenen_sektor", ""))
    if current != "ood":
        return rec  # Zaten doğru etiketli

    msg = rec.get("mesaj", "")
    for pattern, correct_sector in _OOD_RELABEL_PATTERNS:
        if pattern.search(msg):
            corrected = dict(rec)
            # Her iki anahtar varyantı da güncelle
            if "beklened_sektor" in corrected:
                corrected["beklened_sektor"] = correct_sector
            if "beklenen_sektor" in corrected:
                corrected["beklenen_sektor"] = correct_sector
            corrected["ood_relabeled"] = True  # denetim izi
            return corrected

    return rec  # Gerçek OOD — değiştirme


def load_raw(path: Path = RAW_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Ham veri bulunamadı: {path}")
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
    Her kök için TR cümleler + ASCII ikizler (+ ugra san tipi typo).
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


def _apply_class_balancing(
    records: list[dict[str, Any]],
    caps: dict[str, int | None] = CLASS_BALANCE_CAP,
    seed: int = _BALANCE_SEED,
) -> list[dict[str, Any]]:
    """
    Sektör bazında kayıt sayısını cap ile sınırlar (downsample).
    Ham (non-augmented) kayıtlar korunur; yalnızca augmented kayıtlara
    downsample uygulanır.
    """
    rng = random.Random(seed)

    # Ham ve augmented kayıtları ayır
    ham: list[dict[str, Any]] = []
    augmented_by_sector: dict[str, list[dict[str, Any]]] = {}

    for rec in records:
        if rec.get("zorluk") in _OUR_ZORLUKLAR:
            s = rec.get("beklenen_sektor", "belirsiz")
            augmented_by_sector.setdefault(s, []).append(rec)
        else:
            ham.append(rec)

    balanced_augmented: list[dict[str, Any]] = []
    for sektor, recs_list in augmented_by_sector.items():
        cap = caps.get(sektor)
        if cap is not None and len(recs_list) > cap:
            sampled = rng.sample(recs_list, cap)
            print(
                f"  [Dengeleme] '{sektor}': {len(recs_list)} → {len(sampled)} kayıt "
                f"(cap={cap})"
            )
            balanced_augmented.extend(sampled)
        else:
            balanced_augmented.extend(recs_list)

    return ham + balanced_augmented


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
    apply_balancing: bool = True,
) -> dict[str, Any]:
    data = load_raw(raw_path)
    raw_records: list[dict[str, Any]] = list(data.get("kayitlar") or [])

    # ── Adım 1: OOD mislabeling düzeltmesi ──────────────────────────────────
    relabeled_count = 0
    corrected_records: list[dict[str, Any]] = []
    for rec in raw_records:
        fixed = relabel_ood_record(rec)
        if fixed.get("ood_relabeled"):
            relabeled_count += 1
        corrected_records.append(fixed)
    raw_records = corrected_records

    if relabeled_count:
        print(f"[+] OOD düzeltmesi: {relabeled_count} kayıt doğru sektöre yönlendirildi")

    raw_base = [r for r in raw_records if not _is_our_augment(r)]
    processed_base = [r for r in _load_processed_base() if not _is_our_augment(r)]

    # Processed base'deki OOD kayıtlarını da düzelt
    corrected_processed: list[dict[str, Any]] = []
    for rec in processed_base:
        fixed = relabel_ood_record(rec)
        corrected_processed.append(fixed)
    processed_base = corrected_processed

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

    # ── Adım 2: Augmentation ────────────────────────────────────────────────
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

    # ── Adım 3: Sınıf Dengeleme ─────────────────────────────────────────────
    if apply_balancing:
        print("\n[+] Sınıf dengeleme uygulanıyor...")
        processed_merged = _apply_class_balancing(processed_merged)
        raw_merged = _apply_class_balancing(raw_merged)

    n_ascii = sum(1 for r in generated if r.get("ascii_twin"))
    n_tr = len(generated) - n_ascii

    # ── Adım 4: Dağılım raporu ──────────────────────────────────────────────
    import collections
    dist = collections.Counter(
        r.get("beklened_sektor", r.get("beklenen_sektor", "?"))
        for r in processed_merged
    )
    print("\n[+] Son sektör dağılımı (processed):")
    for k, v in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"    {k:<20} {v:>5}")

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
                "ood_relabeled": relabeled_count,
                "sinif_dengeleme": apply_balancing,
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
                "ood_relabeling",
                "sinif_dengeleme",
            ],
        },
        "kayitlar": processed_merged,
    }

    if update_raw:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        with raw_path.open("w", encoding="utf-8") as f:
            json.dump(raw_doc, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] Ham veri güncellendi: {raw_path} ({len(raw_merged)} kayıt)")

    if write_processed:
        PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
        with PROCESSED_PATH.open("w", encoding="utf-8") as f:
            json.dump(processed_doc, f, ensure_ascii=False, indent=2)
        print(f"[OK] Processed yazıldı: {PROCESSED_PATH} ({len(processed_merged)} kayıt)")

    print(
        f"\n[i] Özet: ham_taban={len(raw_base)} | corpus_taban={len(corpus_base)} "
        f"| yeni={len(generated)} (tr={n_tr}, ascii={n_ascii}) "
        f"| processed_toplam={len(processed_merged)}"
    )
    for sektor, roots in AUGMENTATION_TARGETS.items():
        n = sum(1 for r in generated if r["beklenen_sektor"] == sektor)
        print(f"    - {sektor}: {n} yeni kayıt ({len(roots)} kök)")

    return processed_doc if write_processed else raw_doc


def run() -> None:
    print("=" * 60)
    print("  Veri Artirma - Prefix/Suffix + ASCII Ikizler + OOD Duzeltme")
    print("=" * 60)
    augment_dataset()
    print("=" * 60)
    print("  Bitti. Indeksi yenilemek icin:")
    print("    python scripts/build_index.py")
    print("=" * 60)


if __name__ == "__main__":
    run()
