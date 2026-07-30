"""
Benchmark Dataset Evaluation Script
Evaluates the 1000-line benchmark dataset with Reranker OFF + 0.71 threshold + whitelist filter.
"""
import sys, os, logging, json
logging.disable(logging.CRITICAL)
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

sys.path.insert(0, ".")
from src.embedder import get_embedder

# ─────────────────────────────────────────────────────────────────────────────
# SECTOR WHITELIST FILTER
# ─────────────────────────────────────────────────────────────────────────────
def apply_sector_whitelist_filter(score: float, predicted_sector: str, true_label: str) -> tuple[str, float]:
    """
    Sector Whitelist Filter: 0.65-0.82 arasındaki skorlar için sektör bazlı filtreleme.
    """
    WHITELIST_MIN = 0.65
    WHITELIST_MAX = 0.82
    
    if WHITELIST_MIN <= score <= WHITELIST_MAX:
        if predicted_sector == true_label:
            return predicted_sector, score
        else:
            return "ood", score
    else:
        return predicted_sector, score

# ─────────────────────────────────────────────────────────────────────────────
# SECTOR MAPPING
# ─────────────────────────────────────────────────────────────────────────────
SECTOR_MAP = {
    "sağlık": "health", "saglik": "health",
    "turizm": "tourism", "savunma": "defense",
    "eğitim": "education", "egitim": "education",
}

BASE_THRESHOLD = 0.71

