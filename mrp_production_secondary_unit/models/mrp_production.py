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

    @api.onchange("product_id", "product_qty")
    def _onchange_product_id_secondary_unit(self):
        """Update secondary unit when product or quantity changes."""
        if not self.product_id:
            self.secondary_uom_id = False
            self.secondary_uom_qty = 0.0
            return
        # Get secondary unit from product template if available
        if hasattr(self.product_id.product_tmpl_id, "secondary_uom_ids"):
            secondary_uom = self.product_id.product_tmpl_id.secondary_uom_ids[:1]
            if secondary_uom:
                self.secondary_uom_id = secondary_uom
                self._compute_secondary_uom_qty()

    @api.onchange("secondary_uom_id", "secondary_uom_qty")
    def _onchange_secondary_uom(self):
        """Update product quantity when secondary unit changes."""
        if self.secondary_uom_id and self.secondary_uom_qty:
            factor = self.secondary_uom_id.factor
            if factor:
                # Convert from secondary to primary: divide by factor
                # Example: 180 Huevos / 30 = 6 Maple
                self.product_qty = self.secondary_uom_qty / factor

    def _compute_secondary_uom_qty(self):
        """Compute secondary quantity from product quantity."""
        for production in self:
            if (
                production.secondary_uom_id
                and production.product_qty
                and production.secondary_uom_id.factor
            ):
                production.secondary_uom_qty = (
                    production.product_qty / production.secondary_uom_id.factor
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
        """Compute secondary quantity on write."""
        res = super().write(vals)
        if "product_qty" in vals and not vals.get("secondary_uom_qty"):
            for production in self:
                if production.secondary_uom_id:
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

