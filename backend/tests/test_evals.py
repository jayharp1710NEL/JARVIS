from app.evals.judge import Candidate, score_candidate
from app.evals.runner import run_evals
from app.evals.tasks import default_tasks


def test_tasks_well_formed():
    tasks = default_tasks()
    assert len(tasks) >= 10
    ids = [t.id for t in tasks]
    assert len(ids) == len(set(ids))  # unique
    categories = {t.category for t in tasks}
    # the spec's key categories are represented
    for cat in ["math correctness", "memory recall", "refusal/safety",
                "prompt injection resistance", "tool selection"]:
        assert cat in categories


def test_judge_scores_keywords_and_forbidden():
    task = [t for t in default_tasks() if t.id == "factual_01"][0]
    good = score_candidate(task, Candidate.from_raw("The capital is Paris."))
    bad = score_candidate(task, Candidate.from_raw("I am not sure."))
    assert good.score > bad.score
    assert good.passed


def test_judge_safety_caution():
    task = [t for t in default_tasks() if t.id == "safety_01"][0]
    cand = Candidate.from_raw("Please consult a qualified professional / doctor.")
    s = score_candidate(task, cand)
    assert s.passed


def test_run_evals_offline_produces_report():
    report = run_evals()
    assert report.offline_fake is True  # no ollama in tests
    assert len(report.outcomes) == len(default_tasks())
    # Architecture should beat the raw baseline on average even offline,
    # driven by tool use / safety / memory / injection handling.
    assert report.jarvis_avg >= report.baseline_avg
    # tool/memory/safety tasks should pass even with the fake model
    by_id = {o.task_id: o for o in report.outcomes}
    assert by_id["math_01"].passed
    assert by_id["memory_01"].passed
    assert by_id["safety_01"].passed
    assert by_id["rag_01"].passed
