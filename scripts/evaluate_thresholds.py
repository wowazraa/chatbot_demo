import sys
import time
import json
import logging
from typing import List, Tuple

# Suppress logs for cleaner output
logging.getLogger("omniintent.embedder").setLevel(logging.WARNING)

from src.embedder import get_embedder

# Kapsamlı Test Seti (B2B ve OOD)
# Format: (Sorgu, Beklenen_Sektör)
TEST_DATA = [
    # --- KOLAY / NET (B2B) ---
    ("Şirketimiz için acil olarak klinik randevu otomasyonu kurmak istiyoruz", "health"),
    ("Kurumsal düzeyde insansız hava aracı (İHA) kontrol yazılımı hizmeti almak istiyoruz", "defense"),
    ("Yeni bir öğrenci bilgi sistemi (OBS) entegrasyonuna ihtiyacımız var", "education"),
    ("Lüks otel zincirimiz için çevrimiçi biletleme motoru yazılımı gerekiyor", "tourism"),
    ("HBYS sistemimizi güncellemek ve e-nabız entegrasyonu yapmak istiyoruz", "health"),
    ("Radarlardan gelen veriyi analiz edecek yerli bir yazılım arıyoruz", "defense"),
    ("Turizm acentamız için paket tur satış ve rezervasyon platformu", "tourism"),
    
    # --- ORTA / BAĞLAMSAL (B2B) ---
    ("Kripto komuta ve telsiz altyapısı ihalelerine girmek istiyoruz", "defense"),
    ("Ameliyathanelerdeki tıbbi cihazların anlık bakım takip süreçlerini dijitalleştirmek", "health"),
    ("Kampüs içindeki tüm ağ ve donanım süreçlerini tek bir portaldan yönetmek istiyoruz", "education"),
    ("Personelimizin yıllık izinlerini ve seyahat rotalarını planlayacak kurumsal bir tatil paketi arıyoruz", "tourism"),
    ("Üniversite kütüphanesi için dijital kataloglama otomasyonu arıyoruz", "education"),
    
    # --- ZOR / TUZAK / OOD (Reddedilmesi Gerekenler) ---
    ("Eğitim uçakları ve savaş jetleri için evime oyun bilgisayarı toplamak istiyorum", "ood"),
    ("Bugün acil hastanenin önünde çok büyük bir zincirleme trafik kazası olmuş", "ood"),
    ("Savunma sanayi şirketlerinin hisse senedi borsa fiyatları ne kadar oldu?", "ood"),
    ("Kardiyoloji doktorundan randevu almak istiyorum", "ood"), # B2C
    ("Üniversite güz dönemi harç ödememi nereye yapacağım?", "ood"), # B2C
    ("Sağlık veya hastane ile ilgisi yok, sadece lojistik kargo rotalarımızı optimize etmemiz lazım", "ood"),
    ("Havalar bugün nasıl?", "ood"),
    ("Aselsan hisseleri bugün tavan yaptı, yatırım tavsiyesi verir misiniz?", "ood"),
    ("Otelde değil, çadırda kamp yapmak istiyorum, uygun çadır fiyatları neler?", "ood")
]

def main():
    print("Modeller yükleniyor (Sadece BGE-M3)...")
    emb = get_embedder()
    
    # BGE Skorlarını toplayalım
    print(f"Toplam {len(TEST_DATA)} sorgu analiz ediliyor...")
    results = []
    
    for query, true_label in TEST_DATA:
        # BGE sorgusu
        hits = emb.find_top_k_hybrid(query, k=1, alpha=0.9)
        if not hits:
            score = 0.0
            pred_sector = "ood"
        else:
            best = hits[0]
            score = float(best.score)
            metadata_sector = (best.metadata or {}).get("beklenen_sektor", "")
            # Sektör mapping
            mapping = {
                "sağlık": "health", "saglik": "health",
                "turizm": "tourism",
                "savunma": "defense",
                "eğitim": "education", "egitim": "education"
            }
            pred_sector = mapping.get(metadata_sector, "ood")
            
        results.append({
            "query": query,
            "true_label": true_label,
            "bge_score": score,
            "raw_pred_sector": pred_sector
        })
        
    print("\n--- EŞİK (THRESHOLD) ANALİZİ ---")
    thresholds = [i / 100.0 for i in range(50, 86)]
    
    best_t = 0.0
    best_acc = 0.0
    best_stats = {}
    
    print(f"{'Threshold':<10} | {'Doğruluk(Acc)':<13} | {'Kabul Edilen Doğru':<20} | {'Yanlış Kabul (FAR)':<20} | {'Yanlış Red (FRR)':<20}")
    print("-" * 90)
    
    for t in thresholds:
        correct = 0
        false_accept = 0 # OOD olan bir şeyi içeri aldık (Çok tehlikeli)
        false_reject = 0 # İçeri almamız gereken B2B'yi reddettik (Daha az tehlikeli)
        true_accept = 0  # B2B soruyu doğru bildik
        true_reject = 0  # OOD soruyu doğru şekilde OOD dedik
        
        for r in results:
            final_pred = r["raw_pred_sector"] if r["bge_score"] >= t else "ood"
            
            if final_pred == r["true_label"]:
                correct += 1
                if final_pred == "ood":
                    true_reject += 1
                else:
                    true_accept += 1
            else:
                if r["true_label"] == "ood":
                    # Gerçekte OOD ama biz içeri aldık
                    false_accept += 1
                elif final_pred == "ood":
                    # Gerçekte B2B ama biz reddettik
                    false_reject += 1
                else:
                    # Yanlış sektöre yönlendirdik
                    false_accept += 1 

        accuracy = correct / len(results)
        
        print(f"{t:.2f}       | %{accuracy*100:<12.1f} | {true_accept:<20} | {false_accept:<20} | {false_reject:<20}")
        
        # En iyi threshold seçimi:
        # 1. Hiçbir OOD soruyu içeri alma (FAR == 0)
        # 2. Bunu sağlayan en yüksek doğruluk oranını bul
        if accuracy > best_acc and false_accept == 0:
            best_acc = accuracy
            best_t = t
            best_stats = {"TA": true_accept, "FA": false_accept, "FR": false_reject, "TR": true_reject}
        elif accuracy == best_acc and false_accept == 0 and t < best_t:
            # Aynı doğrulukta daha düşük threshold daha çok esneklik sağlar
            best_acc = accuracy
            best_t = t
            best_stats = {"TA": true_accept, "FA": false_accept, "FR": false_reject, "TR": true_reject}

    print("-" * 90)
    if best_acc > 0:
        print(f"\n=> TAVSİYE EDİLEN EN GÜVENLİ VE VERİMLİ EŞİK: {best_t:.2f}")
        print(f"=> Doğruluk: %{best_acc*100:.1f}")
    else:
        print("\n=> FAR=0 şartını sağlayan ideal bir eşik bulunamadı. Lütfen sonuçları manuel inceleyin.")
    print("Detaylı sonuçlar alındı.")
    
if __name__ == '__main__':
    main()
