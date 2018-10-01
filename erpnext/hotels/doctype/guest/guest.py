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

    def validate(self):
        self.link_customer_address()
        self.full_name = ' '.join(
            filter(None, (self.first_name, self.middle_name, self.last_name)))

    def after_insert(self):
        if not self.customer:
            self.create_customer()

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

    def create_customer(self):
        customer = frappe.new_doc("Customer")
        fullname = "{0} {1} {2} - {3}".format(
            self.first_name, self.middle_name[0] if self.middle_name else "", self.last_name, self.name.replace("GUES-", ""))
        default_customer_group = frappe.db.get_single_value(
            "Hotel Settings", "default_customer_group") or "Hotel Guest"

        customer.update({
                        "gender": self.gender,
                        "customer_name": fullname,
                        "customer_type": "Individual",
                        "customer_group": default_customer_group,
                        "territory": get_root_of("Territory")
                        })
        if self.salutation:
            customer.update({"salutation": self.salutation})
        company = get_default_company()
        debtors_account = get_account_name("Receivable", "Asset", is_group=0,
                                           account_currency=get_company_currency(company), company=company)

        customer.update({
            "accounts": [{
                "company": company,
                "account": debtors_account
            }]
        })

        customer.flags.ignore_mandatory = False
        customer.insert(ignore_permissions=True)
        self.customer = customer.name


@frappe.whitelist()
def make_customer(source_name, target_doc=None):
    return _make_customer(source_name, target_doc)


def _make_customer(source_name, target_doc=None, ignore_permissions=False):
    def set_missing_values(source, target):
        target.customer_type = "Individual"
        target.customer_name = source.full_name
        target.salutation = source.salutation

        default_customer_group = frappe.db.get_single_value(
            "Hotel Settings", "default_customer_group") or "Hotel Guest"

        target.customer_group = default_customer_group

    doclist = get_mapped_doc("Guest", source_name,
                             {"Guest": {
                                 "doctype": "Customer",
                                 "field_map": {
                                     "name": "full_name",
                                     # "company_name": "customer_name",
                                     "contact_no": "phone_1",
                                 }
                             }}, target_doc, set_missing_values, ignore_permissions=ignore_permissions)

    return doclist
