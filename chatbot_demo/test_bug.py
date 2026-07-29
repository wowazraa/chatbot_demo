from src.chatbot import Chatbot
from src.frontend import serialize_response
import json

bot = Chatbot()
# Check active sector behavior if any
# We will just run the query.
query = "Bilgisayar mühendisliği taban puanları"
resp = bot.sor(query)
print("ChatbotResponse from bot.sor:")
print("sektor:", resp.sektor)
print("mod:", resp.mod)
print("skor:", resp.skor)

res = serialize_response(resp)
print("\nJSON from serialize_response:")
print("mod:", res["mod"])
print("sektor:", res["sektor"])
print("skor:", res["skor"])
print("inspector_label:", res["inspector_label"])
print("candidates:", json.dumps(res.get("top_candidates", []), indent=2))
