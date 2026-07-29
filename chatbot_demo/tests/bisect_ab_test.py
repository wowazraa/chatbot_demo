"""
Exact A07/A12 regression diagnosis: uses the EXACT stress test queries.
Tests both preprocess_query output AND full pipeline result.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.v2_pipeline import V2IntentPipeline, preprocess_query
from src.llm_rewriter import LLMRewriter

# Exact queries from stress test (b477986 JSON)
A07_QUERY = "lms kurulumundan vazgeçtik, telemedicine altyapısı talep ediyoruz"
A12_QUERY = "Eğitim kurumu değiliz, hastaneler için teletıp altyapısı arıyoruz."

print("=" * 90)
print("REGRESSION DIAGNOSIS: A07 & A12")
print("=" * 90)

for label, query in [("A07", A07_QUERY), ("A12", A12_QUERY)]:
    print(f"\n{'-' * 90}")
    print(f"[{label}] Original query: {query}")
    
    # Step 1: preprocess
    pp = preprocess_query(query)
    print(f"[{label}] preprocess_query output: {repr(pp)}")
    
    # Step 2: negation check
    negation_keywords = ["değil", "degil", "hariç", "haric", "istemiyoruz", "istemiyorum", 
                         "not", "without", "except", "vazgeç", "vazgec", "boşver", "bosver"]
    has_neg_original = any(w in query.lower() for w in negation_keywords)
    has_neg_preprocessed = any(w in pp.lower() for w in negation_keywords)
    print(f"[{label}] has_negation (on original query): {has_neg_original}")
    print(f"[{label}] has_negation (on preprocessed):   {has_neg_preprocessed}")
    
    # Step 3: rewriter output
    if has_neg_preprocessed:
        rewriter = LLMRewriter(force_simulated=True)
        # Test rewriter on ORIGINAL vs PREPROCESSED
        rew_orig = rewriter.rewrite(query)
        rew_pp = rewriter.rewrite(pp)
        print(f"[{label}] Rewriter(original).clean_query:      {repr(rew_orig.clean_query)}")
        print(f"[{label}] Rewriter(original).negated_sectors:   {rew_orig.negated_sectors}")
        print(f"[{label}] Rewriter(preprocessed).clean_query:   {repr(rew_pp.clean_query)}")
        print(f"[{label}] Rewriter(preprocessed).negated_sectors:{rew_pp.negated_sectors}")
    
    # Step 4: full pipeline
    pipe = V2IntentPipeline()
    result = pipe.run(query)
    print(f"[{label}] Pipeline result: sector={result.sector}, score={result.confidence_score:.4f}, layer={result.layer}, status={result.status}")
    print(f"[{label}] Pipeline negated_sectors: {result.negated_sectors}")

print(f"\n{'=' * 90}")
