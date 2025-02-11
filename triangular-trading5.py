import ccxt
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

counter = 0

# Define a whitelist of popular exchanges (optional)
whitelist = [
    "binance",
    "coinbase",
    "kucoin",
    "huobi",
    "okx",
    "kraken",
    "bitfinex",
    "bybit",
    "mexc",
    "poloniex",
    "bitget",
    "deribit",
    "bingx",
    "coinex",
    "gateio",
    "bitstamp",
    "gemini",
    "phemex",
    "hitbtc",
]

# Define the whitelist of cryptocurrencies
WHITELIST = {
    "BTC", "ETH", "USDT", "BNB", "SOL", "ADA", "DOGE", "XRP", "LTC", "DOT",
    "SHIB", "AVAX", "MATIC", "ATOM", "UNI", "LINK", "NEAR", "XMR", "BCH", "TRX",
    "ALGO", "AAVE", "FTM", "ICP", "FIL", "VET", "EOS", "SAND", "MANA", "XTZ", "THETA",
    "EGLD", "GRT", "CAKE", "AXS", "STX", "CRV", "KLAY", "GALA", "LDO", "QNT", "RUNE",
    "CHZ", "ENJ", "FLOW", "DYDX", "1INCH", "KAVA", "GMT", "SNX", "HNT", "IMX", "ZEC",
    "MINA", "COMP", "ANKR", "RSR", "FTT", "HOT", "RVN", "HBAR", "ZIL", "NEXO", "CELR",
    "WAVES", "BAT", "TWT", "DASH", "LRC", "ROSE", "CELO", "ENS", "IOST",
    "AR", "MASK", "XEC", "CSPR", "OMG", "TFUEL", "GNO", "REEF", "KSM", "GLMR",
    "CTSI", "ZEN", "OCEAN", "SC", "COTI", "IOTA", "WOO", "KEEP", "PERP", "JASMY",
    "SXP", "FLUX", "SPELL", "UMA", "YFI", "BAL"
}

# Initialize exchanges
exchanges = {name: getattr(ccxt, name)() for name in whitelist}
for exchange in exchanges.values():
    exchange.load_markets()

def get_trading_pairs():
    """Fetch available trading pairs and filter by whitelist."""
    print("Fetching trading pairs from exchanges...")
    pairs = set()
    for exchange in exchanges.values():
        pairs.update(exchange.symbols)
    print(f"Total trading pairs fetched: {len(pairs)}")

    # Filter pairs by whitelist
    filtered_pairs = [
        pair for pair in pairs
        if all(symbol in WHITELIST for symbol in pair.replace("/", " ").split())
    ]
    print(f"Filtered trading pairs by whitelist: {len(filtered_pairs)}")
    return filtered_pairs

def find_triangular_pairs(pairs):
    """Find all valid triangular trading combinations."""
    print("Identifying potential triangular pairs...")
    pair_dict = {}
    triangles = []

    for pair in pairs:
        if '/' not in pair:
            continue
        base, quote = pair.split('/')
        if base in WHITELIST and quote in WHITELIST:
            if base not in pair_dict:
                pair_dict[base] = set()
            if quote not in pair_dict:
                pair_dict[quote] = set()
            pair_dict[base].add(quote)
            pair_dict[quote].add(base)

    for base in pair_dict:
        for quote1 in pair_dict[base]:
            for quote2 in pair_dict[quote1]:
                if base in pair_dict[quote2]:
                    triangle = (f"{base}/{quote1}", f"{quote1}/{quote2}", f"{quote2}/{base}")
                    if triangle not in triangles:
                        triangles.append(triangle)

    print(f"Total triangles found: {len(triangles)}")
    return triangles

def fetch_price(pair):
    global counter
    """Fetch price for a given pair, including reverse if necessary."""
    for exchange in exchanges.values():
        try:
            order_book = exchange.fetch_order_book(pair)
            best_ask = order_book['asks'][0][0] if order_book['asks'] else None
            best_bid = order_book['bids'][0][0] if order_book['bids'] else None
            counter += 1
            print(f"Getting price for {counter}: {pair} on {exchange.id}...           \r", end="")
            return best_ask, best_bid, exchange.id
        except ccxt.BaseError:
            base, quote = pair.split('/')
            reverse_pair = f"{quote}/{base}"
            try:
                order_book = exchange.fetch_order_book(reverse_pair)
                best_ask = order_book['asks'][0][0] if order_book['asks'] else None
                best_bid = order_book['bids'][0][0] if order_book['bids'] else None
                return 1 / best_bid if best_bid else None, 1 / best_ask if best_ask else None, exchange.id
            except ccxt.BaseError:
                continue
    return None, None, None

def calculate_profitability(triangle):
    """Calculate profitability for a given triangular arbitrage opportunity."""
    try:
        rate1_ask, rate1_bid, exchange1 = fetch_price(triangle[0])
        rate2_ask, rate2_bid, exchange2 = fetch_price(triangle[1])
        rate3_ask, rate3_bid, exchange3 = fetch_price(triangle[2])

        if not all([rate1_ask, rate1_bid, rate2_ask, rate2_bid, rate3_ask, rate3_bid]):
            return triangle, -math.inf

        starting_amount = 1.0
        usdt_received = starting_amount * rate1_bid if rate1_bid else starting_amount / rate1_ask
        eth_received = usdt_received * rate2_bid if rate2_bid else usdt_received * rate2_ask
        btc_received = eth_received * rate3_bid if rate3_bid else eth_received / rate3_ask

        profit_percentage = (btc_received - starting_amount) / starting_amount * 100
        return (triangle, exchange1, exchange2, exchange3), profit_percentage
    except Exception as e:
        return triangle, -math.inf

def main():
    print("Starting triangular arbitrage analysis...")
    pairs = get_trading_pairs()
    triangular_pairs = find_triangular_pairs(pairs)

    print("Calculating profitability for each triangle...")
    results = []

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_triangle = {
            executor.submit(calculate_profitability, triangle): triangle
            for triangle in triangular_pairs
        }

        for future in as_completed(future_to_triangle):
            triangle, profit = future.result()
            if profit > 0:
                results.append((triangle, profit))

    # Sort and display results
    results = sorted(results, key=lambda x: x[1], reverse=True)
    print("Top 5 profitable triangular arbitrage opportunities:")
    for i, (triangle, profit) in enumerate(results[:5]):
        print(f"{i+1}. Triangle: {triangle}, Profit: {profit:.2f}%")

if __name__ == "__main__":
    main()
