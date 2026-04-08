import os
import requests
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

SKU = "94300067"
STORE = "2219"

last_status = None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": f"https://www.target.com/p/-/A-{SKU}",
    "Origin": "https://www.target.com",
}

def walk_json(obj, path="root"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_json(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_json(v, f"{path}[{i}]")
    else:
        yield path, obj

def extract_stock_signals(data):
    signals = []
    for path, value in walk_json(data):
        if not isinstance(value, (str, int, float, bool)) or value is None:
            continue

        path_lower = path.lower()
        value_str = str(value)

        interesting = (
            "availability" in path_lower
            or "fulfillment" in path_lower
            or "pickup" in path_lower
            or "shipping" in path_lower
            or "store" in path_lower
            or "inventory" in path_lower
            or "buy" in path_lower
            or "stock" in path_lower
            or "quantity" in path_lower
        )

        if interesting:
            signals.append((path, value_str))
    return signals

def decide_status_from_signals(signals):
    joined = " | ".join(f"{p}={v}" for p, v in signals).upper()

    positive_terms = [
        "IN_STOCK",
        "IN STOCK",
        "LIMITED_STOCK",
        "LIMITED STOCK",
        "PREORDER",
        "PRE_ORDER",
        "AVAILABLE",
        "ADD_TO_CART",
        "ADD TO CART",
        "BUY",
        "PURCHASABLE",
    ]

    negative_terms = [
        "OUT_OF_STOCK",
        "OUT OF STOCK",
        "UNAVAILABLE",
        "NOT_SOLD_IN_STORES",
        "NOT AVAILABLE",
        "SOLD_OUT",
        "SOLD OUT",
    ]

    for term in positive_terms:
        if term in joined:
            return "IN_STOCK"

    for term in negative_terms:
        if term in joined:
            return "OUT_OF_STOCK"

    return "UNKNOWN"

def check_stock():
    print("check_stock started", flush=True)

    url = (
        "https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1"
        "?key=9f36aeafbe60771e321a7cc95a78140772ab3e96"
        f"&tcin={SKU}"
        f"&store_id={STORE}"
        f"&pricing_store_id={STORE}"
        "&has_pricing_store_id=true"
        "&is_bot=false"
    )

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"HTTP status: {r.status_code}", flush=True)
        print(f"Content-Type: {r.headers.get('Content-Type')}", flush=True)

        if not r.text.strip():
            print("Empty response body", flush=True)
            return None

        data = r.json()

        product = data.get("data", {}).get("product", {})
        print(f"Top-level product keys: {list(product.keys())[:20]}", flush=True)

        signals = extract_stock_signals(product)
        print(f"Found {len(signals)} stock-related signals", flush=True)

        for path, value in signals[:25]:
            print(f"SIGNAL: {path} = {value}", flush=True)

        status = decide_status_from_signals(signals)
        print(f"Derived status: {status}", flush=True)
        return status

    except Exception as e:
        print(f"Error checking stock: {e}", flush=True)
        return None

def send_alert():
    print("🚨 ITEM BACK IN STOCK!", flush=True)

def tracker_loop():
    global last_status
    print("tracker_loop started", flush=True)

    while True:
        status = check_stock()
        print(f"Current status: {status}", flush=True)

        if last_status in [None, "OUT_OF_STOCK", "UNKNOWN"] and status == "IN_STOCK":
            send_alert()

        last_status = status
        print("Sleeping for 300 seconds", flush=True)
        time.sleep(300)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Tracker is running")

    def log_message(self, format, *args):
        return

def run_server():
    port = int(os.environ.get("PORT", "10000"))
    print(f"Starting server on port {port}", flush=True)
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

print("Launching tracker thread", flush=True)
threading.Thread(target=tracker_loop, daemon=True).start()
run_server()