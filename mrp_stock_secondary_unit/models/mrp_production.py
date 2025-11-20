# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _get_move_raw_values(
        self,
        product,
        product_uom_qty,
        product_uom,
        operation_id=False,
        bom_line=False,
    ):
        """Add secondary unit info to raw material moves."""
        values = super()._get_move_raw_values(
            product=product,
            product_uom_qty=product_uom_qty,
            product_uom=product_uom,
            operation_id=operation_id,
            bom_line=bom_line,
        )
        # Get secondary unit from product if available
        if product and hasattr(product.product_tmpl_id, "secondary_uom_ids"):
            secondary_uom = product.product_tmpl_id.secondary_uom_ids[:1]
            if secondary_uom:
                values["secondary_uom_id"] = secondary_uom.id
                if secondary_uom.factor:
                    values["secondary_uom_qty"] = product_uom_qty / secondary_uom.factor
        return values

    def _get_move_finished_values(
        self,
        product_id,
        product_uom_qty,
        product_uom,
        operation_id=False,
    ):
        """Add secondary unit info to finished product moves."""
        values = super()._get_move_finished_values(
            product_id=product_id,
            product_uom_qty=product_uom_qty,
            product_uom=product_uom,
            operation_id=operation_id,
        )
        # Transfer secondary unit from production order
        if self.secondary_uom_id:
            values["secondary_uom_id"] = self.secondary_uom_id.id
            if self.secondary_uom_qty:
                values["secondary_uom_qty"] = self.secondary_uom_qty
            elif self.secondary_uom_id.factor:
                values["secondary_uom_qty"] = product_uom_qty / self.secondary_uom_id.factor
        return values

