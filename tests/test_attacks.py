"""Every attack in the suite must be stopped, even against an agent that obeys every injection,
and no honest page may be blocked."""
import pytest

import store
from bench import run_one
from alibi.paypal import FakePayPal

ATTACKS = [n for n, s in store.SCENARIOS.items() if s.kind == "attack" and n != "poisoned"]
BENIGN = [n for n, s in store.SCENARIOS.items() if s.kind == "benign"]


@pytest.mark.parametrize("name", ATTACKS)
def test_attack_is_blocked(name):
    pp = FakePayPal()
    r = run_one(name, offline=True, paypal=pp)
    assert r["fooled"], "the worst-case agent should take the bait"
    assert not r["stolen"]
    assert pp.payments == []


@pytest.mark.parametrize("name", BENIGN)
def test_honest_page_not_blocked(name):
    pp = FakePayPal()
    r = run_one(name, offline=True, paypal=pp)
    assert r["completed"] and not r["false_block"]
    assert pp.payments[0]["payee"] == store.REAL_PAYEE
