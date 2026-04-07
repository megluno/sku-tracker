import os
import requests
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# Replace these with real Target values
SKU = "94300067"
STORE = "2219"

last_status = None

def check_stock():
    url = f"https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v2?tcin={SKU}&store_id={STORE}&key=eb7f29dbb2f34a3ca0f3d3b1d3dcbf2b"
    try:
        r = requests.get(url, timeout=20)
        data = r.json()
        stores = data["data"]["product"]["availability"]["stores"]
        for s in stores:
            if s["location_id"] == STORE:
                return s["availability_status"]
        return "UNKNOWN"
    except Exception as e:
        print("Error checking stock:", e, flush=True)
        return None

def send_alert():
    print("ITEM BACK IN STOCK!", flush=True)

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
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Server running on port {port}", flush=True)
    server.serve_forever()

thread = threading.Thread(target=tracker_loop, daemon=True)
thread.start()

run_server()