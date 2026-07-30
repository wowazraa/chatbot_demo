import ast
from pathlib import Path


def test_cekim_eki_header_and_active_scenario_count_are_consistent():
    path = Path(__file__).resolve().parent / "run_cekim_eki_orijinal.py"
    text = path.read_text(encoding="utf-8")
    module = ast.parse(text, filename=str(path))

    senaryolar_assign = next(
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "SENARYOLAR" for target in node.targets)
    )
    active_scenarios = [
        elt for elt in senaryolar_assign.value.elts
        if isinstance(elt, ast.Tuple) and len(elt.elts) == 4
    ]

    assert len(active_scenarios) == 30
    assert "30 aktif senaryo" in text
    assert "ORIJINAL CEKIM EKI TEST SETI — {AKTIF_SENARYO_SAYISI}" in text
