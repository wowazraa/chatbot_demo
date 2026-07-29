import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "reports" / "stres_testi_sonuclari.json"

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

cat_a = [r for r in data if r['kategori'] == 'A']
for r in cat_a:
    print(f"ID: {r['id']}")
    print(f"  Girdi: {r['girdi_metni']}")
    print(f"  Beklenen: {r['beklenen_sektor']}")
    print(f"  Tespit: {r['tespit_edilen_sektor']} ({r['tespit_edilen_mod']})")
    print(f"  Skor: {r['skor']} | Katman: {r['katman']} | Basarili: {r['basarili']}")
    print("-" * 50)
