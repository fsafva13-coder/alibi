"""The ledger remembers every piece of text the agent has seen, and where it came from.

When the agent asks to pay, Alibi looks up each payment value in the ledger to find its origin.
A value that appears only in untrusted content, or nowhere at all (the model invented it), has no alibi.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .provenance import Origin, Tainted, Trust

_NUM = re.compile(r"\d+(?:\.\d+)?")
_STOP = {"a", "an", "the", "for", "my", "of", "and", "to", "buy", "get", "me", "some", "under", "small", "please"}


@dataclass
class Entry:
    trust: Trust
    source: str
    text: str


class Ledger:
    def __init__(self) -> None:
        self.entries: list[Entry] = []

    def record(self, trust: Trust, source: str, text: str) -> str:
        self.entries.append(Entry(trust, source, text))
        return text

    def _origins(self, match) -> tuple[Origin, ...]:
        found = []
        for e in self.entries:
            hit = match(e.text)
            if hit:
                found.append(Origin(e.trust, e.source, _excerpt(e.text, hit)))
        return tuple(found)

    def trace_text(self, value: str) -> Tainted:
        """Where did this exact string (an email, a name) appear?"""
        v = value.strip().lower()
        origins = self._origins(lambda t: v if v and v in t.lower() else None)
        return Tainted(value, _strongest_only(origins))

    def trace_amount(self, value: float) -> Tainted:
        """Where did this number appear?"""
        def match(t):
            for m in _NUM.finditer(t):
                if abs(float(m.group()) - float(value)) < 0.005:
                    return m.group()
            return None
        return Tainted(value, _strongest_only(self._origins(match)))

    def trace_item(self, value: str) -> Tainted:
        """An item has an alibi if the user asked for it in their own words."""
        words = {w for w in re.findall(r"[a-z]+", value.lower()) if w not in _STOP and len(w) > 2}
        origins = self._origins(
            lambda t: next((w for w in words if re.search(rf"\b{w}", t.lower())), None)
        )
        return Tainted(value, origins)


def _strongest_only(origins: tuple[Origin, ...]) -> tuple[Origin, ...]:
    """If a value is vouched for by the user or a verified merchant, untrusted copies don't matter.
    If it only appears in untrusted content, keep those origins so the gate can name the culprit."""
    strong = tuple(o for o in origins if o.trust is not Trust.UNTRUSTED)
    return strong or origins


def _excerpt(text: str, hit: str, width: int = 60) -> str:
    i = text.lower().find(str(hit).lower())
    if i < 0:
        return text[:width]
    start = max(0, i - width // 2)
    return ("…" if start else "") + text[start:start + width].replace("\n", " ") + "…"
