# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    secondary_uom_id = fields.Many2one(
        comodel_name="product.secondary.unit",
        string="Secondary UoM",
        domain="[('product_tmpl_id', '=', product_id.product_tmpl_id)]",
    )
    secondary_uom_qty = fields.Float(
        string="Secondary Quantity",
        digits="Product Unit of Measure",
        compute="_compute_secondary_uom_qty",
        store=False,
        readonly=False,
    )

    @api.depends("product_qty", "product_uom_id", "secondary_uom_id")
    def _compute_secondary_uom_qty(self):
        """Compute secondary quantity based on primary quantity and conversion factor."""
        for production in self:
            if not production.secondary_uom_id or not production.product_qty:
                production.secondary_uom_qty = 0.0
                continue
            # Get the factor from secondary unit
            factor = production.secondary_uom_id.factor
            secondary_uom_record = production.secondary_uom_id.uom_id
            # Convert from product UoM to secondary UoM base, then apply factor
            if production.product_uom_id.category_id == secondary_uom_record.category_id:
                # Same UoM category, convert using UoM conversion
                converted_qty = production.product_uom_id._compute_quantity(
                    production.product_qty, secondary_uom_record
                )
                production.secondary_uom_qty = converted_qty * factor
            else:
                # Different UoM category, cannot convert directly
                production.secondary_uom_qty = 0.0

    def write(self, vals):
        """Override write to ensure secondary_uom_qty doesn't interfere with standard recalculation."""
        # If product_qty is being changed, temporarily remove it from vals to let Odoo recalculate first
        product_qty_val = vals.pop('product_qty', None) if 'product_qty' in vals else None
        
        # Write without product_qty first to let Odoo recalculate move_raw_ids
        result = super().write(vals)
        
        # Now update product_qty and let the compute field handle secondary_uom_qty
        if product_qty_val is not None:
            for production in self:
                production.product_qty = product_qty_val
        
        return result

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

