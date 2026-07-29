"""B2B Intent Router — K1 Regex Guardrails + strict decision threshold.

Single source of truth for router_server.py and v2_pipeline.py:
  STEP 2 Clause Parse (extract_active_clause)   -> completed/rejected action
         clause'ları at, yalnızca aktif talebi bırak
  STEP 3 Hard OOD Blocklist (check_restricted_domain) -> Legal/Real Estate/
         Finance/Defense/Energy/Food-Hospitality -> her zaman REJECT
         (teknik jargon eşlik etse bile)
  IF   K1_Regex_Match (sector)   -> ACCEPT (confidence 1.00, <5ms, no embedding call)
  ELIF OOD_Fast_Reject (B2C/chat)-> REJECT (<1ms, no embedding call)
  ELIF BGE_M3_Raw_Score >= 0.65  -> ACCEPT
  ELSE                           -> REJECT ("Sektör Belirsiz")

No reranker / cross-encoder / fusion step anywhere in this decision.
"""

from __future__ import annotations

import re

DECISION_THRESHOLD = 0.65

# STOPGAP (Asama 2 yanlış-pozitif düzeltmesi):
# 'yazilim', 'sistem', 'platform', 'otomasyon', 'altyapi' sektörler arası jenerik kelimeler —
# bunları bare B2B_MODIFIERS fallback'ten çıkardık; sadece K2/BGE-M3'e bırakıyoruz.
# Asama 3'te bağlam-farkında K1 ile geri getirilecek.
B2B_MODIFIERS = re.compile(
    r'\b(saas|api|cloud|portal|portalı|ağ\s*yönetimi|network\s*yönetimi|e-öğrenme|lms\s*platform|devops|ci\/cd|sızma\s*testi)\b',
    re.IGNORECASE
)

SECTOR_MAP: dict[str, str] = {
    "sağlık": "saglik", "saglik": "saglik",
    "turizm": "turizm",
    "eğitim": "egitim", "egitim": "egitim",
    "bilişim": "bilisim", "bilisim": "bilisim",
    "eğlence": "eglence", "eglence": "eglence",
}

STRICT_SECTOR_REGEX: dict[str, re.Pattern[str]] = {
    "saglik": re.compile(
        r"\b("
        r"hastane|hastne|hbys|poliklinik|klinik|hekim|medikal|sağlık|saglik|"
        r"hl7|fhir|pacs|lis|randevu\s*sistemi|klinik\s*otomasyon"
        r")\b",
        re.IGNORECASE,
    ),
    "egitim": re.compile(
        r"\b("
        r"öbs|obs|lms|okul|üniversite|universite|akademik|eğitim|egitim|"
        r"öğrenci|ogrenci|ldap|sso|kampüs\s*bilgi|kampus\s*bilgi|"
        r"üniversite\s*otomasyon|universite\s*otomasyon"
        r")\b",
        re.IGNORECASE,
    ),
    "turizm": re.compile(
        r"\b("
        r"pms|otel|otelleri|rezervasyon|acente|turizm|konaklama|booking|"
        r"channel\s*manager|gds|kanal\s*yöneticisi|kanal\s*yoneticisi|"
        r"otel\s*zinciri"
        r")\b",
        re.IGNORECASE,
    ),
    "bilisim": re.compile(
        r"\b("
        # Spesifik/kesin teknik terimler — sektörler arası çakışma riski yok
        r"api|sdk|saas|bulut|cloud|entegrasyon|crm|erp|"
        r"siber\s*güvenlik|siber\s*guvenlik|veritabanı|veritabani|kodlama|sunucu|server|"
        r"network|ağ\s*yönetimi|ag\s*yonetimi|alientos|alintos|alientas|buyumevizyon|büyümevizyon|ddx|ddx\+|"
        r"turquality|e-turquality|dijital\s*dönüşüm|dijital\s*donusum|kosgeb|kosgeb\s*desteği|kosgeb\s*teşviği|it\s*altyapı|it\s*altyapısı|"
        r"dashboard|bi\s*tool|powerbi|business\s*intelligence|"
        r"bulut\s*altyapı|bulut\s*altyapisi|devops\s*otomasyon|ci\/cd\s*boru|sızma\s*testi|güvenlik\s*duvarı"
        # KALDIRILDI (stopgap): 'yazilim', 'otomasyon' — cross-sector, 9 yanlış-pozitif kaynağı
        r")\b",
        re.IGNORECASE,
    ),
    "eglence": re.compile(
        r"\b("
        r"ott|streaming|yayıncılık|yayincilik|oyun\s*motoru|unity|unreal|render|"
        r"oyun\s*geliştirme|oyun\s*gelistirme|metacast|medya|etkinlik|konser|biletleme|"
        r"bilet\s*sistemi|bilet\s*satış|bilet\s*satis|etkinlik\s*yönetimi|etkinlik\s*yonetimi|festival\s*geçiş|festival\s*gecis"
        r")\b",
        re.IGNORECASE,
    ),
}


