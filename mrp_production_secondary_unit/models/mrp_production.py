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
        readonly=False,
    )

    def _calculate_secondary_uom_qty(self):
        """Calculate secondary quantity based on primary quantity and conversion factor.
        
        Formula: secondary_qty = (product_qty converted to product base UoM) 
                 * (conversion to secondary UoM base) * factor
        """
        if not self.secondary_uom_id or not self.product_qty or not self.product_id:
            return 0.0
        
        # Get the factor from secondary unit
        factor = self.secondary_uom_id.factor
        secondary_uom_record = self.secondary_uom_id.uom_id
        product_uom = self.product_id.uom_id
        
        # Step 1: Convert from production order UoM to product's base UoM
        if not self.product_uom_id or not product_uom:
            return 0.0
            
        # Convert production qty to product's base UoM
        if self.product_uom_id.category_id != product_uom.category_id:
            # Categories don't match, can't convert
            return 0.0
            
        base_qty = self.product_uom_id._compute_quantity(
            self.product_qty, product_uom
        )
        
        # Step 2: Convert from product's base UoM to secondary UoM base
        if product_uom.category_id != secondary_uom_record.category_id:
            # Categories don't match, can't convert
            return 0.0
            
        converted_qty = product_uom._compute_quantity(
            base_qty, secondary_uom_record
        )
        
        # Step 3: Apply factor
        return converted_qty * factor


    @api.onchange("product_id")
    def _onchange_product_id_secondary_unit(self):
        """Set secondary unit when product changes."""
        if self.product_id:
            secondary_uom = self.product_id.product_tmpl_id.secondary_uom_ids[:1]
            if secondary_uom:
                self.secondary_uom_id = secondary_uom
                # Recalculate secondary quantity
                if self.product_qty:
                    self.secondary_uom_qty = self._calculate_secondary_uom_qty()
        else:
            self.secondary_uom_id = False
            self.secondary_uom_qty = 0.0

    @api.onchange("secondary_uom_id")
    def _onchange_secondary_uom_id(self):
        """Recalculate secondary quantity when secondary unit changes."""
        if self.secondary_uom_id and self.product_qty:
            self.secondary_uom_qty = self._calculate_secondary_uom_qty()
        elif not self.secondary_uom_id:
            self.secondary_uom_qty = 0.0

    @api.onchange("product_qty", "product_uom_id")
    def _onchange_product_qty_secondary_unit(self):
        """Recalculate secondary quantity when product quantity or UoM changes."""
        if self.secondary_uom_id and self.product_qty and self.product_uom_id:
            self.secondary_uom_qty = self._calculate_secondary_uom_qty()

    @api.model_create_multi
    def create(self, vals_list):
        """Set secondary_uom_id and calculate secondary_uom_qty when creating production orders."""
        productions = super().create(vals_list)
        for production in productions:
            # Set secondary_uom_id from product if not already set
            if not production.secondary_uom_id and production.product_id:
                if hasattr(production.product_id.product_tmpl_id, "secondary_uom_ids"):
                    secondary_uom = production.product_id.product_tmpl_id.secondary_uom_ids[:1]
                    if secondary_uom:
                        production.secondary_uom_id = secondary_uom
            # Always recalculate secondary_uom_qty after all fields are set
            # Force recalculation even if secondary_uom_qty was set in vals
            if production.secondary_uom_id and production.product_qty and production.product_uom_id:
                calculated_qty = production._calculate_secondary_uom_qty()
                # Always update, even if it's the same value, to ensure it's correct
                if calculated_qty != production.secondary_uom_qty:
                    production.write({"secondary_uom_qty": calculated_qty})
        return productions
    
    def write(self, vals):
        """Recalculate secondary_uom_qty when product_qty, product_uom_id, or secondary_uom_id changes."""
        result = super().write(vals)
        # Recalculate if product_qty, product_uom_id, or secondary_uom_id changed
        if "product_qty" in vals or "product_uom_id" in vals or "secondary_uom_id" in vals:
            for production in self:
                if production.secondary_uom_id and production.product_qty and production.product_uom_id:
                    calculated_qty = production._calculate_secondary_uom_qty()
                    if calculated_qty != production.secondary_uom_qty:
                        # Use super().write to avoid recursion
                        super(MrpProduction, production).write({"secondary_uom_qty": calculated_qty})
        return result

