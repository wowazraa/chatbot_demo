import json
from pathlib import Path

ROOT = Path("c:/Users/AZRA/OneDrive/Desktop/Chatbot_Bilgi_Merkezi_Projesi/chatbot_demo")
DISCARDED_SECTORS = {"savunma", "finans", "lojistik", "e_ticaret", "enerji", "ik_kurumsal"}

def clean_json_fixture(path):
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
        
    is_dict = isinstance(data, dict)
    recs = data.get("senaryolar", data) if is_dict else data
    
    filtered = []
    for item in recs:
        if isinstance(item, str):
            continue
        # Check if beklenen_sektor or any list references discarded sectors
        sec = item.get("beklenen_sektor", "")
        if isinstance(sec, list):
            if any(s in DISCARDED_SECTORS for s in sec):
                continue
        elif sec in DISCARDED_SECTORS:
            continue
            
        yasak = item.get("yasak_sektor", [])
        if isinstance(yasak, list):
            item["yasak_sektor"] = [s for s in yasak if s not in DISCARDED_SECTORS]
            
        filtered.append(item)
        
    if is_dict:
        data["senaryolar"] = filtered
        if "meta" in data and "toplam_senaryo" in data["meta"]:
            data["meta"]["toplam_senaryo"] = len(filtered)
    else:
        data = filtered
        
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Cleaned JSON fixture: {path.name} (Remaining: {len(filtered)})")

# Clean json fixtures
clean_json_fixture(ROOT / "tests" / "fixtures" / "test_scenarios.json")
clean_json_fixture(ROOT / "tests" / "fixtures" / "chaos_monkey.json")
clean_json_fixture(ROOT / "tests" / "fixtures" / "the_crucible.json")

# For python test files, comment out or replace occurrences.
cekim_eki = ROOT / "tests" / "test_cekim_eki.py"
if cekim_eki.exists():
    content = cekim_eki.read_text(encoding="utf-8")
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if any(sec in line.lower() for sec in DISCARDED_SECTORS):
            new_lines.append("# " + line)
        else:
            new_lines.append(line)
    cekim_eki.write_text("\n".join(new_lines), encoding="utf-8")
    print("Cleaned test_cekim_eki.py")

cekim_eki_orig = ROOT / "tests" / "run_cekim_eki_orijinal.py"
if cekim_eki_orig.exists():
    content = cekim_eki_orig.read_text(encoding="utf-8")
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if any(sec in line.lower() for sec in DISCARDED_SECTORS):
            new_lines.append("# " + line)
        else:
            new_lines.append(line)
    cekim_eki_orig.write_text("\n".join(new_lines), encoding="utf-8")
    print("Cleaned run_cekim_eki_orijinal.py")

stres_test = ROOT / "tests" / "run_stres_test.py"
if stres_test.exists():
    content = stres_test.read_text(encoding="utf-8")
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if any(sec in line.lower() for sec in DISCARDED_SECTORS):
            new_lines.append("# " + line)
        else:
            new_lines.append(line)
    stres_test.write_text("\n".join(new_lines), encoding="utf-8")
    print("Cleaned run_stres_test.py")
