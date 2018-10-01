# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from frappe import _
from frappe.utils import date_diff, add_days, flt
from erpnext import get_company_currency, get_default_company


class HotelRoomUnavailableError(frappe.ValidationError):
    pass


class HotelRoomPricingNotSetError(frappe.ValidationError):
    pass


class HotelRoomReservation(Document):
    def validate(self):
        self.total_rooms = {}
        self.set_rates()
        self.validate_availability()
        if not self.company:
            self.company = get_default_company()

    def validate_availability(self):
        for i in xrange(date_diff(self.to_date, self.from_date)):
            day = add_days(self.from_date, i)
            self.rooms_booked = {}

            items = [frappe._dict(
                {"item": self.item, "qty": 1})] if self.item else []

            for d in items:
                if not d.item in self.rooms_booked:
                    self.rooms_booked[d.item] = 0

                room_type = frappe.db.get_value("Hotel Room Package",
                                                d.item, 'hotel_room_type')
                rooms_booked = get_rooms_booked(room_type, day, exclude_reservation=self.name) \
                    + d.qty + self.rooms_booked.get(d.item)
                total_rooms = self.get_total_rooms(d.item)
                if total_rooms < rooms_booked:
                    frappe.throw(_("Hotel Rooms of type {0} are unavailable on {1}".format(d.item,
                                                                                           frappe.format(day, dict(fieldtype="Date")))), exc=HotelRoomUnavailableError)

                self.rooms_booked[d.item] += rooms_booked

    def get_total_rooms(self, item):
        if not item in self.total_rooms:
            self.total_rooms[item] = frappe.db.sql("""
                select count(*)
                from
                    `tabHotel Room Package` package
                inner join
                    `tabHotel Room` room on package.hotel_room_type = room.hotel_room_type
                where
                    package.item = %s""", item)[0][0] or 0

        return self.total_rooms[item]

    def set_rates(self):
        self.net_total = 0
        for d in self.items:
            if not d.item:
                continue
            item = self.item if d.item == 'Booking Advance' else d.item
            net_rate = 0.0
            for i in xrange(date_diff(self.to_date, self.from_date)):
                day = add_days(self.from_date, i)
                day_rate = frappe.db.sql("""
                    select
                        item.rate
                    from
                        `tabHotel Room Pricing Item` item,
                        `tabHotel Room Pricing` pricing
                    where
                        item.parent = pricing.name
                        and item.item = %s
                        and %s between pricing.from_date
                            and pricing.to_date""", (item, day))

                if day_rate:
                    net_rate += day_rate[0][0]
                else:
                    frappe.throw(
                        _("Please set Hotel Room Rate on {}".format(
                            frappe.format(day, dict(fieldtype="Date")))), exc=HotelRoomPricingNotSetError)
            d.rate = net_rate
            d.amount = net_rate * flt(d.qty)
            self.net_total += d.amount

    def add_group_items(self, args=None):
        if not self.group_id:
            self.db_set('group_id', self.name)

        for n in range(args.get('qty')):
            doc = frappe.copy_doc(self)
            doc.item = args.get('item')
            doc.from_date = args.get('from_date')
            doc.to_date = args.get('to_date')
            doc.group_id = self.group_id or self.name
            doc.save(ignore_permissions=True)
            frappe.db.commit()

    def checkin_group(self):
        filters = {"group_id": self.group_id,
                   "room_status": "Booked", "room": ["!=", ""]}
        doclist = frappe.db.get_list("Hotel Room Reservation", filters=filters)
        for name in doclist:
            frappe.db.set_value("Hotel Room Reservation",
                                name, "room_status", "Checked In")


@frappe.whitelist()
def get_room_rate(hotel_room_reservation):
    """Calculate rate for each day as it may belong to different Hotel Room Pricing Item"""
    doc = frappe.get_doc(json.loads(hotel_room_reservation))
    doc.set_rates()
    return doc.as_dict()


@frappe.whitelist()
def checkout(hotel_room_reservation, is_group=False):
    """Checkout and handle group checkout"""
    doc = frappe.get_doc(json.loads(hotel_room_reservation))
    return doc.as_dict()


def get_rooms_booked(room_type, day, exclude_reservation=None):
    exclude_condition = ''
    if exclude_reservation:
        exclude_condition = 'and reservation.name != "{0}"'.format(
            frappe.db.escape(exclude_reservation))

    return frappe.db.sql("""
        select sum(item.qty)
        from
            `tabHotel Room Package` room_package,
            `tabHotel Room Reservation Item` item,
            `tabHotel Room Reservation` reservation
        where
            item.parent = reservation.name
            and room_package.item = item.item
            and room_package.hotel_room_type = %s
            and reservation.docstatus = 1
            {exclude_condition}
            and %s between reservation.from_date
                and reservation.to_date""".format(exclude_condition=exclude_condition),
                         (room_type, day))[0][0] or 0


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
    # Should use get_mapped_doc ?
    target = frappe.new_doc("Sales Invoice")
    reservation = frappe.get_doc('Hotel Room Reservation', source_name)

    hotel_settings = frappe.get_single("Hotel Settings")
    if not hotel_settings.default_customer:
        frappe.throw("Default customer is not set in Hotel Settings")

    target.company = reservation.company
    target.customer = reservation.customer or hotel_settings.default_customer
    target.naming_series = hotel_settings.default_invoice_naming_series
    if hotel_settings.default_taxes_and_charges:
        target.taxes_and_charges = hotel_settings.default_taxes_and_charges
        target.set_taxes()

    for d in reservation.items:
        target.append("items", {
            "item_code": d.item,
            "qty": d.qty,
            "rate": d.rate
        })

    target.flags.ignore_permissions = 1
    target.set_missing_values()
    target.calculate_taxes_and_totals()

    target.insert()
    reservation.sales_invoice = target.name
    reservation.status = "Invoiced"
    reservation.save()

    frappe.db.commit()

    return target


def make_status_as_paid(doc, method):
    # for invoice in [ref.reference_name for ref in doc.references if ref.reference_doctype == "Sales Invoice"]:
    for invoice in [ref.reference_name for ref in doc.references]:
        doclist = frappe.get_list("Hotel Room Reservation", fields=['name', 'status'], filters={
            "sales_invoice": invoice})
        for doc in doclist:
            if doc['status'] == 'Invoiced':
                frappe.db.set_value("Hotel Room Reservation",
                                    doc['name'], "status", "Paid")
                frappe.db.commit()
