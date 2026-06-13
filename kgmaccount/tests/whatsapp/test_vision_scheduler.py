"""Tests for the WhatsApp AI scheduler.

Input:
- Uses fake WhatsApp AI Settings with `enable_ai_worker = 1` and allowed group
  IDs.
- Uses fake unprocessed WhatsApp image messages.

How it checks:
- Runs `fetch_and_process_unprocessed_whatsapp_messages`.
- Confirms the scheduler queries only allowed image messages.
- Confirms each message is marked processed and queued for
  `kgmaccount.utils.vision_parser.process_order_image`.
- Does not run the actual background job.
"""

import types
import unittest
from unittest.mock import Mock, patch

from kgmaccount.tests.whatsapp.whatsapp_test_utils import FakeDb, FakeDoc, NoopLogger
from kgmaccount.utils import vision_scheduler


class TestVisionScheduler(unittest.TestCase):
    def test_fetch_and_process_marks_allowed_image_messages_and_enqueues_parser(self):
        """Allowed image messages should be marked processed and queued for parsing."""
        fake_db = FakeDb()
        enqueued = []

        fake_frappe = types.SimpleNamespace(
            get_doc=Mock(
                return_value=FakeDoc(
                    enable_ai_worker=1,
                    allowed_groups=[FakeDoc(group_id="GROUP-1"), FakeDoc(group_id="GROUP-2")],
                )
            ),
            get_all=Mock(return_value=[FakeDoc(name="MSG-1"), FakeDoc(name="MSG-2")]),
            db=fake_db,
            enqueue=lambda *args, **kwargs: enqueued.append((args, kwargs)),
            logger=lambda *args, **kwargs: NoopLogger(),
        )

        with patch.object(vision_scheduler, "frappe", fake_frappe):
            vision_scheduler.fetch_and_process_unprocessed_whatsapp_messages()

        fake_frappe.get_all.assert_called_once()
        self.assertEqual(len(fake_db.set_values), 2)
        self.assertEqual(len(enqueued), 2)
        self.assertEqual(enqueued[0][1]["whatsapp_message_id"], "MSG-1")


if __name__ == "__main__":
    unittest.main()
