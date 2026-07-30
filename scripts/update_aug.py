import re

file_path = "src/data_augmented.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove "savunma" from AUGMENTATION_TARGETS
content = re.sub(r'\s*"savunma": \([^)]+\),', '', content, flags=re.DOTALL)

# 2. Remove "savunma" mappings from KISALTMALAR
content = re.sub(r'\s*"[^"]+": "savunma",', '', content)

# 3. Remove Savunma section from _OOD_RELABEL_PATTERNS
content = re.sub(r'\s*# ── Savunma ─+.*?(?=\s*# ── Eğitim)', '', content, flags=re.DOTALL)

# 4. Update CLASS_BALANCE_CAP
new_caps = """CLASS_BALANCE_CAP: dict[str, int | None] = {
    "turizm":   947,
    "saglik":   947,
    "bilisim":  947,
    "egitim":   947,
    "eglence":  947,
    "ood":      None,
}"""
content = re.sub(r'CLASS_BALANCE_CAP: dict\[str, int \| None\] = \{[^}]+\}', new_caps, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated data_augmented.py")
