"""
1000 sorguluk threshold tarama — Hibrit Mimari (BGE-M3 + SmartGate + Reranker + Soft Fusion).
Her sorgu icin fused skor hesaplanir, sonra farkli esikler taranir.
"""
import sys, os, logging, random
logging.disable(logging.CRITICAL)
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

sys.path.insert(0, ".")

# ── Augmented 1000-sorgu seti (ayni seed) ────────────────────────────────────
SEEDS = {
    "health": [
        "hastane yönetim yazılımı", "klinik randevu otomasyonu", "poliklinik iş akışı yazılımı",
        "hasta takip sistemi", "HBYS entegrasyonu", "e-nabız entegrasyonu",
        "tele-tıp altyapısı", "ameliyathane yönetim yazılımı", "hekim takvim sistemi",
        "uzaktan sağlık asistanı", "AHBS entegrasyonu", "muayene yönetim sistemi",
        "radyoloji dijital görüntüleme yazılımı", "acil servis yönetim yazılımı",
        "laboratuvar takip sistemi", "hemşire iş akışı otomasyonu", "tıbbi cihaz bakım takibi",
        "kurumsal sağlık bilgi sistemi", "doktor performans takip yazılımı", "klinik veri analiz platformu",
        "poliklinik yazılımı", "hasta kayıt sistemi", "eczane yönetim yazılımı",
        "sağlık analitik platformu", "bölgesel sağlık ağı entegrasyonu",
        "diyaliz merkezi yönetim yazılımı", "patoloji laboratuvarı otomasyon sistemi",
        "hasta faturalandırma yazılımı", "sağlık sigortası entegrasyon yazılımı",
        "mobil sağlık uygulaması geliştirme", "gece nöbeti planlama yazılımı",
        "sterilizasyon takip sistemi", "biyomedikal cihaz yönetimi",
        "tıbbi kayıt dijitalleştirme hizmeti", "röntgen arşiv sistemi PACS",
        "sağlık portalı yazılımı", "klinik test yönetim sistemi",
        "yoğun bakım takip yazılımı", "psikiyatri klinik yazılımı",
        "diş kliniği yönetim sistemi", "optisyen yönetim yazılımı",
        "fizyoterapi klinik yazılımı", "onkoloji vaka takip sistemi",
        "hematoloji laboratuvar yazılımı", "nöroloji klinik veri sistemi",
        "kardiyoloji takip yazılımı kurumsal", "ortopedi klinik yönetimi",
        "tıbbi görüntü işleme yazılımı", "klinik karar destek sistemi",
        "sağlık hizmetleri kalite güvence yazılımı",
    ],
    "defense": [
        "radar veri analiz yazılımı", "insansız hava aracı kontrol yazılımı",
        "askeri haberleşme altyapısı", "kripto komuta telsiz altyapısı",
        "hava savunma sistemi yazılımı", "komuta kontrol sistemi",
        "siber güvenlik saldırı tespit sistemi", "kriptolu haberleşme entegrasyonu",
        "savunma sanayi yerli yazılım", "İHA filo yönetim yazılımı",
        "TSK lojistik yönetim sistemi", "elektronik harp yazılımı",
        "askeri lojistik takip yazılımı", "denizaltı sonar yazılımı",
        "kara kuvvetleri personel yönetim sistemi", "savunma projesi yazılım geliştirme",
        "mayın tespit sistemi yazılımı", "gece görüş sistemi entegrasyonu",
        "savaş simülatörü yazılımı", "zırhlı araç kontrol yazılımı",
        "füze güdüm sistemi yazılımı", "savunma bütçe planlama sistemi",
        "askeri envanter yönetim yazılımı", "NATO uyumlu haberleşme sistemi",
        "saha komuta kontrol uygulaması", "radar izleme ve takip yazılımı",
        "hava trafik kontrol yazılımı savunma", "silahlı İHA yazılım entegrasyonu",
        "uydu haberleşme şifreleme yazılımı", "deniz gücü operasyon yazılımı",
        "elektronik istihbarat yazılımı", "hedef tespit ve tanıma yazılımı",
        "kriptografik protokol entegrasyonu", "askeri proje yönetim yazılımı",
        "güvenli veri aktarım sistemi savunma", "savunma tedarik zinciri yazılımı",
        "muharebe simülasyon platformu", "hava ikmal sistemi yazılımı",
        "çok fonksiyonlu radar yazılımı", "savunma Ar-Ge yönetim platformu",
        "deniz mayını tespit yazılımı", "topçu ateş kontrol sistemi",
        "gözetleme kamera analitik yazılımı savunma", "askeri harita ve coğrafi bilgi sistemi",
        "savunma sanayi ihale takip yazılımı", "kara radar entegrasyonu",
        "insansız deniz aracı kontrol yazılımı", "siber savunma operasyon merkezi yazılımı",
        "savunma sanayi ERP sistemi", "ASELSAN entegrasyon yazılımı",
    ],
    "education": [
        "öğrenci bilgi sistemi OBS", "üniversite otomasyon sistemi",
        "LMS kurulumu yazılımı", "kampüs yönetim sistemi",
        "e-öğrenme platformu", "sınav değerlendirme sistemi",
        "üniversite kütüphane otomasyon sistemi", "ÖBYS entegrasyonu",
        "öğrenci devam takip sistemi", "akademik kadro yönetim sistemi",
        "uzaktan eğitim altyapısı", "öğrenci burs yönetim sistemi",
        "transkript diploma sistemi", "ders programı planlama yazılımı",
        "öğrenci danışmanlık sistemi", "kampüs portal entegrasyonu",
        "öğrenci harç yönetim sistemi", "okul yönetim yazılımı",
        "çift anadal yönetim yazılımı", "yaz okulu kayıt sistemi",
        "öğrenci kariyer merkezi yazılımı", "mezuniyet takip sistemi",
        "öğrenci etkinlik yönetim platformu", "dijital sınıf yönetim yazılımı",
        "eğitim analitik platformu", "öğrenci geri bildirim sistemi",
        "akademik değerlendirme yazılımı", "öğrenci kimlik kart sistemi",
        "kampüs güvenlik yönetim yazılımı", "öğrenci yurt yönetim sistemi",
        "eğitim ERP sistemi", "öğrenci sağlık merkezi yazılımı",
        "ilköğretim okul yönetim yazılımı", "lise otomasyon sistemi",
        "mesleki eğitim kurumu yazılımı", "sertifika ve belge yönetim sistemi",
        "öğrenci proje takip yazılımı", "akademik takvim planlama sistemi",
        "e-sınav güvenlik yazılımı", "eğitim kurumu muhasebe yazılımı",
        "staj takip yönetim sistemi", "mezun takip sistemi",
        "öğretmen performans değerlendirme sistemi", "öğrenci mentoring platformu",
        "kampüs Wi-Fi yönetim yazılımı", "öğrenci giriş çıkış takip sistemi",
        "interaktif akıllı tahta yazılımı", "dijital öğrenci portföy sistemi",
        "çevrimiçi sınav platformu", "öğrenci beklenti analiz yazılımı",
    ],
    "tourism": [
        "otel rezervasyon yazılımı", "turizm acentası tur satış platformu",
        "otel biletleme motoru yazılımı", "konaklama yönetim sistemi",
        "tatil paketi satış platformu", "otel check-in otomasyon yazılımı",
        "tur operatörü CRM sistemi", "PNR yönetim sistemi",
        "havayolu bilet satış yazılımı", "resort misafir deneyim yazılımı",
        "online ödeme entegrasyonu turizm", "otel fiyat kanal manager yazılımı",
        "seyahat acentası B2B rezervasyon", "müze dijital biletleme sistemi",
        "kamp outdoor rezervasyon yazılımı", "termal otel SPA yönetim yazılımı",
        "kruvaziyer yolcu yönetim sistemi", "kurumsal tatil planlama yazılımı",
        "golf sahası rezervasyon yazılımı", "uçak otel kombine satış platformu",
        "butik otel yönetim yazılımı", "kış turizmi kayak merkezi yazılımı",
        "tur rehberi takip sistemi", "turizm analitik platformu",
        "otel gelir yönetim yazılımı", "misafir sadakat programı yazılımı",
        "villa kiralama yönetim platformu", "etkinlik organizasyon yazılımı turizm",
        "yat marina yönetim sistemi", "kültür turu dijital rehberlik yazılımı",
        "otel temizlik yönetim yazılımı", "oda servisi otomasyon sistemi",
        "kongre toplantı yönetim yazılımı", "seyahat sigortası entegrasyon yazılımı",
        "transfer ve ulaşım yönetim yazılımı", "vize takip entegrasyon sistemi",
        "turizm ihracat platformu yazılımı", "otel insan kaynakları yazılımı",
        "sağlık turizmi yönetim yazılımı", "agro turizm rezervasyon platformu",
        "turizm bakanlığı entegrasyon yazılımı", "otel enerji yönetim sistemi",
        "misafir deneyim anketi platformu", "turizm şikayeti takip sistemi",
        "otel havuz fitness yönetim yazılımı", "restoran rezervasyon entegrasyon sistemi",
        "turizm franchise yönetim yazılımı", "çevrimiçi seyahat acentası platformu",
        "otel güvenlik yönetim yazılımı", "turizm raporlama analitik yazılımı",
    ],
    "ood": [
        "havalar bugün nasıl", "borsa fiyatları ne kadar",
        "kardiyoloji doktorundan randevu almak istiyorum",
        "üniversite harç ödememi nereye yapacağım",
        "antalyada en ucuz otel bulmak istiyorum",
        "trafik kazası haberleri", "oyun bilgisayarı fiyatları",
        "kargo rota optimizasyonu",
        "bitcoin fiyatı", "sosyal medya hesap güvenliği",
        "aselsan hisse senedi", "pizza sipariş vermek",
        "araba tamiri usta", "bordro yazılımı",
        "e-ticaret sitesi kurmak istiyorum",
        "muhasebe yazılımı ERP genel",
        "CRM yazılımı arıyoruz sektörsüz",
        "sel felaketi haber takibi", "kripto para yatırımı",
        "tarım sulama sistemi yazılımı",
        "inşaat proje yönetim yazılımı",
        "otomobil satış platformu yazılımı",
        "perakende mağaza yönetim yazılımı",
        "finans sektörü risk analiz yazılımı",
        "elektrik dağıtım şebeke yönetim yazılımı",
        "iklim değişikliği raporu haberleri",
        "uluslararası nakliye lojistik sistemi",
        "hukuk bürosu dava takip yazılımı",
        "spor kulübü yönetim yazılımı",
        "medya yayın akış platformu yazılımı",
        "emlak gayrimenkul yönetim yazılımı",
        "restoran yönetim yazılımı",
        "sağlık eğitim hastane değil yazılım değil genel bilgi",
        "yapay zeka genel danışmanlık hizmeti",
        "blockchain tabanlı tedarik zinciri genel",
        "veri merkezi altyapı yönetimi genel",
        "nesnelerin interneti IoT platformu genel",
        "bulut bilişim geçiş danışmanlığı genel",
        "sigorta hasar yönetim yazılımı",
        "enerji verimliliği izleme yazılımı",
        "kamu yönetim e-devlet yazılımı genel",
        "çevre izleme sistemi yazılımı",
        "tarım drone ilaçlama yazılımı",
        "güzellik salonu yönetim yazılımı",
        "veteriner klinik yazılımı",
        "optik mağaza yönetim yazılımı bireysel",
        "fırın pastane yönetim yazılımı",
        "çocuk kreş yönetim yazılımı",
        "berber kuaför yönetim yazılımı",
    ],
}

