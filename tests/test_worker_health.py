from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
from time import sleep

from backend.worker.health import HealthHandler


def test_worker_health_endpoint():
    server = ThreadingHTTPServer(("127.0.0.1", 0), HealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for _ in range(50):
            try:
                connection = HTTPConnection("127.0.0.1", server.server_port, timeout=1)
                connection.request("GET", "/health")
                response = connection.getresponse()
                body = response.read()
                connection.close()
                break
            except OSError:
                sleep(0.01)
        else:
            raise AssertionError("Worker health server did not start")
        assert response.status == 200
        assert body == b'{"status": "ok", "mode": "placeholder"}'
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
