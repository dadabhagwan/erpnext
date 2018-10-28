// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Hotel Analytics"] = {
	"filters": [
		{
			"fieldname":"date_range",
			"label": __("Date Range"),
			"fieldtype": "DateRange",
			"default": [frappe.datetime.add_months(frappe.datetime.get_today(),-1), frappe.datetime.get_today()],
			"reqd": 1
		},
		{
			"fieldname":"hotel_room_type",
			"label": __("Room Type"),
			"fieldtype": "Check",
			"default": 1,
			"reqd": 0
		},
		{
			"fieldname":"room",
			"label": __("Room"),
			"fieldtype": "Check",
			"default": 0,
			"reqd": 0
		},
		{
			"fieldname":"item",
			"label": __("Items"),
			"fieldtype": "Check",
			"default": 0,
			"reqd": 0
		}
	]
}