PREFIXES = [
    "lütfen", "acil olarak", "şirketimiz için", "kurumsal düzeyde",
    "bize", "hızlıca", "yeni bir", "acaba", "şirketimiz olarak",
    "kurum olarak", "projemiz için", "ihale kapsamında",
    "çözüm ortağı arıyoruz:", "merhaba",
]
SUFFIXES = [
    "entegrasyonu istiyoruz", "yazılımı gerekiyor", "çözümüne ihtiyacımız var",
    "sistemi lazım", "altyapısı kurulacak", "hizmeti almak istiyoruz",
    "konusunda teklif istiyoruz", "için firma arıyoruz",
    "modülü lazım", "platformu kurmak istiyoruz",
]

random.seed(42)

def augment(seed, label, n):
    out = []
    for _ in range(n):
        s = seed
        if random.random() < 0.4:
            s = random.choice(PREFIXES) + " " + s
        if label != "ood" and random.random() < 0.5:
            s = s + " " + random.choice(SUFFIXES)
        out.append((s.strip(), label))
    return out

def build_dataset(target=1000):
    per_sector = target // len(SEEDS)
    data = []
    for label, seeds in SEEDS.items():
        base = [(s, label) for s in seeds]
        data.extend(base)
        remaining = per_sector - len(base)
        for i in range(remaining):
            seed = seeds[i % len(seeds)]
            data.extend(augment(seed, label, 1))
    random.shuffle(data)
    return data[:target]


