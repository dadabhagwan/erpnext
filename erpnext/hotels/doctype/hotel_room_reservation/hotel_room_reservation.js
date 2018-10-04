// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hotel Room Reservation', {

	onload: function (frm) {
		frm.fields_dict['item'].get_query = function (doc, cdt, cdn) {
			return {
				filters: [
					["Item", "item_group", "=", "Hotel Room Package"]
				]
			}
		}

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

		//group tools
		erpnext.hotels.hotel_room_reservation.add_group_buttons(frm);

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

	guest: function (frm) {

	}


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

		// frm.set_value("guest_name", "Test Customer 1");
		// frm.set_value("customer", "Darshanarthi");
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

		if (!frm.doc.sales_invoice) {
			frm.page.add_action_item(__("Make Invoice"), function () {
				erpnext.hotels.hotel_room_reservation.make_sales_invoice(frm);
			});
		}

		frm.page.add_action_item(__("Cancel Reservation"), function () {
			erpnext.hotels.hotel_room_reservation.cancel_reservation(frm);
		});
	},

	add_group_buttons: (frm) => {

		frm.page.add_inner_button(__("Add Rooms"), function () {
			erpnext.hotels.hotel_room_reservation.show_add_dialog(frm);
		}, __('Group'));

		if (frm.doc.group_id) {
			frm.page.add_inner_button(__("Show Group Summary"), function () {
				erpnext.hotels.hotel_room_reservation.show_group_summary(frm);
			}, __('Group'));
			// 
		}

	},

	show_add_dialog: (frm) => {

		let d = new frappe.ui.Dialog({
			title: __('Add Rooms to Group Reservation'),
			fields: [
				{
					"label": "Item",
					"fieldname": "item",
					"fieldtype": "Link",
					"options": "Item",
					"default": frm.doc.item,
					"reqd": 1,
				},
				{
					"label": "From",
					"fieldname": "from_date",
					"fieldtype": "Date",
					"default": frm.doc.from_date,
					"reqd": 1,
				},
				{
					"label": "To",
					"fieldname": "to_date",
					"fieldtype": "Date",
					"default": frm.doc.to_date,
					"reqd": 1,
				},
				{
					"label": "Qty",
					"fieldname": "qty",
					"fieldtype": "Int",
					"default": 1,
					"reqd": 1,
				}],

			primary_action_label: __('Add Rooms'),
			primary_action: function () {
				var data = d.get_values();

				let args = {
					'item': data.item,
					'qty': data.qty,
					'from_date': data.from_date,
					'to_date': data.to_date
				};

				frappe.call({
					doc: frm.doc,
					args: args,
					method: 'add_group_items',
				}).done((r) => {
					frm.reload_doc();
					d.hide();
				});

			}
		});
		d.show();
	},

	checkin_group: () => {
		let frm = this.frm;
		frappe.call({
			doc: frm.doc,
			method: "checkin_group",
		}).done((r) => {
			frm.reload_doc();
		});
	},

	checkin: (frm) => {
		debugger;
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
			|| !frm.doc.items || !frm.doc.items.length) {
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

	show_group_summary: (frm) => {
		let d = new frappe.ui.Dialog({
			title: __('Group Summary for {0}', [frm.doc.group_id]),
			fields: [{ "fieldtype": "HTML", "fieldname": "summary_html" }]
		});

		frappe.db.get_list('Hotel Room Reservation', {
			fields: ['name', 'item', 'from_date', 'to_date', 'net_total'],
			filters: { group_id: frm.doc.group_id },
			// or_filters: [['for_user', '=', frappe.session.user], ['for_user', '=', '']]
		}).then((group) => {
			let template = erpnext.hotels.hotel_room_reservation.get_summary_template();
			d.get_field("summary_html").$wrapper.append(frappe.render_template(template, { "group": group, "frm": frm }));
			d.show();
		});
	},

	get_summary_template: function (frm) {
		return `
			<table class="table table-bordered small">
				<thead>
					<tr>
						<td style="width: 18%">{{ __("Reservation Id") }}</td>
						<td style="width: 17%">{{ __("Item") }}</td>
						<td style="width: 10%">{{ __("Room") }}</td>
						<td style="width: 10%">{{ __("Status") }}</td>
						<td style="width: 15%">{{ __("From Date") }}</td>
						<td style="width: 15%">{{ __("To Date") }}</td>
						<td style="width: 15%" class="text-right">{{ __("Outstanding") }}</td>
					</tr>
				</thead>
				<tbody>
					{% $.each(group, (idx, d) => { %}
					<tr>
						<td> <a class="invoice-link" href="/desk#Form/Hotel Room Reservation/{{ d.name }}">{{ d.name }}</a> </td>
						<td> {{ d.item }} </td>
						<td> {{ d.room }} </td>
						<td> {{ d.room_status }} </td>
						<td> {{ d.from_date }} </td>
						<td> {{ d.to_date }} </td>
						<td class="text-right"> {{ format_currency(d.outstanding_amount, "INR", 2) }} </td>
					</div>
					{% }); %}
				</tbody>
			</table>
		<div class="text-right">						
			<button class="btn btn-default" onclick="erpnext.hotels.hotel_room_reservation.checkin_group();return false;">Check In</button>
			<button class="btn btn-danger">Check Out</button>
		</div>
		`;
	}
}



