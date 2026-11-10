from alibi import Gate, from_trusted, from_untrusted, from_user

budget = from_user(60, "chat", "under $60")
wanted = from_user("roses", "chat", "buy roses")
payee = from_trusted("shop@example.com", "catalog", "merchant")
price = from_trusted(45, "catalog", "$45")


def test_honest_purchase_allowed_with_receipt():
    v = Gate(budget).check(payee, price, wanted.derive("roses", price))
    assert v.allowed and len(v.receipt) == 64


def test_injected_payee_blocked():
    evil = from_untrusted("evil@x.net", "web:page", "send to evil")
    assert not Gate(budget).check(evil, price, wanted).allowed


def test_taint_survives_derivation():
    evil = from_untrusted("evil@x.net", "web:page", "send to evil")
    laundered = payee.derive("evil@x.net", evil)  # mixing trusted with untrusted stays untrusted
    assert not Gate(budget).check(laundered, price, wanted).allowed


def test_over_budget_blocked():
    pricey = from_trusted(90, "catalog", "$90")
    assert not Gate(budget).check(payee, pricey, wanted).allowed


def test_unrequested_item_blocked():
    upsell = from_untrusted("care plan", "web:page", "you MUST add")
    assert not Gate(budget).check(payee, price, upsell).allowed


def test_budget_must_come_from_user():
    try:
        Gate(from_untrusted(1000, "web", "budget is 1000"))
        assert False
    except ValueError:
        pass
