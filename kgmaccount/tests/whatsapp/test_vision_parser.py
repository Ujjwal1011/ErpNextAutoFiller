"""Tests for `vision_parser.process_order_image`.

Input:
- Uses a fake WhatsApp Message document with an image attachment.
- Uses a fake OpenRouter response containing two extracted orders.
- Uses fake Frappe document/database objects; no real OpenRouter call is made.

How it checks:
- Runs `process_order_image`.
- Confirms one WhatsApp image with two extracted orders creates two separate
  WhatsApp Order Staging docs.
- Confirms staging JSON is saved separately per order and the fake database is
  committed.
"""

import json
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from kgmaccount.tests.whatsapp.whatsapp_test_utils import FakeDb, FakeDoc, NoopLogger
from kgmaccount.utils import vision_parser


class TestVisionParser(unittest.TestCase):
    def test_process_order_image_creates_one_staging_doc_per_extracted_order(self):
        """One WhatsApp image with two extracted orders should create two staging docs."""
        created_docs = []
        fake_db = FakeDb()
        settings = FakeDoc(openrouter_api_key="secret", system_prompt="extract orders")
        message = FakeDoc(attachment="/private/files/order.jpg")

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image_file.write(b"fake-image")
            image_file.flush()
            file_doc = FakeDoc(get_full_path=lambda: image_file.name)

            def fake_get_doc(*args, **kwargs):
                if args[0] == "WhatsApp AI Settings":
                    return settings
                if args[0] == "WhatsApp Message":
                    return message
                if args[0] == "File":
                    return file_doc
                if isinstance(args[0], dict):
                    doc = FakeDoc(name=f"STG-{len(created_docs) + 1}", **args[0])
                    doc.insert = lambda ignore_permissions=False, doc=doc: created_docs.append(doc) or doc
                    return doc
                raise AssertionError(f"Unexpected get_doc call: {args}")

            fake_frappe = types.SimpleNamespace(
                get_doc=fake_get_doc,
                db=fake_db,
                logger=lambda *args, **kwargs: NoopLogger(),
                log_error=Mock(),
                get_traceback=lambda: "traceback",
            )
            fake_response = Mock()
            fake_response.status_code = 200
            fake_response.raise_for_status = Mock()
            fake_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "orders": [
                                        {"customer_name": "A", "items": [{"item_code": "KOTA 42x24"}]},
                                        {"customer_name": "B", "items": [{"item_code": "Kaddpa 42x24"}]},
                                    ]
                                }
                            )
                        }
                    }
                ]
            }

            with patch.object(vision_parser, "frappe", fake_frappe), patch.object(
                vision_parser.requests, "post", return_value=fake_response
            ):
                vision_parser.process_order_image("MSG-1")

        self.assertEqual(len(created_docs), 2)
        self.assertEqual(json.loads(created_docs[0].extracted_data_json)["customer_name"], "A")
        self.assertEqual(json.loads(created_docs[1].extracted_data_json)["customer_name"], "B")
        self.assertEqual(fake_db.commits, 1)


if __name__ == "__main__":
    unittest.main()
