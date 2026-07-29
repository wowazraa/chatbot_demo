"""
LLM Query Rewriter
==================
Sınıflandırma YAPMAZ. Kaotik kullanıcı metnini "saf arama sorgusuna" çevirir.

Akış (Chatbot core):
  Kullanıcı → LLMRewriter.rewrite() → temiz sorgu → K1 → K2

Backend seçimi:
  1) OPENAI_API_KEY / LLM_REWRITER_API_KEY varsa gerçek LLM API
  2) Aksi halde SimulatedLLMBackend (çevrimiçi demo / test)

Simülasyon, "ama/fakat ezberi" değildir: cümleleri skorlar (hipotetik↓, rica↑,
zamansal yenilik↑) ve en yüksek niyet cümlesinden temiz sorgu üretir.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Protocol


@dataclass
class RewriteResult:
    """Rewriter çıktısı — sektör sınıflandırmaz; negasyon işaretleri taşıyabilir."""
    original: str
    clean_query: str
    backend: str          # "api" | "simulated"
    note: str = ""
    negated_sectors: tuple[str, ...] = ()  # Negated_Sector_Keyword listesi


class RewriterBackend(Protocol):
    def rewrite(self, text: str) -> RewriteResult: ...


# ---------------------------------------------------------------------------
# Prompt (API ve simülasyon aynı sözleşmeyi paylaşır)
# ---------------------------------------------------------------------------
REWRITE_SYSTEM = """Sen bir sorgu yeniden yazma motorusun (Query Rewriter).
Görevin: kullanıcı mesajındaki ASIL niyeti bulup kısa, nötr bir arama sorgusu yazmak.
- Sektör sınıflandırma YAPMA, etiket uydurma.
- İroni, şart kipi (olsaydık), geçmiş anlatı ve sohbet gürültüsünü at.
- Kullanıcının metnindeki günlük hayat konuşmalarını (kahve içmek, hava durumu,
  toplantı yorgunluğu, üşümek/soğumak, trafikte kalmak, yemek molası) TAMAMEN YOK SAY.
  Bu tür fiilleri asla 'sağlık' veya 'turizm' gibi sektörlerle ilişkilendirme.
  Yalnızca B2B / Kurumsal yazılım ve hizmet niyetini çıkar.
- NEGASYON KORUMASI: Negasyon içeren (değil, hariç, dışında, asla) sektörel kavramları
  asla silme. Bunları çıktıda 'Negated_Sector_Keyword:SAHA' biçiminde işaretle
  (örn. Negated_Sector_Keyword:sağlık). Olumsuzlanan kelimeyi olumlu sinyal gibi bırakma.
- SEKTÖREL BAĞLAM KORUMASI: Girişteki Lojistik, Savunma, Bilişim, Sağlık vb. terimler
  sektörel niyet taşıyorsa cümleden atılması YASAKTIR; temiz sorguda tut.
- Mesajda 'siber' / 'cyber' geçiyorsa ve çıktıda 'savunma' kalıyorsa, 'siber'
  kelimesini ASLA düşürme (bağlam kaybı askeri sektörü yanlış tetikler).
- Sadece talep edilen ürün/hizmeti kısa Türkçe veya İngilizce anahtar kelimelerle yaz.
- Tek satır çıktı ver, açıklama ekleme."""


REWRITE_USER_TMPL = """Mesaj:
\"\"\"{text}\"\"\"

Temiz arama sorgusu:"""


# ---------------------------------------------------------------------------
# API backend
# ---------------------------------------------------------------------------
class OpenAICompatibleRewriter:
    """OpenAI-uyumlu Chat Completions API (opsiyonel)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def rewrite(self, text: str) -> RewriteResult:
        import json
        import urllib.error
        import urllib.request

        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": REWRITE_SYSTEM},
                {"role": "user", "content": REWRITE_USER_TMPL.format(text=text)},
            ],
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            clean = data["choices"][0]["message"]["content"].strip().strip('"')
            clean = re.sub(r"\s+", " ", clean)
            if not clean:
                raise ValueError("empty rewrite")
            return RewriteResult(text, clean, "api", "OpenAI-compatible rewrite")
        except (urllib.error.URLError, KeyError, ValueError, TimeoutError) as exc:
            # API düşerse simülasyona düş
            sim = SimulatedLLMBackend().rewrite(text)
            sim.note = f"API hata → simulated ({exc})"
            return sim


