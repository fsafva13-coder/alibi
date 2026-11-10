"""The gate: plain code, not an AI, decides whether a payment has an alibi."""
from __future__ import annotations

from dataclasses import dataclass

from .provenance import Tainted, Trust, alibi_hash


@dataclass
class Verdict:
    allowed: bool
    reasons: list[str]
    receipt: str | None = None


class Gate:
    def __init__(self, budget: Tainted):
        if budget.weakest is not Trust.USER:
            raise ValueError("The budget must come from the user")
        self.budget = budget

    def check(self, payee: Tainted, amount: Tainted, item: Tainted) -> Verdict:
        reasons: list[str] = []

        # Rule 1: who gets paid must trace to the user or a verified merchant, never to content the agent read.
        if payee.weakest is Trust.UNTRUSTED:
            bad = [o for o in payee.origins if o.trust is Trust.UNTRUSTED]
            if bad:
                reasons.append(f"Payee '{payee.value}' comes from untrusted content: {bad[0].source}")
            else:
                reasons.append(f"Payee '{payee.value}' appears nowhere you said or the agent read: "
                               "the agent assembled it")

        # Rule 2: the amount must come from a trusted price, not from text on a page.
        if amount.weakest is Trust.UNTRUSTED:
            src = next((o.source for o in amount.origins), None)
            reasons.append(f"Amount {amount.value} was not taken from a verified price"
                           + (f": it comes from {src}" if src else ": it appears nowhere"))

        # Rule 3: the amount must fit the budget the user set.
        if float(amount.value) > float(self.budget.value):
            reasons.append(f"Amount {amount.value} exceeds the user's budget of {self.budget.value}")

        # Rule 4: what is being bought must trace back to something the user asked for.
        if not any(o.trust is Trust.USER for o in item.origins):
            reasons.append(f"Item '{item.value}' was never requested by the user")

        if reasons:
            return Verdict(False, reasons)
        receipt = alibi_hash({"payee": payee, "amount": amount, "item": item, "budget": self.budget})
        return Verdict(True, ["Every value traces to the user or a verified merchant"], receipt)
