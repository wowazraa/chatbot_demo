"""
Conservative Benchmark Evaluation Script - Strict Security Mode
Implements strict regex matching, conservative parameters, and negative bias for OOD protection.
"""
import sys, os, logging, json, re
logging.disable(logging.CRITICAL)
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

sys.path.insert(0, ".")
from src.embedder import get_embedder

# ─────────────────────────────────────────────────────────────────────────────
# 1. STRICT REGEX CONFIGURATION (Word boundaries for precision)
# ─────────────────────────────────────────────────────────────────────────────
STRICT_SECTOR_REGEX = {
    "health": re.compile(
        r"\b(hastane|hastne|hbys|poliklinik|klinik|hekim|medikal)\b",
        re.IGNORECASE
    ),
    "defense": re.compile(
        r"\b(iha|siha|savunma|askeri|radar|mühimmat|taktik)\b",
        re.IGNORECASE
    ),
    "education": re.compile(
        r"\b(obs|lms|okul|üniversite|akademik|eğitim|öğrenci)\b",
        re.IGNORECASE
    ),
    "tourism": re.compile(
        r"\b(pms|otel|otelleri|rezervasyon|acente|turizm|konaklama)\b",
        re.IGNORECASE
    )
}

def check_strict_regex_match(query: str, predicted_sector: str) -> bool:
    """Check if query matches strict sector regex pattern."""
    pattern = STRICT_SECTOR_REGEX.get(predicted_sector)
    if not pattern:
        return False
    return bool(pattern.search(query.lower()))

# ─────────────────────────────────────────────────────────────────────────────
# 2. CONSERVATIVE PARAMETERS (Negative Bias for OOD Protection)
# ─────────────────────────────────────────────────────────────────────────────
BASE_THRESHOLD = 0.64
HIGH_CONFIDENCE_THRESHOLD = 0.82
REGEX_BONUS = 0.08   # Low bonus (prevent OOD leakage)
REGEX_PENALTY = -0.18 # Strict penalty (eliminate adversarial OOD)

def evaluate_query_conservative(query: str, raw_bge_score: float, predicted_sector: str) -> tuple[bool, float]:
    """
    Conservative Router with Negative Bias for OOD Protection.
    Returns: (is_accepted: bool, final_score: float)
    """
    # PASS 1: High Confidence Auto-Accept
    if raw_bge_score >= HIGH_CONFIDENCE_THRESHOLD:
        return True, raw_bge_score

    # PASS 2: Dynamic Two-Pass with Conservative Weighting
    has_regex_match = check_strict_regex_match(query, predicted_sector)
    
    if has_regex_match:
        final_score = raw_bge_score + REGEX_BONUS
    else:
        final_score = raw_bge_score + REGEX_PENALTY

    # Final Decision
    is_accepted = final_score >= BASE_THRESHOLD
    return is_accepted, final_score

# ─────────────────────────────────────────────────────────────────────────────
# 3. SECTOR MAPPING
# ─────────────────────────────────────────────────────────────────────────────
SECTOR_MAP = {
    "sağlık": "health", "saglik": "health",
    "turizm": "tourism", "savunma": "defense",
    "eğitim": "education", "egitim": "education",
}

