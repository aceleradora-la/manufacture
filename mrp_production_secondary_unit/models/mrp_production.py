# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


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

    def write(self, vals):
        """Recalculate secondary_uom_qty when product_uom_id or product_qty changes."""
        _logger.info("MRP Production write() called with vals: %s", vals)
        # Note: We do NOT modify move_finished_ids here to avoid interfering with Odoo's merge logic
        # which causes the finished product to be split into two lines.
        # Instead, we rely on _get_move_finished_values() and action_confirm() to set the correct values.
        result = super().write(vals)
        # If product_uom_id or product_qty changed, recalculate secondary_uom_qty
        # and update raw material moves to fix rounding errors (e.g., 30.01 instead of 30)
        if 'product_uom_id' in vals or 'product_qty' in vals:
            for production in self:
                _logger.info("MRP Production write() - Recalculating secondary_uom_qty for production %s", production.name)
                _logger.info("  - secondary_uom_id: %s", production.secondary_uom_id.id if production.secondary_uom_id else False)
                _logger.info("  - product_qty: %s", production.product_qty)
                _logger.info("  - product_uom_id: %s", production.product_uom_id.id if production.product_uom_id else False)
                if production.secondary_uom_id and production.product_qty and production.product_uom_id:
                    production._onchange_helper_product_uom_for_secondary()
                    # Force save the computed value by reading it and invalidating cache
                    # This ensures it's available when _get_move_finished_values is called
                    production.invalidate_recordset(['secondary_uom_qty'])
                    secondary_uom_qty = production.secondary_uom_qty
                    _logger.info("  - Calculated secondary_uom_qty: %s", secondary_uom_qty)
                    # Update raw material moves to fix rounding errors
                    # This fixes the 30.01 issue when changing UoM
                    _logger.info("  - Checking %s raw material moves", len(production.move_raw_ids))
                    for move in production.move_raw_ids:
                        _logger.info("  - Raw move %s: product=%s, product_uom_qty=%s, secondary_uom_id=%s, secondary_uom_qty=%s", 
                                    move.id, move.product_id.name if move.product_id else None, 
                                    move.product_uom_qty, 
                                    move.secondary_uom_id.id if move.secondary_uom_id else False,
                                    move.secondary_uom_qty)
                        if move.secondary_uom_id and move.product_uom_qty:
                            # Recalculate using the helper method which includes rounding
                            recalculated_qty = move._calculate_secondary_uom_qty()
                            _logger.info("    - Recalculated secondary_uom_qty: %s (current: %s, diff: %s)", 
                                        recalculated_qty, move.secondary_uom_qty, abs(move.secondary_uom_qty - recalculated_qty))
                            if abs(move.secondary_uom_qty - recalculated_qty) > 0.0001:
                                _logger.info("    - Updating raw move %s secondary_uom_qty from %s to %s", move.id, move.secondary_uom_qty, recalculated_qty)
                                move.secondary_uom_qty = recalculated_qty
                            else:
                                _logger.info("    - Raw move %s secondary_uom_qty is already correct", move.id)
                        else:
                            _logger.info("    - Raw move %s: missing secondary_uom_id or product_uom_qty", move.id)
        return result

    def action_confirm(self):
        """Ensure secondary_uom_qty is calculated and saved before creating moves."""
        _logger.info("MRP Production action_confirm() called for: %s", [p.name for p in self])
        # Force calculation of secondary_uom_qty before creating moves
        # This ensures the computed field has the correct value when _get_move_finished_values is called
        for production in self:
            _logger.info("MRP Production action_confirm() - Processing production %s", production.name)
            _logger.info("  - Existing move_finished_ids: %s moves", len(production.move_finished_ids))
            for move in production.move_finished_ids:
                _logger.info("    - Move %s: product=%s, product_uom_qty=%s, secondary_uom_id=%s, secondary_uom_qty=%s",
                            move.id, move.product_id.name if move.product_id else None,
                            move.product_uom_qty,
                            move.secondary_uom_id.id if move.secondary_uom_id else False,
                            move.secondary_uom_qty)
            if production.secondary_uom_id and production.product_qty and production.product_uom_id:
                _logger.info("MRP Production action_confirm() - Recalculating secondary_uom_qty for production %s", production.name)
                # Force recalculation - this updates the computed field value in memory
                production._onchange_helper_product_uom_for_secondary()
                # Invalidate and read to ensure computed field is recalculated
                production.invalidate_recordset(['secondary_uom_qty'])
                # Read the value to ensure it's in cache and trigger recalculation if needed
                secondary_uom_qty = production.secondary_uom_qty
                _logger.info("  - secondary_uom_qty after recalculation: %s", secondary_uom_qty)
                # DO NOT update existing moves here - this causes move splitting
                # The values should already be set correctly by _get_move_finished_values()
                # Only set secondary_uom_id if completely missing (shouldn't happen)
                for move in production.move_finished_ids:
                    if move.product_id == production.product_id:
                        if not move.secondary_uom_id and production.secondary_uom_id:
                            _logger.info("  - Setting move %s secondary_uom_id to %s", move.id, production.secondary_uom_id.id)
                            move.secondary_uom_id = production.secondary_uom_id.id
        result = super().action_confirm()
        _logger.info("MRP Production action_confirm() - After super(), checking moves again")
        for production in self:
            _logger.info("  - Production %s: %s move_finished_ids after confirm", production.name, len(production.move_finished_ids))
            for move in production.move_finished_ids:
                _logger.info("    - Move %s: product=%s, product_uom_qty=%s, secondary_uom_id=%s, secondary_uom_qty=%s",
                            move.id, move.product_id.name if move.product_id else None,
                            move.product_uom_qty,
                            move.secondary_uom_id.id if move.secondary_uom_id else False,
                            move.secondary_uom_qty)
        return result
