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
        readonly=False,
    )

    def _calculate_secondary_uom_qty(self):
        """Calculate secondary quantity based on primary quantity and conversion factor."""
        if not self.secondary_uom_id or not self.product_uom_qty:
            return 0.0
        # Get the factor from secondary unit
        factor = self.secondary_uom_id.factor
        secondary_uom_record = self.secondary_uom_id.uom_id
        # Convert from product UoM to secondary UoM base, then apply factor
        if self.product_uom.category_id == secondary_uom_record.category_id:
            # Same UoM category, convert using UoM conversion
            converted_qty = self.product_uom._compute_quantity(
                self.product_uom_qty, secondary_uom_record
            )
            return converted_qty * factor
        else:
            # Different UoM category, cannot convert directly
            return 0.0

    @api.onchange("product_id")
    def _onchange_product_id_secondary_unit(self):
        """Set secondary unit when product changes."""
        if self.product_id:
            secondary_uom = self.product_id.product_tmpl_id.secondary_uom_ids[:1]
            if secondary_uom:
                self.secondary_uom_id = secondary_uom
                # Calculate secondary_uom_qty if product_uom_qty is available
                if self.product_uom_qty:
                    self.secondary_uom_qty = self._calculate_secondary_uom_qty()
        else:
            self.secondary_uom_id = False
            self.secondary_uom_qty = 0.0