# ---------------------------------------------------------------------------
# Simulated LLM — clause scoring (ezberci bağlaç regex'i değil)
# ---------------------------------------------------------------------------
# Cümle/clause sınırı — tire (-) BİLEŞİK kelime (e-ticaret) için kullanılmaz
_SPLIT = re.compile(r"[.!?;:—]+|\n+")
# Soft clause: bağlaçla böl (segmentasyon; "ama sonrası tut" kuralı değil)
_CONJ_SPLIT = re.compile(r"\s+(?:ama|fakat|ancak|lakin|o yüzden|bu yüzden)\s+", re.I)

# Bağlaç sonrası clause flag'i — hangi clause'ların bağlaçtan sonra geldiğini izle
# Kullanım: _split_clauses_with_pos() → (clause, is_post_conj) çiftleri
_CONJ_RX = re.compile(r"\b(ama|fakat|ancak|lakin)\b", re.I)

# Rica / aktif talep
_REQUEST = re.compile(
    r"\b("
    r"arıyoruz|arıyorum|lazım|istiyoruz|istiyorum|bakıyoruz|bakıyorum|"
    r"bulur\s*musun|gerek(li|iyor)?|ihtiyacımız|kuracağız|kurmak|"
    r"geçtik|geciyoruz|öncelik|acil|need|looking\s+for|want|require|seeking"
    r")\b",
    re.I,
)
# Hipotetik / karşı-olgusal (düşük skor)
_HYPOTH = re.compile(
    r"\b("
    r"olsaydı|olsaydık|olsam|olsak|olursa|eğer|alseydi|"
    r"isterdik|alırdık|isterdik|olurdu"
    r")\b",
    re.I,
)
# Geçmiş anlatı (düşük; rica yoksa)
_PAST = re.compile(
    r"\b("
    r"aldık|aldım|gittim|gittik|sattığınız|çalışıyorum|çalışıyor|"
    r"yoruldum|geçen\s+yıl|geçen\s+hafta|dün(?!\s+onu)|"
    r"bayılıyor|çöktü|efsane|muhteşem|süper\s+lms"
    r")\b",
    re.I,
)
# Güncel / niyet kayması (yüksek)
_RECENT = re.compile(
    r"\b("
    r"şimdi|bundan\s+sonra|bu\s+arada|asıl|artık|bundan\s+böyle|"
    r"çöpe\s+atıp|geçtik|geciyoruz|arıyoruz|lazım"
    r")\b",
    re.I,
)
# Red / terk (önceki konuyu düşür — cümle içi)
_REJECT = re.compile(
    r"\b("
    r"çöpe|vazgeç|boşver|değil|istemiyoruz|şaka\s*bir\s*yana|"
    r"keşke|çalışsaydı|"
    # Türkçe red/ret fiilleri: ver-mi-yoruz, et-mi-yoruz, yap-mı-yoruz...
    r"\w+mi(yoruz|yorum|yor|yorlar)|"    # vermiyoruz, etmiyoruz, kabul etmiyoruz
    r"\w+mı(yoruz|yorum|yor|yorlar)|"    # yapmıyoruz, almıyoruz
    r"\w+mu(yoruz|yorum|yor|yorlar)|"    # sunmuyoruz, bulunmuyoruz
    r"\w+mü(yoruz|yorum|yor|yorlar)"     # gelmiyoruz (soft form)
    r")\b",
    re.I,
)

# Günlük hayat gürültüsü — asla niyet/sektör sinyali sayma
_SMALLTALK = re.compile(
    r"\b("
    r"kahve|kahveler|kahvemi|so[gğ]udu|so[gğ]uk|hava|yağmur|g[uü]zeldi|"
    r"toplantı\s+yo[gğ]undu|yoruldum|üşüd|trafikte|yemekhane|asansör|"
    r"her\s+neyse|naber|selam"
    r")\b",
    re.I,
)

_STOP = {
    "ben", "biz", "bir", "ve", "ile", "için", "çok", "da", "de", "mi", "mı",
    "mu", "mü", "o", "bu", "şu", "ki", "ya", "ha", "ay", "naber", "selam",
    "selamm", "tşkk", "teşekkürler", "evet", "tabii", "olan", "gibi",
    "kadar", "sonra", "önce", "ama", "fakat", "ancak", "lakin", "veya",
    "şimdi", "her", "şeyi", "gerçek", "bize", "ise", "hangi", "neydi",
    "eskiden", "artık", "bırakıyoruz", "kullanıyorduk", "yüzden",
    "kahve", "kahveler", "soğudu", "hava", "toplantı", "yoğundu", "neyse",
}


