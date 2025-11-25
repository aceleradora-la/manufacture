# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    secondary_uom_id = fields.Many2one(
        comodel_name="product.secondary.unit",
        string="Secondary UoM",
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
        help="Secondary unit of measure for the product to produce",
    )
    secondary_uom_qty = fields.Float(
        string="Secondary Qty",
        digits="Product Unit of Measure",
        help="Quantity in secondary unit of measure",
        store=True,
    )

    @api.onchange("product_id")
    def _onchange_product_id_secondary_unit(self):
        """Set secondary unit when product changes (but don't calculate quantity yet)."""
        if not self.product_id:
            self.secondary_uom_id = False
            self.secondary_uom_qty = 0.0
            return
        # Get secondary unit from product template if available
        # Only set the unit, don't calculate quantity until confirmation
        # Use safe access to avoid errors during record creation
        try:
            product_tmpl = self.product_id.product_tmpl_id
            if product_tmpl and hasattr(product_tmpl, "secondary_uom_ids"):
                secondary_uom = product_tmpl.secondary_uom_ids[:1]
                if secondary_uom:
                    self.secondary_uom_id = secondary_uom
                    # Don't calculate quantity here - wait until confirmation
                    self.secondary_uom_qty = 0.0
        except Exception:
            # If there's any error accessing the product, just clear the fields
            self.secondary_uom_id = False
            self.secondary_uom_qty = 0.0

    def _compute_secondary_uom_qty(self):
        """Compute secondary quantity from product quantity, considering UoM conversion."""
        for production in self:
            if (
                production.secondary_uom_id
                and production.product_qty
                and production.secondary_uom_id.factor
            ):
                # Get the UoM used in the production order
                order_uom = production.product_uom_id or production.product_id.uom_id
                # Get the base UoM of the product
                base_uom = production.product_id.uom_id
                # Get the secondary UoM
                secondary_uom = production.secondary_uom_id.uom_id
                
                # Convert quantity from order UoM to base UoM
                qty_in_base_uom = order_uom._compute_quantity(
                    production.product_qty, base_uom, rounding_method='HALF-UP'
                )
                
                # If secondary UoM is the same as order UoM, factor is 1
                if secondary_uom.id == order_uom.id:
                    production.secondary_uom_qty = production.product_qty
                # If secondary UoM is the same as base UoM, use the factor directly
                elif secondary_uom.id == base_uom.id:
                    # Factor is defined relative to base UoM, so if secondary = base, factor should be 1
                    production.secondary_uom_qty = qty_in_base_uom
                else:
                    # Convert from base UoM to secondary UoM using the factor
                    # Factor is defined as: 1 base UoM = factor secondary UoM
                    production.secondary_uom_qty = (
                        qty_in_base_uom * production.secondary_uom_id.factor
                    )
            else:
                production.secondary_uom_qty = 0.0

    @api.model
    def create(self, vals):
        """Compute secondary quantity on create."""
        production = super().create(vals)
        if production.secondary_uom_id and not production.secondary_uom_qty:
            production._compute_secondary_uom_qty()
        return production

    def write(self, vals):
        """Don't auto-compute secondary quantity on write during editing."""
        # Only compute if explicitly requested or if order is confirmed
        res = super().write(vals)
        # Don't auto-calculate during editing - only on confirmation
        return res

    def action_confirm(self):
        """Calculate secondary unit quantity when confirming the order."""
        res = super().action_confirm()
        for production in self:
            # Calculate secondary quantity only when confirming
            if production.secondary_uom_id and production.product_qty:
                production._compute_secondary_uom_qty()
        return res

    def _get_move_finished_values(
        self,
        product_id,
        product_uom_qty,
        product_uom,
        operation_id=False,
    ):
        """Add secondary unit info to finished product move."""
        values = super()._get_move_finished_values(
            product_id=product_id,
            product_uom_qty=product_uom_qty,
            product_uom=product_uom,
            operation_id=operation_id,
        )
        if self.secondary_uom_id:
            values["secondary_uom_id"] = self.secondary_uom_id.id
            if self.secondary_uom_qty:
                values["secondary_uom_qty"] = self.secondary_uom_qty
        return values

