# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime_str, getdate
from erpnext import get_default_company


class NightAudit(Document):
    def autoname(self):
        self.name = "NADT-%s-%s" % (self.company, self.date.replace("-", ""))

    def validate_pending_checkout(self):
        # check for invalid reservations - checked in room status & to_date <= today
        checked_in = frappe.db.sql("""
            select res.room
            from `tabHotel Room Reservation` res
            where res.room_status = 'Checked In' and to_date <= %s
            limit 1
            """, (self.date))
        if checked_in:
            checked_in = ", ".join([d[0] for d in checked_in])
            frappe.throw(
                """Please checkout or extend pending checkouts. Rooms : {} <br>
                 <a href='desk#query-report/Occupancy'><strong>Occupancy Report</strong></a>""".format(checked_in))

    def get_audit_items(self):
        self.validate_pending_checkout()
        items = frappe.db.sql("""
select a.*, g.full_name guest_name, g.mobile_no
from 
(   select res.room, res.name, res.guest, res.item, 1 qty
    from `tabHotel Room Reservation` res
    where res.room_status = 'Checked In'
    union all
    select res.room, res.name, res.guest, s.value, res.extra_bed qty
    from `tabHotel Room Reservation` res
    inner join tabSingles s on s.doctype='Hotel Settings' and s.field='extra_bed_service' 	
    where res.room_status = 'Checked In' and res.extra_bed > 0
) a
inner join `tabGuest` g on g.name = a.guest
where not exists 
(select 1 from `tabHotel Room Reservation Item` x where x.parent=a.name and x.date= %s and x.item = a.item)
        """, (self.date), as_dict=1)
        for d in items:
            if not list(filter(lambda x: x.room ==
                               d["room"] and x.reservation == d["name"] and x.item == d["item"], self.items)):
                self.append("items", {
                    "room": d["room"],
                    "reservation": d["name"],
                    "guest": d["guest"],
                    "guest_name": d["guest_name"],
                    "mobile_no": d["mobile_no"],
                    "item": d["item"],
                    "qty": d["qty"]
                })
        return self.as_dict()

    def on_submit(self):
        self.validate_pending_checkout()
        for d in self.items:
            doc = frappe.get_doc('Hotel Room Reservation', d.reservation)
            doc.post_room_and_tax(getdate(self.date))


@frappe.whitelist()
def make_night_audit(audit_date, company):
    try:
        doc = frappe.new_doc("Night Audit")
        doc.date = audit_date
        doc.company = get_default_company()
        doc.save(ignore_permissions=True)
        return doc.name
    except frappe.DuplicateEntryError:
        doc = frappe.get_list(
            "Night Audit", {"date": audit_date, "company": company})
        if doc:
            return doc[0].name