def _split_clauses(text: str) -> list[str]:
    parts = _SPLIT.split(text)
    out: list[str] = []
    for p in parts:
        for conj_chunk in _CONJ_SPLIT.split(p):
            for chunk in re.split(r"\s*,\s*", conj_chunk):
                c = chunk.strip()
                if len(c) >= 4:
                    out.append(c)
    return out or [text.strip()]


def _split_clauses_with_pos(text: str) -> list[tuple[str, bool]]:
    """Clause'ları (metin, bağlaçtan_sonra_mi) çiftleri olarak döner.

    Bağlaç tespiti: 'ama/fakat/ancak/lakin' geçtiğinde sonraki segment
    is_post_conj=True olarak işaretlenir.
    """
    parts = _SPLIT.split(text)
    out: list[tuple[str, bool]] = []
    for p in parts:
        segments = _CONJ_SPLIT.split(p)
        for idx, seg in enumerate(segments):
            is_post = idx > 0  # bağlaçtan sonra mı?
            for chunk in re.split(r"\s*,\s*", seg):
                c = chunk.strip()
                if len(c) >= 4:
                    out.append((c, is_post))
    return out or [(text.strip(), False)]


def _score_clause(clause: str, index: int, n: int, is_post_conj: bool = False) -> float:
    """LLM'in 'hangi parça asıl niyet?' dikkat skorunun kaba simülasyonu.

    Akıllı Negasyon Maskesi (Aşama 3):
    - Bir clause bağlaçtan (ama/fakat) SONRA geliyorsa VE REQUEST fiili taşıyorsa:
      → Bu asıl talep kısmıdır, +2.5 bonus ver.
    - Bağlaçtan ÖNCE REQUEST fiili olan ama sonrası REJECT/olumsuzlama içeren yapılarda:
      → Önceki clause kazanır (skor farkıyla).

    Örn. A: "Turistik bölgede ofisimiz var [ama] yazılım arıyoruz"
      → post-conj clause: REQUEST(arıyoruz) → +2.5 → kazanır ✓
    Örn. B: "Sağlık sektöründe yazılım satıyoruz [ama] destek vermiyoruz"
      → post-conj clause: REJECT(vermiyoruz) ama REQUEST YOK → bonus YOK
      → pre-conj clause daha yüksek skorla kazanır ✓
    """
    c = clause.lower()
    score = 0.0

    if _REQUEST.search(c):
        score += 3.0
    if _RECENT.search(c):
        score += 2.0
    if _HYPOTH.search(c):
        score -= 4.0
    if _PAST.search(c) and not _REQUEST.search(c):
        score -= 2.0
    if _REJECT.search(c):
        # "X şart değil" / "şaka bir yana" → niyet değil
        score -= 3.0 if not _REQUEST.search(c) else 1.0
    if _SMALLTALK.search(c) and not _REQUEST.search(c):
        score -= 5.0

    # Akıllı bağlaç bonusu: post-conj + REQUEST → asıl talep kısmı
    if is_post_conj and _REQUEST.search(c):
        score += 2.5

    # Recency bias: sondaki cümleler (zaman kayması / asıl rica) avantajlı
    if n > 1:
        score += 1.5 * (index / (n - 1))

    # Çok kısa gürültü
    if len(c.split()) <= 2:
        score -= 1.0

    return score


# Sektörel niyet taşıyan kökler — temiz sorgudan atılamaz
_SECTORAL_INTENT_TERMS: dict[str, tuple[str, ...]] = {
    # lojistik archived
    # savunma archived
    "bilişim": ("bilişim", "yazılım", "kod", "döküman", "doküman", "debug", "script"),
    "sağlık": ("sağlık", "hastane", "klinik", "poliklinik", "teletıp"),
    # e_ticaret archived
    # finans archived
    "eğitim": ("eğitim", "lms", "öğrenci", "üniversite"),
    "turizm": ("turizm", "otel", "rezervasyon"),
}

