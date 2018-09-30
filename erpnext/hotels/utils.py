# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For lice

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff, add_days
from frappe.utils.data import getdate, formatdate

import pandas as pd


def test():
    return get_reservation_chart("2018-08-28", "2018-08-31")


def get_available_rooms(doctype, txt, searchfield, start, page_len, filters):
    if not filters:
        filters = {}
    where_conditions = ''

    return frappe.db.sql("""
select hotel_room.name 
from `tabHotel Room` hotel_room
inner join `tabHotel Room Package` hotel_room_package on hotel_room_package.hotel_room_type=hotel_room.hotel_room_type
where 
hotel_room_package.item = '{item}'
and not EXISTS
(
 select 1 
 from `tabHotel Room Reservation` r 
 where
 r.room = hotel_room.name
 and r.room_status in ('Checked In','Booked')
 and not (r.from_date > '{to_date}' or r.to_date < '{from_date}')
 {where_conditions}
)""".format(item=filters.get("item"), from_date=filters.get("from_date"), to_date=filters.get("to_date"), where_conditions=where_conditions))


@frappe.whitelist()
def get_reservation_chart(from_date, to_date):
    records = frappe.db.sql("""
select hotel_room.hotel_room_type, hotel_room.name hotel_room_name, cal.db_date date, 
replace(lower(coalesce(allot.allotment_status,'Checked In')),'','checkedin') info 
from `tabHotel Room` hotel_room
cross join `tabCalendar` cal
left outer join `tabHotel Room Reservation Allotment` allot on allot.from_date <= cal.db_date and allot.to_date > cal.db_date and allot.allotment_status in ('Booked', 'Checked In')
where cal.db_date between '{from_date}' and '{to_date}'
order by hotel_room.hotel_room_type, hotel_room.name, cal.db_date
    """.format(from_date=from_date, to_date=to_date), as_list=True)

    df = pd.DataFrame.from_records(
        records, columns=['hotel_room_type', 'hotel_room_name', 'date', 'info'])
    pivot = pd.pivot_table(df, index=['hotel_room_type', 'hotel_room_name'], columns=[
        'date'], values='info', aggfunc=max, fill_value='', )
    data = pd.DataFrame(pivot.to_records()).to_dict('records')

    # print(data)

    columns = [{"headerName": 'Room Type', "field": 'hotel_room_type', 'width': 150, },
               {"headerName": 'Room', "field": 'hotel_room_name', 'width': 100},
               ]

    for i in range(date_diff(to_date, from_date)):
        day = add_days(from_date, i)
        columns.append({'headerName': formatdate(
            getdate(day), "MMM dd"), 'field': day, 'width': 80})

    return {"data": data, "columns": columns}