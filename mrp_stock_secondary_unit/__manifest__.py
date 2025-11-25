# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "MRP Stock Secondary Unit",
    "summary": "Transfer secondary unit from manufacturing orders to stock moves",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "license": "AGPL-3",
    "author": "Aceleradora, Odoo Community Association (OCA)",
    "website": "https://github.com/aceleradora-la/manufacture",
    "depends": ["mrp_production_secondary_unit", "stock"],
    "data": [
        "views/stock_move_views.xml",
    ],
    "installable": True,
    "application": False,
}