_NEGATION_RX = re.compile(
    r"\b(de[gğ]il\w*|hari[cç]|d[ıi][sş][ıi]nda|asla|istemiyoruz|not|vazge[cç]\w*|boşver|bırak\w*)\b",
    re.I,
)


def _extract_negated_sectors(text: str) -> list[str]:
    """Negasyon ÖNCESİNDEKI sektörel kavramları çıkar (sonrası niyet olabilir).

    Örn: '(sağlık/hastane değil!) kod dökümanı' → yalnızca sağlık;
    'kod' olumsuzlanmaz.
    """
    t = text.lower()
    found: list[str] = []
    for sektor, terms in _SECTORAL_INTENT_TERMS.items():
        for term in terms:
            # term[/term2] ... değil/hariç/asla  (terim negasyondan ÖNCE)
            pat = re.compile(
                rf"\b{re.escape(term)}\w*(?:\s*/\s*[a-zçğıöşü]+)*"
                rf".{{0,20}}{_NEGATION_RX.pattern}",
                re.I,
            )
            if pat.search(t):
                found.append(sektor)
                break
    out: list[str] = []
    for s in found:
        if s not in out:
            out.append(s)
    return out


def _sectoral_terms_in(text: str) -> list[str]:
    """Metinde geçen sektörel niyet token'ları (kök düzeyinde)."""
    t = text.lower()
    hits: list[str] = []
    for _sektor, terms in _SECTORAL_INTENT_TERMS.items():
        for term in terms:
            if re.search(rf"\b{re.escape(term)}\w*", t):
                if term not in hits:
                    hits.append(term)
    return hits


