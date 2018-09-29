// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hotel Room Reservation', {

	onload: function (frm) {
		frm.fields_dict['room'].get_query = function (doc, cdt, cdn) {
			return {
				query: "erpnext.hotels.utils.get_available_rooms",
				filters: { 'from_date': doc.from_date, 'to_date': doc.to_date, 'item': doc.item }
			}
		}
	},

	refresh: function (frm) {
		if (frm.is_new()) {
			erpnext.hotels.hotel_room_reservation.set_default_values(frm);
		}

		erpnext.hotels.hotel_room_reservation.setup_custom_actions(frm);

	},

	validate: function (frm) {
		if (frm.doc.room && !frm.doc.room_status) {
			frm.set_value("room_status", "Booked");
		}
	},

	from_date: function (frm) {
		erpnext.hotels.hotel_room_reservation.recalculate_rates(frm);
	},

	to_date: function (frm) {
		erpnext.hotels.hotel_room_reservation.recalculate_rates(frm);
	},

	item: function (frm) {
		// let days = frappe.datetime.get_diff(frm.doc.to_date, frm.doc.from_date);
		//TODO: Prevent change if room already checked in, because rates will be affected
	},


});

frappe.ui.form.on('Hotel Room Reservation Item', {

	item: function (frm, doctype, name) {
		erpnext.hotels.hotel_room_reservation.recalculate_rates(frm);
	},

	qty: function (frm) {
		erpnext.hotels.hotel_room_reservation.recalculate_rates(frm);
	}

});

frappe.provide('erpnext.hotels');

erpnext.hotels.hotel_room_reservation = {

	set_default_values: function (frm) {
		frm.set_value("from_date", frappe.datetime.nowdate());
		frm.set_value("to_date", frappe.datetime.add_days(frappe.datetime.nowdate(), 1));

		frm.set_value("guest_name", "Test Customer 1");
		frm.set_value("customer", "Darshanarthi");
		frm.set_value("company", frappe.defaults.get_default('company'));
	},

	setup_custom_actions: (frm) => {

		if (frm.doc.item && frm.doc.room) {
			if (frm.doc.room_status == "Booked") {
				frm.page.add_action_item(__("Check In"), function () {
					erpnext.hotels.hotel_room_reservation.checkin(frm);
				});
			}
			if (frm.doc.room_status === "Checked In") {
				frm.page.add_action_item(__("Check Out"), function () {
					erpnext.hotels.hotel_room_reservation.checkout(frm);
				});
			}
		}

		frm.page.add_action_item(__("Add to Group"), function () {
			erpnext.hotels.hotel_room_reservation.show_group_dialog(frm);
		});

		if (!frm.doc.sales_invoice) {
			frm.page.add_action_item(__("Make Invoice"), function () {
				erpnext.hotels.hotel_room_reservation.make_sales_invoice(frm);
			});
		}

		frm.page.add_action_item(__("Cancel Reservation"), function () {
			erpnext.hotels.hotel_room_reservation.cancel_reservation(frm);
		});
	},

	checkin: (frm) => {
		if (!frm.doc.room) {
			frappe.msgprint(__("Please select a room for reservation."))
			return;
		}
		frm.set_value('room_status', 'Checked In');
		let days = frappe.datetime.get_diff(frm.doc.to_date, frm.doc.from_date);
		frm.add_child("items", {
			"item": frm.doc.item,
			"qty": days
		})
		frm.refresh_field("items");
		erpnext.hotels.hotel_room_reservation.recalculate_rates(frm);
	},

	checkout: (frm) => {
		console.log('');
		frappe.call({
			"method": "erpnext.hotels.doctype.hotel_room_reservation.hotel_room_reservation.checkout",
			"args": { "hotel_room_reservation": frm.doc, is_group: 0 }
		}).done((r) => {
			frm.set_value("room_status", "Checked Out");
			frappe.run_serially([
				() => frm.set_value("net_total", r.message.net_total),
				() => frm.refresh_field("items")
			]);
		});
	},

	recalculate_rates: (frm) => {

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

	make_sales_invoice: function (frm) {
		// Using this instead of make_invoice. make_invoice not setting default values in Sales Invoice.	
		frappe.model.open_mapped_doc({
			method: "erpnext.hotels.doctype.hotel_room_reservation.hotel_room_reservation.make_sales_invoice",
			frm: frm
		})
	},

}



