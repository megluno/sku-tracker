import os
import requests
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

SKU = "94300067"
STORE = "2219"

last_status = None

def check_stock():
    url = (
        "https://redsky.target.com/redsky_aggregations/v1/web/pdp_fulfillment_v1"
        "?key=ff457966e64d5e877fdbad070f276d18ecec4a01"
        f"&tcin={SKU}"
        f"&store_id={STORE}"
        f"&store_positions_store_id={STORE}"
        "&has_store_positions_store_id=true"
        f"&pricing_store_id={STORE}"
        "&has_pricing_store_id=true"
        "&is_bot=false"
    )

    try:
        r = requests.get(url, timeout=20)
        data = r.json()

        print("Raw response received", flush=True)

        product = data.get("data", {}).get("product", {})
        fulfillment = product.get("fulfillment", {})
        store_options = fulfillment.get("store_options", [])

        for store in store_options:
            if str(store.get("location_id")) == STORE:
                pickup = store.get("order_pickup", {})
                in_store = store.get("in_store_only", {})

                status = pickup.get("availability_status") or in_store.get("availability_status")
                return status

        return "UNKNOWN"

    except Exception as e:
        print(f"Error checking stock: {e}", flush=True)
        return None

def send_alert():
    print("🚨 ITEM BACK IN STOCK!", flush=True)

def tracker_loop():
    global last_status
    while True:
        status = check_stock()
        print(f"Current status: {status}", flush=True)

        if last_status == "OUT_OF_STOCK" and status == "IN_STOCK":
            send_alert()

        last_status = status
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

threading.Thread(target=tracker_loop, daemon=True).start()
run_server()