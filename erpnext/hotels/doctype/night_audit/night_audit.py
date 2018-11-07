# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime_str, getdate
from erpnext import get_default_currency


class NightAudit(Document):
    def autoname(self):
        self.name = "NADT-%s-%s" % (self.company, self.date.replace("-", ""))

    def validate(self):
        self.items = []
        filters = {"room_status": "Checked In",
                   "company": self.company, "from_date": ["<=", self.date], "to_date": [">=", self.date]}
        fields = ['room', 'name','guest_name', 'mobile_no', 'item', 'extra_bed']
        doclist = frappe.db.get_list(
            "Hotel Room Reservation", filters=filters, fields=fields)
        for d in doclist:
            for item in [d["item"]] + ["Extra Bed"] * d["extra_bed"]:
                self.append("items", {
                    "room": d["room"],
                    "reservation": d["name"],
                    "guest_name": d["guest_name"],
                    "mobile_no": d["mobile_no"],
                    "item": item,
                    "qty": 1,
                })

    def on_submit(self):
        for d in self.items:
            doc = frappe.get_doc('Hotel Room Reservation', d.reservation)
            doc.post_room_and_tax(getdate(self.date))