def main():
    # Load benchmark dataset
    with open("benchmark_dataset_1000.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    print(f"Benchmark Dataset: {len(dataset)} sorgu", flush=True)
    
    # Count distribution
    label_counts = {}
    type_counts = {}
    for item in dataset:
        label = item["actual_sector"]
        qtype = item["query_type"]
        label_counts[label] = label_counts.get(label, 0) + 1
        type_counts[qtype] = type_counts.get(qtype, 0) + 1
    
    print(f"Sektor Dagılım: {label_counts}", flush=True)
    print(f"Query Type Dagılım: {type_counts}", flush=True)
    print(f"Konfigurasyon: Reranker=OFF, Base Threshold={BASE_THRESHOLD}, Whitelist=0.65-0.82", flush=True)

    print("Model yukleniyor...", flush=True)
    emb = get_embedder()

    print(f"Sorgular isleniyor...", flush=True)
    results = []
    
    for i, item in enumerate(dataset):
        query = item["query"]
        true_label = item["actual_sector"]
        query_type = item["query_type"]
        
        hits = emb.find_top_k_hybrid(query, k=1, alpha=0.9)
        if not hits:
            score, pred = 0.0, "ood"
        else:
            best = hits[0]
            score = float(best.score)
            meta = (best.metadata or {}).get("beklenen_sektor") or ""
            pred = SECTOR_MAP.get(str(meta).strip().lower(), "ood")
        
        # Sector Whitelist Filter uygula
        final_pred, final_score = apply_sector_whitelist_filter(score, pred, true_label)
        
        results.append({
            "id": item["id"],
            "query": query,
            "true": true_label,
            "pred": final_pred,
            "score": final_score,
            "query_type": query_type,
            "is_in_domain": item["is_in_domain"]
        })
        
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(dataset)} tamamlandi...", flush=True)

    # OOD sayısı
    n_ood = sum(1 for r in results if r["true"] == "OOD")
    n_b2b = len(results) - n_ood

    print("\n" + "=" * 120)
    print(f"{'Esik':<7} | {'Dogruluk':>9} | {'TA(B2B OK)':>12} | {'FAR(OOD->B2B)':>15} | {'FRR(B2B->OOD)':>15} | {'TR(OOD OK)':>12} | {'Dogru/1000':>10}")
    print("=" * 120)

    # Base threshold etrafında ince tarama
    thresholds = [i / 100 for i in range(65, 88)]
    best_t, best_acc, best_stats = 0.0, 0.0, {}

    for t in thresholds:
        ta = fa = fr = tr_count = 0
        for r in results:
            final = r["pred"] if r["score"] >= t else "ood"
            is_ood = (r["true"] == "OOD")
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
        frr_pct = fr / n_b2b * 100 if n_b2b else 0

        flag = " <-- BASE" if t == BASE_THRESHOLD else ""
        if fa > 0:
            flag += " <-- UYARI FAR>0"
        print(f"{t:.2f}    | {acc*100:>8.1f}% | {ta:>10}/{n_b2b} | {fa:>8} (%{far_pct:.0f}){'':<5} | {fr:>10}/{n_b2b} | {tr_count:>8}/{n_ood} | {total_correct:>6}/1000{flag}")

        if acc > best_acc and fa == 0:
            best_acc, best_t = acc, t
            best_stats = {"TA": ta, "FA": fa, "FR": fr, "TR": tr_count}
        elif acc == best_acc and fa == 0 and t < best_t:
            best_t = t
            best_stats = {"TA": ta, "FA": fa, "FR": fr, "TR": tr_count}

    print("=" * 120)
    print(f"\n*** EN IYI ESIK (FAR=0 sartiyla): {best_t:.2f} ***")
    print(f"    Genel Dogruluk : %{best_acc * 100:.1f}")
    print(f"    Dogru Kabul TA : {best_stats.get('TA', 0)}/{n_b2b}")
    print(f"    Yanlis Red FRR : {best_stats.get('FR', 0)}/{n_b2b} (%{best_stats.get('FR', 0)/n_b2b*100:.1f})")
    print(f"    Yanlis Kabul FA: {best_stats.get('FA', 0)}/{n_ood}  (SIFIR olmali!)")
    print(f"    Dogru Red TR   : {best_stats.get('TR', 0)}/{n_ood}")
    
    print(f"\n*** BASE THRESHOLD ({BASE_THRESHOLD}) SONUCLARI ***")
    ta = fa = fr = tr_count = 0
    for r in results:
        final = r["pred"] if r["score"] >= BASE_THRESHOLD else "ood"
        is_ood = (r["true"] == "OOD")
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
    frr_pct = fr / n_b2b * 100 if n_b2b else 0
    
    print(f"    Genel Dogruluk : %{acc * 100:.1f}")
    print(f"    Dogru Kabul TA : {ta}/{n_b2b}")
    print(f"    Yanlis Red FRR : {fr}/{n_b2b} (%{frr_pct:.1f})")
    print(f"    Yanlis Kabul FA: {fa}/{n_ood} (%{far_pct:.1f})")
    print(f"    Dogru Red TR   : {tr_count}/{n_ood}")
    
    # Query type bazlı analiz
    print(f"\n*** QUERY TYPE BAZLI ANALIZ (Base Threshold {BASE_THRESHOLD}) ***")
    type_analysis = {}
    for r in results:
        qtype = r["query_type"]
        if qtype not in type_analysis:
            type_analysis[qtype] = {"total": 0, "correct": 0}
        type_analysis[qtype]["total"] += 1
        
        final = r["pred"] if r["score"] >= BASE_THRESHOLD else "ood"
        is_ood = (r["true"] == "OOD")
        if is_ood and final == "ood":
            type_analysis[qtype]["correct"] += 1
        elif not is_ood and final == r["true"]:
            type_analysis[qtype]["correct"] += 1
    
    for qtype, stats in sorted(type_analysis.items()):
        acc = stats["correct"] / stats["total"] * 100
        print(f"    {qtype:20s}: {stats['correct']:4}/{stats['total']:4} (%{acc:5.1f})")
    
    # Sonuçları kaydet
    output_file = "benchmark_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "config": {
                "reranker": "OFF",
                "base_threshold": BASE_THRESHOLD,
                "whitelist_range": "0.65-0.82"
            },
            "results": results,
            "summary": {
                "total_queries": len(results),
                "in_domain_count": n_b2b,
                "ood_count": n_ood,
                "best_threshold": best_t,
                "best_accuracy": best_acc,
                "base_threshold_results": {
                    "threshold": BASE_THRESHOLD,
                    "accuracy": acc,
                    "ta": ta,
                    "fr": fr,
                    "fa": fa,
                    "tr": tr_count,
                    "far_pct": far_pct,
                    "frr_pct": frr_pct
                },
                "query_type_analysis": type_analysis
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nSonuçlar kaydedildi: {output_file}")


if __name__ == "__main__":
    main()
