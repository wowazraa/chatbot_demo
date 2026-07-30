import json

data = json.load(open('reports/stres_testi_sonuclari.json', encoding='utf-8'))
for r in data:
    if r['kategori'] == 'A':
        sid = r['id']
        ok = 'PASS' if r['basarili'] else 'FAIL'
        skor = r['skor']
        tahmin = r['tespit_edilen_sektor']
        beklenen = r['beklenen_sektor']
        girdi = r['girdi_metni'][:70]
        print(f"{sid:5s} {ok:4s} skor={skor:<8.4f} tahmin={tahmin:15s} beklenen={beklenen:15s} | {girdi}")
