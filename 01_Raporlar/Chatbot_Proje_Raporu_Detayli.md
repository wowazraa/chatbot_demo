# Chatbot Bilgi Merkezi Projesi — Ayrıntılı Rapor

**Proje:** Chatbot / Bilgi Merkezi — Sektör yönlendirme motoru  
**Tarih:** 17 Temmuz 2026  
**Kapsam:** Araştırma, mimari, uygulama durumu, kararlar, testler, sonraki adımlar  
**Aktif kod kökü:** `chatbot_demo/`

---

## 1. Yönetici Özeti

Bu proje, kurumsal ziyaretçinin mesajından **sektör** (sağlık, turizm, savunma, eğitim vb.) ve **mod** (doğrudan eşleşme / fallback / oturum hafızası) üreten bir Türkçe ağırlıklı chatbot motorudur. Amaç, kullanıcıyı doğru bilgi merkezi / form hattına yönlendirmek; emin olunmayan durumda ise zorla sektör atamak yerine **fallback (FB)** ile güvenli davranmaktır.

Bugün itibarıyla çalışan akış şöyledir: **LLM Query Rewriter → K1 Hint Collector (sektör atamaz) → K2 BGE-M3 anlamsal eşleştirme + skor karışımı → karar (K2 / FB / HAFIZA)**. Arayüz olarak hem Streamlit (`app.py`) hem hafif web demo (`demo/server.py`, Intent Inspector) mevcuttur. Politika olarak **precision-first** benimsenmiştir: doğru cevap, “her soruya bir sektör”den önce gelir; skorlar şişirilmez.

Kısa durum: motor politikası ve demo iskeleti oturmuştur. Asıl kaldıraç artık yeni kural eklemek değil; **temiz veri, indeks yenileme ve ölçüme dayalı iyileştirmedir.**

---

## 2. Projenin Amacı ve Kapsamı

### 2.1 Amaç
- Kullanıcı mesajını sektörel niyete göre sınıflandırmak.
- Belirsiz, small-talk veya çelişkili sorgularda yanlış yönlendirmeyi engellemek (FB).
- Çok turlu diyalogda önceki sektör bağlamını korumak (HAFIZA).
- Mentör / staj çerçevesinde: model seçimi, veri artırma, eşik ve mimari kararlarını belgelendirmek.

### 2.2 Kapsam içi
- Demo motoru ve UI (Streamlit + web inspector)
- Veri artırma pipeline’ı ve BGE-M3 indeksleme
- Stres / red-team test altyapısı
- Araştırma notları ve raporlar (`01_Raporlar`, `02_Toplanti_Notlari`)

### 2.3 Kapsam dışı (şimdilik)
- Üretim ortamı deploy / ölçekli API gateway
- Gerçek şirket form URL’lerinin canlı entegrasyonu (placeholder aşamasında)
- Tam LLM sohbet cevabı üretimi (odak: niyet / sektör yönlendirme)

---

## 3. Kronolojik Gelişim

| Dönem | Yapılanlar |
|-------|------------|
| Başlangıç | Klasör yapısı, ham veri, prototip scriptler, staj/rapor dokümanları |
| Model araştırması | Hugging Face adayları, MTEB mantığı, BGE-M3 / Türkçe embedding karşılaştırmaları, model dışı araştırma notları |
| Demo iskeleti | `chatbot_demo`: regex + veri artırma, simülatör, Streamlit |
| Anlamsal katman | BGE-M3 dense(+sparse) indeks, `embedder`, `build_index` |
| Motor evrimi | Rewriter, K1’in “atayan kural”dan “hint collector”a dönüşü, blend skor, session hafızası |
| Güven politikası | Sahte 0.85 skor şişirmesinin reddi; precision-first (`FINAL_MIN=0.75`, margin ile FB) |
| UX | Soft SaaS arayüz, inspector, `k1_hints` görünürlüğü |
| Temizlik | Klasör düzeni, ölü TF-IDF kodunun kaldırılması, obsolete testlerin arşivi |

---

## 4. Klasör ve Sistem Yapısı

