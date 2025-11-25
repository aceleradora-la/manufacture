# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    secondary_uom_id = fields.Many2one(
        comodel_name="product.secondary.unit",
        string="Secondary UoM",
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
        help="Secondary unit of measure",
    )
    secondary_uom_qty = fields.Float(
        string="Secondary Qty",
        digits="Product Unit of Measure",
        help="Quantity in secondary unit of measure",
    )

    @api.onchange("product_id", "product_uom_qty")
    def _onchange_product_id_secondary_unit(self):
        """Update secondary unit when product or quantity changes."""
        if not self.product_id:
            self.secondary_uom_id = False
            self.secondary_uom_qty = 0.0
            return
        # For raw materials, get secondary unit from product
        if self.raw_material_production_id:
            if hasattr(self.product_id.product_tmpl_id, "secondary_uom_ids"):
                secondary_uom = self.product_id.product_tmpl_id.secondary_uom_ids[:1]
                if secondary_uom:
                    self.secondary_uom_id = secondary_uom
                    self._compute_secondary_uom_qty()
        # For finished products and byproducts, get from production order or product
        elif self.production_id:
            # Check if it's a byproduct (different from main product)
            if self.product_id != self.production_id.product_id:
                # For byproducts, get secondary unit from product
                if hasattr(self.product_id.product_tmpl_id, "secondary_uom_ids"):
                    secondary_uom = self.product_id.product_tmpl_id.secondary_uom_ids[:1]
                    if secondary_uom:
                        self.secondary_uom_id = secondary_uom
                        self._compute_secondary_uom_qty()
            # For main finished product, get from production order
            elif hasattr(self.production_id, "secondary_uom_id") and self.production_id.secondary_uom_id:
                self.secondary_uom_id = self.production_id.secondary_uom_id.id
                if self.production_id.secondary_uom_qty:
                    self.secondary_uom_qty = self.production_id.secondary_uom_qty

    @api.onchange("secondary_uom_id", "secondary_uom_qty")
    def _onchange_secondary_uom(self):
        """Update product quantity when secondary unit changes."""
        if self.secondary_uom_id and self.secondary_uom_qty:
            factor = self.secondary_uom_id.factor
            if factor:
                # Convert from secondary to primary: divide by factor
                # Example: 180 Huevos / 30 = 6 Maple
                self.product_uom_qty = self.secondary_uom_qty / factor

    def _compute_secondary_uom_qty(self):
        """Compute secondary quantity from product quantity."""
        for move in self:
            if (
                move.secondary_uom_id
                and move.product_uom_qty
                and move.secondary_uom_id.factor
            ):
                # Convert from primary to secondary: multiply by factor
                # Example: 6 Maple * 30 = 180 Huevos
                move.secondary_uom_qty = (
                    move.product_uom_qty * move.secondary_uom_id.factor
                )
            else:
                move.secondary_uom_qty = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """Compute secondary quantity on create."""
        moves = super().create(vals_list)
        for move in moves:
            if move.secondary_uom_id and not move.secondary_uom_qty:
                move._compute_secondary_uom_qty()
        return moves

    def write(self, vals):
        """Compute secondary quantity on write."""
        res = super().write(vals)
        if "product_uom_qty" in vals and not vals.get("secondary_uom_qty"):
            for move in self:
                if move.secondary_uom_id:
                    move._compute_secondary_uom_qty()
        return res

