"""
Eşik Analiz Yardımcı Modülü (check_eightyfive.py)
=================================================
Kullanıcının önerdiği 0.85 parametrelerini test ederek sonuçları karşılaştırır.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot
from tests.run_stres_test import TEST_SENARYOLARI

def load_base_scenarios() -> list[dict]:
    path = ROOT / "tests" / "fixtures" / "test_scenarios.json"
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("senaryolar", data)

def test_combination(min_bge: float, alpha: float) -> tuple[int, int, dict]:
    Chatbot.MIN_BGE = min_bge
    Chatbot.ALPHA = alpha
    bot = Chatbot()
    
    # 1. Base 20
    base_scenarios = load_base_scenarios()
    base_passed = 0
    for s in base_scenarios:
        res = bot.sor(s["girdi"])
        bkl_sektor = s["beklenen_sektor"]
        bkl_mod = s.get("beklenen_mod", s.get("beklened_mod", "K1"))
        if res.sektor == bkl_sektor and res.mod == bkl_mod:
            base_passed += 1
            
    # 2. Stres
    stres_passed = 0
    kategori_stats = {k: 0 for k in "ABCDEFGHI"}
    kategori_totals = {k: 0 for k in "ABCDEFGHI"}
    
    current_session_id = None
    for case in TEST_SENARYOLARI:
        girdi = case["girdi"]
        bkl_sektor = case["beklenen_sektor"]
        bkl_mod = case["beklenen_mod"]
        kategori = case["kategori"]
        tip = case.get("tip", "")
        
        if kategori == "I":
            if tip == "dialog_tur1":
                current_session_id = f"session_I_{case['id']}"
            session_id = current_session_id
        else:
            session_id = f"session_other_{case['id']}"
            
        res = bot.sor(girdi, session_id=session_id)
        
        basarili = False
        if bkl_sektor == "tartışmalı":
            basarili = (res.mod == bkl_mod)
        else:
            basarili = (res.sektor == bkl_sektor) and (res.mod == bkl_mod)
            
        kategori_totals[kategori] += 1
        if basarili:
            stres_passed += 1
            kategori_stats[kategori] += 1
            
    cat_rates = {k: f"{kategori_stats[k]}/{kategori_totals[k]}" for k in "ABCDEFGHI"}
    return base_passed, stres_passed, cat_rates

def main():
    # 1. Mevcut Durum (Referans)
    # MIN_BGE = 0.50, ALPHA = 0.90
    print("Mevcut optimum ayarlar hesaplanıyor (MIN_BGE=0.50, ALPHA=0.90)...")
    base_ref, stres_ref, cat_ref = test_combination(0.50, 0.90)
    
    # 2. İhtimal A: Benzerlik eşiği olan MIN_BGE'yi 0.85 yapmak
    # MIN_BGE = 0.85, ALPHA = 0.90
    print("İhtimal A hesaplanıyor: Benzerlik Eşiği MIN_BGE = 0.85 yapmak...")
    base_a, stres_a, cat_a = test_combination(0.85, 0.90)
    
    # 3. İhtimal B: Hibrit ağırlık olan ALPHA'yı 0.85 yapmak
    # MIN_BGE = 0.50, ALPHA = 0.85
    print("İhtimal B hesaplanıyor: Dense Ağırlığı ALPHA = 0.85 yapmak...")
    base_b, stres_b, cat_b = test_combination(0.50, 0.85)

    print("\n" + "="*50)
    print("       KARŞILAŞTIRMA SONUÇLARI")
    print("="*50)
    print(f"1. Referans (MIN_BGE=0.50, ALPHA=0.90):")
    print(f"   Temel Test: {base_ref}/20 | Stres Testi: {stres_ref}/92 | Toplam: {base_ref+stres_ref}/112")
    print(f"   Kategoriler: {cat_ref}\n")
    
    print(f"2. Eşik Değişimi (MIN_BGE = 0.85, ALPHA=0.90):")
    print(f"   Temel Test: {base_a}/20 | Stres Testi: {stres_a}/92 | Toplam: {base_a+stres_a}/112")
    print(f"   Kategoriler: {cat_a}\n")
    
    print(f"3. Hibrit Ağırlık Değişimi (MIN_BGE=0.50, ALPHA = 0.85):")
    print(f"   Temel Test: {base_b}/20 | Stres Testi: {stres_b}/92 | Toplam: {base_b+stres_b}/112")
    print(f"   Kategoriler: {cat_b}")
    print("="*50)

if __name__ == "__main__":
    main()
