# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _get_move_raw_values(
        self,
        product_id,
        product_uom_qty,
        product_uom,
        operation_id=False,
        bom_line=False,
    ):
        """Add secondary unit info to raw material moves."""
        values = super()._get_move_raw_values(
            product_id,
            product_uom_qty,
            product_uom,
            operation_id=operation_id,
            bom_line=bom_line,
        )
        # Get secondary unit from product if available
        # product_id can be an ID or a recordset
        if isinstance(product_id, (int,)):
            product = self.env["product.product"].browse(product_id)
        else:
            product = product_id
        if product and hasattr(product.product_tmpl_id, "secondary_uom_ids"):
            secondary_uom = product.product_tmpl_id.secondary_uom_ids[:1]
            if secondary_uom:
                values["secondary_uom_id"] = secondary_uom.id
        return values

    def _get_move_finished_values(
        self,
        product_id,
        product_uom_qty,
        product_uom,
        operation_id=False,
        byproduct_id=False,
        cost_share=0,
    ):
        """Add secondary unit info to finished product moves."""
        values = super()._get_move_finished_values(
            product_id,
            product_uom_qty,
            product_uom,
            operation_id=operation_id,
            byproduct_id=byproduct_id,
            cost_share=cost_share,
        )
        
        # For main finished product, use production order secondary unit
        if not byproduct_id and self.secondary_uom_id:
            values["secondary_uom_id"] = self.secondary_uom_id.id
            # secondary_uom_qty will be computed automatically based on product_uom_qty
        # For byproducts, get from product
        elif byproduct_id:
            # product_id can be an ID or a recordset
            if isinstance(product_id, (int,)):
                product = self.env["product.product"].browse(product_id)
            else:
                product = product_id
            if product and hasattr(product.product_tmpl_id, "secondary_uom_ids"):
                secondary_uom = product.product_tmpl_id.secondary_uom_ids[:1]
                if secondary_uom:
                    values["secondary_uom_id"] = secondary_uom.id
        return values

