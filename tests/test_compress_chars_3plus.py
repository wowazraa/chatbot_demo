from src.v2_pipeline import compress_chars_3plus, preprocess_query


def test_legitimate_double_letter_words_are_preserved():
    assert compress_chars_3plus("elli") == "elli"
    assert compress_chars_3plus("belli") == "belli"
    assert compress_chars_3plus("kelle") == "kelle"
    assert compress_chars_3plus("tibbi") == "tibbi"
    assert compress_chars_3plus("hall") == "hall"


def test_typo_examples_still_compress():
    assert preprocess_query("tuuurizm") == "turizm"
    assert preprocess_query("saglikk") == "saglikk"
    assert preprocess_query("saglik") == "sağlık"
