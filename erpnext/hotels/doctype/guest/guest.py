# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import functools
from frappe.utils.nestedset import get_root_of
from erpnext import get_company_currency, get_default_company
from erpnext.accounts.utils import get_account_name
from frappe.contacts.doctype.address.address import get_address_display
from frappe.model.mapper import get_mapped_doc


class Guest(Document):
    def onload(self):
        """Load address and contacts in `__onload`"""
        self.set_onload('addr_list', self.get_address_list())

    def get_address_list(self):
        """Loads address list in `__onload`"""
        filters = [
            ["Dynamic Link", "link_doctype", "=", self.doctype],
            ["Dynamic Link", "link_name", "=", self.name],
            ["Dynamic Link", "parenttype", "=", "Address"],
        ]
        address_list = frappe.get_all("Address", filters=filters, fields=["*"])

        address_list = [a.update({"display": get_address_display(a)})
                        for a in address_list]

        address_list = sorted(address_list,
                              key=functools.cmp_to_key(lambda a, b:
                                                       (int(a.is_primary_address - b.is_primary_address)) or
                                                       (1 if a.modified - b.modified else 0)), reverse=True)
        return address_list

    def validate(self):
        self.link_customer_address()
        self.full_name = ' '.join(
            filter(None, (self.first_name, self.middle_name, self.last_name)))

    def link_customer_address(self):
        if not self.customer:
            return
        if not frappe.db.sql("""select 1 from `tabDynamic Link` dl
        where dl.parenttype='Address' and dl.link_doctype='Customer' and dl.link_name='{customer} limit 1'
        """.format(customer=self.customer), as_list=1):
            address_list = self.get_address_list()
            for a in address_list:
                address = frappe.get_doc("Address", a.name)
                address.append("links", {
                    "link_doctype": "Customer",
                    "link_name": self.customer
                })
                address.save()
                frappe.db.commit()
                break
