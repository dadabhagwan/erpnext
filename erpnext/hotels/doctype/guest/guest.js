// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Guest', {
	onload: function(frm) {
		frm.fields_dict['customer'].get_query = function(doc) {
			return {
				filters: {
					'customer_type': 'Individual'
				}
			}
		}
	},
	refresh: function (frm) {
		var doc = frm.doc;

		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Guest' }
		frm.toggle_display(['address_html'], !frm.doc.__islocal);
		if (!frm.doc.__islocal) {
			frm.trigger("render_address");
		}
		if (!doc.__islocal) {
			frm.add_custom_button(__("Reservation"), () => {
				frappe.route_options = {
					'guest': frm.doc.name,
					'customer': frm.doc.customer
				}
				frappe.new_doc('Hotel Room Reservation');
				// frappe.set_route('Form', 'Hotel Room Reservation')
			}, __("Make"));
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
