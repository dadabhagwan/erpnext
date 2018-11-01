# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For lice

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff, add_days, cint, getdate
from frappe.utils.data import getdate, formatdate


def test():
    return get_reservation_chart("2018-08-28", "2018-08-31")


def get_available_rooms(doctype, txt, searchfield, start, page_len, filters):
    if not filters:
        filters = {}
    where_conditions = ''
    if not filters.get("from_date") or not filters.get("to_date") or not filters.get("item"):
        frappe.throw("Please select dates and Pacakge for selecting room.")

    return frappe.db.sql("""
select hotel_room.name
from `tabHotel Room` hotel_room
inner join `tabHotel Room Package` hotel_room_package on hotel_room_package.hotel_room_type=hotel_room.hotel_room_type
where
hotel_room_package.item = '{item}'
and not EXISTS
(
	select 1 from tabHousekeeping x where x.room = hotel_room.name and x.room_status = 'Dirty' and '{from_date}'=curdate()
)
and not EXISTS
(
 select 1
 from `tabHotel Room Reservation` r
 where
 r.room = hotel_room.name
 and r.room_status in ('Checked In','Booked')
 and not (r.from_date > '{to_date}' or r.to_date <= '{from_date}')
 {where_conditions}
)""".format(item=filters.get("item"), from_date=filters.get("from_date"), to_date=filters.get("to_date"), where_conditions=where_conditions))


@frappe.whitelist()
def get_reservation_chart(from_date, to_date):
    records = frappe.db.sql("""
    select hotel_room.hotel_room_type, hotel_room.name hotel_room_name, cal.db_date date,
    replace(lower(coalesce(allot.allotment_status,'Checked In')),'','checkedin') info
    from `tabHotel Room` hotel_room
    cross join `tabDate` cal
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


def get_calendar(from_date, to_date, as_dict=0):
    from datetime import timedelta

    dates = [(getdate(from_date)+timedelta(days=d)).strftime('%Y%m%d')
             for d in range((getdate(to_date)-getdate(from_date)).days+1)]

    select_agg = " , ".join(
        ["cast(max(`{0}`) as char) `{0}`".format(getdate(d).strftime('%b %d')) for d in dates])

    select_columns = " , ".join(["case when a.db_date = '{0}' then a.data else '' end as `{1}`".format(
        d, getdate(d).strftime('%b %d')) for d in dates])

    columns = ["room_type", "room_name"] + \
        [getdate(d).strftime('%b %d') for d in dates]

    data = frappe.db.sql("""
        select hotel_room_type, hotel_room_name, {select_agg}
        from (
            select a.hotel_room_type, a.hotel_room_name, 
            {select_columns}
            from
            (select hr.hotel_room_type, hr.name hotel_room_name, cal.db_date,
            concat_ws('|',r.guest_name,right(r.name,4),case room_status when 'Checked In' then 'O' when 'Booked' then 'B' else '' end,0) data
            from `tabHotel Room` hr
            left outer join `tabHotel Room Reservation` r on r.room = hr.name
            left outer join `tabDate` cal on cal.db_date>= r.from_date and cal.db_date <= r.to_date
            ) a
        ) t
        group by hotel_room_type, hotel_room_name
        order by hotel_room_type, hotel_room_name
    """.format(from_date=from_date, to_date=to_date, select_columns=select_columns, select_agg=select_agg), as_dict=as_dict, debug=0)
    return columns, data