SECTOR_ANCHORS: dict[str, list[str]] = {
    "bilisim": [
        # Spesifik/Teknik terimler — güvenli, bağlam gerektirmiyor
        "api", "saas", "bulut", "sunucu", "veri tabanı", "siber güvenlik", "yazılım", "kod", "lisanslama", "entegrasyon",
        "dijital dönüşüm", "dijital olgunluk", "teşvik danışmanlığı", "kosgeb desteği", "ddx", "ddx+", "turquality",
        "e-turquality", "alientos", "buyumevizyon", "kosgeb", "kosgeb teşviği", "alintos", "alientas", "it altyapı", "it altyapısı",
        "dashboard", "bi tool", "powerbi", "business intelligence",
        # Bileşik kalıplar — güvenli, spesifik bağlam taşıyor
        "bulut altyapı", "devops otomasyon", "ci/cd boru hattı", "sızma testi", "güvenlik duvarı",
        # KALDIRILDI (stopgap — Asama 2 yanlış-pozitif kaynağı):
        # "platform", "otomasyon", "sistem", "altyapı"
        # Bu 4 bare kelime cekim eki testinde 9 yanlış-pozitif vakayla kanıtlandı.
        # Asama 3'te bağlam-farkında K1 ile geri getirilecek.
    ],
    "saglik": ["hasta", "hastane", "randevu", "tahlil", "klinik", "hekim", "doktor", "reçete", "poliklinik", "tıbbi"],
    "egitim": ["kurs", "uzaktan eğitim", "okul", "sınav", "öğrenci", "ders", "eğitmen", "devamsızlık", "müfredat", "l&d", "kurumsal akademi", "akademi", "akademisi", "akademisinde", "e-öğrenme", "öğrenme"],
    "turizm": ["otel", "rezervasyon", "uçak bileti", "acente", "tur", "konaklama", "uçuş", "tatil"],
    "eglence": ["konser", "tiyatro", "etkinlik", "bilet", "organizasyon", "mekan", "koltuk seçimi", "gösteri", "bilet sistemi", "bilet satış", "etkinlik yönetimi", "festival geçiş"],
}


def check_regex_match(query: str, sector: str) -> bool:
    """Sorguda ilgili sektörün anchor kelimelerinden en az 2 tanesi geçiyor mu?"""
    q = (query or "").lower()
    keywords = SECTOR_ANCHORS.get(sector)
    if not keywords:
        return False
    hits = 0
    for kw in keywords:
        escaped_kw = re.escape(kw)
        pattern = rf"\b{escaped_kw}\b" if " " in kw else rf"\b{escaped_kw}\w*\b"
        if re.search(pattern, q, re.IGNORECASE):
            hits += 1
    return hits >= 2


def match_any_sector(query: str) -> str | None:
    """
    Aynı sektör kümesinden EN AZ 2 kelime geçiyorsa ve çakışma yoksa doğrudan o sektörü döner.
    Ayrıca Alientos/Büyümevizyon/DDX/Turquality marka ve hizmetleri için tek-kelime deterministic match sağlar.
    Aksi takdirde None döner (K2/V2 pipeline'ına devreder).
    """
    q = (query or "").lower()
    
    # 1. Önce Hard OOD / Kısıtlı alan kelimesi var mı kontrol et!
    if check_restricted_domain(query):
        return None

    # 2. OOD terim yoksa veya B2B modifiyeri ile muaf tutulmuşsa K1 Marka/Hizmet Match (Fast-Path) çalışsın
    if re.search(r"\b(alientos|alintos|alientas|buyumevizyon|büyümevizyon|ddx\+|ddx|turquality|e-turquality|dijital\s*dönüşüm|dijital\s*donusum|kosgeb|it\s+altyapı|it\s+altyapısı|saas\s+vendor|custom\s+crm|crm\s+platform)\b|info@buyumevizyon\.com", q):
        return "bilisim"

    sector_hits = {}
    for sector, keywords in SECTOR_ANCHORS.items():
        hits = 0
        for kw in keywords:
            escaped_kw = re.escape(kw)
            pattern = rf"\b{escaped_kw}\b" if " " in kw else rf"\b{escaped_kw}\w*\b"
            if re.search(pattern, q, re.IGNORECASE):
                hits += 1
        if hits >= 2:
            sector_hits[sector] = hits

    if len(sector_hits) == 1:
        return list(sector_hits.keys())[0]
    elif len(sector_hits) > 1:
        return max(sector_hits, key=sector_hits.get)

    # 3. Hiçbir sektör >= 2 hit almadıysa ama B2B modifiyeri varsa bilisim'e yönlendir (Fallback)
    if B2B_MODIFIERS.search(q):
        return "bilisim"

    return None


