# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "MRP Production Secondary Unit",
    "summary": "Adds secondary unit of measure to Manufacturing Orders",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "website": "https://github.com/OCA/manufacture",
    "author": "Aceleradora, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mrp",
        "product_secondary_unit",
    ],
    "data": [
        "views/mrp_production_views.xml",
        "views/mrp_production_pivot_views.xml",
        "views/mrp_unbuild_views.xml",
        "views/stock_move_views.xml",
    ],
}

