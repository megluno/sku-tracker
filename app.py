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
        print(f"Response preview: {r.text[:300]}", flush=True)

        if not r.text.strip():
            print("Empty response body", flush=True)
            return None

        data = r.json()

        product = data.get("data", {}).get("product", {})
        fulfillment = product.get("fulfillment", {})
        store_options = fulfillment.get("store_options", [])
        shipping = fulfillment.get("shipping_options", {})

        print(f"store_options count: {len(store_options)}", flush=True)

        for store in store_options:
            if str(store.get("location_id")) == STORE:
                pickup = store.get("order_pickup", {})
                in_store = store.get("in_store_only", {})

                status = pickup.get("availability_status") or in_store.get("availability_status")
                print(f"Matched store {STORE}, status={status}", flush=True)
                return status

        shipping_status = shipping.get("availability_status")
        print(f"Shipping status fallback: {shipping_status}", flush=True)

        return shipping_status or "UNKNOWN"

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

        if last_status == "OUT_OF_STOCK" and status == "IN_STOCK":
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