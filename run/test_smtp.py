import socket, ssl, sys

HOST = "smtp.gmail.com"
PORTS = [465, 587]

for port in PORTS:
    try:
        print(f"Testing {HOST}:{port} ...")
        if port == 465:
            sock = socket.create_connection((HOST, port), timeout=10)
            ss = ssl.create_default_context().wrap_socket(sock, server_hostname=HOST)
            print("  -> connected with SSL (465)")
            ss.close()
        else:
            sock = socket.create_connection((HOST, port), timeout=10)
            print("  -> TCP connected (587) — STARTTLS reachable")
            sock.close()
    except Exception as e:
        print("  -> ERROR:", repr(e))