```
Chatbot_Bilgi_Merkezi_Projesi/
├── 01_Raporlar/                 # Raporlar (bu dosya dahil)
├── 02_Toplanti_Notlari/         # Toplantı notları
├── archive/                     # Legacy kod + eski test çıktıları
│   ├── 03_Kaynak_Kod/
│   ├── test_ciktilari/
│   └── obsolete_tests/
└── chatbot_demo/                # Tek aktif uygulama
    ├── app.py                   # Streamlit demo
    ├── demo/                    # HTTP demo + index.html
    ├── src/                     # Motor
    │   ├── chatbot.py
    │   ├── llm_rewriter.py
    │   ├── embedder.py
    │   ├── frontend.py
    │   ├── data_augmented.py
    │   └── simulator.py
    ├── data/raw|processed/      # Veri + embeddings.npz
    ├── scripts/build_index.py
    ├── tests/ (+ fixtures/)
    └── reports/                 # Üretilen test raporları
```

**Çalıştırma:**
- Web demo: `python demo/server.py` → `http://localhost:8080`
- Streamlit: `streamlit run app.py`

---

## 5. Mimari

### 5.1 Uçtan uca akış

```
Kullanıcı mesajı
      │
      ▼
 LLMRewriter          → temiz sorgu, negasyon / small-talk ipuçları
      │
      ▼
 K1 Hint Collector    → sektör ATAMAZ; sektör başına hint_score ≤ 0.50
      │
      ▼
 K2 BGE-M3            → corpus benzerliği + sektör sinyali
      │
      ▼
 Blend                → Final(s) = 0.30·K1(s) + 0.70·K2(s)
      │
      ├── skor & margin yeterli → mod = K2, sektör atanır
      ├── belirsiz / yakın yarış / small-talk → mod = FB
      └── diyalog devamı (sektörsüz) → mod = HAFIZA
```

### 5.2 Katmanların rolü

| Katman | Rol | Ne yapmaz |
|--------|-----|-----------|
| **LLMRewriter** | Gürültüyü temizler, saf sorgu üretir; negasyonlu sektörleri işaretler | Nihai sektör kararı vermez |
| **K1 Hint Collector** | Regex / anahtar ile çoklu sektör ipucu toplar | Erken sektör ataması yapmaz; güveni 0.50 üstüne çıkarmaz |
| **K2 BGE-M3** | Anlamsal benzerlik (BAAI/bge-m3) | Tek başına “her zaman cevap” zorunluluğu yoktur |
| **Blend + kapı** | Final skor, sektör eşiği, `WIN_MARGIN` | Skoru yapay olarak şişirmez |
| **HAFIZA** | Oturumda bilinen sektörü diyalog devamında taşır | Yeni sektörel niyet yoksa zorla K2 üretmez |

### 5.3 Kritik sabitler (güncel politika)

| Sabit | Değer | Anlamı |
|-------|-------|--------|
| `K1_MAX_CONFIDENCE` | 0.50 | K1 asla nihai otorite gibi davranmaz |
| `K1_BLEND` / `K2_BLEND` | 0.30 / 0.70 | Karışım ağırlıkları |
| `FINAL_MIN` | 0.75 | Precision-first alt kapı |
| `WIN_MARGIN` | 0.06 | İki aday yakınsa → FB |
| Savunma eşiği | 0.82 | Corpus zehri / yanlış pozitife karşı daha sıkı |
| Diğer sektörler | ~0.75 | Varsayılan BGE kapısı |

### 5.4 Desteklenen sektör sinyalleri (motor sözlüğü)

sağlık, turizm, savunma, eğitim, finans, ik_kurumsal, bilişim, e_ticaret, lojistik (ve ilgili tuzak / soft-only kuralları).

### 5.5 Çıktı sözleşmesi (`ChatbotResponse`)

Başlıca alanlar: `sektor`, `mod` ∈ {`K2`, `FB`, `HAFIZA`}, `skor`, `yontem`, `aciklama`, `temiz_sorgu`, `k1_hints`, `negated_sectors`, `masked_sectors`. Web UI bunları `frontend.serialize_response` ile inspector’a taşır.

---

## 6. Veri ve İndeks

