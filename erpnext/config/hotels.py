from __future__ import unicode_literals
from frappe import _


def get_data():

    return [
        {
            "label": _("Front Desk"),
            "icon": "icon-star",
                    "items": [
                {
                    "type": "doctype",
                    "name": "Guest",
                    "label": _("Guest"),
                },
                {
                    "type": "doctype",
                    "name": "Hotel Room Reservation",
                    "label": _("Hotel Room Reservation"),
                }


            ]
        },
        {
            "label": _("Masters"),
            "icon": "icon-list",
                    "items": [
                {
                    "type": "doctype",
                    "name": "Hotel Room",
                    "label": _("Hotel Room"),
                },
                        {
                    "type": "doctype",
                    "name": "Hotel Room Amenity",
                    "label": _("Hotel Room Amenity"),
                },
                        {
                    "type": "doctype",
                    "name": "Hotel Room Package",
                    "label": _("Hotel Room Package"),
                },
                        {
                    "type": "doctype",
                    "name": "Hotel Room Pricing",
                    "label": _("Hotel Room Pricing"),
                },
                        {
                    "type": "doctype",
                    "name": "Hotel Room Pricing Package",
                    "label": _("Hotel Room Pricing Package"),
                }

            ]
        },
        {
            "label": _("Setup"),
            "icon": "icon-cog",
                    "items": [
                {
                    "type": "doctype",
                    "name": "Hotel Settings",
                    "label": _("Hotel Settings"),
                }
            ]
        }
    ]
