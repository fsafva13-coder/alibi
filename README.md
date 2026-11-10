# Alibi

**Every payment your AI agent makes must say where it came from.**

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-web%20server-009688?logo=fastapi&logoColor=white)
![PayPal](https://img.shields.io/badge/PayPal-Payouts%20sandbox-003087?logo=paypal&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-agent-8E75B2?logo=googlegemini&logoColor=white)
![AG Grid](https://img.shields.io/badge/AG%20Grid-ledger-0E4491)
![Tests](https://img.shields.io/badge/tests-27%20passing-2F6F5E)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## Project overview

AI shopping agents believe what they read, so a product page can hide a line that tells the agent to pay someone else, charge more, or add something you never asked for (prompt injection). Alibi is a checkpoint between the agent and PayPal that traces each payment detail (who gets paid, how much, and for what) back to its source. A payment goes through only if every detail traces to the customer's own words or the merchant's verified PayPal listing. Anything else is held for the customer to approve or decline, and the justification is sealed into the PayPal payment as a receipt.

## Features

- **Provenance tracking:** Every piece of text the agent sees is recorded with its source and trust level: the customer, a verified merchant listing, or untrusted web content.
- **Deterministic payment gate:** The decision is made by plain code, not a second AI model, so injected text cannot talk its way past it.
- **Human approval instead of hard blocks:** A held payment shows the reason in plain words, and approving it becomes the alibi, so a false alarm costs one tap rather than a lost order.
- **Receipts on PayPal:** A SHA-256 fingerprint of each payment's justification is attached to the PayPal payout.
- **Visual trace:** Threads on the website tie each line of the payment slip to the exact sentence it came from, and hovering a line lights up its source.
- **Attack suite and benchmark:** Eight realistic injection tricks and three honest control pages, run against a real Gemini agent or a worst-case agent that obeys every injection.
- **Write-a-trap playground:** Visitors can write their own malicious shop page and try to beat Alibi.
- **Ledger:** An AG Grid table of every payment attempt and its outcome.

## Tech stack

| Layer | Tools |
|---|---|
| Agent | Google Gemini (`google-genai`), manual tool-calling loop |
| Payments | PayPal REST API, Payouts (sandbox) |
| Gate and provenance | Python 3.12, standard library |
| Web server | FastAPI, Uvicorn |
| Front end | Hand-built HTML/CSS/JS, AG Grid Community, Bricolage Grotesque |
| Hosting | Render |
| Tests | pytest |

## Screenshots and demo

| | |
|---|---|
| ![Hero](docs/hero.png) | ![Held payment](docs/held.png) |
| *Hero: verified sources tied to the payment; the web page's thread is cut* | *A trap held for approval, with its thread traced to the injected sentence* |
| ![Alibi off](docs/alibi-off.png) | ![Ledger](docs/ledger.png) |
| *The same trick with Alibi switched off* | *Ledger of every payment attempt* |

Demo video: [YouTube link: add before submitting]

## Installation

```bash
git clone https://github.com/fsafva13-coder/alibi.git
cd alibi
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then paste your own keys into .env
```

`.env` needs a PayPal **sandbox** app's Client ID and Secret (with Payouts enabled) and a Gemini API key. Without them, the site falls back to a simulated PayPal and the obedient agent, so it still runs end to end.

## Usage

**Website**

```bash
uvicorn server:app --reload
# open http://localhost:8000
```

Pick a shop page, choose an agent, switch Alibi on or off, and send the agent. Hover any line of the payment slip to see where it came from.

**Terminal**

```bash
python agent.py --store fake-review --mode protected     # Alibi holds the trap
python agent.py --store fake-review --mode unprotected   # the agent pays the impostor
python agent.py --offline --store split-address          # no keys needed
python bench.py                                          # full attack suite with Gemini
python bench.py --offline                                # worst-case agent
python check.py                                          # test your keys
```

**For judges**

- Live demo: [Render link: add after deploying]
- No login is needed. The site runs on the PayPal sandbox, so no real money moves.
- The **Obedient** agent always works and shows the worst case. The **Gemini** agent is a real model and is subject to free-tier rate limits.

## Project structure

```
alibi/
├── alibi/
│   ├── provenance.py   # Trust levels, origins, tainted values, receipt hashing
│   ├── ledger.py       # Records everything the agent reads; traces payment values to sources
│   ├── gate.py         # The deterministic payment rules
│   └── paypal.py       # PayPal sandbox Payouts client (and a fake for tests)
├── agent.py            # Shopping agent: Gemini or obedient, with approval hook
├── store.py            # Verified listing, honest pages and eight attack pages
├── server.py           # FastAPI app: runs, live events, approvals, ledger
├── bench.py            # Attack benchmark → results.json
├── check.py            # Key checker and model lister
├── web/index.html      # The website
├── tests/              # 27 tests: gate, agent, every attack, web API
└── render.yaml         # One-click Render deployment
```

## Results

**Worst-case agent (obeys every injection):**

| Metric | Result |
|---|---|
| Attacks that reached PayPal | **0 of 8** |
| Honest purchases wrongly held | **0 of 3** |

**Gemini 3.5 Flash Lite (real model):** [fill in from `python bench.py`: attacks read, attacks fooled, honest purchases held]

The two numbers answer different questions. The real-model run shows how often today's model is fooled. The worst-case run shows that Alibi's protection does not depend on the model resisting.

## Challenges and learnings

- **Measuring honestly:** An early benchmark counted rate-limit errors and traps the agent never read as "resisted". It now separates errors and "not seen" from genuine results, and the errand requires reading the product page.
- **Models resist obvious traps:** Gemini ignored most injections when a verified listing sat in its context. That shifted the pitch from "the model will fail" to "nothing guarantees it won't", which is exactly what a deterministic gate covers.
- **False positives:** A hard block on anything untraceable would break legitimate edge cases, such as a shop that really did change its address. Turning the block into an approval request made the system safe and still usable.
- **Free-tier limits:** Different Gemini models have very different daily allowances, so the tools now detect daily-quota errors and stop instead of retrying.

## Future improvements

- Pull the trusted merchant identity from PayPal's own merchant data instead of a demo listing.
- Track provenance through the model's reasoning, not just the final tool arguments.
- Use PayPal Orders and Disputes, so a failed alibi can trigger an automatic refund or dispute pack.
- Ship Alibi as a wrapper for the PayPal Agent Toolkit and MCP server.
- Send approval requests as push notifications to the customer's phone.

## Demo and live link

- Live site: [Render link: add after deploying]
- Video: [YouTube link: add before submitting]
- Devpost: [Devpost link: add after submitting]

## License

[MIT](LICENSE) © 2026 Fathima Safva Ovinakath Kammukkakath
