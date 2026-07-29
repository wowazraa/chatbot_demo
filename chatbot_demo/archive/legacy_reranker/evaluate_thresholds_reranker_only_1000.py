"""1000 sorguluk threshold tarama — Reranker skoru (soft fusion yok)."""
import sys, os, logging, random

logging.disable(logging.CRITICAL)
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

sys.path.insert(0, ".")

from scripts.evaluate_thresholds_hybrid_1000 import build_dataset, SECTOR_MAP
from src.embedder import get_embedder
from src.models.reranker import get_reranker
from src.smart_gate import should_skip_reranker

random.seed(42)


def main():
    dataset = build_dataset(1000)
    label_counts = {}
    for _, lbl in dataset:
        label_counts[lbl] = label_counts.get(lbl, 0) + 1
    print(f"Dataset: {len(dataset)} sorgu | Dagilim: {label_counts}", flush=True)

    print("Modeller yukleniyor (BGE-M3 + Reranker)...", flush=True)
    emb = get_embedder()
    reranker = get_reranker()
    print("Modeller hazir.", flush=True)

    print("Sorgular isleniyor (reranker skoru)...", flush=True)
    results = []
    for i, (query, true_label) in enumerate(dataset):
        hits = emb.find_top_k_hybrid(query, k=1, alpha=0.9)
        if not hits:
            results.append({"true": true_label, "pred": "ood", "score": 0.0})
            continue
        best = hits[0]
        bge = float(best.score)
        meta = (best.metadata or {}).get("beklenen_sektor") or ""
        pred = SECTOR_MAP.get(str(meta).strip().lower(), "ood")
        if should_skip_reranker(bge):
            score = bge
        else:
            rr_scores = reranker.score(query, [best.text or ""])
            score = float(rr_scores[0]) if rr_scores else bge
        results.append({"true": true_label, "pred": pred, "score": score})
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/1000 tamamlandi...", flush=True)

    n_ood = sum(1 for r in results if r["true"] == "ood")
    n_b2b = len(results) - n_ood

    print("\n" + "=" * 106)
    print(
        f"{'Esik':<7} | {'Dogruluk':>9} | {'TA(B2B OK)':>12} | "
        f"{'FAR(OOD->B2B)':>15} | {'FRR(B2B->OOD)':>15} | "
        f"{'TR(OOD OK)':>12} | {'Toplam':>10}"
    )
    print("=" * 106)

    thresholds = [i / 100 for i in range(50, 87)]
    best_t, best_acc, best_stats = 0.0, 0.0, {}

    for t in thresholds:
        ta = fa = fr = tr_count = 0
        for r in results:
            final = r["pred"] if r["score"] >= t else "ood"
            is_ood = r["true"] == "ood"
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
        print(
            f"{t:.2f}    | {acc*100:>8.1f}% | {ta:>10}/{n_b2b} | "
            f"{fa:>8} (%{far_pct:.0f}){'':<5} | {fr:>10}/{n_b2b} | "
            f"{tr_count:>8}/{n_ood} | {total_correct:>6}/1000{flag}"
        )

        if acc > best_acc and fa == 0:
            best_acc, best_t = acc, t
            best_stats = {"TA": ta, "FA": fa, "FR": fr, "TR": tr_count}
        elif acc == best_acc and fa == 0 and t < best_t:
            best_t = t
            best_stats = {"TA": ta, "FA": fa, "FR": fr, "TR": tr_count}

    print("=" * 106)
    print(f"\n*** EN IYI ESIK (FAR=0 sartiyla): {best_t:.2f} ***")
    print(f"    Genel Dogruluk : %{best_acc * 100:.1f}")
    print(f"    Dogru Kabul TA : {best_stats.get('TA', 0)}/{n_b2b}")
    print(f"    Yanlis Red FRR : {best_stats.get('FR', 0)}/{n_b2b}")
    print(f"    Yanlis Kabul FA: {best_stats.get('FA', 0)}/{n_ood}  (SIFIR olmali!)")
    print(f"    Dogru Red TR   : {best_stats.get('TR', 0)}/{n_ood}")


if __name__ == "__main__":
    main()
