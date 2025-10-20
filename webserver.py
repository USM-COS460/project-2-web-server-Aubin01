"""
Simple HTTP Web Server for COS 460/540

This script starts a small multi-threaded web server.
It can serve HTML pages, images, and other files from a given folder.
It supports GET and HEAD requests, handles basic errors,
and follows the HTTP/1.1 rules.

Author: Aubin Mugisha
Language: Python 3
"""

import os
import sys
import socket
import threading
import mimetypes
from urllib.parse import unquote
from datetime import datetime, timezone
from email.utils import format_datetime

MAX_REQUEST_BYTES = 64 * 1024  # cap request size for safety


def http_date_now() -> str:
    """Return the current date in standard HTTP format."""
    return format_datetime(datetime.now(timezone.utc), usegmt=True)


class SimpleHTTPServer:
    """A minimal multi-threaded HTTP/1.1 server."""

    def __init__(self, host: str, port: int, document_root: str):
        """Initialize server parameters."""
        self.host = host
        self.port = port
        self.document_root = os.path.abspath(os.path.normpath(document_root))
        self.server_socket = None

    def start(self):
        """Start the server and handle incoming connections."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(128)
        print(f"Serving HTTP on {self.host or '0.0.0.0'}:{self.port} from {self.document_root}")

        try:
            while True:
                client_socket, _ = self.server_socket.accept()
                t = threading.Thread(target=self.handle_client, args=(client_socket,))
                t.daemon = True
                t.start()
        except KeyboardInterrupt:
            print("\nShutting down server.")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def handle_client(self, client_socket: socket.socket):
        """Read and process a single client request."""
        try:
            request = self._recv_until_headers_end(client_socket)
            if not request:
                return

            first_line = request.split("\r\n", 1)[0]
            parts = first_line.split()
            if len(parts) != 3:
                self.send_error(client_socket, 400, "Bad Request")
                return

            method, path, version = parts
            if version not in ("HTTP/1.0", "HTTP/1.1"):
                self.send_error(client_socket, 400, "Bad Request")
                return

            if method not in ("GET", "HEAD"):
                self.send_error(client_socket, 405, "Method Not Allowed")
                return

            self.handle_get(client_socket, path, is_head=(method == "HEAD"))
        except Exception:
            self.send_error(client_socket, 500, "Internal Server Error")
        finally:
            client_socket.close()

    def _recv_until_headers_end(self, sock: socket.socket) -> str:
        """Read full HTTP headers up to a limit or until CRLFCRLF."""
        sock.settimeout(2.0)
        data = bytearray()
        try:
            while b"\r\n\r\n" not in data and len(data) < MAX_REQUEST_BYTES:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data.extend(chunk)
        except socket.timeout:
            pass
        return data.decode("utf-8", errors="replace")

    def handle_get(self, client_socket: socket.socket, raw_path: str, is_head: bool = False):
        """Serve a GET or HEAD request for a specific file path."""
        path = raw_path.split("?", 1)[0]
        path = unquote(path)
        if path.startswith("/"):
            path = path[1:]
        if path == "" or path.endswith("/"):
            path = os.path.join(path, "index.html")

        file_path = os.path.abspath(os.path.normpath(os.path.join(self.document_root, path)))

        # prevent directory traversal
        try:
            if os.path.commonpath([self.document_root, file_path]) != self.document_root:
                self.send_error(client_socket, 403, "Forbidden")
                return
        except ValueError:
            self.send_error(client_socket, 403, "Forbidden")
            return

        if not (os.path.exists(file_path) and os.path.isfile(file_path)):
            self.send_error(client_socket, 404, "Not Found")
            return

        try:
            with open(file_path, "rb") as f:
                body = f.read()
        except Exception:
            self.send_error(client_socket, 500, "Internal Server Error")
            return

        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = "application/octet-stream"

        if is_head:
            self.send_ok(client_socket, b"", content_type, content_length_override=len(body))
        else:
            self.send_ok(client_socket, body, content_type)

    # ---------- Response helpers ----------

    def _send_response(self, sock: socket.socket, code: int, text: str,
                       headers: list[tuple[str, str]], body: bytes, content_length_override: int | None = None):
        """Build and send a full HTTP response."""
        base = [
            ("Date", http_date_now()),
            ("Server", "SimpleHTTPServer/1.0"),
            ("Content-Length", str(content_length_override if content_length_override is not None else len(body))),
            ("Connection", "close"),
        ]
        all_headers = base + headers
        header_text = "".join(f"{k}: {v}\r\n" for k, v in all_headers) + "\r\n"
        response_line = f"HTTP/1.1 {code} {text}\r\n"

        sock.sendall(response_line.encode("utf-8"))
        sock.sendall(header_text.encode("utf-8"))
        if body:
            sock.sendall(body)

    def send_ok(self, sock: socket.socket, body: bytes, ctype: str, content_length_override: int | None = None):
        """Send a standard 200 OK response."""
        self._send_response(sock, 200, "OK", [("Content-Type", ctype)], body, content_length_override)

    def send_error(self, sock: socket.socket, code: int, text: str):
        """Send an error page with status code and message."""
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{code} {text}</title></head>
<body><h1>{code} {text}</h1><p>The requested resource could not be processed.</p></body></html>"""
        self._send_response(sock, code, text, [("Content-Type", "text/html; charset=utf-8")], html.encode("utf-8"))


def parse_args(argv):
    """Parse command-line arguments for port and document root."""
    host = "0.0.0.0"
    port = 8080
    root = "./www"

    if len(argv) >= 2:
        try:
            port = int(argv[1])
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            print("Invalid port. Use 1–65535.")
            sys.exit(2)
    if len(argv) >= 3:
        root = argv[2]

    return host, port, root


def main():
    """Entry point: start the HTTP server."""
    host, port, root = parse_args(sys.argv)
    server = SimpleHTTPServer(host, port, root)
    server.start()


if __name__ == "__main__":
    main()
