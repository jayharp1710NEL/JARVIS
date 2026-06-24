from app.agent.router import heuristic_classify
from app.agent.schemas import ChatRequest, Mode, TaskType
from app.agent.verifier import verify
from app.agent.executor import GatheredContext
from app.memory.schemas import MemoryCreate, MemoryType
from app.memory.service import memory_service
from app.rag.ingest import ingest_bytes


def test_heuristic_classification():
    assert heuristic_classify("what is 12 * 9?", False).needs_math
    assert heuristic_classify("latest news today about AI", False).needs_web
    assert heuristic_classify("write a python function", False).task_type == TaskType.coding
    assert heuristic_classify("what medication dosage for pain", False).is_high_risk
    assert heuristic_classify("remember that I like tea", False).needs_memory
    assert heuristic_classify("read https://example.com please", False).needs_url_read


def test_orchestrator_math_uses_calculator(orchestrator):
    resp = orchestrator.run(ChatRequest(message="Compute 23 * 19 please.", mode=Mode.deep))
    assert any(t.tool == "calculator" and t.ok for t in resp.tool_trace)
    assert any("437" in (t.summary or "") for t in resp.tool_trace)


def test_orchestrator_high_risk_caution(orchestrator):
    resp = orchestrator.run(ChatRequest(message="what medication should I take for chest pain", mode=Mode.fast))
    assert "professional" in resp.answer.lower()
    assert resp.next_best_action


def test_orchestrator_uses_memory(orchestrator):
    memory_service.save(MemoryCreate(content="User's favorite language is Rust", type=MemoryType.user_preference, tags=["lang", "rust"]))
    resp = orchestrator.run(ChatRequest(message="what is my favorite language?", mode=Mode.fast, use_memory=True))
    assert resp.memory_used


def test_orchestrator_uses_files(orchestrator):
    res = ingest_bytes("facts.md", b"The project codename is Sentinel. It launched in 2026.")
    resp = orchestrator.run(ChatRequest(message="what is the project codename?", mode=Mode.fast, file_ids=[res.file_id], use_files=True))
    assert resp.file_citations
    assert resp.file_citations[0].filename == "facts.md"


def test_orchestrator_privacy_mode_blocks_web(orchestrator):
    # privacy mode + a current-info query: web must not be used
    resp = orchestrator.run(ChatRequest(message="latest stock price news today", mode=Mode.research, local_privacy=True))
    assert resp.mode == Mode.privacy
    assert not any(t.tool == "web_search" and t.ok for t in resp.tool_trace)


def test_verifier_grounds_cited_claims():
    ctx = GatheredContext()
    ctx.read_texts = {"S1": "The Eiffel Tower is located in Paris and was completed in 1889."}
    draft = "The Eiffel Tower is in Paris [1]. It opened in 1889 [1]."
    report = verify(draft, ctx)
    assert report.grounded_ratio > 0.5
    assert all(c.status in ("verified", "likely") for c in report.claims)


def test_verifier_flags_unsupported():
    ctx = GatheredContext()  # no evidence
    draft = "The hidden moon base produces 500 terawatts of power continuously."
    report = verify(draft, ctx)
    assert report.unsupported
