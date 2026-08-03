import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import capstone.agent as capstone_agent
import harness


def test_target_enables_auto_approval_for_eval(monkeypatch, tmp_path):
    observed = {}

    def fake_run_agent_slice(**kwargs):
        observed["auto_approve"] = os.environ.get("AUTO_APPROVE_HITL")
        return None

    monkeypatch.setattr(capstone_agent, "run_agent_slice", fake_run_agent_slice)
    monkeypatch.setenv("AUTO_APPROVE_HITL", "")
    monkeypatch.setattr(harness, "_read_doc_artifact", lambda path: "doc content")
    monkeypatch.setattr(harness, "_cleanup_doc_artifacts", lambda: None)

    harness.target("hello")

    assert observed["auto_approve"] == "1"
