"""Minimal PayPal sandbox client.

The agent pays merchants from its own sandbox wallet using PayPal Payouts, which sends money
to an email address without a checkout page. Each payout carries the Alibi receipt so the
payment and its justification are permanently linked.
"""
from __future__ import annotations

import os
import uuid

import requests

SANDBOX = "https://api-m.sandbox.paypal.com"


class PayPal:
    def __init__(self, client_id: str | None = None, secret: str | None = None, base: str = SANDBOX):
        self.client_id = client_id or os.environ["PAYPAL_CLIENT_ID"]
        self.secret = secret or os.environ["PAYPAL_CLIENT_SECRET"]
        self.base = base
        self._token: str | None = None

    def _auth(self) -> dict:
        if not self._token:
            r = requests.post(
                f"{self.base}/v1/oauth2/token",
                auth=(self.client_id, self.secret),
                data={"grant_type": "client_credentials"},
                timeout=20,
            )
            r.raise_for_status()
            self._token = r.json()["access_token"]
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    def pay(self, payee_email: str, amount: float, note: str, receipt: str | None) -> dict:
        body = {
            "sender_batch_header": {
                "sender_batch_id": f"alibi-{uuid.uuid4().hex[:12]}",
                "email_subject": "You have a payment",
                "email_message": note[:255],
            },
            "items": [{
                "recipient_type": "EMAIL",
                "receiver": payee_email,
                "amount": {"value": f"{amount:.2f}", "currency": "USD"},
                "note": note[:4000],
                # The receipt rides on the PayPal payment itself. "NONE" marks an unprotected payment.
                "sender_item_id": (receipt or "NONE")[:30],
            }],
        }
        r = requests.post(f"{self.base}/v1/payments/payouts", json=body, headers=self._auth(), timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"PayPal error {r.status_code}: {r.text[:300]}")
        data = r.json()
        return {"batch_id": data["batch_header"]["payout_batch_id"], "status": data["batch_header"]["batch_status"]}


class FakePayPal:
    """Stands in for PayPal in tests and offline runs."""

    def __init__(self) -> None:
        self.payments: list[dict] = []

    def pay(self, payee_email: str, amount: float, note: str, receipt: str | None) -> dict:
        p = {"batch_id": f"FAKE-{len(self.payments) + 1}", "status": "SUCCESS",
             "payee": payee_email, "amount": amount, "receipt": receipt}
        self.payments.append(p)
        return {"batch_id": p["batch_id"], "status": p["status"]}
