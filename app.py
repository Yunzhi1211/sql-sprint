#!/usr/bin/env python3
"""本地练习: 打开静态页（与 GitHub Pages 同一套）。python app.py"""
import os
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HOST, PORT = "127.0.0.1", 8765
ROOT = os.path.dirname(os.path.abspath(__file__))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()


def main():
    os.chdir(ROOT)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print("练习应用:", url, flush=True)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    httpd.serve_forever()


if __name__ == "__main__":
    main()
