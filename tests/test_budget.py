from studio_runner.budget import Budget

def test_budget_ceiling(tmp_path):
    b = Budget(tmp_path / "b.json", 10)
    assert b.can_spend(9.5)
    b.record(9.5)
    assert not b.can_spend(0.6)