### 6.1 Ham veri
- Dosya: `data/raw/chatbot_dataset.json`
- Yaklaşık **116** kayıt (TR + EN karışık)
- Alanlar: `mesaj`, `lang`, `beklenen_sektor`, `beklenen_mod`, `zorluk`

Ham sektör dağılımı (özet): sağlık 27, turizm 20, savunma 15, eğitim 12, finans 10, ik_kurumsal 10; bir kısım kayıt sektör etiketi belirsiz (`?`).

### 6.2 Artırılmış veri
- Dosya: `data/processed/chatbot_dataset_augmented.json`
- Yaklaşık **4264** kayıt
- Yöntemler: yazım düzeltme / typo, prefix–suffix kombinasyonları, pattern varyasyonları (`src/data_augmented.py`)

### 6.3 Anlamsal indeks
- `scripts/build_index.py` + `src/embedder.py`
- Model: **BAAI/bge-m3**
- Çıktılar: `embeddings.npz`, `index_meta.json`

**Not:** Ham/artırılmış sette hâlâ eski `beklenen_mod: "K1"` etiketleri görülebilir. Motor artık atama modunu `K2` olarak döndürür; etiketlerin veri tarafında da güncellenmesi ileride yapılmalıdır.

---

## 7. Kullanıcı Arayüzleri

### 7.1 Web demo (`demo/`)
- Tek sayfa widget + Intent Inspector
- Temiz sorgu, güven bandı, maskelenen / negasyonlu sektörler, K1 ipuçları
- Canlı senaryo örneği (negasyon + lojistik)

### 7.2 Streamlit (`app.py`)
- Sohbet arayüzü + simülasyon / metrik sekmeleri
- Geliştirici kartında motor özeti (Rewriter → K1 hints → K2)

Görsel dil: soft lavender / slate / warm gray SaaS yaklaşımı; aşırı “AI cliché” (mor glow vb.) bilinçli olarak sınırlandırılmıştır.

---

## 8. Test ve Kalite

### 8.1 Aktif testler
| Test | Amaç |
|------|------|
| `tests/test_k1_celiski.py` | K1’in atama yapmadan çoklu ipucu üretmesi |
| `tests/run_stres_test.py` | Geniş senaryo bataryası (kategoriler: doğrudan, tuzak, negasyon, session…) |
| `tests/chaos_monkey_test.py` + fixture | Red-team / kırılma odaklı |
| `tests/the_crucible_test.py` + fixture | İleri düzey ölçüm |
| `src/simulator.py` + `fixtures/test_scenarios.json` | Demo simülasyonu |

### 8.2 Arşivlenenler
Tek seferlik kalibrasyon ve repro scriptleri `archive/obsolete_tests/` altına alınmıştır (sweep, check_eightyfive, singularity vb.). Geçmiş rapor çıktıları `archive/test_ciktilari/` içindedir.

### 8.3 Beklenti güncellemesi
Fixture ve stres senaryolarında atama beklenen mod **`K2`**, oturum devamı **`HAFIZA`**, belirsiz durumlar **`FB`** olacak şekilde hizalanmıştır.

---

## 9. Önemli Tasarım Kararları

1. **K1 sektör atamaz.** Erken regex kararı çoklu niyet ve tuzaklarda yanlış pozitif üretiyordu; K1 yalnızca ipucu üretir.
2. **Skor dürüstlüğü.** Eşik altında kalan skoru 0.85’e “kalibre etmek” reddedildi; bu, metriği değil güveni bozar.
3. **Precision-first.** `FINAL_MIN=0.75` ve `WIN_MARGIN` ile yakın yarışlarda FB tercih edilir. Mentöre anlatım: “her mesaja sektör” değil, “yanlış yönlendirmektense güvenli fallback”.
4. **BGE-M3.** Genel MTEB / çok dilli retrieval ihtiyacı ve yerel domain denemeleriyle ana embedding modeli olarak seçildi.
5. **TF-IDF yedek katmanı kaldırıldı.** Kullanılmayan sklearn yolu teknik borçtu; motor sadeleştirildi.
6. **Session = HAFIZA.** Diyalog devamında sektörel sinyal yoksa önceki sektör taşınır; bu durum K1/K2 ataması gibi raporlanmaz.

---

