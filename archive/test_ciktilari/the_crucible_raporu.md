# The Crucible Raporu

- Skor: **31/31** (100.0%) — FAIL **0**

## Vektör kırılımı

- `sarcasm`: 5/5 pass — **0 fail**
- `conditional`: 5/5 pass — **0 fail**
- `code_switch`: 6/6 pass — **0 fail**
- `phonetic`: 6/6 pass — **0 fail**
- `dilution`: 6/6 pass — **0 fail**
- `temporal_shift`: 3/3 pass — **0 fail**

## Fail detayları

## Mimari not

- Akış: `Kullanıcı → LLMRewriter → K1 → K2` (söylem regex yok).
- Rewriter sınıflandırmaz; temiz arama sorgusu üretir.
- Bu koşu `force_simulated_rewriter=True` ile tekrarlanabilir kanıt üretir.

## Gözlem özeti

- İroni/şart/zaman kayması: rewriter asıl niyeti süzmeli; K1/K2 temiz sorguya bakmalı.
- Code-switch: EN jargon (HR, PMS, EHR) regex sözlüğünde yoksa BGE'ye kalır.
- Fonetik: leet/noktalı yazım K1'i deler; BGE kurtarabilir veya FB'ye düşer.
- Dilution: uzun gürültü + sonda niyet; rewriter gürültüyü düşürmeli.
