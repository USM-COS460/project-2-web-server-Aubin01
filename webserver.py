
"""
Simple HTTP Web Server (COS 460/540)

Serves static files from a folder.
Supports GET and HEAD, basic errors, and HTTP/1.1.

Author: Aubin Mugisha
"""

import os, sys, socket, threading, mimetypes
from urllib.parse import unquote
from datetime import datetime, timezone
from email.utils import format_datetime

HOST = "0.0.0.0"
PORT = 8080
DOC_ROOT = "./www"
MAX_REQ = 64 * 1024  # cap request size

def http_date():
    return format_datetime(datetime.now(timezone.utc), usegmt=True)

def start_server(host, port, root):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(128)
    print(f"Serving HTTP on {host}:{port} from {os.path.abspath(root)}")
    try:
        while True:
            c, _ = s.accept()
            t = threading.Thread(target=handle_client, args=(c, root), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\nShutting down server.")
    finally:
        s.close()

def handle_client(c, root):
    try:
        req = recv_headers(c)
        if not req:
            return
        line = req.split("\r\n", 1)[0]
        parts = line.split()
        if len(parts) != 3:
            return send_error(c, 400, "Bad Request")
        method, path, version = parts
        if version not in ("HTTP/1.0", "HTTP/1.1"):
            return send_error(c, 400, "Bad Request")
        if method not in ("GET", "HEAD"):
            return send_error(c, 405, "Method Not Allowed")
        serve_file(c, root, path, is_head=(method == "HEAD"))
    except Exception:
        send_error(c, 500, "Internal Server Error")
    finally:
        try: c.close()
        except: pass

def recv_headers(sock):
    sock.settimeout(2.0)
    data = bytearray()
    try:
        while b"\r\n\r\n" not in data and len(data) < MAX_REQ:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data.extend(chunk)
    except socket.timeout:
        pass
    return data.decode("utf-8", errors="replace")

def serve_file(c, root, raw_path, is_head=False):
    # strip query, decode, normalize
    path = raw_path.split("?", 1)[0]
    path = unquote(path)
    if path.startswith("/"):
        path = path[1:]
    if path == "" or path.endswith("/"):
        path = os.path.join(path, "index.html")

    root_abs = os.path.abspath(os.path.normpath(root))
    file_abs = os.path.abspath(os.path.normpath(os.path.join(root_abs, path)))

    # no escapes outside root
    try:
        if os.path.commonpath([root_abs, file_abs]) != root_abs:
            return send_error(c, 403, "Forbidden")
    except ValueError:
        return send_error(c, 403, "Forbidden")

    if not (os.path.exists(file_abs) and os.path.isfile(file_abs)):
        return send_error(c, 404, "Not Found")

    try:
        with open(file_abs, "rb") as f:
            body = f.read()
    except Exception:
        return send_error(c, 500, "Internal Server Error")

    ctype, _ = mimetypes.guess_type(file_abs)
    if not ctype:
        ctype = "application/octet-stream"

    if is_head:
        send_response(c, 200, "OK", [("Content-Type", ctype)], b"", content_length=len(body))
    else:
        send_response(c, 200, "OK", [("Content-Type", ctype)], body)

def send_response(c, code, text, headers, body, content_length=None):
    base = [
        ("Date", http_date()),
        ("Server", "StudentHTTP/1.0"),
        ("Content-Length", str(content_length if content_length is not None else len(body))),
        ("Connection", "close"),
    ]
    head = "".join(f"{k}: {v}\r\n" for k, v in base + headers)
    status = f"HTTP/1.1 {code} {text}\r\n"
    try:
        c.sendall(status.encode("utf-8"))
        c.sendall((head + "\r\n").encode("utf-8"))
        if body:
            c.sendall(body)
    except Exception:
        pass

def send_error(c, code, text):
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{code} {text}</title></head>
<body><h1>{code} {text}</h1><p>The requested resource could not be processed.</p></body></html>"""
    send_response(c, code, text, [("Content-Type", "text/html; charset=utf-8")], html.encode("utf-8"))

def parse_args(argv):
    host, port, root = HOST, PORT, DOC_ROOT
    if len(argv) >= 2:
        try:
            port = int(argv[1])
            if not (1 <= port <= 65535): raise ValueError
        except ValueError:
            print("Invalid port. Use 1–65535."); sys.exit(2)
    if len(argv) >= 3:
        root = argv[2]
    return host, port, root

if __name__ == "__main__":
    h, p, r = parse_args(sys.argv)
    start_server(h, p, r)
