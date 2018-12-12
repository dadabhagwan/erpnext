# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	if not filters: filters = {}
	filters.update({"from_date": filters.get("date_range") and filters.get("date_range")[0], "to_date": filters.get("date_range") and filters.get("date_range")[1]})
	columns, data = get_data(filters)
	return columns, data

def get_columns(filters):
	pass

def get_data(filters):
	query = """
		SELECT hrri.date,
		hr.hotel_room_type,
		hrr.room,
		hrri.item,
		sum(hrri.amount) revenue
		FROM `tabHotel Room Reservation` hrr 
		INNER JOIN `tabHotel Room Reservation Item` hrri ON hrri.parent = hrr.name
		INNER JOIN `tabItem` i ON hrri.item = i.name
		LEFT OUTER JOIN `tabHotel Room` hr ON hrr.room = hr.name 
		where hrri.date BETWEEN '{from_date}' AND '{to_date}'
		GROUP BY hrri.date, hr.hotel_room_type, hrr.room, hrri.item
		ORDER BY hrri.date, i.item_group, i.name
		""".format(from_date = filters.get("from_date"), to_date = filters.get("to_date"))
	data = frappe.db.sql(query, filters, as_list=1)
	import pandas
	df=pandas.DataFrame(data, columns=["date", "hotel_room_type", "room", "item", "revenue"], dtype=float)
	index = []
	for key in filters:
		if key in ['hotel_room_type','room','item'] and filters.get(key) == 1:
			index.append(key)
	if not len(index) or len(data) == 0:
		return [[],[]]
	values = "revenue"
	
	pivot = pandas.pivot_table(df, index=index, columns=["date"], values=values, fill_value=0
				,aggfunc='sum', margins=True, margins_name='Total')
	return to_array(pivot)

def to_array(pivot):
    columns = [ dict(label=d,fieldname=d,fieldtype="Varchar",width=120) for d in pivot.index.names]
    columns = columns + [dict(label=c, fieldname=c, fieldtype="Currency", width=90) for c in pivot.columns]
    # data = [[l for l in pivot.index[idx]]+([i for i in d])  for idx,d in enumerate(pivot.values)]
    from frappe.utils.csvutils import read_csv_content
    csv = read_csv_content(pivot.to_csv())
    return columns, csv[1:]