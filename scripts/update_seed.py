import re

file_path = "db_api/routers/seed.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r'\s*\("defense",\s*"Savunma",\s*"Defense"\),', '', content)
content = re.sub(r'\s*\("defense_communications","https://example\.com/forms/defense",\s*"Savunma haberleşme formu"\),', '', content)
content = re.sub(r'\s*\("Delta Savunma Ltd\.",\s*"defense"\),', '', content)
content = re.sub(r'\s*\("NATO standartlarında güvenli askeri mesajlaşma sistemi ihtiyacımız var\.",\s*"Savunma projeleri için uçtan uca şifreli altyapı\.",\s*"defense",\s*\),', '', content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated seed.py")
