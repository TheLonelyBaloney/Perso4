from pprint import pprint


#asked claude to make me a printer cuz aint no way im doing all that "front" end stuff


def print_event(event: dict):
    # ── Core Identity ──────────────────────────────────────────
    print(f"{'='*60}")
    print(f"  {event.get('title', 'N/A')}  [{event.get('ticker', '?')}]")
    print(f"  ID: {event.get('id')}  |  Slug: {event.get('slug')}")
    print(f"{'='*60}")
    # ── Dates ─────────────────────────────────────────────────
    for label, key in [('Start',   'startDate'),   ('End',     'endDate')]:
        val = event.get(key)
        if val:
            print(f"  {label:<8}: {val}")

    # ── Volume & Liquidity ────────────────────────────────────
    for label, key in [('Volume',    'volume')]:
        val = event.get(key)
        if val is not None:
            print(f"  {label:<10}: ${float(val):>14,.2f}")

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

# This one is mine tho
def print_trade(t :dict):
    print(f"  {'─'*50}")

    print("  "+t['name'])
    print("  "+t['proxyWallet'])
    # Size
    print(f"  Size     :  ${t['size']}")
    # Price 
    print(f"  Price    :  {t['price']}")
    # Timestamp
    print(f"  Timestamp:  {t['timestamp']}")
    #outcome
    print(f"  Outcome  :  {t['outcome']}")
    #outcome Index
    print(f"  Win?     :  {t['outcomeIndex']}")


    print(f"  {'─'*50}")



if __name__ == "__main__":
    print("Wrong place brochacho")