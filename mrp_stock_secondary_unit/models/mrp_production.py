# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


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
        """Transfer secondary unit info to raw material moves."""
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
                # Calculate secondary quantity using product_secondary_unit mixin logic
                # The calculation will be done by stock.move using the mixin
        return values

    def _get_move_finished_values(
        self,
        product_id,
        product_uom_qty,
        product_uom,
        operation_id=False,
        **kwargs
    ):
        """Transfer secondary unit info to finished product and byproduct moves."""
        # Get byproduct_id from kwargs if present (for byproducts)
        byproduct_id = kwargs.get('byproduct_id', False)
        cost_share = kwargs.get('cost_share', 0)
        
        # Call super - only pass parameters that standard Odoo accepts
        try:
            values = super()._get_move_finished_values(
                product_id=product_id,
                product_uom_qty=product_uom_qty,
                product_uom=product_uom,
                operation_id=operation_id,
                byproduct_id=byproduct_id,
                cost_share=cost_share,
            )
        except TypeError:
            # Fallback: standard Odoo only accepts 4 parameters
            values = super()._get_move_finished_values(
                product_id=product_id,
                product_uom_qty=product_uom_qty,
                product_uom=product_uom,
                operation_id=operation_id,
            )
        
        # Get product record (product_id can be an ID or a record)
        if isinstance(product_id, int):
            product = self.env["product.product"].browse(product_id)
        else:
            product = product_id
        
        # For byproducts, get secondary unit from byproduct product itself
        if byproduct_id:
            if product and hasattr(product.product_tmpl_id, "secondary_uom_ids"):
                secondary_uom = product.product_tmpl_id.secondary_uom_ids[:1]
                if secondary_uom:
                    values["secondary_uom_id"] = secondary_uom.id
                    # The calculation will be done by stock.move using the mixin
        # For main finished product, transfer secondary unit from production order
        elif product and product.id == self.product_id.id and self.secondary_uom_id:
            values["secondary_uom_id"] = self.secondary_uom_id.id
            if self.secondary_uom_qty:
                values["secondary_uom_qty"] = self.secondary_uom_qty
        return values
