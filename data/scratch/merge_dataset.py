import json
import os
import shutil
from datetime import datetime

base_dir = r"C:\Users\AZRA\OneDrive\Desktop\Chatbot_Bilgi_Merkezi_Projesi\chatbot_demo\data"
raw_dir = os.path.join(base_dir, "raw")
original_path = os.path.join(raw_dir, "chatbot_dataset.json")
preview_path = os.path.join(base_dir, "scratch", "new_dataset_preview.json")

# 1. Yedekleme
backup_name = f"chatbot_dataset_yedek_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
backup_path = os.path.join(raw_dir, backup_name)

if os.path.exists(original_path):
    shutil.copy2(original_path, backup_path)
    print(f"Yedek alındı: {backup_path}")
else:
    print("HATA: Orijinal dataset bulunamadı!")
    exit(1)

# 2. Orijinal veriyi oku
with open(original_path, "r", encoding="utf-8") as f:
    orijinal_data = json.load(f)

# 3. Yeni veriyi oku
with open(preview_path, "r", encoding="utf-8") as f:
    yeni_data = json.load(f)

# 4. Birleştir
orijinal_kayitlar = orijinal_data.get("kayitlar", [])
yeni_kayitlar = yeni_data.get("kayitlar", [])

print(f"Orijinal kayıt sayısı: {len(orijinal_kayitlar)}")
print(f"Eklenecek yeni kayıt sayısı: {len(yeni_kayitlar)}")

birlestirilmis = orijinal_kayitlar + yeni_kayitlar
orijinal_data["kayitlar"] = birlestirilmis

# 5. Kaydet
with open(original_path, "w", encoding="utf-8") as f:
    json.dump(orijinal_data, f, ensure_ascii=False, indent=2)

print(f"BAŞARILI: Toplam kayıt sayısı {len(birlestirilmis)} olarak güncellendi ve {original_path} dosyasına yazıldı.")
