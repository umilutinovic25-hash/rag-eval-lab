from src.human_agreement import analyse, kappa


def test_kappa_values():
    assert kappa([("ok", "ok"), ("wrong", "wrong")]) == 1.0
    assert kappa([("ok", "wrong"), ("wrong", "ok")]) == -1.0
    assert kappa([]) is None


def test_analyse_counts_and_compares_with_ai_labels():
    answers = [{"id": "test4:W20", "answer": "No, you do not need to."}, {"id": "test4:W22", "answer": "Yes, you can."}]
    review = {"reviewer": "x", "answers": {"test4:W20": {"v": "wrong"}, "test4:W22": {"v": "ok"}},
              "translation": {"hb-01-chunk-0": {"v": "fix", "c": "bolji izraz"}}}
    out = analyse(review, answers)
    assert out["answers_judged"] == 2 and out["wrong"] == ["test4:W20"]
    assert out["yes_no_agreement"] == 1.0  # AI also marks W20 wrong (label yes, answer no) and W22 ok
    assert out["translation_fix"] == {"hb-01-chunk-0": "bolji izraz"}
