import json
import re
from pathlib import Path

ROOT = Path("c:/Users/AZRA/OneDrive/Desktop/Chatbot_Bilgi_Merkezi_Projesi/chatbot_demo")

RAW_PATH = ROOT / "data" / "raw" / "chatbot_dataset.json"
CLEAN_PATH = ROOT / "data" / "processed" / "chatbot_dataset_clean.json"
AUG_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"
ARCHIVE_PATH = ROOT / "data" / "raw" / "chatbot_dataset_archived_sektorler.json"

DISCARDED_SECTORS = {"savunma", "finans", "lojistik", "e_ticaret", "enerji", "ik_kurumsal"}

def clean_datasets():
    print("--- Cleaning Datasets ---")
    archived_records = []
    
    # helper to check if a record belongs to discarded sectors
    def is_discarded(r):
        sec = r.get("beklenen_sektor", "")
        sec_dep = r.get("beklened_sektor", "")
        # normalization
        if isinstance(sec, str):
            sec = sec.strip().lower()
        if isinstance(sec_dep, str):
            sec_dep = sec_dep.strip().lower()
        return sec in DISCARDED_SECTORS or sec_dep in DISCARDED_SECTORS

    # 1. Raw Dataset
    if RAW_PATH.exists():
        with RAW_PATH.open(encoding="utf-8") as f:
            raw_data = json.load(f)
        raw_recs = raw_data.get("kayitlar", raw_data)
        
        filtered_raw = []
        for r in raw_recs:
            if is_discarded(r):
                archived_records.append(r)
            else:
                filtered_raw.append(r)
                
        if isinstance(raw_data, dict):
            raw_data["kayitlar"] = filtered_raw
        else:
            raw_data = filtered_raw
            
        with RAW_PATH.open("w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
        print(f"Raw dataset filtered. Kalan: {len(filtered_raw)}")
        
    # 2. Clean Dataset
    if CLEAN_PATH.exists():
        with CLEAN_PATH.open(encoding="utf-8") as f:
            clean_data = json.load(f)
        clean_recs = clean_data.get("kayitlar", clean_data)
        
        filtered_clean = []
        for r in clean_recs:
            if not is_discarded(r):
                filtered_clean.append(r)
                
        if isinstance(clean_data, dict):
            clean_data["kayitlar"] = filtered_clean
        else:
            clean_data = filtered_clean
            
        with CLEAN_PATH.open("w", encoding="utf-8") as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=2)
        print(f"Clean dataset filtered. Kalan: {len(filtered_clean)}")

    # 3. Augmented Dataset
    if AUG_PATH.exists():
        with AUG_PATH.open(encoding="utf-8") as f:
            aug_data = json.load(f)
        aug_recs = aug_data.get("kayitlar", aug_data)
        
        filtered_aug = []
        for r in aug_recs:
            if not is_discarded(r):
                filtered_aug.append(r)
                
        if isinstance(aug_data, dict):
            aug_data["kayitlar"] = filtered_aug
        else:
            aug_data = filtered_aug
            
        with AUG_PATH.open("w", encoding="utf-8") as f:
            json.dump(aug_data, f, ensure_ascii=False, indent=2)
        print(f"Augmented dataset filtered. Kalan: {len(filtered_aug)}")

    # Save archived records
    if archived_records:
        archive_data = {"meta": {"aciklama": "Arşivlenen sektörlerin kayıtları"}, "kayitlar": archived_records}
        with ARCHIVE_PATH.open("w", encoding="utf-8") as f:
            json.dump(archive_data, f, ensure_ascii=False, indent=2)
        print(f"Archived {len(archived_records)} records to {ARCHIVE_PATH.name}")


def clean_codebase():
    print("--- Cleaning Codebase ---")
    
    # 1. k1_guardrails.py
    k1_file = ROOT / "src" / "k1_guardrails.py"
    if k1_file.exists():
        content = k1_file.read_text(encoding="utf-8")
        
        # clean SECTOR_MAP
        content = content.replace('"savunma": "ood",', "# 'savunma': 'ood' archived")
        content = content.replace('"defense": "ood",', "# 'defense': 'ood' archived")
        
        # clean STRICT_SECTOR_REGEX and SECTOR_ANCHORS
        # We can comment out or remove them. Let's make sure they are updated.
        # Since we modified the file earlier, let's keep only 5 core sectors.
        
        k1_file.write_text(content, encoding="utf-8")
        print("Updated k1_guardrails.py")

    # 2. llm_rewriter.py
    llm_file = ROOT / "src" / "llm_rewriter.py"
    if llm_file.exists():
        content = llm_file.read_text(encoding="utf-8")
        content = content.replace('"lojistik": ("lojistik", "kargo", "sevkiyat", "depo", "palet", "kamyon", "filo", "rota"),', "# lojistik archived")
        content = content.replace('"savunma": ("savunma", "radar", "nato", "komuta", "muharebe", "askeri"),', "# savunma archived")
        content = content.replace('"e_ticaret": ("e-ticaret", "eticaret", "sepet", "checkout"),', "# e_ticaret archived")
        content = content.replace('"finans": ("finans", "banka", "poliçe", "sigorta"),', "# finans archived")
        llm_file.write_text(content, encoding="utf-8")
        print("Updated llm_rewriter.py")

    # 3. data_augmented.py
    da_file = ROOT / "src" / "data_augmented.py"
    if da_file.exists():
        content = da_file.read_text(encoding="utf-8")
        # Remove savunma from KISALTMALAR and other dicts
        content = content.replace('"tsk": "savunma",', "# tsk archived")
        content = content.replace('"aselsan": "savunma",', "# aselsan archived")
        content = content.replace('"kkk": "savunma",', "# kkk archived")
        da_file.write_text(content, encoding="utf-8")
        print("Updated data_augmented.py")

    # 4. index.html
    html_file = ROOT / "demo" / "index.html"
    if html_file.exists():
        content = html_file.read_text(encoding="utf-8")
        # Clean up any custom configurations/dropdowns
        content = content.replace('"savunma",', "")
        content = content.replace('"finans",', "")
        content = content.replace('"lojistik",', "")
        content = content.replace('"e_ticaret",', "")
        content = content.replace('"enerji",', "")
        content = content.replace('"ik_kurumsal",', "")
        html_file.write_text(content, encoding="utf-8")
        print("Updated demo/index.html")


def flag_stale_index():
    print("--- Flagging Stale Index ---")
    npz_path = ROOT / "data" / "processed" / "embeddings.npz"
    meta_path = ROOT / "data" / "processed" / "index_meta.json"
    
    if npz_path.exists():
        stale_npz = npz_path.with_suffix(".npz.stale")
        if stale_npz.exists():
            stale_npz.unlink()
        npz_path.rename(stale_npz)
        print(f"Renamed {npz_path.name} to {stale_npz.name}")
        
    if meta_path.exists():
        stale_meta = meta_path.with_name("index_meta.json.stale")
        if stale_meta.exists():
            stale_meta.unlink()
        meta_path.rename(stale_meta)
        print(f"Renamed {meta_path.name} to {stale_meta.name}")

if __name__ == "__main__":
    clean_datasets()
    clean_codebase()
    flag_stale_index()
