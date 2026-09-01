import json
from studio_runner.config import load_config

def test_template_config_loads(tmp_path):
    d = tmp_path / ".studio"
    d.mkdir()
    d.joinpath("studio.yaml").write_text(json.dumps({"studio":{"canonical_branch":"main"},"review":{"max_builder_reviewer_rounds":2}}))
    c = load_config(tmp_path)
    assert c.canonical_branch == "main"
    assert c.max_review_rounds == 2
