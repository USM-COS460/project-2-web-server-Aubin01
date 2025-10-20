## COS 460/540 - Computer Networks
# Project 2: HTTP Server

# Aubin Mugisha

This project is written in Python 3 on macOS.

## How to compile

This project is written in Python, so no compilation is needed. Just ensure you have Python 3 installed on your system.

## How to run

To run the HTTP server:

```bash
python3 webserver.py [port] [document_root]
```

**Parameters:**
- `port` (optional): Port number to listen on (default: 8080)
- `document_root` (optional): Directory to serve files from (default: ./www)

**Examples:**
```bash
# Run with default settings (port 8080, serve from ./www)
python3 webserver.py

# Run on port 9000
python3 webserver.py 9000
```

Once running, open your web browser and go to `http://localhost:8080` (or whatever port you specified).

## My experience with this project

This project helped me understand how the HTTP protocol works at a low level.
I learned how to handle requests, build proper responses, and set correct headers such as Content-Type, Content-Length, and Connection.

The most challenging part was making sure the server handled all possible errors correctly (400, 403, 404, 405, 500) and stayed secure by preventing directory traversal.
Adding multi-threading also helped me see how real servers handle many clients at the same time.

Overall, it was a good exercise to learn how browsers and servers communicate “under the hood.”

