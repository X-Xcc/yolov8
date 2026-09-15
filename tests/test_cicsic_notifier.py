import base64
import sys
import threading
import unittest
from pathlib import Path


DETECTION_DIR = Path(__file__).resolve().parents[1] / "detection"
sys.path.insert(0, str(DETECTION_DIR))

from cicsic_notifier import CicsicReviewNotifier, build_review_payload


class CicsicNotifierTests(unittest.TestCase):
    def test_build_review_payload_only_accepts_gathering_and_embeds_frame(self):
        image_path = Path(__file__).resolve().parent / "_notifier_test_frame.jpg"
        image_path.write_bytes(b"jpeg-fixture")
        self.addCleanup(lambda: image_path.unlink(missing_ok=True))

        payload = build_review_payload(
            ["人员聚集"], 5, 12.5, 30, "2026-08-28 12:00:00", "USB摄像头", "cam0", str(image_path)
        )

        self.assertEqual(payload["eventKey"], "yolo:cam0:2026-08-28 12:00:00")
        self.assertEqual(payload["personCount"], 5)
        self.assertEqual(base64.b64decode(payload["imageBase64"]), b"jpeg-fixture")
        self.assertIsNone(build_review_payload(["跌倒"], 1, 1, 1, "now", None, None, None))

    def test_notifier_posts_in_background_and_deduplicates_inflight(self):
        image_path = Path(__file__).resolve().parent / "_notifier_test_frame.jpg"
        image_path.write_bytes(b"frame")
        self.addCleanup(lambda: image_path.unlink(missing_ok=True))
        received = []
        done = threading.Event()

        def fake_post(url, payload, headers, timeout):
            received.append((url, payload, headers, timeout))
            done.set()

        notifier = CicsicReviewNotifier(
            url="http://127.0.0.1:8010/api/security-ai/yolo-reviews",
            enabled=True,
            post_func=fake_post,
        )

        self.assertTrue(notifier.notify(["人员聚集"], 4, 8, 10, "2026-08-28T12:00:00", "cam", "0", str(image_path)))
        self.assertFalse(notifier.notify(["人员聚集"], 4, 8, 10, "2026-08-28T12:00:01", "cam", "0", str(image_path)))
        self.assertTrue(done.wait(2))
        self.assertTrue(received[0][0].endswith("/api/security-ai/yolo-reviews"))
        self.assertEqual(received[0][1]["actions"], ["人员聚集"])
