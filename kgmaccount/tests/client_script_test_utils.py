"""Compatibility imports for the reorganized Client Script test helpers.

The real helper module now lives at
`kgmaccount.tests.client_scripts.shared.client_script_test_utils` so Sales
Order and Quotation tests can share one profile-based runner. This file stays
in place because older tests, including WhatsApp order-builder tests, import
`get_client_script` from the old path.
"""

from kgmaccount.tests.client_scripts.shared.client_script_test_utils import *  # noqa: F401,F403
