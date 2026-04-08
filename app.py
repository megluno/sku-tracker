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

        data = r.json()

        product = data.get("data", {}).get("product", {})

        # 🔥 NEW: check fulfillment summary
        fulfillment = product.get("fulfillment", {})

        print(f"Fulfillment keys: {list(fulfillment.keys())}", flush=True)

        # Try pickup first
        pickup = fulfillment.get("pickup", {})
        shipping = fulfillment.get("shipping", {})

        pickup_status = pickup.get("availability_status")
        shipping_status = shipping.get("availability_status")

        print(f"Pickup status: {pickup_status}", flush=True)
        print(f"Shipping status: {shipping_status}", flush=True)

        # Prefer pickup if exists
        if pickup_status:
            return pickup_status

        if shipping_status:
            return shipping_status

        return "UNKNOWN"

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