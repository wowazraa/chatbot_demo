import re
from pathlib import Path

ROOT = Path("c:/Users/AZRA/OneDrive/Desktop/Chatbot_Bilgi_Merkezi_Projesi/chatbot_demo")
DISCARDED_SECTORS = {"savunma", "finans", "lojistik", "e_ticaret", "enerji", "ik_kurumsal"}

# 1. Cleaning tests/run_stres_test.py
stres_path = ROOT / "tests" / "run_stres_test.py"
if stres_path.exists():
    content = stres_path.read_text(encoding="utf-8")
    
    # We want to parse the dictionary blocks.
    # A simple regex to find the dict blocks in TEST_SENARYOLARI:
    # { ... }
    pattern = re.compile(r"\{\s*[^}]*?\}", re.DOTALL)
    
    def repl(match):
        block = match.group(0)
        # check if it references any discarded sector
        # For stres test, check: "beklenen_sektor": "savunma", etc.
        # Or look at individual fields
        if any(f'"{sec}"' in block.lower() or f"'{sec}'" in block.lower() for sec in DISCARDED_SECTORS):
            # Instead of keeping it, we will return empty string or comment it out completely
            # Let's comment out every line of this dictionary block
            lines = block.splitlines()
            return "\n".join("# " + l for l in lines)
        return block
        
    new_content = pattern.sub(repl, content)
    stres_path.write_text(new_content, encoding="utf-8")
    print("Cleaned run_stres_test.py successfully.")

# 2. Cleaning tests/test_cekim_eki.py
cekim_path = ROOT / "tests" / "test_cekim_eki.py"
if cekim_path.exists():
    content = cekim_path.read_text(encoding="utf-8")
    # In test_cekim_eki.py, the lines are tuples: ("A1", "Biz...", "sektor", "K2"),
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("(") and any(f'"{sec}"' in line.lower() or f"'{sec}'" in line.lower() for sec in DISCARDED_SECTORS):
            new_lines.append("# " + line)
        else:
            new_lines.append(line)
    cekim_path.write_text("\n".join(new_lines), encoding="utf-8")
    print("Cleaned test_cekim_eki.py successfully.")

# 3. Cleaning tests/run_cekim_eki_orijinal.py
orig_path = ROOT / "tests" / "run_cekim_eki_orijinal.py"
if orig_path.exists():
    content = orig_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("(") and any(f'"{sec}"' in line.lower() or f"'{sec}'" in line.lower() for sec in DISCARDED_SECTORS):
            new_lines.append("# " + line)
        else:
            new_lines.append(line)
    orig_path.write_text("\n".join(new_lines), encoding="utf-8")
    print("Cleaned run_cekim_eki_orijinal.py successfully.")
