# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from frappe import _
from frappe.utils import date_diff, add_days, flt, cint, nowdate, nowtime, cstr, now_datetime
from erpnext import get_company_currency, get_default_company, get_default_currency


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

    def post_room_and_tax(self, date):
        '''Post room charges for the day. Used in Night Audit and at the time of Check In'''
        exists = [d for d in self.items if d.date ==
                  date and d.item == self.item]
        if exists:
            return

        if not self.room_status == "Checked In":
            frappe.throw("Can post only to 'Checked In' rooms")
        if date < self.from_date or date > self.to_date:
            frappe.throw("Date is out of booking period.")

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
                    and pricing.to_date""", (self.item, date))

        if not day_rate:
            frappe.throw(
                _("Please set Hotel Room Rate on {}".format(
                    frappe.format(date, dict(fieldtype="Date")))), exc=HotelRoomPricingNotSetError)
        else:
            day_rate = day_rate[0][0]
            self.append("items", {
                "date": date,
                "item": self.item,
                "qty": 1,
                "currency": get_default_currency(),
                "rate": day_rate,
                "amount": day_rate
            })
            self.net_total += day_rate
            self.save()

    def set_rates(self):
        self.net_total = 0
        for d in self.items:
            if not d.item or not frappe.db.get_value("Item", d.item, ["item_group"])[0][0] == "Hotel Room Package":
                continue
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
                            and pricing.to_date""", (d.item, day))

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

    def checkout(self):
        self.room_status = "Checked Out"
        folio = validate_folio(self.name)
        if folio and cint(folio["is_folio_open"]) == 0:
            self.status = "Completed"
        self.checkout_date = now_datetime()
        self.save()

        # make housekeeping entry
        he = frappe.new_doc("Housekeeping")
        he.room = self.room
        he.room_status = "Dirty"
        he.fo_status = "Vacant"
        he.insert(ignore_permissions=True)


@frappe.whitelist()
def get_room_rate(hotel_room_reservation):
    """Calculate rate for each day as it may belong to different Hotel Room Pricing Item"""
    doc = frappe.get_doc(json.loads(hotel_room_reservation))
    doc.set_rates()
    return doc.as_dict()


@frappe.whitelist()
def get_group(reservation):
    return frappe.db.sql("""
        select r.name, r.item, r.from_date, r.to_date, r.net_total, r.room, r.room_status, coalesce(i.amount,0) amount
        from `tabHotel Room Reservation` r
        left outer join 
        (
            select sum(amount) amount, parent from `tabHotel Room Reservation Item`
            group by parent
        ) i on i.parent = r.name
        where r.group_id = '%s'
    """ % (reservation,), as_dict=1)


@frappe.whitelist()
def settle(hotel_room_reservation):
    """Set charges for today if late checkout"""
    doc = frappe.get_doc(json.loads(hotel_room_reservation))

    hotel_settings = frappe.get_single("Hotel Settings")
    if not hotel_settings.default_checkout_time:
        frappe.throw("Default checkout time is not set in Hotel Settings")

    if nowtime() > hotel_settings.default_checkout_time:
        doc.post_room_and_tax(nowdate())
    return doc.as_dict()


@frappe.whitelist()
def validate_folio(reservation):
    # check for unsettled open folio e.g in case of group booking
    # reservation = frappe.get_doc('Hotel Room Reservation', reservation)
    return {"is_folio_open": 0}


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

    # TODO: validate all reservations in group if ready to invoice
    items = frappe.db.sql("""
        select r.name, i.item item_code, i.qty, i.rate, i.amount
        from `tabHotel Room Reservation` r
        inner join `tabHotel Room Reservation Item` i on i.parent = r.name 
        where r.group_id = %s or r.name = %s
    """, (reservation.group_id, source_name), as_dict=1)

    for d in items:
        target.append("items", {
            "item_code": d.item_code,
            "qty": d.qty,
            "rate": d.rate
        })

    target.flags.ignore_permissions = 1
    target.set_missing_values()
    target.calculate_taxes_and_totals()

    target.insert()

    frappe.db.sql(
        """update `tabHotel Room Reservation` set sales_invoice = %s, status='Invoiced' where group_id = %s""", (target.name, reservation.group_id))
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
