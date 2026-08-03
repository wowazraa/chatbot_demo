import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Silinecek Klasörler (Tamamen yok edilecek)
FOLDERS_TO_DELETE = [
    "archive",
    "reports",
    "data/scratch"
]

# Silinecek Belirli Dosyalar
FILES_TO_DELETE = [
    "data/processed/chatbot_dataset_augmented.json",
    "data/processed/chatbot_dataset_clean.json",
    "data/raw/chatbot_dataset_archived_sektorler.json",
    "data/raw/chatbot_dataset_yedek_20260730_161250.json",
    "data/benchmark_dataset_1000.json",
    "data/benchmark_results.json",
    "data/benchmark_results_conservative.json",
    "data/benchmark_results_optimized.json",
    "test_manual_scenarios.py"
]

# Silinmekten KORUNACAK tests/ dosyaları
TESTS_KEEP = [
    "run_cekim_eki_orijinal.py",
    "run_stres_test.py",
    "cleanup.py"
]

# Silinmekten KORUNACAK scripts/ dosyaları
SCRIPTS_KEEP = [
    "build_index.py"
]

print("Temizlik başlıyor...")

# 1. Klasörleri sil
for folder in FOLDERS_TO_DELETE:
    folder_path = ROOT / folder
    if folder_path.exists() and folder_path.is_dir():
        shutil.rmtree(folder_path)
        print(f"Silindi: {folder}/")

# 2. Belirli dosyaları sil
for file in FILES_TO_DELETE:
    file_path = ROOT / file
    if file_path.exists() and file_path.is_file():
        file_path.unlink()
        print(f"Silindi: {file}")

# 3. scripts/ klasörünü temizle (build_index.py HARİÇ)
scripts_dir = ROOT / "scripts"
if scripts_dir.exists():
    for f in scripts_dir.iterdir():
        if f.is_file() and f.name not in SCRIPTS_KEEP:
            f.unlink()
            print(f"Silindi: scripts/{f.name}")

# 4. tests/ klasörünü temizle (KORUNANLAR ve fixtures HARİÇ)
tests_dir = ROOT / "tests"
if tests_dir.exists():
    for f in tests_dir.iterdir():
        if f.is_file() and f.name not in TESTS_KEEP:
            f.unlink()
            print(f"Silindi: tests/{f.name}")
        elif f.is_dir() and f.name not in ("fixtures", "__pycache__"):
            shutil.rmtree(f)
            print(f"Silindi: tests/{f.name}/")
            
    # tests/fixtures içinde sadece test_scenarios.json kalsın
    fixtures_dir = tests_dir / "fixtures"
    if fixtures_dir.exists():
        for f in fixtures_dir.iterdir():
            if f.is_file() and f.name != "test_scenarios.json":
                f.unlink()
                print(f"Silindi: tests/fixtures/{f.name}")

print("\nTemizlik tamamlandı! Hedef yapı başarıyla oluşturuldu.")
