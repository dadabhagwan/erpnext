frappe.listview_settings['Night Audit'] = {

    filters: [["room_status", "=", "Dirty"]],

    onload: function (list_view) {
        list_view.page.add_inner_button("Make Night Audit",
            function () {
                frappe.call({
                    method: "erpnext.hotels.doctype.night_audit.night_audit.make_night_audit",
                    args: {
                        audit_date: frappe.datetime.get_today(),
                        company: frappe.defaults.get_default('company')
                    },
                    callback: function (r) {
                        frappe.set_route('Form', 'Night Audit', r.message);
                    }
                });
            });
    },

}