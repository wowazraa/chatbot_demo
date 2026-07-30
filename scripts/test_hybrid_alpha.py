"""
Hybrid Alpha Test - H ve I Kategorileri için Sparse Ağırlık Optimizasyonu
Farklı alpha değerleriyle H ve I kategorilerindeki başarısızlıkları çözmeyi hedefler.
"""
import sys, json, time
from pathlib import Path

sys.path.insert(0, ".")
from src.embedder import get_embedder

# Test sorguları (H ve I kategorileri)
H_QUERIES = [
    ("H01", "Aslında sağlık değil ama sağlık yazıyorum, siz turizm anlayın.", "turizm"),
    ("H05", "sağlık sağlık sağlık sağlık sağlık sağlık sağlık sağlık sağlık", "sağlık"),
    ("H08", "turizm turizm turizm", "turizm"),
    ("H16", "Siber saldırılara karşı savunma sanayi değil, kurumsal SaaS bulut altyapısı ve sunucu barındırma arıyoruz.", "bilişim"),
]

I_QUERIES = [
    ("I01", "Sağlık sektöründeyiz.", "sağlık"),
    ("I02", "Peki fiyatlandırma nasıl?", "sağlık"),
    ("I03", "Oteller için ne gibi çözümleriniz var?", "turizm"),
    ("I04", "Referanslarınızı listeler misiniz?", "turizm"),
]

def test_alpha(alpha: float, embedder) -> dict:
    """Belirli bir alpha değeriyle test yap."""
    results = {"H": {"total": len(H_QUERIES), "correct": 0}, "I": {"total": len(I_QUERIES), "correct": 0}}
    
    for query_id, query, expected_sector in H_QUERIES + I_QUERIES:
        hits = embedder.find_top_k_hybrid(query, k=1, alpha=alpha)
        
        if hits:
            predicted_sector = (hits[0].metadata or {}).get("beklenen_sektor", "")
            category = "H" if query_id.startswith("H") else "I"
            
            if predicted_sector == expected_sector:
                results[category]["correct"] += 1
    
    return results

def main():
    print("=" * 80)
    print("HYBRID ALPHA TEST - H ve I Kategorileri")
    print("=" * 80)
    
    embedder = get_embedder()
    
    # Farklı alpha değerleri test et (dense ağırlığı)
    alphas = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
    
    print(f"\n{'Alpha':<10} {'H Success':<15} {'I Success':<15} {'Total Success':<15}")
    print("-" * 80)
    
    best_alpha = None
    best_total = 0
    
    for alpha in alphas:
        results = test_alpha(alpha, embedder)
        
        h_rate = f"{results['H']['correct']}/{results['H']['total']}"
        i_rate = f"{results['I']['correct']}/{results['I']['total']}"
        total = results['H']['correct'] + results['I']['correct']
        total_rate = f"{total}/{results['H']['total'] + results['I']['total']}"
        
        print(f"{alpha:<10.1f} {h_rate:<15} {i_rate:<15} {total_rate:<15}")
        
        if total > best_total:
            best_total = total
            best_alpha = alpha
    
    print("-" * 80)
    print(f"Best Alpha: {best_alpha} (Total: {best_total})")
    
    # Sonuçları kaydet
    output = {
        "test_type": "hybrid_alpha_optimization",
        "categories_tested": ["H", "I"],
        "best_alpha": best_alpha,
        "best_total_success": best_total,
        "all_results": []
    }
    
    for alpha in alphas:
        results = test_alpha(alpha, embedder)
        output["all_results"].append({
            "alpha": alpha,
            "H": results["H"],
            "I": results["I"],
            "total": results["H"]["correct"] + results["I"]["correct"]
        })
    
    with open("hybrid_alpha_test_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\nSonuçlar kaydedildi: hybrid_alpha_test_results.json")

if __name__ == "__main__":
    main()
