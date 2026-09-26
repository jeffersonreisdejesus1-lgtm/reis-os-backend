import threading
import time
import unittest
from urllib.request import urlopen, Request
from urllib.parse import urlencode

import app


class AppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.HTTPServer(("127.0.0.1", 8765), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start(); time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()

    def test_health(self):
        self.assertEqual(urlopen("http://127.0.0.1:8765/health").read(), b"OK")

    def test_add_task(self):
        data = urlencode({"task": "prove loop"}).encode()
        req = Request("http://127.0.0.1:8765/", data=data, method="POST")
        with urlopen(req) as response:
            body = response.read().decode()
        self.assertIn("prove loop", body)


if __name__ == "__main__":
    unittest.main()
