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
		};

		frm.fields_dict['room'].get_query = function (doc, cdt, cdn) {
			return {
				query: "erpnext.hotels.utils.get_available_rooms",
				filters: { 'from_date': doc.from_date, 'to_date': doc.to_date, 'item': doc.item }
			}
		};

		frm.set_query("item", "items", function (doc, cdt, cdn) {
			return {
				filters: [["item_group", "=", "Services"]]
			}
		});
	},

	refresh: function (frm) {
		if (frm.is_new()) {
			erpnext.hotels.hotel_room_reservation.set_default_values(frm);
		} else if (frm.doc.status == "Completed") {
			frm.set_read_only();
			frm.fields_dict["items"].df.read_only = 1;
			frm.set_intro(__("This reservation is 'Completed' and cannot be edited."));
			frm.refresh_fields();
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

	},

	get_item_data: function (frm, item) {
		frm.call({
			method: "erpnext.stock.get_item_details.get_item_details",
			child: item,
			args: {
				args: {
					item_code: item.item,
					doctype: "Sales Invoice",
					price_list: frappe.defaults.get_default('selling_price_list'),
					currency: frappe.defaults.get_default('Currency'),
					price_list_currency: frappe.defaults.get_default('Currency'),
					company: "DBF",
					qty: item.qty || 1,
					company: frm.doc.company,
					conversion_rate: 1,
					customer: frm.doc.customer,
					is_pos: 0,
				}
			},
			callback: function (r) {
				console.log(r);
				item.rate = r.message.price_list_rate;
				item.amount = item.rate * (item.qty || 1)
				frm.refresh_field("items");
			}
		});
	},

});

frappe.ui.form.on('Hotel Room Reservation Item', {

	item: function (frm, doctype, name) {
		const item = locals[doctype][name];
		frm.events.get_item_data(frm, item);
		erpnext.hotels.hotel_room_reservation.recalculate_rates(frm);
	},

	qty: function (frm, doctype, name) {
		const item = locals[doctype][name];
		if (!item.rate) {
			frm.events.get_item_data(frm, item);
		}
		item.amount = item.rate * item.qty;
		erpnext.hotels.hotel_room_reservation.recalculate_rates(frm);
	},


});

frappe.provide('erpnext.hotels');

