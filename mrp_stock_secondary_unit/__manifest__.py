# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "MRP Stock Secondary Unit",
    "summary": "Transfer secondary unit of measure from Manufacturing Orders to Stock Moves",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "website": "https://github.com/OCA/manufacture",
    "author": "Aceleradora, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mrp",
        "mrp_production_secondary_unit",
        "product_secondary_unit",
    ],
    "data": [],
}

