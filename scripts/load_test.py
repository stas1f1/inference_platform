"""
Sustained concurrent load against the LLM /v1/generate endpoint.

Keeps `--concurrency` requests in flight for `--duration` seconds so the
`llm_pending_requests` gauge stays above the HPA target long enough for
Prometheus to scrape it and the HPA to react.

Usage (after `make pf-llm` is running in another shell):
    python scripts/load_test.py
    python scripts/load_test.py -c 30 -d 90 --max-new-tokens 256
"""

import argparse
import asyncio
import time

import httpx


async def worker(client: httpx.AsyncClient, url: str, payload: dict,
                 deadline: float, stats: dict) -> None:
    """Fire requests back-to-back until the deadline; one in flight at a time."""
    while time.monotonic() < deadline:
        try:
            r = await client.post(url, json=payload)
            stats["ok" if r.status_code == 200 else "err"] += 1
        except Exception:
            stats["err"] += 1


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="http://localhost:8000")
    p.add_argument("-c", "--concurrency", type=int, default=20,
                   help="number of requests kept in flight (>5 triggers scale-up)")
    p.add_argument("-d", "--duration", type=int, default=60, help="seconds")
    p.add_argument("--prompt", default="Write a long detailed story about a robot.")
    p.add_argument("--max-new-tokens", type=int, default=128)
    args = p.parse_args()

    url = f"{args.host}/v1/generate"
    payload = {"prompt": args.prompt, "max_new_tokens": args.max_new_tokens}
    stats = {"ok": 0, "err": 0}

    print(f">> {args.concurrency} concurrent for {args.duration}s -> {url}")
    deadline = time.monotonic() + args.duration
    limits = httpx.Limits(max_connections=args.concurrency)
    timeout = httpx.Timeout(120.0)
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        await asyncio.gather(*[
            worker(client, url, payload, deadline, stats)
            for _ in range(args.concurrency)
        ])

    total = stats["ok"] + stats["err"]
    rps = total / args.duration if args.duration else 0
    print(f">> done: {stats['ok']} ok, {stats['err']} err, {total} total ({rps:.1f} req/s)")


if __name__ == "__main__":
    asyncio.run(main())