SECTOR_MAP = {
    "sağlık": "health", "saglik": "health",
    "turizm": "tourism", "savunma": "defense",
    "eğitim": "education", "egitim": "education",
}


def main():
    dataset = build_dataset(1000)
    label_counts = {}
    for _, lbl in dataset:
        label_counts[lbl] = label_counts.get(lbl, 0) + 1
    print(f"Dataset: {len(dataset)} sorgu | Dagılım: {label_counts}", flush=True)

    print("Modeller yukleniyor (BGE-M3 + Reranker)...", flush=True)
    from src.embedder import get_embedder
    from src.models.reranker import get_reranker
    from src.score_fusion import fuse_bge_rerank
    from src.smart_gate import SMART_RERANK_SKIP_THRESHOLD, should_skip_reranker

    emb = get_embedder()
    reranker = get_reranker()
    print("Modeller hazir.", flush=True)

    print("Sorgular isleniyor...", flush=True)
    results = []
    for i, (query, true_label) in enumerate(dataset):
        # BGE retrieval
        hits = emb.find_top_k_hybrid(query, k=1, alpha=0.9)
        if not hits:
            fused_score, pred = 0.0, "ood"
        else:
            best_hit = hits[0]
            bge_score = float(best_hit.score)
            meta_sector = (best_hit.metadata or {}).get("beklenen_sektor") or ""
            pred = SECTOR_MAP.get(str(meta_sector).strip().lower(), "ood")

            # SmartGate: yüksek BGE → Reranker atlat
            if should_skip_reranker(bge_score):
                fused_score = bge_score
            else:
                # Reranker
                try:
                    rr_scores = reranker.score(query, [best_hit.text or ""])
                    rr = float(rr_scores[0]) if rr_scores else bge_score
                    fused_score = float(fuse_bge_rerank(bge_score, rr))
                except Exception:
                    fused_score = bge_score

        results.append({"true": true_label, "pred": pred, "fused": fused_score})

        if (i + 1) % 100 == 0:
            print(f"  {i+1}/1000 tamamlandi...", flush=True)

    n_ood = sum(1 for r in results if r["true"] == "ood")
    n_b2b = len(results) - n_ood

    print("\n" + "=" * 110)
    print(f"{'Esik':<7} | {'Dogruluk':>9} | {'TA(B2B OK)':>14} | {'FAR(OOD->OK)':>14} | {'FRR(B2B->OOD)':>15} | {'TR(OOD Red)':>13} | {'Toplam':>8}")
    print("=" * 110)

    thresholds = [i / 100 for i in range(50, 92)]
    best_t, best_acc, best_stats = 0.0, 0.0, {}

    for t in thresholds:
        ta = fa = fr = tr_count = 0
        for r in results:
            final = r["pred"] if r["fused"] >= t else "ood"
            is_ood = (r["true"] == "ood")
            if is_ood and final == "ood":
                tr_count += 1
            elif not is_ood and final == r["true"]:
                ta += 1
            elif is_ood and final != "ood":
                fa += 1
            else:
                fr += 1

        total_correct = ta + tr_count
        acc = total_correct / len(results)
        far_pct = fa / n_ood * 100 if n_ood else 0
        flag = " <-- UYARI FAR>0" if fa > 0 else ""
        print(f"{t:.2f}    | {acc*100:>8.1f}% | {ta:>9}/{n_b2b} | {fa:>5} (%{far_pct:4.1f})   | {fr:>10}/{n_b2b} | {tr_count:>8}/{n_ood} | {total_correct:>5}/1000{flag}")

        if acc > best_acc and fa == 0:
            best_acc, best_t = acc, t
            best_stats = {"TA": ta, "FA": fa, "FR": fr, "TR": tr_count}
        elif acc == best_acc and fa == 0 and t < best_t:
            best_t = t
            best_stats = {"TA": ta, "FA": fa, "FR": fr, "TR": tr_count}

    print("=" * 110)
    print(f"\n*** EN IYI ESIK (FAR=0 sartiyla): {best_t:.2f} ***")
    print(f"    Genel Dogruluk : %{best_acc * 100:.1f}")
    print(f"    Dogru Kabul TA : {best_stats.get('TA', 0)}/{n_b2b}")
    print(f"    Yanlis Red FRR : {best_stats.get('FR', 0)}/{n_b2b}")
    print(f"    Yanlis Kabul FA: {best_stats.get('FA', 0)}/{n_ood}  (SIFIR olmali!)")
    print(f"    Dogru Red TR   : {best_stats.get('TR', 0)}/{n_ood}")


if __name__ == "__main__":
    main()
