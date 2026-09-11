# Running and stopping ZAPFISH

Use a dedicated account portfolio. ZAPFISH is an experiment capable of losing its entire allocated balance. The funding cap is **100 USDC at initialization**, not an assertion that USDC always equals one dollar.

## Installation and data

Python 3.11 or newer. `python -m zapfish prepare` downloads about 260 MB of public ZAPBench chunks and verifies them against `zapfish/neural/sources.lock.json`; `python -m zapfish verify` re-checks. `python -m zapfish train` fits the model (about a minute, 300 MB of RAM). Set `ZAPFISH_DATA` to use another data location.

## Paper modes

```sh
# Real public prices; simulated fills and 0.6% fee per side.
python -m zapfish run --steps 10

# Explicit synthetic offline market, accelerated development run.
python -m zapfish run --fixture --fast --steps 10 --out runs/fixture

# Frozen-memory control, always in a separate run directory.
python -m zapfish run --fixture --fast --frozen --steps 10 --out runs/frozen
```

`--fast` skips wall waits only in paper mode; the real 60-second execution cooldown still applies, so an accelerated probe can have many rejected trades. `--fixture` never claims real market data.

## Coinbase setup, performed by you

1. Create a separate Coinbase Advanced portfolio and put up to 100 USDC in it. Start without other assets or open orders.
2. Create a Coinbase App API key with ECDSA, **View and Trade**, **Transfer disabled**, scoped only to that portfolio. The program checks permissions and portfolio scope; an account-wide key is rejected.
3. Save the key JSON locally as `coinbase-key.json` and restrict its permissions. Never commit it.
4. `pip install -e '.[live]'`. Copy `.env.example` to `.env`, set the key path and `COINBASE_PORTFOLIO_ID`, then set `ZAPFISH_LIVE=I_ACCEPT_REAL_TRADES`. The CLI also requires `--live`.
5. `python -m zapfish run --live --preflight-only` reads permissions, balances and order state and initializes the ledger without submitting orders. Then `python -m zapfish run --live`.

## Execution guarantees and limits

Unchanged from STONKFLY: maximum buy commitment 10 USDC including a 2% fee reserve; sells capped by inventory; at most 24 attempts per UTC day and 60 seconds between attempts; price-bounded fill-or-kill orders with 0.5% slippage and spread limits; quotes no older than 15 seconds; a fresh book after neural integration; a $20 drawdown stops new orders without liquidating; a unique client order ID is persisted before submission and an uncertain response stays unresolved until reconciled. A local lock prevents two workers on one run directory.

## State, recovery and privacy

`runs/<name>/` holds a SQLite ledger, two alternating brain checkpoints, `events.jsonl`, `latest.json`, `latest-input.png` and `provenance.json` (settings, dataset verification, model hash, decoder description, source hashes). Stop with Ctrl-C or `touch runs/<name>/STOP`. After manual review, `--resume-reviewed` clears a transient halt; it cannot clear a drawdown or fee stop or accept changed source. All runtime state, `.env` and key files are git-ignored.
