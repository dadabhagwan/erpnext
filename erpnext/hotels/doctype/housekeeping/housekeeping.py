# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class Housekeeping(Document):
    pass


@frappe.whitelist()
def update_room_status(names, status):
    import json
    names = json.loads(names or [])
    frappe.db.sql(
        """update `tabHousekeeping` set room_status = %s where name in (%s)""" % (
            '%s', ','.join(['%s'] * len(names))), (status,)+tuple(names))
    frappe.db.commit()
