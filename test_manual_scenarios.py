"""
Manuel demo test senaryoları
"""
from src.chatbot import Chatbot

bot = Chatbot()

# Senaryo 1: Session memory testi
print("=== Senaryo 1: Session Memory Test ===")
session_id = "test_session_1"

# İlk mesaj
resp1 = bot.sor("Bir otel işletiyoruz, rezervasyon sistemi arıyoruz.", session_id=session_id)
print(f"Mesaj 1: {resp1.sektor} / {resp1.mod} / {resp1.skor}")

# Debug: aktif_sektor kontrolü
if hasattr(bot, '_v2_pipeline'):
    aktif = bot._v2_pipeline.get_aktif_sektor(session_id)
    print(f"Aktif sektor: {aktif}")

# İkinci mesaj (generic follow-up)
resp2 = bot.sor("Kurulum süresi ne kadar sürer?", session_id=session_id)
print(f"Mesaj 2: {resp2.sektor} / {resp2.mod} / {resp2.skor}")

# Senaryo 2: Otel kelimesi yaması daraltma testi
print("\n=== Senaryo 2: Otel Kelimesi Yaması Daraltma Test ===")
session_id = "test_session_2"

# Debug: self_subject_keywords kontrolü
query = "Yazılımcıyız, otellere çözüm sunuyoruz."
self_subject_keywords = ["yazılımcıyız", "yazılım firması", "bilişim şirketi", "teknoloji şirketi", "yazılım geliştiriyoruz", "yazılım çözüm"]
is_self_subject = any(keyword in query.lower() for keyword in self_subject_keywords)
print(f"Self subject detected: {is_self_subject}")

resp3 = bot.sor(query, session_id=session_id)
print(f"Mesaj 3: {resp3.sektor} / {resp3.mod} / {resp3.skor}")

# Beklenen: turizm değil, belirsiz veya bilişim
