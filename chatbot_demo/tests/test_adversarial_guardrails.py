import json
import pytest
from pathlib import Path
from src.chatbot import Chatbot

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "tests" / "adversarial_scenarios.json"

def load_scenarios():
    with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="module")
def bot():
    return Chatbot()

@pytest.mark.parametrize("scenario", load_scenarios())
def test_adversarial_query(bot, scenario):
    query = scenario["input_query"]
    expected = scenario["expected_sector"]
    
    # Sor
    resp = bot.sor(query)
    
    # Assert
    assert resp.sektor == expected, (
        f"Test {scenario['test_id']} FAILED!\n"
        f"Query: {query}\n"
        f"Expected: {expected}, Got: {resp.sektor}\n"
        f"Layer: {resp.mod}, Score: {resp.skor}\n"
        f"Reason: {scenario['why_it_breaks_the_rule']}"
    )
