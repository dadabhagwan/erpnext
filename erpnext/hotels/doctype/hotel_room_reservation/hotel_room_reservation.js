// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hotel Room Reservation', {
	onload: function (frm) {
		frm.trigger("setup_queries");
	},
	refresh: function (frm) {
		if (true || frm.doc.docstatus == 1) {
			// frm.add_custom_button(__("Make Proforma Invoice"), () => {
			// 	frm.trigger("make_sales_order");
			// });

			frm.page.add_menu_item(__("Recalculate"), () => {
				frm.trigger("recalculate_rates");
			});

			frm.page.add_menu_item(__("Make Invoice"), () => {
				frm.trigger("make_invoice");
			});

			frm.fields_dict["items"].grid.add_custom_button(__('Check In'), () => {

			});
		}
	},
	from_date: function (frm) {
		frm.trigger("recalculate_rates");
	},
	to_date: function (frm) {
		frm.trigger("recalculate_rates");
	},
	setup_queries: function (frm) {
		frm.set_query("room", "room_allotment", function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				query: "erpnext.hotels.utils.get_available_rooms",
				filters: { 'from_date': d.from_date, 'to_date': d.to_date, 'item': d.item }
			}
		});

	},
	recalculate_rates: function (frm) {
		if (!frm.doc.from_date || !frm.doc.to_date
			|| !frm.doc.items.length) {
			return;
		}
		frappe.call({
			"method": "erpnext.hotels.doctype.hotel_room_reservation.hotel_room_reservation.get_room_rate",
			"args": { "hotel_room_reservation": frm.doc }
		}).done((r) => {
			for (var i = 0; i < r.message.items.length; i++) {
				frm.doc.items[i].rate = r.message.items[i].rate;
				frm.doc.items[i].amount = r.message.items[i].amount;
			}
			frappe.run_serially([
				() => frm.set_value("net_total", r.message.net_total),
				() => frm.refresh_field("items")
			]);
		});
	},
	make_sales_order: function (frm) {
		frappe.model.with_doc("Hotel Settings", "Hotel Settings", () => {
			frappe.model.with_doctype("Sales Order", () => {
				let hotel_settings = frappe.get_doc("Hotel Settings", "Hotel Settings");
				let sales_order = frappe.model.get_new_doc("Sales Order");
				sales_order.customer = frm.doc.customer || hotel_settings.default_customer;
				if (hotel_settings.default_invoice_naming_series) {
					sales_order.naming_series = hotel_settings.default_invoice_naming_series;
				}
				for (let d of frm.doc.items) {
					let invoice_item = frappe.model.add_child(invoice, "items")
					invoice_item.item_code = d.item;
					invoice_item.qty = d.qty;
					invoice_item.rate = d.rate;
				}
				if (hotel_settings.default_taxes_and_charges) {
					invoice.taxes_and_charges = hotel_settings.default_taxes_and_charges;
				}
				frappe.set_route("Form", invoice.doctype, invoice.name);
			});
		});
	},
	make_invoice: function (frm) {
		frappe.model.with_doc("Hotel Settings", "Hotel Settings", () => {
			frappe.model.with_doctype("Sales Invoice", () => {
				let hotel_settings = frappe.get_doc("Hotel Settings", "Hotel Settings");
				let invoice = frappe.model.get_new_doc("Sales Invoice");
				invoice.customer = frm.doc.customer || hotel_settings.default_customer;
				if (hotel_settings.default_invoice_naming_series) {
					invoice.naming_series = hotel_settings.default_invoice_naming_series;
				}
				for (let d of frm.doc.items) {
					let invoice_item = frappe.model.add_child(invoice, "items")
					invoice_item.item_code = d.item;
					invoice_item.qty = d.qty;
					invoice_item.rate = d.rate;
				}
				if (hotel_settings.default_taxes_and_charges) {
					invoice.taxes_and_charges = hotel_settings.default_taxes_and_charges;
				}
				frappe.set_route("Form", invoice.doctype, invoice.name);
			});
		});
	}
});

frappe.ui.form.on('Hotel Room Reservation Item', {
	from_date: function (frm, cdt, cdn) {
		let item = locals[cdt][cdn];
		if (item.from_date && item.to_date && item.room_count) {
			let days = frappe.datetime.get_diff(item.to_date, item.from_date);
			item.qty = days * item.room_count;
			frm.refresh_field("items")
		}

	},
	to_date: function (frm, cdt, cdn) {
		let item = locals[cdt][cdn];
		if (item.from_date && item.to_date && item.room_count) {
			let days = frappe.datetime.get_diff(item.to_date, item.from_date);
			item.qty = days * item.room_count;
			frm.refresh_field("items")
		}
	},
	room_count: function (frm, cdt, cdn) {
		let item = locals[cdt][cdn];
		if (item.from_date && item.to_date && item.room_count) {
			let days = frappe.datetime.get_diff(item.to_date, item.from_date);
			item.qty = days * item.room_count;
			frm.refresh_field("items")
		}
	},
	item: function (frm, doctype, name) {
		frm.trigger("recalculate_rates");
	},
	qty: function (frm) {
		frm.trigger("recalculate_rates");
	}
});