## 10. Bilinen Sınırlar ve Riskler

- **Veri kalitesi:** Artırma niceliği yüksek (≈4k); fakat etiket gürültüsü (`?` sektör) ve eski `K1` mod etiketleri temizlenmeden “doğal yüksek skor” beklentisi yanıltıcıdır.
- **Domain kayması:** Gerçek şirket metinleri / form URL’leri gelmeden üretim eşlemesi tamamlanmış sayılmaz.
- **Savunma / mecaz / small-talk:** Corpus zehri ve mecazi kullanımlar hâlâ false-positive üretebilir; bu yüzden savunma eşiği daha yüksek tutulmuştur.
- **Session senaryoları:** Hafıza vardır; ancak çok turlu gerçek kullanıcı davranışının tam kapsamlı ölçümü sürekli koşturulmalı ve FAIL’ler sınıflanmalıdır.
- **Çift demo:** Streamlit ve web demo birlikte yaşar; uzun vadede tek “resmi” sunum yüzeyi netleştirilebilir.

---

## 11. Sonraki Adımlar (Önerilen Yol Haritası)

### Kısa vade (1–2 hafta)
1. Ham + artırılmış veri etiket temizliği (`?` ve eski `K1` etiketleri).
2. `build_index.py` ile indeksi yeniden üretme.
3. Stres + Crucible’ı güncel motorla koşturma; FAIL’leri kategorize etme (yanlış sektör / aşırı FB / session).
4. Mentör demosu için 6–8 mesajlık senaryo seti (3 doğru K2, 1 FB, 1 negasyon, 1 HAFIZA, 1 tuzak).

### Orta vade
5. Zayıf sektörlere (ve yeni gelen şirket sektörlerine) kontrollü örnek ekleme — miktar değil etiket doğruluğu.
6. Gerçek form URL / bilgi merkezi eşlemesinin bağlanması.
7. Tek raporda “yanlış pozitif maliyeti”nin düzenli ölçümü (precision odaklı dashboard).

### Uzun vade
8. Üretim API / auth / logging.
9. Gerekirse yeniden sıralama (reranker) veya şirket-özel corpus fine-tune — ancak önce temiz veri + ölçüm.

---

## 12. Mentör / Toplantı İçin Tek Cümlelik Mesajlar

- **Ne yaptık?** Rewriter + hint + BGE-M3 tabanlı, dürüst skorlu bir sektör yönlendirme demosu.
- **Neden FB var?** Yanlış sektöre göndermek, cevap vermemekten daha maliyetli.
- **Model dışında ne var?** Veri artırma, eşik politikası, negasyon/tuzak kuralları, session hafızası, red-team testleri, dokümantasyon.
- **Sırada ne var?** Temiz corpus, indeks yenileme, ölçüme dayalı iyileştirme ve gerçek URL entegrasyonu.

---

## 13. Teknik Referans (Hızlı)

| Bileşen | Konum |
|---------|--------|
| Motor | `chatbot_demo/src/chatbot.py` |
| Rewriter | `chatbot_demo/src/llm_rewriter.py` |
| Embedding | `chatbot_demo/src/embedder.py` |
| UI serialize | `chatbot_demo/src/frontend.py` |
| Veri artırma | `chatbot_demo/src/data_augmented.py` |
| İndeks | `chatbot_demo/scripts/build_index.py` |
| Web demo | `chatbot_demo/demo/server.py` |
| Streamlit | `chatbot_demo/app.py` |
| Bağımlılıklar | `chatbot_demo/requirements.txt` |

---

## 14. Sonuç

Proje, “regex ile hızlı etiket” denemesinden çıkıp **katmanlı, ölçülebilir ve dürüst güven politikasına sahip** bir demo motora dönüşmüştür. Mimari kararlar (K1’in otorite olmaması, precision-first, BGE-M3) bilinçli ve belgelenmiştir. Bundan sonraki başarı, yeni kural yığınından çok **veri temizliği + indeks + düzenli test geri bildirimine** bağlıdır.

---

*Bu rapor, `chatbot_demo` kod tabanı ve 13–17 Temmuz 2026 çalışma sürecine dayanarak hazırlanmıştır.*
