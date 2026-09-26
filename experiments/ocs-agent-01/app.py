from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

TASKS = []


def render():
    items = "".join(f"<li>{task}</li>" for task in TASKS) or "<li>No tasks yet</li>"
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>OCS-Agent-01</title></head>
<body><main><h1>OCS-Agent-01 Task App</h1><p>Runtime experiment artifact.</p>
<form method="post"><input name="task" required placeholder="New task"><button>Add</button></form>
<ul>{items}</ul></main></body></html>'''.encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK"); return
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(render())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = parse_qs(self.rfile.read(length).decode())
        task = data.get("task", [""])[0].strip()
        if task:
            TASKS.append(task)
        self.send_response(303); self.send_header("Location", "/"); self.end_headers()

    def log_message(self, format, *args):
        pass


def run(port=8000):
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    run()
