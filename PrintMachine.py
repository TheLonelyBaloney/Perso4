from pprint import pprint



def print_event(event: dict):
    # ── Core Identity ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  {event.get('title', 'N/A')}  [{event.get('ticker', '?')}]")
    print(f"  ID: {event.get('id')}  |  Slug: {event.get('slug')}")
    print(f"{'='*60}")

    # ── Description ───────────────────────────────────────────
    desc = event.get('description', '')
    if desc:
        print(f"\n{desc[:200]}{'...' if len(desc) > 200 else ''}")

    # ── Status Flags ──────────────────────────────────────────
    flag_keys = ['active', 'closed', 'archived', 'new', 'featured',
                 'restricted', 'cyom', 'negRiskAugmented']
    active_flags = [key for key in flag_keys if event.get(key)]
    print(f"\n  Status : {' | '.join(active_flags) or 'none'}")

    # ── Dates ─────────────────────────────────────────────────
    print(f"\n  Dates")
    print(f"  {'-'*30}")
    for label, key in [('Start',   'startDate'),   ('End',     'endDate'),
                       ('Created', 'creationDate'), ('Closed',  'closedTime')]:
        val = event.get(key)
        if val:
            print(f"  {label:<8}: {val}")

    # ── Volume & Liquidity ────────────────────────────────────
    print(f"\n  Volume & Liquidity")
    print(f"  {'-'*30}")
    for label, key in [('Volume',    'volume'),       ('Vol 24h',   'volume24hr'),
                       ('Vol 1wk',   'volume1wk'),    ('Vol 1mo',   'volume1mo'),
                       ('Vol 1yr',   'volume1yr'),    ('Liquidity', 'liquidity'),
                       ('Liq AMM',   'liquidityAmm'), ('Liq CLOB',  'liquidityClob'),
                       ('Open Int',  'openInterest')]:
        val = event.get(key)
        if val is not None:
            print(f"  {label:<10}: ${float(val):>14,.2f}")

    # ── Category & Tags ───────────────────────────────────────
    print(f"\n  Category : {event.get('category', 'N/A')}")
    tags = event.get('tags', [])
    if tags:
        tag_labels = [t.get('label', str(t)) if isinstance(t, dict) else str(t) for t in tags]
        print(f"  Tags     : {', '.join(tag_labels)}")
    series = event.get('series') or event.get('seriesSlug')
    if series:
        print(f"  Series   : {series}")

    # ── Markets ───────────────────────────────────────────────
    markets = event.get('markets', [])
    if markets:
        print(f"\n  Markets ({len(markets)})")
        print(f"  {'-'*30}")
        for m in markets[:5]:
            question = m.get('question', m.get('title', 'N/A'))
            prices   = m.get('outcomePrices') or m.get('outcomes', '')
            print(f"  + {question[:70]}")
            if prices:
                print(f"    Prices: {prices}")
        if len(markets) > 5:
            print(f"  ... and {len(markets) - 5} more")

    # ── Misc ──────────────────────────────────────────────────
    print(f"\n  Comments : {event.get('commentCount', 0)}")
    print(f"  Sort By  : {event.get('sortBy', 'N/A')}")
    meta = event.get('eventMetadata')
    if meta:
        print(f"\n  Metadata :")
        pprint(meta, indent=4)

    print(f"\n{'─'*60}\n")

def print_market(m: dict):
    # parse outcomes/prices
    outcomes = m.get('outcomes', '[]')
    prices   = m.get('outcomePrices', '[]')
    if isinstance(outcomes, str):
        import json
        outcomes = json.loads(outcomes)
        prices   = json.loads(prices)

    print(f"\n  {'─'*56}")
    print(f"  {m.get('question', 'N/A')}")
    print(f"  Condition_id: {m.get('conditionId')}")
    print(f"  {'─'*56}")

    # Outcomes
    for outcome, price in zip(outcomes, prices):
        bar_len = int(float(price) * 20)
        bar     = '#' * bar_len + '.' * (20 - bar_len)
        print(f"  {outcome:<12} [{bar}] {float(price)*100:>5.1f}%")

    # Volume & liquidity
    print(f"  Volume  : ${float(m.get('volume', 0)):>12,.2f}  ")
    print(f"  Liq     : ${float(m.get('liquidity', 0)):>12,.2f}")

    # Status flags
    flag_keys = ['active', 'closed', 'archived', 'new', 'featured',
                 'restricted', 'approved', 'funded', 'fpmmLive']
    flags = [k for k in flag_keys if m.get(k)]
    print(f"  Flags   : {' | '.join(flags) or 'none'}")
    print(f"  {'─'*56}\n")

def print_trade(t :dict):
    print(f"  {'─'*56}")

    print("  "+t['name'])

    # Size
    print(f"  Size     : ${t['size']}")
    # Price 
    print(f"  Price    :  {t['price']}")
    # Timestamp
    print(f"  Timestamp:  {t['timestamp']}")

    print(f"  {'─'*50}\n")



if __name__ == "__main__":
    print("Wrong place brochacho")