erpnext.hotels.hotel_room_reservation = {

	set_default_values: function (frm) {
		// frm.set_value("from_date", frappe.datetime.nowdate());
		// frm.set_value("to_date", frappe.datetime.add_days(frappe.datetime.nowdate(), 1));
		frm.set_value("company", frappe.defaults.get_default('company'));
	},

	setup_custom_actions: (frm) => {

		if (frm.doc.item && frm.doc.room) {
			if (frm.doc.room_status == "Booked") {
				frm.page.add_action_item(__("Check In"), function () {
					erpnext.hotels.hotel_room_reservation.checkin(frm);
				});
			}

			if (frm.doc.status == "In House" && frm.doc.room_status === "Checked In") {

				frm.page.add_action_item(__("Check Out"), function () {
					erpnext.hotels.hotel_room_reservation.checkout(frm);
				});


				if (frm.doc.from_date == frappe.datetime.get_today() && !frm.doc.sales_invoice)
					frm.page.add_action_item(__("Cancel Check In"), function () {
						erpnext.hotels.hotel_room_reservation.cancel_checkin(frm);
					});
			}

		}

		if (!frm.doc.sales_invoice) {
			frm.page.add_action_item(__("Make Invoice"), function () {
				erpnext.hotels.hotel_room_reservation.make_sales_invoice(frm);
			});
		}

		if (!frm.doc.sales_invoice && frm.doc.status == 'Booked') {
			frm.page.add_action_item(__("Cancel Reservation"), function () {
				erpnext.hotels.hotel_room_reservation.cancel_reservation(frm);
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

	checkin: (frm) => {
		if (!frm.doc.room) {
			frappe.msgprint(__("Please select a room for reservation."))
			return;
		}

		frappe.run_serially([
			() => {
				frappe.model.with_doc('Hotel Settings')
					.then((doc) => {
						if (doc.default_checkin_time > frappe.datetime.now_time()) {
							frappe.confirm(
								__('Early Checkin. Do you wish to apply charges for yesterday?'),
								function () {
									let room_date = frappe.datetime.add_days(frappe.datetime.get_today(), -1);
									erpnext.hotels.hotel_room_reservation.add_room_charge(frm, room_date, 1);
								}
							);
						}
					});
			},
			() => {
				let room_date = frappe.datetime.get_today();
				erpnext.hotels.hotel_room_reservation.add_room_charge(frm, room_date, 1);
			},
			() => {
				frm.set_value("checkin_date", frappe.datetime.now_datetime())
				frm.set_value('status', 'In House');
				frm.set_value('room_status', 'Checked In');
			},
		])
	},


	checkout: (frm) => {

		frappe.run_serially([
			() => {
				if (cur_frm.doc.checkin_date < frappe.datetime.get_today()) {
					frappe.model.with_doc('Hotel Settings')
						.then((doc) => {
							if (doc.default_checkout_time < frappe.datetime.now_time()) {
								frappe.confirm(
									__('Late Checkout. Do you wish to apply charges for today?'),
									function () {
										erpnext.hotels.hotel_room_reservation.add_room_charge(frm, frappe.datetime.get_today(), 1);
									}
								);
							}
						});
				};
			},
			() => {
				frm.set_value("checkout_date", frappe.datetime.now_datetime())
				frm.set_value('status', 'Completed');
				frm.set_value('room_status', 'Checked Out');
			}
		]);

	},


	cancel_checkin: (frm) => {
		debugger;

		//remove room charge for the day
		var index = -1;
		for (var j = 0; j < frm.doc.items.length; j++) {
			if (frm.doc.items[j].date == frappe.datetime.get_today() && frm.doc.item == frm.doc.items[j].item) {
				index = j;
			}
		}
		if (index > -1) {
			frm.doc.items.splice(index, 1);
			frm.get_field("items").grid.grid_rows[index].remove();
		}
		frm.set_value('room', null);
		frm.set_value('room_status', null);

		frm.refresh_field("items");
		erpnext.hotels.hotel_room_reservation.recalculate_rates(frm);
	},


	settle: (frm) => {
		frappe.call({
			"method": "erpnext.hotels.doctype.hotel_room_reservation.hotel_room_reservation.settle",
			"args": { "hotel_room_reservation": frm.doc }
		}).done((r) => {
			var doc = frappe.model.sync(r.message)[0];
			frm.set_value("status", "Due Out");
		});
	},

	add_room_charge: function (frm, date, qty) {
		// let days = frappe.datetime.get_diff(frm.doc.to_date, frm.doc.from_date);
		frm.add_child("items", {
			"date": date,
			"item": frm.doc.item,
			"qty": qty
		})
		frm.refresh_field("items");
		erpnext.hotels.hotel_room_reservation.recalculate_rates(frm);
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

		frappe.call({
			"method": "erpnext.hotels.doctype.hotel_room_reservation.hotel_room_reservation.get_group",
			"args": { "reservation": frm.doc.group_id }
		}).then((r) => {
			let template = erpnext.hotels.hotel_room_reservation.get_summary_template();
			d.get_field("summary_html").$wrapper.append(frappe.render_template(template, { "group": r.message, "frm": frm }));
			d.show();
		});
	},

	get_summary_template: function (frm) {
		return `
			<table class="table table-bordered small">
				<thead>
					<tr>
						<td style="width: 10%">{{ __("Res Id") }}</td>
						<td style="width: 25%">{{ __("Item") }}</td>
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
						<td> <a class="invoice-link" href="/desk#Form/Hotel Room Reservation/{{ d.name }}">{{ parseInt(d.name.slice(4)) }}</a> </td>
						<td> {{ d.item }} </td>
						<td> {{ d.room }} </td>
						<td> {{ d.room_status }} </td>
						<td> {{ d.from_date }} </td>
						<td> {{ d.to_date }} </td>
						<td class="text-right"> {{ format_currency(d.amount, "INR", 2) }} </td>
					</div>
					{% }); %}
				</tbody>
			</table>

		`;
	}
}



