# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr, cint


class Calendar(Document):
    def autoname(self):
        pass
        # self.name = "{0}{1}{2}".format(
        #     cstr(self.year), cstr(self.month), cstr(self.day))

    def validate(self):
        pass