def check_any_regex_match(query: str) -> bool:
    return match_any_sector(query) is not None


# ─────────────────────────────────────────────────────────────────────────────
# OOD Fast-Reject — B2C / chit-chat guardrail (checked after K1 sector regex,
# before BGE-M3). Eşleşme -> anında REJECT, embedding çağrılmaz.
# Amaç: "bugün hava nasıl" gibi genel sorguların yüksek BGE skoruyla
# yanlışlıkla ACCEPT edilmesini önlemek.
# ─────────────────────────────────────────────────────────────────────────────
OOD_FAST_REJECT_REGEX: re.Pattern[str] = re.compile(
    r"\b("
    r"hava\s*durumu|hava\s*nasil|hava\s*nasıl|hava\s*sicakligi|hava\s*sıcaklığı|"
    r"fikra|fıkra|saka\s*yap|şaka\s*yap|komik\s*bir\s*sey|"
    r"nasilsin|nasılsın|nasilsiniz|nasılsınız|naber|ne\s*haber|"
    r"agri\s*kesici|ağrı\s*kesici|parasetamol|aspirin|"
    r"yks|lgs|kpss|dgs|tyt|ayt|taban\s*puan\w*|burs\s*imkan\w*|burs\s*basvuru\w*|"
    r"burc|burç|astroloji|fal\s*bak|"
    r"mac\s*sonucu|maç\s*sonucu|"
    r"kac\s*yasindasin|kaç\s*yaşındasın|seni\s*kim\s*yapti|seni\s*kim\s*yaptı"
    r")\b",
    re.IGNORECASE,
)


