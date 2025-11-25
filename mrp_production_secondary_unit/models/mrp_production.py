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
        """Compute secondary quantity from product quantity, considering UoM conversion.
        
        The factor in secondary_uom_id is defined relative to the product's base UoM.
        When the order uses a different UoM, we need to convert directly from order UoM
        to secondary UoM, not through the base UoM.
        
        Example:
        - Base UoM: Cajón (360 huevos)
        - Secondary UoM: Huevo (factor = 360, meaning 1 Cajón = 360 Huevos)
        - Order UoM: Maple 30 (30 huevos)
        - Quantity: 4 Maples
        
        Correct calculation: 4 Maples × 30 = 120 Huevos
        Wrong calculation: 4 Maples × 30 × 360 = 43200 (multiplying by factor)
        """
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
                
                # If secondary UoM is the same as order UoM, quantity is the same
                if secondary_uom.id == order_uom.id:
                    production.secondary_uom_qty = production.product_qty
                # If order UoM is the same as base UoM, use the factor directly
                elif order_uom.id == base_uom.id:
                    # Factor is defined as: 1 base UoM = factor secondary UoM
                    production.secondary_uom_qty = (
                        production.product_qty * production.secondary_uom_id.factor
                    )
                else:
                    # Order UoM is different from both base and secondary UoM
                    # Convert directly from order UoM to secondary UoM
                    # The factor in secondary_uom_id is relative to BASE UoM, not to order UoM
                    # So we need to convert order -> reference -> secondary
                    # OR convert order -> base -> secondary (but that would use the factor incorrectly)
                    # OR convert directly order -> secondary using UoM category factors
                    
                    # Best approach: convert through the reference unit of the category
                    # All UoMs in a category have factors relative to the reference unit (factor = 1.0)
                    category = order_uom.category_id
                    if category and secondary_uom.category_id.id == category.id:
                        # Both are in the same category, we can convert directly
                        # Find reference unit (factor = 1.0)
                        reference_uoms = category.uom_ids.filtered(lambda u: abs(u.factor - 1.0) < 0.0001)
                        if reference_uoms:
                            reference_uom = reference_uoms[0]
                            # Convert: order -> reference -> secondary
                            # order.factor = units of reference per 1 order unit
                            # secondary.factor = units of reference per 1 secondary unit
                            # So: qty_secondary = (qty_order * order.factor) / secondary.factor
                            
                            # But secondary.factor in product.secondary.unit is relative to BASE!
                            # We need secondary.factor relative to reference
                            # If base.factor = 360 and secondary = reference (factor = 1), then:
                            # secondary_uom.factor (in product.secondary.unit) = 360 (base to secondary)
                            # But we need: secondary relative to reference
                            
                            # Actually, if secondary is the reference unit:
                            if abs(secondary_uom.factor - 1.0) < 0.0001:
                                # Secondary is reference, so: qty_secondary = qty_order * order.factor
                                production.secondary_uom_qty = production.product_qty * order_uom.factor
                            else:
                                # Secondary is not reference, need to find its factor relative to reference
                                # secondary.factor in UoM model = units of reference per 1 secondary
                                # So: qty_secondary = (qty_order * order.factor) / secondary.factor
                                if secondary_uom.factor:
                                    production.secondary_uom_qty = (
                                        production.product_qty * order_uom.factor / secondary_uom.factor
                                    )
                                else:
                                    production.secondary_uom_qty = 0.0
                        else:
                            # No reference unit found, fallback to direct conversion
                            production.secondary_uom_qty = order_uom._compute_quantity(
                                production.product_qty, secondary_uom, rounding_method='HALF-UP'
                            )
                    else:
                        # Different categories, use direct conversion
                        production.secondary_uom_qty = order_uom._compute_quantity(
                            production.product_qty, secondary_uom, rounding_method='HALF-UP'
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

