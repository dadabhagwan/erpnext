// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Night Audit', {
	refresh: function (frm) {
		frm.page.add_inner_button("Refresh", function () {
			erpnext.hotels.night_audit.get_audit_items(frm);
		});
	},
});

frappe.provide('erpnext.hotels');
erpnext.hotels.night_audit = {
	get_audit_items: function (frm) {
		frappe.call({
			method: "get_audit_items",
			doc: frm.doc,
			callback: function (r) {
				var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("Form", doc.doctype, doc.name);
				frm.refresh_field("items");
				frm.dirty();
			}
		});


	}

}
