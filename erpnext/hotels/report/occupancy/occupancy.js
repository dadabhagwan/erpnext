// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Occupancy"] = {


    onload: function (report) {
        report.page.remove_inner_button("Set Chart");
    },

    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.now_date(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.now_date(),
            "reqd": 1
        },
        {
            "fieldname": "report",
            "label": __("Report"),
            "fieldtype": "Select",
            "options": "In House\nArrival\nDeparture\nReserved\nCompleted",
            "default": "In House",
            "reqd": 1
        },
        {
            "fieldname": "today",
            "label": __("Today"),
            "fieldtype": "Date",
            "default": frappe.datetime.nowdate(),
            "hidden": 1
        },

    ]
}
