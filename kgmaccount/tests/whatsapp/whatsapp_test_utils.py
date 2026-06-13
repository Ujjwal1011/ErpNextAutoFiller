"""Shared helper objects for WhatsApp suite unit tests.

Input:
- These helpers do not read files or call external services.
- Tests pass fake documents, fake database writes, fake logger calls, and fake
  whitelisted-function calls into the WhatsApp modules.

How checks work:
- `FakeDb` records `set_value`, `commit`, and `rollback` calls.
- `FakeDoc` behaves enough like a Frappe document for tests to set fields,
  call `insert`, `save`, and `get_password`.
- `call_whitelisted` calls the real body of a function wrapped by
  `@frappe.whitelist`.

Purpose:
- Keep WhatsApp tests separate from WAHA, OpenRouter, and a real Frappe site.
"""

import types


class NoopLogger:
    """Logger replacement used when the code under test writes diagnostic logs."""

    def info(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def exception(self, *args, **kwargs):
        pass


class FakeDb:
    """Minimal fake `frappe.db` that records writes and transaction calls."""

    def __init__(self):
        self.set_values = []
        self.commits = 0
        self.rollbacks = 0

    def set_value(self, *args, **kwargs):
        self.set_values.append((args, kwargs))

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def exists(self, *args, **kwargs):
        return False


class FakeDoc(types.SimpleNamespace):
    """Simple object that behaves enough like a Frappe document for unit tests."""

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def insert(self, ignore_permissions=False):
        self.inserted = True
        return self

    def save(self, ignore_permissions=False):
        self.saved = True
        return self

    def get_password(self, fieldname):
        return getattr(self, fieldname)


def call_whitelisted(function, *args, **kwargs):
    """Call the real function body when @frappe.whitelist wraps it for request validation."""
    return getattr(function, "__wrapped__", function)(*args, **kwargs)
