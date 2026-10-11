import json, sys

CONTRACT = "contracts/ruling_parity.py"
RULE = "https://authority.example.org/eligibility-rule"
CASE_A = "https://decisions.example.org/case-a"
CASE_B = "https://decisions.example.org/case-b"
TEXT_RULE = "Applications qualify when the applicant maintained a local office for twelve continuous months before filing. Temporary closures shorter than thirty days do not interrupt continuity."
TEXT_A = "The applicant maintained a local office for fourteen continuous months before filing. A ten-day renovation closure occurred. The panel therefore GRANTS the application under the local-office rule."
TEXT_B = "The applicant maintained a local office for fifteen continuous months before filing. A twelve-day safety closure occurred. The panel nevertheless DENIES the application under the local-office rule."


def result(similarity="MATERIALLY_SIMILAR", outcome_b="DENIED"):
    return {
        "rule": {"source_index": 0, "criterion": "A local office must be maintained for twelve continuous months, ignoring closures shorter than thirty days.", "criterion_quote": "maintained a local office for twelve continuous months before filing"},
        "case_a": {"source_index": 1, "outcome": "GRANTED", "fact_quote": "maintained a local office for fourteen continuous months before filing", "outcome_quote": "panel therefore GRANTS the application", "explanation": "Fourteen months satisfies the duration and the ten-day closure is below the exception limit."},
        "case_b": {"source_index": 2, "outcome": outcome_b, "fact_quote": "maintained a local office for fifteen continuous months before filing", "outcome_quote": "panel nevertheless DENIES the application", "explanation": "Fifteen months satisfies the duration and the twelve-day closure is below the exception limit."},
        "comparison": {"similarity": similarity, "shared_factor": "Both applicants exceed twelve months and have a closure shorter than thirty days.", "distinguishing_factor": "No material distinction under the published continuity rule is stated."},
    }


def create(contract, review_id="office-decisions"):
    return contract.create_review(review_id, "Local office decision parity", "Did two materially similar applications receive inconsistent outcomes under the same local-office rule?", RULE, CASE_A, CASE_B)


def consensus(contract, monkeypatch, comparator=None):
    module = sys.modules[contract.__class__.__module__]
    monkeypatch.setattr(module.gl.eq_principle, "strict_eq", lambda fn: fn())
    monkeypatch.setattr(module.gl.eq_principle, "prompt_comparative", comparator or (lambda fn, *_args, **_kwargs: fn()))


def mocks(vm, payload=None):
    vm.mock_web(RULE, {"method": "GET", "status": 200, "body": TEXT_RULE})
    vm.mock_web(CASE_A, {"method": "GET", "status": 200, "body": TEXT_A})
    vm.mock_web(CASE_B, {"method": "GET", "status": 200, "body": TEXT_B})
    vm.mock_llm("RULINGPARITY_PRODUCER", json.dumps(json.dumps(payload or result())))


def test_contract_loads(direct_deploy):
    assert direct_deploy(CONTRACT) is not None


def test_rejects_duplicate_id_unsafe_and_duplicate_documents(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT); create(contract)
    with direct_vm.expect_revert("already exists"):
        create(contract)
    with direct_vm.expect_revert("public HTTPS"):
        contract.create_review("unsafe-review", "Unsafe review", "A sufficiently complete parity question for two decisions.", "http://localhost/rule", CASE_A, CASE_B)
    with direct_vm.expect_revert("distinct documents"):
        contract.create_review("duplicate-review", "Duplicate review", "A sufficiently complete parity question for two decisions.", RULE, CASE_A, CASE_A)


def test_derives_precedent_fork_and_final_receipt(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT); review = create(contract); consensus(contract, monkeypatch); mocks(direct_vm)
    evaluation = contract.evaluate(review)
    assert evaluation["verdict"] == "PRECEDENT_FORK"
    assert evaluation["case_a"]["outcome"] == "GRANTED" and evaluation["case_b"]["outcome"] == "DENIED"
    assert len(evaluation["receipts"]) == 3 and all(len(item["sha256"]) == 64 for item in evaluation["receipts"])
    final = contract.finalize(review)
    assert final["status"] == "FINAL" and len(final["final_receipt"]["receipt_sha256"]) == 64
    with direct_vm.expect_revert("Only an evaluated review"):
        contract.finalize(review)


def test_distinct_cases_are_consistent_even_with_different_outcomes(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT); review = create(contract); consensus(contract, monkeypatch); mocks(direct_vm, result("MATERIALLY_DISTINCT"))
    assert contract.evaluate(review)["verdict"] == "CONSISTENT"


def test_unclear_similarity_fails_closed_to_inconclusive(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT); review = create(contract); consensus(contract, monkeypatch); mocks(direct_vm, result("UNCLEAR"))
    assert contract.evaluate(review)["verdict"] == "INCONCLUSIVE"


def test_forged_quote_and_swapped_indexes_are_rejected(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT); review = create(contract); consensus(contract, monkeypatch)
    forged = result(); forged["case_b"]["outcome_quote"] = "fabricated disposition absent from the decision"; mocks(direct_vm, forged)
    with direct_vm.expect_revert("Outcome quote"):
        contract.evaluate(review)
    direct_vm.clear_mocks(); swapped = result(); swapped["case_a"]["source_index"] = 2; mocks(direct_vm, swapped)
    with direct_vm.expect_revert("Source indexes"):
        contract.evaluate(review)


def test_validator_disagreement_and_unreadable_source_preserve_ready_state(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT); review = create(contract)
    def disagree(fn, *_args, **_kwargs):
        fn(); raise RuntimeError("validator disagreement")
    consensus(contract, monkeypatch, disagree); mocks(direct_vm)
    try:
        contract.evaluate(review); assert False, "unexpected evaluation success"
    except RuntimeError as error:
        assert "disagreement" in str(error)
    assert contract.get_review(review)["status"] == "READY"
    direct_vm.clear_mocks(); review2 = create(contract, "office-decisions-two"); consensus(contract, monkeypatch)
    direct_vm.mock_web(RULE, {"method": "GET", "status": 200, "body": "too short"}); direct_vm.mock_web(CASE_A, {"method": "GET", "status": 200, "body": TEXT_A}); direct_vm.mock_web(CASE_B, {"method": "GET", "status": 200, "body": TEXT_B})
    with direct_vm.expect_revert("unavailable or unreadable"):
        contract.evaluate(review2)
