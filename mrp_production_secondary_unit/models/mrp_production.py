# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = ["mrp.production", "product.secondary.unit.mixin"]
    _name = "mrp.production"
    
    _secondary_unit_fields = {
        "qty_field": "product_qty",
        "uom_field": "product_uom_id",
    }

    secondary_uom_id = fields.Many2one(
        domain="[('product_tmpl_id', '=', product_id.product_tmpl_id)]",
    )

    @api.model
    def _get_secondary_uom_qty_depends(self):
        """Include product_uom_id and secondary_uom_id in depends to recalculate when UoM changes."""
        depends = super()._get_secondary_uom_qty_depends()
        # Add product_uom_id to depends so secondary_uom_qty recalculates when UoM changes
        if self._secondary_unit_fields.get("uom_field"):
            uom_field = self._secondary_unit_fields["uom_field"]
            if uom_field not in depends:
                depends.append(uom_field)
        # Also include secondary_uom_id because the factor may change
        if "secondary_uom_id" not in depends:
            depends.append("secondary_uom_id")
        return depends

    @api.onchange("product_id")
    def _onchange_product_id(self):
        """Set secondary unit when product changes."""
        res = super()._onchange_product_id() if hasattr(super(), "_onchange_product_id") else {}
        if self.product_id and not self.env.context.get("skip_secondary_uom_default"):
            # Try to get secondary_uom_ids directly from product (if available)
            # Otherwise fall back to product_tmpl_id
            secondary_uom = False
            if hasattr(self.product_id, "secondary_uom_ids") and self.product_id.secondary_uom_ids:
                secondary_uom = self.product_id.secondary_uom_ids[:1]
            elif hasattr(self.product_id.product_tmpl_id, "secondary_uom_ids"):
                secondary_uom = self.product_id.product_tmpl_id.secondary_uom_ids[:1]
            if secondary_uom:
                self.secondary_uom_id = secondary_uom
                if self.product_qty == 1.0:
                    self.secondary_uom_qty = 1.0
                    self._onchange_helper_product_uom_for_secondary()
        return res

    @api.onchange("product_uom_id")
    def _onchange_product_uom_id(self):
        """Recalculate secondary quantity when UoM changes."""
        res = super()._onchange_product_uom_id() if hasattr(super(), "_onchange_product_uom_id") else {}
        self._onchange_helper_product_uom_for_secondary()
        return res

    @api.onchange("product_qty")
    def _onchange_product_qty(self):
        """Recalculate secondary quantity when quantity changes."""
        res = super()._onchange_product_qty() if hasattr(super(), "_onchange_product_qty") else {}
        self._onchange_helper_product_uom_for_secondary()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Set secondary_uom_id when creating production orders."""
        productions = super().create(vals_list)
        for production in productions:
            # Set secondary_uom_id from product if not already set
            if not production.secondary_uom_id and production.product_id:
                if not self.env.context.get("skip_secondary_uom_default"):
                    # Try to get secondary_uom_ids directly from product (if available)
                    # Otherwise fall back to product_tmpl_id
                    secondary_uom = False
                    if hasattr(production.product_id, "secondary_uom_ids") and production.product_id.secondary_uom_ids:
                        secondary_uom = production.product_id.secondary_uom_ids[:1]
                    elif hasattr(production.product_id.product_tmpl_id, "secondary_uom_ids"):
                        secondary_uom = production.product_id.product_tmpl_id.secondary_uom_ids[:1]
                    if secondary_uom:
                        production.secondary_uom_id = secondary_uom
                        # Recalculate secondary_uom_qty using mixin helper
                        if production.product_qty and production.product_uom_id:
                            production._onchange_helper_product_uom_for_secondary()
        return productions

    def action_confirm(self):
        """Ensure secondary_uom_qty is calculated before creating moves."""
        # Force calculation of secondary_uom_qty before creating moves
        # This ensures the computed field has the correct value when _get_move_finished_values is called
        for production in self:
            if production.secondary_uom_id and production.product_qty and production.product_uom_id:
                # Force recalculation - this updates the computed field value in memory
                production._onchange_helper_product_uom_for_secondary()
                # Read the value to ensure it's in cache
                _ = production.secondary_uom_qty
        return super().action_confirm()

