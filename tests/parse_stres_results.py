import json, sys

data = json.load(open('reports/stres_testi_sonuclari.json', encoding='utf-8'))

# Genel ozet
toplam = len(data)
basarili = sum(1 for r in data if r['basarili'])
print(f"GENEL: {basarili}/{toplam} ({basarili/toplam*100:.1f}%)")
print()

# Kategori breakdown
cats = {}
for r in data:
    k = r['kategori']
    cats.setdefault(k, {'b': 0, 't': 0})
    cats[k]['t'] += 1
    if r['basarili']:
        cats[k]['b'] += 1

kat_aciklamalar = {
    "A": "Negasyon",
    "B": "Coklu Niyet",
    "C": "Yazim/Kisaltma",
    "D": "Dil Karisimi",
    "E": "Uzun Kurumsal",
    "F": "False-Positive Traplar",
    "G": "Fiyat/Genel Soru",
    "H": "Adversarial",
    "I": "Session Hafiza"
}

print("KATEGORI BAZLI:")
for k, v in sorted(cats.items()):
    oran = v['b']/v['t']*100
    durum = "KRITIK" if oran < 50 else ("ORTA" if oran < 80 else "BASARILI")
    print(f"  {k} ({kat_aciklamalar.get(k,'?')}): {v['b']}/{v['t']} ({oran:.1f}%) [{durum}]")

print()
print("F KATEGORISI (False-Positive Traplar) DETAY:")
for r in data:
    if r['kategori'] == 'F':
        ok = "PASS" if r['basarili'] else "FAIL"
        girdi = r['girdi_metni'][:55].encode('ascii','replace').decode()
        sektor = r['tespit_edilen_sektor'].encode('ascii','replace').decode()
        beklenen = r['beklenen_sektor'].encode('ascii','replace').decode()
        print(f"  {r['id']}: {ok} | Beklenen:{beklenen:<10} Alinan:{sektor:<10} | {r['tespit_edilen_mod']} | {girdi}")

print()
print("BASARISIZ OLAN SENARYOLAR:")
for r in data:
    if not r['basarili']:
        girdi = r['girdi_metni'][:50].encode('ascii','replace').decode()
        alinan = r['tespit_edilen_sektor'].encode('ascii','replace').decode()
        beklenen = r['beklenen_sektor'].encode('ascii','replace').decode()
        print(f"  {r['id']}: Beklenen={beklenen}/{r['beklenen_mod']}, Alinan={alinan}/{r['tespit_edilen_mod']} | {girdi}")