def _to_clean_query(clause: str, drop_positive_sectors: set[str] | None = None) -> str:
    """Seçilen niyet cümlesini kısa arama sorgusuna sıkıştır."""
    blob = clause.lower()
    drop_positive_sectors = drop_positive_sectors or set()
    # Olumsuzlanan sektör kelimelerini olumlu sinyal olarak bırakma
    for sektor in drop_positive_sectors:
        for term in _SECTORAL_INTENT_TERMS.get(sektor, ()):
            blob = re.sub(rf"\b{re.escape(term)}\w*", " ", blob)
    # Red/terk + smalltalk ifadelerini sorgudan temizle
    blob = _REJECT.sub(" ", blob)
    blob = _SMALLTALK.sub(" ", blob)
    blob = re.sub(r"\b(onu|bunu|bunları|atıp|geçen\s+yıl|dün|bugün|bundan)\b", " ", blob)
    # Bileşik kelimeleri koru (e-ticaret, check-in)
    tokens = re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+(?:-[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+)*", blob)
    kept = [t for t in tokens if t not in _STOP and len(t) > 2]
    # Rica fiillerini sorgudan düş (ürün odaklı kalsın)
    drop_verbs = {
        "arıyoruz", "arıyorum", "istiyoruz", "istiyorum", "bakıyoruz",
        "lazım", "bulur", "musun", "kuracağız", "geçtik", "geciyoruz",
        "öncelik", "kesinlikle", "acil", "arada", "need", "looking",
        "want", "require", "seeking", "gidermek", "istiyorum",
    }
    kept = [t for t in kept if t not in drop_verbs]
    # Genel dolgu isimler (ürün adı varken BGE'yi saptırır: "e-ticaret altyapısı"→yanlış sektör)
    filler = {"altyapısı", "altyapı", "yazılımı", "yazilimi", "otomasyonu", "modülü", "modulu"}
    if len(kept) > 1:
        kept = [t for t in kept if t not in filler] or kept
    if not kept:
        return clause.strip()
    # En fazla ~14 token (sektörel koruma için biraz daha geniş)
    return " ".join(kept[:14])


def _normalize_surface_noise(text: str) -> str:
    """Leet / noktalı yazım — sorgu yüzeyi temizliği (sektör etiketlemez)."""
    t = text
    # f.i.n.a.n.s → finans
    t = re.sub(
        r"\b(?:[a-zçğıöşü]\.){2,}[a-zçğıöşü]\b",
        lambda m: m.group(0).replace(".", ""),
        t,
        flags=re.I,
    )
    # Chatbot._normalize ile aynı leet sözleşmesi (+ ekstra homoglyph)
    leet = str.maketrans({
        "!": "i", "1": "i", "0": "o", "@": "a", "3": "e",
        "4": "a", "5": "s", "7": "t",
    })
    t = t.translate(leet)
    return t


class SimulatedLLMBackend:
    """
    Çevrimiçi LLM yokken aynı sözleşmeyi yerine getirir.
    Bağlaç ezberi yok: tüm clause'lar skorlanır, kazanan sıkıştırılır.
    Negasyon + sektörel niyet koruması uygulanır.
    """

    def rewrite(self, text: str) -> RewriteResult:
        raw = (text or "").strip()
        if not raw:
            return RewriteResult(raw, raw, "simulated", "empty")

        raw = _normalize_surface_noise(raw)
        negated = _extract_negated_sectors(raw)
        negated_set = set(negated)

        # Akıllı bağlaç maskesi: clause pozisyonunu (ama-öncesi/sonrası) skorlamaya taşı
        clauses_pos = _split_clauses_with_pos(raw)
        scored = [
            (i, cl, _score_clause(cl, i, len(clauses_pos), is_post_conj=is_post))
            for i, (cl, is_post) in enumerate(clauses_pos)
        ]
        scored.sort(key=lambda x: x[2], reverse=True)
        best_i, best_cl, best_s = scored[0]

        # Yakın skorlu sonraki clause'ları birleştir
        merged = [best_cl]
        for i, cl, s in scored[1:]:
            if s >= best_s - 1.0 and i >= best_i:
                merged.append(cl)
            if len(merged) >= 3:
                break

        # Sektörel niyet clause'larını zorla dahil et (bağlam kaybını önle)
        for _i, cl, _s in scored:
            if cl in merged:
                continue
            terms = _sectoral_terms_in(cl)
            # Olumsuzlanmamış sektörel niyet taşıyan parçaları koru
            if terms and not (_NEGATION_RX.search(cl) and len(terms) <= 2):
                # Lojistik/savunma/bilişim niyet clause'ı
                if any(
                    t in cl.lower()
                    for t in (
                        "lojistik", "kargo", "rota", "sevkiyat", "depo",
                        "kod", "döküman", "doküman", "yazılım", "debug",
                    )
                ):
                    merged.append(cl)

        blob = " ".join(merged)
        clean = _to_clean_query(blob, drop_positive_sectors=negated_set)

        def _term_negated(term: str) -> bool:
            for sektor in negated_set:
                for t in _SECTORAL_INTENT_TERMS.get(sektor, ()):
                    if term == t or term.startswith(t) or t.startswith(term):
                        return True
            return False

        # Orijinaldeki sektörel niyet token'larını geri yaz (atıldıysa)
        for term in _sectoral_terms_in(raw):
            if _term_negated(term):
                continue
            if not re.search(rf"\b{re.escape(term)}\w*", clean, re.I):
                clean = f"{clean} {term}".strip()

        # Siber bağlamını koru
        if (
            re.search(r"\bsavunma", clean, re.I)
            and re.search(r"\bsiber\b|\bcyber\b", raw, re.I)
            and not re.search(r"\bsiber\b|\bcyber\b", clean, re.I)
        ):
            clean = f"siber {clean}".strip()

        # Negated_Sector_Keyword işaretleri
        markers = [f"Negated_Sector_Keyword:{s}" for s in negated]
        if markers:
            clean = f"{clean} {' '.join(markers)}".strip()

        note = (
            f"simulated clause-score: #{best_i} score={best_s:.1f} "
            f"negated={negated} → {clean!r}"
        )
        return RewriteResult(
            raw,
            clean or raw,
            "simulated",
            note,
            negated_sectors=tuple(negated),
        )


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------
class LLMRewriter:
    """
    Kullanım:
        rw = LLMRewriter()                 # otomatik backend
        rw = LLMRewriter(force_simulated=True)
        result = rw.rewrite(kullanici_metni)
    """

    def __init__(self, force_simulated: bool = False) -> None:
        self._backend: RewriterBackend
        api_key = os.getenv("LLM_REWRITER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if force_simulated or not api_key:
            self._backend = SimulatedLLMBackend()
            self.mode = "simulated"
        else:
            base = os.getenv("LLM_REWRITER_BASE_URL", "https://api.openai.com/v1")
            model = os.getenv("LLM_REWRITER_MODEL", "gpt-4o-mini")
            self._backend = OpenAICompatibleRewriter(api_key, base, model)
            self.mode = "api"

    def rewrite(self, text: str) -> RewriteResult:
        return self._backend.rewrite(text)
