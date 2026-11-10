"""Alibi core: every value an agent uses in a payment carries a record of where it came from."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum


class Trust(str, Enum):
    USER = "user"            # the human typed it, or approved it
    TRUSTED = "trusted"      # a verified merchant catalogue or quote
    UNTRUSTED = "untrusted"  # anything the agent read: web pages, emails, reviews


@dataclass(frozen=True)
class Origin:
    trust: Trust
    source: str   # e.g. "chat:user", "catalog:petal-and-stem", "web:https://..."
    excerpt: str  # the exact text the value was taken from

    def to_json(self) -> dict:
        return {"trust": self.trust.value, "source": self.source, "excerpt": self.excerpt}


@dataclass(frozen=True)
class Tainted:
    """A value plus every origin it was derived from."""
    value: object
    origins: tuple[Origin, ...] = field(default_factory=tuple)

    def derive(self, value: object, *others: "Tainted") -> "Tainted":
        """A new value computed from this one (and others) inherits all their origins."""
        merged = self.origins + tuple(o for t in others for o in t.origins)
        return Tainted(value, merged)

    @property
    def weakest(self) -> Trust:
        """No origins at all means the agent invented the value, which is treated as untrusted."""
        order = [Trust.USER, Trust.TRUSTED, Trust.UNTRUSTED]
        return max((o.trust for o in self.origins), key=order.index, default=Trust.UNTRUSTED)

    def to_json(self) -> dict:
        return {"value": self.value, "origins": [o.to_json() for o in self.origins],
                "weakest": self.weakest.value}


def from_user(value, source: str, excerpt: str) -> Tainted:
    return Tainted(value, (Origin(Trust.USER, source, excerpt),))


def from_trusted(value, source: str, excerpt: str) -> Tainted:
    return Tainted(value, (Origin(Trust.TRUSTED, source, excerpt),))


def from_untrusted(value, source: str, excerpt: str) -> Tainted:
    return Tainted(value, (Origin(Trust.UNTRUSTED, source, excerpt),))


def alibi_hash(args: dict[str, Tainted]) -> str:
    """Fingerprint of the full justification, stored on the PayPal payment as a receipt."""
    record = {
        k: {"value": str(v.value), "origins": [o.to_json() for o in v.origins]}
        for k, v in sorted(args.items())
    }
    return hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
