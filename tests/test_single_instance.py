import os
import time
import unittest

import support


class SingleInstanceTests(unittest.TestCase):
    def test_second_launch_wakes_the_first(self):
        app = support.qt_app()
        from sigildesk.infra.single_instance import SingleInstance

        name = f"sigildesk-test-{os.getpid()}"
        first = SingleInstance(name)
        self.assertFalse(first.notify_running(timeout_ms=100))
        self.assertTrue(first.listen())
        woken = []
        first.activated.connect(lambda: woken.append(True))

        second = SingleInstance(name)
        self.assertTrue(second.notify_running())
        deadline = time.monotonic() + 3
        while not woken and time.monotonic() < deadline:
            app.processEvents()
        self.assertEqual(woken, [True])


if __name__ == "__main__":
    unittest.main()
