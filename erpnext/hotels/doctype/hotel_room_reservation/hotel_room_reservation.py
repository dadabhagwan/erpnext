# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from frappe import _
from frappe.utils import date_diff, add_days, flt, cint
import datetime
import pandas as pd


class HotelRoomUnavailableError(frappe.ValidationError):
    pass


class HotelRoomPricingNotSetError(frappe.ValidationError):
    pass


def test():
    doc = frappe.get_doc("Hotel Room Reservation", "HRES0000001").as_dict()


class HotelRoomReservation(Document):
    def validate(self):
        self.total_rooms = {}
        self.set_rates()
        self.validate_availability()
        self.validate_allotment()

    def after_insert(self):
        self.guest_name = frappe.db.get_value(
            "Guest", self.guest, "full_name")
        if not self.customer:
            self.customer = frappe.db.get_value(
                "Guest", self.guest, "customer") or frappe.db.get_single_value(
                'Hotel Settings', 'default_customer')

    def validate_allotment(self):
        if not self.room_allotment:
            return
        for d in self.items:
            alloted_count = len([i for i in self.room_allotment if i.from_date ==
                                 d.from_date and i.to_date == d.to_date and i.item == d.item])
            if not alloted_count == d.room_count:
                frappe.throw("%d %s rooms to be alloted from %s to %s" %
                             (d.room_count-alloted_count, d.item, d.from_date, d.to_date))
        # check same room alloted more than once for same day
        for d in self.room_allotment:
            dup = [i for i in self.room_allotment if i.name <> d.name and i.room ==
                   d.room and not (i.from_date >= d.to_date or i.to_date <= d.from_date)]
            if dup:
                frappe.throw(_("Duplicate allotment for Room %s in rows %s and %s") % (
                    d.room, d.idx, dup[0].idx))

        # add reservation items if missing
        allotment = []
        for d in self.room_allotment:
            allotment.append(
                {"item": d.item, "from_date": d.from_date, "to_date": d.to_date})

        df = pd.DataFrame(allotment)
        g = df.groupby(["item", "from_date", "to_date"]
                       ).size().reset_index(name='counts')
        for idx, row in g.iterrows():
            items = [i for i in self.items if i.item == row['item']
                     and i.from_date == row['from_date'] and i.to_date == row['to_date']]
            if not items:
                self.append("items", {
                    "item": row["item"],
                    "from_date": row["from_date"],
                    "to_date": row["to_date"],
                    "room_count": row["counts"],
                    "qty": row["counts"] * (date_diff(row["to_date"], row["from_date"]))
                })
        self.set_rates()

    def validate_availability(self):
        self.rooms_booked = {}
        available = get_rooms_availability(
            self.from_date, self.to_date, exclude_reservation=self.name)
        for d in self.items:
            room_type = frappe.db.get_value(
                "Hotel Room Package", d.item, 'hotel_room_type')
            if not self.rooms_booked.get(room_type):
                self.rooms_booked[room_type] = {}
            for i in range(date_diff(d.to_date, d.from_date)):
                day = add_days(d.from_date, i)
                if not self.rooms_booked[room_type].get(day):
                    self.rooms_booked[room_type][day] = 0
                self.rooms_booked[room_type][day] = self.rooms_booked[room_type][day]+d.room_count
                for a in available:
                    if date_diff(a['date'], day) == 0:
                        if cint(a['available']) < self.rooms_booked[room_type][day]:
                            message = "Only {2} Rooms of type {0} are available on {1}"
                            frappe.throw(_(message.format(room_type, frappe.format(
                                day, dict(fieldtype="Date")), cint(a['available']))), exc=HotelRoomUnavailableError)

        for d in self.room_allotment:
            if frappe.db.exists("""
            select 1 
            from 
                `tabHotel Room Reservation Allotment allotment
            where 
                allotment.parent <> {reservation} 
                and allotment.room = {room}
                and allotment.allotment_status in ('Booked','CheckedIn')
                and not (allotment.from_date > '{to_date}' or allotment.to_date < '{from_date}'
            """.format(reservation=self.name, room=d.room, from_date=d.from_date, to_date=d.to_date)):
                frappe.throw(_("Room {room} is not available between {from_date} and {to_date}.".format(
                    room=d.room, from_date=d.from_date, to_date=d.to_date)))

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
            net_rate = 0.0
            for i in range(date_diff(self.to_date, self.from_date)):
                day = add_days(self.from_date, i)
                if not d.item:
                    continue
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


@frappe.whitelist()
def get_room_rate(hotel_room_reservation):
    """Calculate rate for each day as it may belong to different Hotel Room Pricing Item"""
    doc = frappe.get_doc(json.loads(hotel_room_reservation))
    doc.set_rates()
    return doc.as_dict()


def get_rooms_booked_(room_type, day, exclude_reservation=None):
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


def get_rooms_availability(from_date, to_date, exclude_reservation=None):
    exclude_condition = ''
    if exclude_reservation:
        exclude_condition = "and item.parent != '{0}'".format(
            frappe.db.escape(exclude_reservation))

    return frappe.db.sql("""		
select cal.db_date date, room.hotel_room_type, room.room_count - coalesce(sum(booked),0) available
FROM
`tabCalendar` cal
cross join (select hotel_room_type, count(*) room_count from `tabHotel Room`) room
left outer join 
(
	select cal.db_date date, room.hotel_room_type, count(*) booked
	from `tabHotel Room Reservation Allotment` item 
	inner join `tabHotel Room` room on room.name = item.room
	inner join `tabCalendar` cal on cal.db_date>= item.from_date and cal.db_date<=item.to_date
	where cal.db_date between '{from_date}' and '{to_date}'
    {exclude_condition}
	and item.allotment_status in ('Booked','CheckedIn')
	group by cal.db_date
	union all
	select cal.db_date date, room_package.hotel_room_type, sum(item.room_count) booked
	from `tabHotel Room Reservation Item` item 
	inner join `tabHotel Room Package` room_package on room_package.item = item.item
	inner join `tabCalendar` cal on cal.db_date>= item.from_date and cal.db_date<=item.to_date
	where cal.db_date between '{from_date}' and '{to_date}'
    {exclude_condition}
	and not exists (select 1 from `tabHotel Room Reservation Allotment` x where x.parent=item.parent)
	group by cal.db_date
) booked on booked.hotel_room_type = room.hotel_room_type and cal.db_date = booked.date
where cal.db_date between '{from_date}' and '{to_date}'
group by cal.db_date, room.hotel_room_type""".format(exclude_condition=exclude_condition, from_date=from_date, to_date=to_date), as_dict=True)
