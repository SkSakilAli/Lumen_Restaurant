import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from lumen_restaurants.api.notifications import EVENT_BY_KEY, notification_settings


class TestPOSNotifications(FrappeTestCase):
    def test_legacy_roles_are_projected_until_replaced_by_rules(self):
        settings = frappe._dict(
            notification_rules=[
                frappe._dict(event_type="kitchen_ticket_created", role="Kitchen")
            ],
            kitchen_notification_role="Legacy Kitchen",
            bar_notification_role="Bar",
        )

        self.assertEqual(
            notification_settings(settings),
            [
                {"event_type": "kitchen_ticket_created", "role": "Kitchen"},
                {"event_type": "bar_ticket_created", "role": "Bar"},
            ],
        )

    def test_rule_doctype_options_match_registered_events(self):
        rule_path = (
            Path(__file__).resolve().parents[1]
            / "lumen_restaurants"
            / "doctype"
            / "pos_notification_rule"
            / "pos_notification_rule.json"
        )
        rule = json.loads(rule_path.read_text(encoding="utf-8"))
        options = next(
            field["options"]
            for field in rule["fields"]
            if field["fieldname"] == "event_type"
        )

        self.assertEqual(options.splitlines(), list(EVENT_BY_KEY))
