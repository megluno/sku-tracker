import os
import re
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

NEGATIVE_TERMS = [
    "out of stock",
    "sold out",
    "temporarily out of stock",
    "not available",
    "unavailable",
]

POSITIVE_TERMS = [
    "in stock",
    "limited stock",
    "available to ship",
    "ship it",
    "same day delivery",
    "pickup today",
]

def walk_json(obj, path="root"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_json(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_json(v, f"{path}[{i}]")
    else:
        yield path, obj

def normalize_text(text):
    return re.sub(r"\s+", " ", str(text).strip().lower())

def check_api():
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
        print(f"API HTTP status: {r.status_code}", flush=True)
        print(f"API Content-Type: {r.headers.get('Content-Type')}", flush=True)

        if r.status_code != 200 or not r.text.strip():
            return "UNKNOWN", "api empty or non-200"

        data = r.json()
        product = data.get("data", {}).get("product", {})

        candidate_lines = []

        for path, value in walk_json(product):
            if value is None:
                continue
            if not isinstance(value, (str, int, float, bool)):
                continue

            text = normalize_text(value)
            path_lower = path.lower()

            if any(word in path_lower for word in [
                "availability", "stock", "inventory", "fulfillment",
                "shipping", "delivery", "pickup", "cart", "buy", "purchasable"
            ]) or any(term in text for term in NEGATIVE_TERMS + POSITIVE_TERMS):
                candidate_lines.append((path, text))

        print(f"API candidate lines: {len(candidate_lines)}", flush=True)
        for path, text in candidate_lines[:25]:
            print(f"API SIGNAL: {path} = {text}", flush=True)

        joined = " | ".join(text for _, text in candidate_lines)

        for term in NEGATIVE_TERMS:
            if term in joined:
                return "OUT_OF_STOCK", f"api matched '{term}'"

        for term in POSITIVE_TERMS:
            if term in joined:
                return "IN_STOCK", f"api matched '{term}'"

        return "UNKNOWN", "api no explicit stock phrase"

    except Exception as e:
        print(f"API error: {e}", flush=True)
        return "UNKNOWN", f"api exception: {e}"

def check_html():
    url = f"https://www.target.com/p/-/A-{SKU}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"HTML HTTP status: {r.status_code}", flush=True)
        print(f"HTML Content-Type: {r.headers.get('Content-Type')}", flush=True)

        if r.status_code != 200 or not r.text.strip():
            return "UNKNOWN", "html empty or non-200"

        page = normalize_text(r.text)
        print(f"HTML preview: {page[:300]}", flush=True)

        # Negative terms get first priority
        for term in NEGATIVE_TERMS:
            if term in page:
                return "OUT_OF_STOCK", f"html matched '{term}'"

        # Only accept positive signals if they appear near purchase context
        positive_patterns = [
            r"(add to cart.{0,80}ship)",
            r"(ship it.{0,80}add to cart)",
            r"(available to ship.{0,80}add to cart)",
            r"(in stock.{0,80}add to cart)",
            r"(same day delivery.{0,80}add to cart)",
        ]

        for pattern in positive_patterns:
            if re.search(pattern, page):
                return "IN_STOCK", f"html matched purchase pattern '{pattern}'"

        return "UNKNOWN", "html no trusted stock phrase"

    except Exception as e:
        print(f"HTML error: {e}", flush=True)
        return "UNKNOWN", f"html exception: {e}"

def check_stock():
    print("check_stock started", flush=True)

    api_status, api_reason = check_api()
    print(f"API status result: {api_status} ({api_reason})", flush=True)

    if api_status != "UNKNOWN":
        return api_status

    html_status, html_reason = check_html()
    print(f"HTML status result: {html_status} ({html_reason})", flush=True)

    return html_status

def send_alert():
    print("🚨 ITEM BACK IN STOCK ONLINE!", flush=True)

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