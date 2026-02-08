#!/usr/bin/env python3
"""
Simple HTTP server to serve the frontend.
Run: python3 serve.py
Access: http://localhost:3000
"""

import http.server
import socketserver
import os

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"✅ Frontend server running at http://localhost:{PORT}")
        print(f"📂 Serving files from: {DIRECTORY}")
        print(f"🔗 WebSocket API: ws://localhost:8000/ws/chat")
        print(f"\nPress Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped")
