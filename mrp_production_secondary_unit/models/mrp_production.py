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
        if hasattr(self.product_id.product_tmpl_id, "secondary_uom_ids"):
            secondary_uom = self.product_id.product_tmpl_id.secondary_uom_ids[:1]
            if secondary_uom:
                self.secondary_uom_id = secondary_uom
                # Don't calculate quantity here - wait until confirmation
                self.secondary_uom_qty = 0.0

    def _compute_secondary_uom_qty(self):
        """Compute secondary quantity from product quantity."""
        for production in self:
            if (
                production.secondary_uom_id
                and production.product_qty
                and production.secondary_uom_id.factor
            ):
                # Convert from primary to secondary: multiply by factor
                # Example: 6 Maple * 30 = 180 Huevos
                production.secondary_uom_qty = (
                    production.product_qty * production.secondary_uom_id.factor
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

