"""
Ham BGE skor debugger - başarısız senaryolarda gerçek BGE raw skorunu göster
FINAL_MIN ve blend sonrası değil, doğrudan corpus hit skorunu yakala
"""
import sys, pathlib, json
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chatbot import Chatbot

BASARISIZLAR = [
    ("A6", "Hekim takvimi ve muayene kaydi tutacak bir sistem istiyoruz."),
    ("A7", "Poliklinigimiz icin tele-tip altyapisi ariyoruz."),
    ("B2", "Turizmle ugrasan bir firmayiz."),
    ("B4", "Tatil koyu icin online rezervasyon altyapisi istiyoruz."),
    ("B5", "Seyahat acentesi olarak check-in cozumu ariyoruz."),
    ("B6", "Otel yonetim yazilimi teklifi almak istiyoruz."),
    ("C4", "NATO standartlarinda guvenli mesajlasma ariyoruz."),
    ("D5", "LMS kurulumu icin teklif almak istiyoruz."),
    ("G3", "Milli Savunma Bakanligi standartlarina uygun, siber saldirilara dayanikli ve kapali aglarda calisabilen askeri mesajlasma sunucusu tedarik etmek istiyoruz."),
    ("G4", "Kamu kurumlarina egitim ve danismanlik hizmeti sunan bir sirketiz. LMS platformu kurmak istiyoruz."),
]

def run():
    bot = Chatbot()
    emb = bot._get_embedder()

    print("=" * 90)
    print("HAM BGE SKOR DEBUGGER — Basarisiz 10 Senaryo")
    print("FINAL_MIN=0.75 ve MIN_BGE=0.85 filtrelenmeden once gercek top-3 corpus hits")
    print("=" * 90)

    from src.chatbot import _normalize
    
    for cid, girdi in BASARISIZLAR:
        norm = _normalize(girdi)
        print(f"\n[{cid}] {girdi[:60].encode('ascii','replace').decode()}")
        print(f"  Normalize: {norm[:60].encode('ascii','replace').decode()}")
        
        if emb and emb.is_ready():
            results = emb.find_top_k_hybrid(norm, k=5)
            print(f"  Top-5 BGE Hits:")
            for i, r in enumerate(results[:5]):
                sektor = r.metadata.get("beklenen_sektor", "?").encode('ascii','replace').decode()
                metin = r.text[:55].encode('ascii','replace').decode()
                print(f"    #{i+1}: skor={r.score:.4f} | {sektor:<10} | {metin}")
        
        yanit = bot.sor(girdi)
        acik = yanit.aciklama[:80].encode('ascii','replace').decode()
        print(f"  Final: mod={yanit.mod} sektor={yanit.sektor.encode('ascii','replace').decode()} skor={yanit.skor:.4f}")
        print(f"  Aciklama: {acik}")

if __name__ == "__main__":
    run()
