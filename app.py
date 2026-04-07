import requests
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# Replace these with real values
UPC = "196214111387"
STORE = "Target Parker"

last_status = None

def check_stock():
    url = f"https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v2?tcin={SKU}&store_id={STORE}&key=eb7f29dbb2f34a3ca0f3d3b1d3dcbf2b"
    try:
        r = requests.get(url)
        data = r.json()
        stores = data["data"]["product"]["availability"]["stores"]
        for s in stores:
            if s["location_id"] == STORE:
                return s["availability_status"]
    except Exception as e:
        print("Error:", e)
        return None

def send_alert():
    print("🚨 ITEM BACK IN STOCK!")

def tracker_loop():
    global last_status
    while True:
        status = check_stock()
        print("Current status:", status)

        if last_status == "OUT_OF_STOCK" and status == "IN_STOCK":
            send_alert()

        last_status = status
        time.sleep(300)

# Simple web server (keeps Render alive)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Tracker is running")

def run_server():
    port = 10000  # Render uses this port
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

# Run both at the same time
threading.Thread(target=tracker_loop).start()
run_server()