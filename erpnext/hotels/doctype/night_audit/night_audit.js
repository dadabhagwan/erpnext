// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Night Audit', {
	refresh: function (frm) {
		if (frm.is_new()) {
			frm.set_value('date', frappe.datetime.get_today());
		}
	}
});
