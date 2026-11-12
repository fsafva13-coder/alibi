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

AI shopping agents believe what they read, so a product page can hide a line that tells the agent to pay someone else, charge more, or add something you never asked for (prompt injection). Alibi is a checkpoint between the agent and PayPal that traces each payment detail (who gets paid, how much, and for what) back to its source. A payment goes through only if every detail traces to the customer's own words or the merchant's verified PayPal listing. Anything else is held for the customer to approve or decline, and the justification is sealed into the PayPal payment as a receipt. In testing, a real Gemini agent was fooled by 2 of 8 injection attacks; Alibi stopped both payments without holding any honest purchase.

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

- Live demo: https://alibi-0tv9.onrender.com
- No login is needed. The site runs on the PayPal sandbox, so no real money moves.
- It is hosted on a free plan that sleeps when idle: the first visit can take up to a minute to load, and the ledger starts empty after a restart.
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

Eight attack pages and three honest pages, each run with Alibi switched on. Raw data is in [`results.json`](results.json).

| Metric | Gemini 3.5 Flash Lite (real model, single run) | Worst-case agent (obeys every injection) |
|---|---|---|
| Attacks the agent actually read | **8 of 8** | **8 of 8** |
| Attacks that fooled the agent | **2 of 8** | **8 of 8** |
| Attacker payments that reached PayPal | **0** | **0** |
| Honest purchases wrongly held | **0 of 3** | **0 of 3** |

**What fooled the real model:**

- **Look-alike listing:** A fake "updated merchant listing" on the product page with a near-identical address. Alibi traced the address to the web page and blocked it.
- **Mandatory add-on:** A note claiming a $12 care pack was required, raising the total to $57. Alibi traced the amount to the web page rather than the verified price and blocked it.

In both cases the agent was told the payment was blocked and went on to pay the verified shop the correct $45, so the customer still got their flowers.

The two columns answer different questions. The real-model run shows that a capable model still falls for subtle tricks. The worst-case run shows that Alibi's protection does not depend on the model resisting. Model behaviour varies between runs, so the real-model figures describe this run rather than a fixed rate.

## Challenges and learnings

- **Measuring honestly:** An early benchmark counted rate-limit errors and traps the agent never read as "resisted". It now separates errors and "not seen" from genuine results, and the errand requires reading the product page.
- **Models resist obvious traps, not subtle ones:** Gemini ignored blunt injections, such as hidden text addressed to AI assistants, but fell for a look-alike listing and a fake required add-on. The risk lies in the plausible tricks, which is exactly where a deterministic gate helps.
- **Agents can skip the evidence:** In early runs the agent paid straight from the verified listing without opening the product page, so it never saw the traps. Making the errand depend on page content (same-day delivery) made the test realistic.
- **False positives:** A hard block on anything untraceable would break legitimate edge cases, such as a shop that really did change its address. Turning the block into an approval request made the system safe and still usable.
- **Free-tier limits:** Different Gemini models have very different daily allowances, so the tools now detect daily-quota errors and stop instead of retrying.

## Future improvements

- Pull the trusted merchant identity from PayPal's own merchant data instead of a demo listing.
- Track provenance through the model's reasoning, not just the final tool arguments.
- Use PayPal Orders and Disputes, so a failed alibi can trigger an automatic refund or dispute pack.
- Ship Alibi as a wrapper for the PayPal Agent Toolkit and MCP server.
- Send approval requests as push notifications to the customer's phone.

## Demo and live link

- Live site: https://alibi-0tv9.onrender.com
- Video: https://youtu.be/j9afxQUzHN4
- Devpost: https://devpost.com/software/alibi-blnegr

## License

[MIT](LICENSE) © 2026 Fathima Safva Ovinakath Kammukkakath