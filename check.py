"""Checks your .env keys one at a time, so you know exactly which service is the problem.

Run: python check.py
"""
import os

from dotenv import load_dotenv

load_dotenv()


def check_paypal() -> None:
    from alibi.paypal import PayPal
    cid, sec = os.environ.get("PAYPAL_CLIENT_ID", ""), os.environ.get("PAYPAL_CLIENT_SECRET", "")
    if not cid or not sec:
        print("PayPal  ✗ PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET is empty in .env")
        return
    try:
        PayPal()._auth()
        print("PayPal  ✓ sandbox keys work")
    except Exception as e:
        print(f"PayPal  ✗ {e}\n        Check you copied the SANDBOX keys (not Live) with no spaces.")


def check_gemini() -> None:
    from google import genai
    from google.genai import types
    key = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
    if not key:
        print("Gemini  ✗ GEMINI_API_KEY is empty in .env")
        return
    try:
        client = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=30_000, retry_options=types.HttpRetryOptions(attempts=1)))
        r = client.models.generate_content(model=model, contents="Reply with the word OK.")
        print(f"Gemini  ✓ {model} replied: {(r.text or '').strip()[:40]}")
    except Exception as e:
        print(f"Gemini  ✗ {model}: {str(e)[:300]}")


def list_models() -> None:
    """Shows every Gemini model your key can use for chat, so you can pick one with free allowance left."""
    from google import genai
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
    print("Models your key can use (put one in .env as GEMINI_MODEL=...):")
    for m in client.models.list():
        actions = getattr(m, "supported_actions", None) or []
        if "generateContent" in actions and "flash" in m.name.lower():
            print("  ", m.name.removeprefix("models/"))
    print("\nLive free-tier limits per model: aistudio.google.com → Dashboard → Rate limits.")
    print("Each model has its own daily allowance, so switching models gives you a fresh one.")


if __name__ == "__main__":
    import sys
    if "--models" in sys.argv:
        list_models()
        raise SystemExit
    print("Checking PayPal…", flush=True)
    check_paypal()
    print("Checking Gemini…", flush=True)
    check_gemini()
