// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Guest', {
	refresh: function (frm) {

		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Guest' }
		frm.toggle_display(['address_html'], !frm.doc.__islocal);
		if (!frm.doc.__islocal) {
			// frappe.contacts.render_address_and_contact(frm);
			frm.trigger("render_address");
		}
	},

	render_address: function (frm) {
		// render address
		if (frm.fields_dict['address_html'] && "addr_list" in frm.doc.__onload) {
			$(frm.fields_dict['address_html'].wrapper)
				.html(frappe.render_template("address_list",
					cur_frm.doc.__onload))
				.find(".btn-address").on("click", function () {
					frappe.route_options = {
						"address_title": `${frm.doc.name}` || "",
						"is_primary_address": true
					}
					frappe.new_doc("Address");
				});
		}
	}

});
