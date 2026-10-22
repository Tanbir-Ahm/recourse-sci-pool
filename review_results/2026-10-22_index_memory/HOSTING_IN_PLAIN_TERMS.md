# Where to host the pilot's search, in plain terms (2026-10-22)

**The index needs about 1.8 GB of memory in practice, not the 0.5 GB the earlier notes implied.** That is about four times the figure that was in `FOLLOW_UPS.md`, and it is what decides the price and the choice of host. Confidence tags: **[Certain]** = measured here or read from a file; **[Likely]** = strong inference or from a source I could only read second-hand; **[Guessing]** = filling a gap.

## What I measured (this machine, no network, no spend)

`python review_tools/experiments/measure_index_memory_2026-10-22.py --index-dir <index> --out review_results/2026-10-22_index_memory`; numbers in `numbers.json` there. The query embedding was a fake random vector and the re-ranker was never called, so nothing was spent and no real search was run.

| | Measured **[Certain]** for this machine (4 CPUs, Python 3.13, numpy 2.5) |
|---|---|
| Passages in the index | 236,155 |
| Vectors | 483.6 MB (half-precision numbers, 1,024 per passage) |
| Passage text on disk | 258 MB |
| Memory after loading text and vectors | 1,176 MB |
| Memory after building the keyword index (in memory) | 1,756 MB |
| Peak memory | 1,959 MB |
| Start-up (load, then keyword index) | about 16 s + 16 s |
| Local part of one search (meaning search, keyword search, merge) | about 1 s (median 0.95 s, worst 1.55 s of ten) |

Not measured: the re-rank call (a network call, so add its round trip), several users at once, another machine. Memory should carry over to another machine of the same kind; time will not.

Where the memory goes **[Likely]**: the 258 MB of text becomes about 700 MB once it is held as Python objects, and the keyword index adds about 580 MB. Both could be cut (keep the keyword index in a file on disk, keep the passage text on disk and read it only for the 60 candidates). I have **not** built that; **[Guessing]** it would bring the total to roughly 1 GB. It is only worth doing if memory, not your time, is the thing you are paying for.

## Railway or something else

**Railway is acceptable for the pilot, but only as its own service, not inside the live site's container.** My reasons:

1. **Price [Likely]:** Railway's own pricing page, as search results quoted it, lists memory at $10 per GB per month (billed per minute), CPU at $20 per vCPU per month, volume storage at $0.15 per GB per month, and the Hobby plan includes $5 of usage. So 1.8 to 2.0 GB running all the time is about **$18 to $20 a month for memory**, plus a little CPU. All in, **[Guessing]** about $15 to $25 a month after the $5 credit. Because billing is per minute, a service that is stopped between pilot days costs nothing while it is stopped.
2. **The live site already runs there [Certain, from `LIVE_SITE_PLAN.md`]:** no new account or tooling. But putting the pilot inside the live site's service would add about 2 GB to a site whose promise is that it cannot make things up, and would put lawyers' chat ids and marks beside the site's data. Use a separate service, preferably a separate project, so a crash or a memory spike in the pilot cannot take the site down.
3. **Private data:** the pilot store holds chat ids and lawyers' marks. It needs a persistent volume (`pilot_store/` on a Railway Volume) or it is lost at every deploy. **[Likely]** that Railway's container disk is not kept between deploys; check before relying on it.
4. **Telegram, if you choose it [Likely]:** the bot can ask Telegram for new messages (long polling) and needs no public web address, so the pilot service would have no open port. WhatsApp needs a public web address for its messages.

**The alternative is a small rented server (for example Hetzner, 4 GB).** Third-party price lists disagree and Hetzner changed prices on 1 April 2026, so treat this as **[Guessing]**: roughly €4 to €8 a month for 4 GB, three to five times cheaper than Railway. The catch is that you (or I, through you) do the administration: operating-system updates, a firewall, backups, restarting after a crash. For a pilot of four weeks the saving is about $10 to $15; I would not take on that work for it. If the pilot ran for more than about three months, I would move it.

**What I would not do:** host it on your own machine, or inside the live site's service.

## Before you spend anything on hosting

- Decide the sender first. Without a chat service there is nothing to host.
- Set a monthly usage limit on the Railway project **[Likely]** that Railway offers one; I could not confirm it from a first-party page.
- Stop the service when a pilot week ends if nobody is testing.

## Sources (third-party summaries; not first-party pages)

- Railway pricing: https://docs.railway.com/reference/pricing/plans (as summarised by a web search; I did not open the page)
- Hetzner prices: conflicting third-party lists, for example https://kimmo.suominen.com/stuff/cpc-2026-08.txt
- Telegram updates (long polling or a webhook): https://core.telegram.org/bots/webhooks
