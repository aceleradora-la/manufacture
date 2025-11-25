# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "MRP Production Secondary Unit",
    "summary": "Add secondary unit of measure for manufacturing orders",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "license": "AGPL-3",
    "author": "Aceleradora, Odoo Community Association (OCA)",
    "website": "https://github.com/aceleradora-la/manufacture",
    "depends": ["mrp", "product_secondary_unit"],
    "data": [
        "views/mrp_production_views.xml",
    ],
    "installable": True,
    "application": False,
}

