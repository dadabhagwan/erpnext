# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):

    from erpnext.hotels.utils import get_calendar
    columns, data = get_calendar(filters.get("from_date"),
                                 filters.get("to_date"), as_dict=0)
    return get_columns(columns), data


def get_columns(columns):
    result = [
        _("Room Type") + "::150",
        _("Room") + "::90"]
    for d in columns[2:]:
        result.append("{}::75".format(d))
    return result
