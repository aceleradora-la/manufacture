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

    @api.depends("product_uom_id", "secondary_uom_id")
    def _compute_secondary_uom_qty(self):
        """Compute secondary quantity based on primary quantity and conversion factor."""
        # Skip computation during write operations to avoid interfering with standard recalculation
        # The field will be recalculated via onchange when needed
        if self.env.context.get('skip_secondary_uom_compute_during_write'):
            return
        # Don't depend on product_qty to avoid interfering with standard recalculation
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
        """Override write to skip secondary_uom_qty computation during write."""
        # Skip secondary_uom_qty computation during write to avoid interfering
        result = super().write(vals.with_context(skip_secondary_uom_compute_during_write=True))
        # Recalculate secondary_uom_qty after write completes, but only if product_qty changed
        if 'product_qty' in vals:
            # Recalculate manually after standard updates complete
            for production in self:
                if production.secondary_uom_id and production.product_qty:
                    factor = production.secondary_uom_id.factor
                    secondary_uom_record = production.secondary_uom_id.uom_id
                    if production.product_uom_id.category_id == secondary_uom_record.category_id:
                        converted_qty = production.product_uom_id._compute_quantity(
                            production.product_qty, secondary_uom_record
                        )
                        production.with_context(skip_secondary_uom_compute_during_write=True).secondary_uom_qty = converted_qty * factor
                    else:
                        production.with_context(skip_secondary_uom_compute_during_write=True).secondary_uom_qty = 0.0
                elif not production.product_qty:
                    production.with_context(skip_secondary_uom_compute_during_write=True).secondary_uom_qty = 0.0
        return result

    @api.onchange("product_qty")
    def _onchange_product_qty_secondary_unit(self):
        """Recalculate secondary quantity when primary quantity changes."""
        # Only recalculate secondary_uom_qty, don't interfere with standard recalculation
        if self.secondary_uom_id and self.product_qty:
            self._compute_secondary_uom_qty()

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

