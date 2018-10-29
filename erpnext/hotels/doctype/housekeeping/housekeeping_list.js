frappe.listview_settings['Housekeeping'] = {

	filters: [["room_status", "=", "Dirty"]],

	onload: function (list_view) {
		let method = "erpnext.hotels.doctype.housekeeping.housekeeping.update_room_status"

		list_view.page.add_actions_menu_item(__("Mark as Clean"), function () {
			list_view.call_for_selected_items(method, { status: "Clean" });

		});
	},

}