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
        self.set_item_date()
        if self.status == "Completed":
            self.make_housekeeping_entry()
        if not self.company:
            self.company = get_default_company()

    def make_housekeeping_entry(self):
        doc = frappe.db.sql(
            "select name from `tabHousekeeping` where date(creation)=date(%s) and reservation = %s limit 1", (self.checkout_date, self.name))
        if not doc:
            doc = frappe.new_doc("Housekeeping")
            doc.room = self.room
            doc.room_status = "Dirty"
            doc.reservation = self.name
            doc.insert(ignore_permissions=True)

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

    def get_day_rate(self, item, date):
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
                    and pricing.to_date""", (item, date))

        if not day_rate:
            frappe.throw(
                _("Please set Hotel Room Rate on {}".format(
                    frappe.format(date, dict(fieldtype="Date")))), exc=HotelRoomPricingNotSetError)
        else:
            return day_rate[0][0]

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

        line_items = [(self.item, 1)]
        if self.extra_bed:
            line_items.append(("Extra Bed", self.extra_bed))

        for d in line_items:
            day_rate = self.get_day_rate(d[0], date)
            self.append("items", {
                "date": date,
                "item": d[0],
                "qty": d[1],
                "currency": get_default_currency(),
                "rate": day_rate,
                "amount": day_rate
            })

        self.net_total += day_rate
        self.save()

    def set_rates(self):
        self.net_total = 0
        for d in self.items:
            if not d.item or not frappe.db.get_value("Item", d.item, ["item_group"]) == "Hotel Room Package":
                if d.amount:
                    self.net_total += d.amount
                continue
            d.rate = self.get_day_rate(d.item, d.date)
            d.amount = d.rate * flt(d.qty)
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

    def set_item_date(self):
        for d in self.items:
            if not d.date:
                d.date = nowdate()

    def set_item_date(self):
        for d in self.items:
            if not d.date:
                d.date = nowdate()


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
def validate_folio(reservation):
    # check for unsettled open folio e.g in case of group booking
    # reservation = frappe.get_doc('Hotel Room Reservation', reservation)
    return {"is_folio_open": 0}


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


def get_gst_item(rate):
    rate = flt(rate)
    gst_slabs = [(0, 1999, "Slab 1"), (2000, 6999, "Slab 2"),
                 (7000, 3000, "Slab 3")]
    item = [d[2] for d in gst_slabs if d[0] <= rate and d[1] >= rate]
    if len(item):
        return item[0]


def get_invoice_items(name):
    return frappe.db.sql("""
select trim(concat(a.item,' ',slabs.slab)) item_code, a.qty, a.rate, a.amount
from 
(
	select item, 1 qty, sum(rate) rate, sum(amount) amount
	from
	(
		select m.item, t.date, t.rate, t.amount
		from 
		`tabHotel Room Reservation` m 
		inner join `tabHotel Room Reservation Item` t on m.name = t.parent and t.item = m.item
        where m.name = '{0}'
		union all
		select m.item, t.date, t.rate * t.qty rate, sum(t.amount) amount 
		from 
		`tabHotel Room Reservation` m 
		inner join `tabHotel Room Reservation Item` t on m.name = t.parent and t.item = 'Extra Bed'
        where m.name = '{0}'
	) x
	group by item
) a
inner join
(
	select 0 from_rate, 999 to_rate, '(NIL)' slab union all
	select 1000 from_rate, 2499 to_rate, '(12)' slab union all
	select 2500 from_rate, 7499 to_rate, '(18)' slab union all
	select 7500 from_rate, 100000 to_rate, '(28)' slab 	
) slabs on slabs.from_rate <= a.rate and slabs.to_rate >= a.rate
union all
select t.item item_code, sum(t.qty) qty, t.rate, sum(t.amount) amount
from 
`tabHotel Room Reservation` m 
inner join `tabHotel Room Reservation Item` t on m.name = t.parent
inner join tabItem i on i.item_code = t.item and i.item_group <> 'Hotel Room Package'
where m.name = '{0}'
group by t.item, rate
    """.format(name), as_dict=1, debug=0)


def make_item(item, company):
    tax_rate = 0
    if "(NIL)" in item:
        tax_rate = 0.0
    elif "(12)" in item:
        tax_rate = 6.0
    elif "(18)" in item:
        tax_rate = 9.0
    elif "(28)" in item:
        tax_rate = 14.0

    doc = frappe.get_doc({
        "doctype": "Item",
        "item_code": item,
        "item_name": item,
        "description": item,
        "item_group": "Hotel Room Package",
        "is_stock_item": 0,
        "stock_uom": 'Unit'
    })

    from erpnext.setup.doctype.company.company import get_name_with_abbr
    if tax_rate > 0:
        for d in ["CGST", "SGST"]:
            doc.append("taxes", {"tax_type": get_name_with_abbr(
                d, company), "tax_rate": tax_rate})
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.name


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

    for d in get_invoice_items(source_name):
        item = d.item_code
        if not frappe.db.exists("Item", d.item_code):
            item = make_item(d.item_code, reservation.company)
        target.append("items", {
            "item_code": item,
            "qty": d.qty,
            "rate": d.rate,
            "amount": d.amount
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