def main():
    # Load benchmark dataset
    with open("benchmark_dataset_1000.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    print("=== CONSERVATIVE ROUTER TESTİ (STRICT SECURITY MODE) BAŞLATILIYOR ===")
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
    print(f"Konfigurasyon: Reranker=OFF, Base Threshold={BASE_THRESHOLD}, High Confidence={HIGH_CONFIDENCE_THRESHOLD}", flush=True)
    print(f"Conservative Parameters: Bonus=+{REGEX_BONUS}, Penalty={REGEX_PENALTY}", flush=True)
    print(f"Strict Regex: Word boundaries enabled for precision", flush=True)

    print("\nModel yukleniyor...", flush=True)
    emb = get_embedder()

    print(f"Sorgular isleniyor...", flush=True)
    results = []
    
    # Statistics
    stats = {
        "TA": 0, "FAR": 0, "FRR": 0, "TR": 0,
        "by_type": {}
    }
    
    for i, item in enumerate(dataset):
        query = item["query"]
        true_label = item["actual_sector"]
        query_type = item["query_type"]
        is_in_domain = item["is_in_domain"]
        
        # Get BGE prediction
        hits = emb.find_top_k_hybrid(query, k=1, alpha=0.9)
        if not hits:
            raw_score, pred_sector = 0.0, "ood"
        else:
            best = hits[0]
            raw_score = float(best.score)
            meta = (best.metadata or {}).get("beklenen_sektor") or ""
            pred_sector = SECTOR_MAP.get(str(meta).strip().lower(), "ood")
        
        # Conservative Router Decision
        is_accepted, final_score = evaluate_query_conservative(query, raw_score, pred_sector)
        
        # Metrics Setup
        if query_type not in stats["by_type"]:
            stats["by_type"][query_type] = {"correct": 0, "total": 0}
        stats["by_type"][query_type]["total"] += 1

        # Confusion Matrix Logic
        if is_in_domain and is_accepted:
            stats["TA"] += 1
            stats["by_type"][query_type]["correct"] += 1
            final_pred = pred_sector
        elif not is_in_domain and is_accepted:
            stats["FAR"] += 1  # False Accept (Leakage)
            final_pred = pred_sector
        elif is_in_domain and not is_accepted:
            stats["FRR"] += 1  # False Reject (Business Loss)
            final_pred = "ood"
        elif not is_in_domain and not is_accepted:
            stats["TR"] += 1
            stats["by_type"][query_type]["correct"] += 1
            final_pred = "ood"
        
        results.append({
            "id": item["id"],
            "query": query,
            "true": true_label,
            "pred": final_pred,
            "raw_score": raw_score,
            "final_score": final_score,
            "query_type": query_type,
            "is_in_domain": is_in_domain,
            "is_accepted": is_accepted
        })
        
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(dataset)} tamamlandi...", flush=True)

    # Calculate final metrics
    total = len(dataset)
    n_ood = sum(1 for r in results if r["true"] == "OOD")
    n_b2b = len(results) - n_ood
    
    acc = (stats["TA"] + stats["TR"]) / total * 100
    far_pct = (stats["FAR"] / n_ood * 100) if n_ood else 0
    frr_pct = (stats["FRR"] / n_b2b * 100) if n_b2b else 0
    
    print(f"\n==================================================")
    print(f"Genel Doğruluk (Accuracy) : %{acc:.2f}")
    print(f"Doğru Kabul (TA - B2B OK) : {stats['TA']} / {n_b2b}")
    print(f"Hatalı Kabul (FAR - Sızıntı): {stats['FAR']} / {n_ood} (%{far_pct:.2f})  <-- (Hedef: %0-%0.5)")
    print(f"Hatalı Red (FRR - İş Kaybı): {stats['FRR']} / {n_b2b} (%{frr_pct:.2f})  <-- (Hedef: %8-%12)")
    print(f"Doğru Red (TR - OOD OK)  : {stats['TR']} / {n_ood}")
    print(f"==================================================\n")
    
    print("QUERY TYPE BAZLI BAŞARI:")
    for t_name in ["clean_b2b", "noisy_typo", "abbreviation", "short_search", "adversarial_ood", "b2c_noise"]:
        if t_name in stats["by_type"]:
            t_data = stats["by_type"][t_name]
            pct = (t_data["correct"] / t_data["total"]) * 100
            print(f" - {t_name:<18}: {t_data['correct']}/{t_data['total']} (%{pct:.1f})")
    
    # Sonuçları kaydet
    output_file = "benchmark_results_conservative.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "config": {
                "reranker": "OFF",
                "mode": "conservative_strict_security",
                "base_threshold": BASE_THRESHOLD,
                "high_confidence_threshold": HIGH_CONFIDENCE_THRESHOLD,
                "regex_bonus": REGEX_BONUS,
                "regex_penalty": REGEX_PENALTY,
                "strict_regex": True,
                "word_boundaries": True
            },
            "results": results,
            "summary": {
                "total_queries": total,
                "in_domain_count": n_b2b,
                "ood_count": n_ood,
                "accuracy": acc,
                "TA": stats["TA"],
                "FAR": stats["FAR"],
                "FRR": stats["FRR"],
                "TR": stats["TR"],
                "far_pct": far_pct,
                "frr_pct": frr_pct,
                "query_type_analysis": stats["by_type"]
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nSonuçlar kaydedildi: {output_file}")
    print("✓ Conservative Router testi tamamlandı!")


if __name__ == "__main__":
    main()
