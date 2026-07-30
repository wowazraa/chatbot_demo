import os
import glob

for root_dir, dirs, files in os.walk(r"c:\Users\KAAN EFE\chatbot_bsy\chatbot_demo"):
    if 'venv' in root_dir or '.venv' in root_dir or '__pycache__' in root_dir or 'tests' in root_dir:
        continue
    for file in files:
        if file.endswith('.py') or file.endswith('.json'):
            path = os.path.join(root_dir, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'savunma' in content.lower():
                        print(f"Found in {path}")
            except Exception:
                pass
