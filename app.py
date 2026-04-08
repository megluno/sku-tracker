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

POSITIVE_VALUES = {
    "IN_STOCK",
    "IN STOCK",
    "LIMITED_STOCK",
    "LIMITED STOCK",
    "PREORDER",
    "PRE_ORDER",
    "PRE-ORDER",
    "AVAILABLE TO SHIP",
    "SHIP IT",
    "SAME DAY DELIVERY",
    "ORDER PICKUP",
    "PICKUP TODAY",
}

NEGATIVE_VALUES = {
    "OUT_OF_STOCK",
    "OUT OF STOCK",
    "UNAVAILABLE",
    "SOLD_OUT",
    "SOLD OUT",
    "NOT SOLD IN STORES",
    "NOT AVAILABLE",
    "TEMPORARILY OUT OF STOCK",
}

INTERESTING_PATH_WORDS = {
    "availability",
    "stock",
    "inventory",
    "fulfillment",
    "pickup",
    "delivery",
    "shipping",
    "order_pickup",
    "in_store_only",
    "buybox",
    "purchasable",
    "is_out_of_stock",
    "is_in_stock",
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

def extract_stock_signals(product):
    signals = []

    for path, value in walk_json(product):
        if value is None:
            continue

        path_lower = path.lower()
        value_str = str(value).strip()
        value_upper = value_str.upper()

        if not any(word in path_lower for word in INTERESTING_PATH_WORDS):
            continue

        signals.append((path, value_upper))

    return signals

def decide_status_from_signals(signals):
    for path, value in signals:
        if value in POSITIVE_VALUES:
            return "IN_STOCK", f"{path}={value}"

        if value in NEGATIVE_VALUES:
            return "OUT_OF_STOCK", f"{path}={value}"

        if value in {"TRUE", "FALSE"}:
            path_lower = path.lower()
            if "is_out_of_stock" in path_lower:
                return ("OUT_OF_STOCK", f"{path}={value}") if value == "TRUE" else ("IN_STOCK", f"{path}={value}")
            if "is_in_stock" in path_lower or "available_to_promise" in path_lower or "purchasable" in path_lower:
                return ("IN_STOCK", f"{path}={value}") if value == "TRUE" else ("OUT_OF_STOCK", f"{path}={value}")

    return "UNKNOWN", "no explicit stock signal found"

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
        print(f"Found {len(signals)} strict stock-related signals", flush=True)

        for path, value in signals[:30]:
            print(f"SIGNAL: {path} = {value}", flush=True)

        status, reason = decide_status_from_signals(signals)
        print(f"Derived status: {status} ({reason})", flush=True)
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