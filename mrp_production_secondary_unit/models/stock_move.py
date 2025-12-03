# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    secondary_uom_id = fields.Many2one(
        comodel_name="product.secondary.unit",
        string="Secondary UoM",
        domain="[('product_tmpl_id', '=', product_id.product_tmpl_id)]",
    )
    secondary_uom_qty = fields.Float(
        string="Secondary Quantity",
        digits="Product Unit of Measure",
        compute="_compute_secondary_uom_qty",
        store=True,
        readonly=False,
    )

    @api.depends("product_uom_qty", "product_uom", "secondary_uom_id")
    def _compute_secondary_uom_qty(self):
        """Compute secondary quantity based on primary quantity and conversion factor."""
        for move in self:
            if not move.secondary_uom_id or not move.product_uom_qty:
                move.secondary_uom_qty = 0.0
                continue
            # Get the factor from secondary unit
            factor = move.secondary_uom_id.factor
            secondary_uom_record = move.secondary_uom_id.uom_id
            # Convert from product UoM to secondary UoM base, then apply factor
            if move.product_uom.category_id == secondary_uom_record.category_id:
                # Same UoM category, convert using UoM conversion
                converted_qty = move.product_uom._compute_quantity(
                    move.product_uom_qty, secondary_uom_record
                )
                move.secondary_uom_qty = converted_qty * factor
            else:
                # Different UoM category, cannot convert directly
                move.secondary_uom_qty = 0.0

    @api.onchange("product_id")
    def _onchange_product_id_secondary_unit(self):
        """Set secondary unit when product changes."""
        if self.product_id:
            secondary_uom = self.product_id.product_tmpl_id.secondary_uom_ids[:1]
            if secondary_uom:
                self.secondary_uom_id = secondary_uom
        else:
            self.secondary_uom_id = False
            self.secondary_uom_qty = 0.0

    @api.onchange("product_uom_qty", "product_uom")
    def _onchange_product_uom_qty_secondary_unit(self):
        """Recalculate secondary quantity when primary quantity changes."""
        if self.secondary_uom_id and self.product_uom_qty:
            self._compute_secondary_uom_qty()

    @api.onchange("secondary_uom_id", "secondary_uom_qty")
    def _onchange_secondary_uom(self):
        """Update primary quantity when secondary quantity changes manually."""
        # Only update if this is a manual change, not from compute field recalculation
        # Skip if we're in a context that indicates automatic recalculation
        if self.env.context.get('skip_secondary_uom_onchange'):
            return
        # Don't update if product_uom_qty is 0 or not set (likely being recalculated)
        if not self.product_uom_qty:
            return
        if self.secondary_uom_id and self.secondary_uom_qty:
            factor = self.secondary_uom_id.factor
            secondary_uom_record = self.secondary_uom_id.uom_id
            # Convert from secondary UoM to product UoM
            if self.product_uom.category_id == secondary_uom_record.category_id:
                # Calculate expected secondary_qty from current product_uom_qty
                expected_secondary_qty = self.product_uom._compute_quantity(
                    self.product_uom_qty, secondary_uom_record
                ) * factor
                # Only update if secondary_uom_qty differs significantly (manual change)
                # This prevents circular updates when compute field recalculates
                # Also check if the difference is large enough to indicate manual change
                diff = abs(self.secondary_uom_qty - expected_secondary_qty)
                # Use a larger threshold to avoid false positives during recalculation
                if diff > max(0.0001, expected_secondary_qty * 0.01):
                    # Manual change detected, update product_uom_qty
                    base_qty = self.secondary_uom_qty / factor
                    self.product_uom_qty = secondary_uom_record._compute_quantity(
                        base_qty, self.product_uom
                    )