def check_ood_reject(query: str) -> bool:
    """B2C/chit-chat guardrail eşleşiyor mu? True → anında REJECT."""
    return bool(OOD_FAST_REJECT_REGEX.search(query or ""))


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Clause Boundary & Action-State Parsing (tamamlanmış/reddedilen eylem
# temizliği). Sorgu noktalama/bağlaçlara göre clause'lara bölünür;
# COMPLETION_TRIGGER_REGEX içeren clause'lar atılır, yalnızca aktif/bekleyen
# talep STEP 3 ve K2 vektör aramasına bırakılır.
# Örn: "Poliklinik hallettik, kantin için teklif istiyoruz"
#      -> "Poliklinik hallettik" atılır -> "kantin için teklif istiyoruz" kalır.
# ─────────────────────────────────────────────────────────────────────────────
COMPLETION_TRIGGER_REGEX: re.Pattern[str] = re.compile(
    r"\b("
    r"hallettik|zaten\s*aldık|zaten\s*aldik|istemiyoruz|istemiyorum|"
    r"tamamladık|tamamladik|çözdük|cozduk|çözüldü|cozuldu|bitti|bittik|"
    r"var\s*zaten|artık\s*gerekmiyor|gerekmiyor|"
    r"already\s*(bought|have|got|taken|purchased|handled|solved|sorted)|"
    r"sorted\s*out|dealt\s*with|taken\s*care\s*of|took\s*care\s*of|"
    r"we\s*(already|have|don.t\s*need)|we.ve\s*(already|got|handled|sorted|dealt)|"
    r"no\s*longer|not\s*(looking|interested|relevant)"
    r")\b",
    re.IGNORECASE,
)

_CLAUSE_SPLIT_REGEX: re.Pattern[str] = re.compile(
    r",|;|\bama\b|\bfakat\b|\blakin\b|\bancak\b|\bbut\b|\balthough\b|\bhowever\b",
    re.IGNORECASE,
)


def extract_active_clause(query: str) -> str:
    """
    STEP 2: Sorguyu noktalama/bağlaçlara göre clause'lara böl, tamamlanmış/
    reddedilen eylem içeren clause'ları at, yalnızca aktif talebi döndür.
    Tüm clause'lar atılırsa (aşırı temizlik riski) orijinal sorgu korunur.
    """
    q = (query or "").strip()
    if not q:
        return q
    clauses = [c.strip() for c in _CLAUSE_SPLIT_REGEX.split(q) if c.strip()]
    if not clauses:
        return q
    active = [c for c in clauses if not COMPLETION_TRIGGER_REGEX.search(c)]
    if not active:
        return q
    return " ".join(active)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Hard Blocklist: Restricted & Out-of-Scope Domains. Legal, Real
# Estate, Finance/Banking, Defense/Military, Energy, Auxiliary Food/Hospitality
# (Kantin/Cafeteria/Catering). Teknik jargonla (yazılım/software/platform/
# automation/portal/system) birlikte geçse bile HER ZAMAN OOD.
# STEP 2'nin aktif clause'u üzerinde çalışır — tamamlanmış eylemler içindeki
# yasaklı kelimeler (ör. "hallettik" clause'undaki "poliklinik") saymaz.
# ─────────────────────────────────────────────────────────────────────────────
RESTRICTED_DOMAIN_TERMS: list[str] = [
    # Legal / Hukuk
    "avukat", "lawyer", "hukuk", "legal", "dava", "mevzuat", "mahkeme", "court",
    "noterlik", "notary", "icra", "tahkim", "arbitration", "içtihat", "ictihat",
    # Real Estate / Gayrimenkul / Emlak
    "gayrimenkul", "real estate", "emlak", "tapu", "property listing",
    "kira sözleşmesi", "kira sozlesmesi", "lease contract",
    # Finance & Banking / Finans
    "bankacılık", "bankacilik", "banka", "banking", "borsa", "hisse", "finans",
    "finance", "finansal", "finansman", "kredi", "sigorta", "insurance",
    "yatırım", "yatirim", "investment", "fraud detection",
    "pos güvenliği", "pos guvenligi", "pos security",
    # Defense & Military / Savunma
    "savunma", "defense", "defence", "askeri", "military", "silah", "weapon",
    "iha", "uav",
    # Energy & Utilities / Enerji
    "enerji", "energy", "petrol", "oil", "rüzgar türbin", "ruzgar turbin",
    "wind turbine", "power analytics",
    # Auxiliary Food/Hospitality / İkincil Hizmetler
    "kantin", "yemekhane", "cafeteria", "catering",
    # Car Rental / Araç Kiralama / Filo
    "araç kiralama", "arac kiralama", "filo kiralama", "araba kiralama", "car rental", "vehicle rental", "kiralama", "filo", "filosu", "kiralık", "kiralik", "ev", "konut", "tir",
]

_RESTRICTED_TERM_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        rf"\b{re.escape(term)}\b" if len(term) <= 3 else rf"\b{re.escape(term)}\w*\b",
        re.IGNORECASE,
    )
    for term in RESTRICTED_DOMAIN_TERMS
]


def check_restricted_domain_raw(query: str) -> bool:
    """Yasaklı domain kontrolünü modifiyere bakmaksızın yalın olarak gerçekleştirir."""
    active_clause = extract_active_clause(query)
    return any(p.search(active_clause) for p in _RESTRICTED_TERM_PATTERNS)


def check_restricted_domain(query: str) -> bool:
    """STEP 3: Aktif clause'da yasaklı sektör terimi var mı? True → kesin OOD.
    Eğer aktif clause'da B2B modifiyeri bulunuyorsa engeli kaldırır (Stage 2 Override).
    Ancak masa, sandalye, koltuk, mobilya gibi fiziksel eşyalar her zaman OOD'dir."""
    active_clause = extract_active_clause(query)
    
    # Fiziki mobilya vb. doğrudan engellenir
    if re.search(r"\b(masa|sandalye|koltuk|mobilya)\b", active_clause, re.IGNORECASE):
        return True
        
    # B2B modifiyeri varsa OOD kısıtlamasını baypas et (Stage 2 Override)
    if B2B_MODIFIERS.search(active_clause):
        return False
        
    return check_restricted_domain_raw(query)
