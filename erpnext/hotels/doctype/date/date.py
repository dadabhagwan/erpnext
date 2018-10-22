# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class Date(Document):
    def autoname(self):
        self.name = self.db_date.strftime('%Y%m%d')


def make_data(start, end):
    from datetime import date
    from frappe.utils import date_diff, add_months, getdate, add_days
    start = getdate(start)

    for n in range(0-date_diff(getdate(start), getdate(end))+1):
        try:
            day = add_days(start, n)
            frappe.get_doc({
                "doctype": "Date",
                "db_date": day,
                "year": day.year,
                "month": day.month,
                "day": day.day,
                "quarter": get_q(day.month),
                "week": day.isocalendar()[1],
                "day_name": day.strftime("%a"),
                "month_name": day.strftime("%b"),
                "is_weekend": day.isoweekday() == 6 or day.isoweekday() == 7
            }).insert()
        except frappe.DuplicateEntryError:
            pass


def get_q(month):
    if month < 4:
        return 1
    elif month < 7:
        return 2
    elif month < 10:
        return 2
    else:
        return 2
