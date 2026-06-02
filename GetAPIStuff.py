import requests

def getAPIStuff():

    url = "https://external-api.kalshi.com/trade-api/v2/events?limit=100&status=settled&with_nested_markets=true"
    response = requests.get(url)
    events = response.json()['events']

    has_result = [
    e for e in events
    if "markets" in e.keys() # Check if any markets
    if any(m['status'] == 'finalized' for m in e['markets']) #If there are markets make sure at least 1 has ended
    ]

    event = has_result[0]

    markets = event['markets']
    markets = [m for m in markets if float(m['volume_fp']) >= 1000]
    for m in markets:
        print_markets(m)

    return


def print_event(e):
    print("=" * 60)
    print(f"  {e['title']}")
    print(f"  {e['sub_title']}")
    print("=" * 60)
    print(f"  Series:    {e['series_ticker']}  |  Event: {e['event_ticker']}")
    print(f"  Category:  {e['category']}")
    print()

def print_markets(m):
    print(f"  -- {m['yes_sub_title']}")
    print(f"     Ticker:  {m['ticker']}")
    print(f"     Status:  {m['status'].upper()}  |  Result: {m['result'].upper() if m['result'] else 'PENDING'}")
    print(f"     Yes:     ask=${m['yes_ask_dollars']}  bid=${m['yes_bid_dollars']}")
    print(f"     No:      ask=${m['no_ask_dollars']}  bid=${m['no_bid_dollars']}")
    print(f"     Volume:  {m['volume_fp']}  |  Last: ${m['last_price_dollars']}")
    if m.get('rules_primary'):
        print(f"     Rules:   {m['rules_primary']}")
    print()


if __name__ == "__main__":
    getAPIStuff()