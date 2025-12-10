# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

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
        # If move_finished_ids is being created/updated, ensure secondary_uom_qty is set correctly
        if 'move_finished_ids' in vals:
            for production in self:
                if production.secondary_uom_id and production.product_qty and production.product_id:
                    # Calculate secondary_uom_qty directly using the values from vals
                    # This avoids modifying the record which could cause moves to be deleted
                    product_qty = vals.get('product_qty', production.product_qty)
                    product_uom_id = vals.get('product_uom_id', production.product_uom_id.id if production.product_uom_id else False)
                    if product_uom_id:
                        # Get UoM record
                        product_uom = self.env['uom.uom'].browse(product_uom_id)
                        # Calculate secondary_uom_qty directly (similar to mixin logic)
                        factor = production.secondary_uom_id.factor
                        secondary_uom_record = production.secondary_uom_id.uom_id
                        product_base_uom = production.product_id.uom_id
                        # Convert from production UoM to product's base UoM
                        if product_uom.category_id == product_base_uom.category_id:
                            base_qty = product_uom._compute_quantity(product_qty, product_base_uom)
                            # Convert from product's base UoM to secondary UoM base, then apply factor
                            if product_base_uom.category_id == secondary_uom_record.category_id:
                                converted_qty = product_base_uom._compute_quantity(base_qty, secondary_uom_record)
                                production_secondary_uom_qty = converted_qty * factor
                            else:
                                production_secondary_uom_qty = 0.0
                        else:
                            production_secondary_uom_qty = 0.0
                        _logger.info("MRP Production write() - Updating move_finished_ids with secondary_uom_qty: %s (calculated from product_uom_id: %s)", production_secondary_uom_qty, product_uom_id)
                    # Update move_finished_ids to include correct secondary_uom_qty
                    for command in vals['move_finished_ids']:
                        if isinstance(command, (list, tuple)) and len(command) >= 3:
                            if command[0] in (0, 1):  # create or update
                                move_vals = command[2] if len(command) > 2 else {}
                                if 'secondary_uom_id' not in move_vals or not move_vals.get('secondary_uom_id'):
                                    move_vals['secondary_uom_id'] = production.secondary_uom_id.id
                                # Calculate secondary_uom_qty for the move based on its quantity
                                if 'product_uom_qty' in move_vals and move_vals['product_uom_qty']:
                                    move_qty = move_vals['product_uom_qty']
                                    if production.product_qty:
                                        ratio = move_qty / production.product_qty
                                        move_vals['secondary_uom_qty'] = production_secondary_uom_qty * ratio
                                        _logger.info("  - Updated move secondary_uom_qty: %s (ratio: %s)", move_vals['secondary_uom_qty'], ratio)
                                elif not move_vals.get('secondary_uom_qty'):
                                    move_vals['secondary_uom_qty'] = production_secondary_uom_qty
        result = super().write(vals)
        # If product_uom_id or product_qty changed, recalculate secondary_uom_qty
        # and force save to ensure it's available when _get_move_finished_values is called
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
        return result

    def action_confirm(self):
        """Ensure secondary_uom_qty is calculated and saved before creating moves."""
        _logger.info("MRP Production action_confirm() called for: %s", [p.name for p in self])
        # Force calculation of secondary_uom_qty before creating moves
        # This ensures the computed field has the correct value when _get_move_finished_values is called
        for production in self:
            if production.secondary_uom_id and production.product_qty and production.product_uom_id:
                _logger.info("MRP Production action_confirm() - Recalculating secondary_uom_qty for production %s", production.name)
                # Force recalculation - this updates the computed field value in memory
                production._onchange_helper_product_uom_for_secondary()
                # Invalidate and read to ensure computed field is recalculated
                production.invalidate_recordset(['secondary_uom_qty'])
                # Read the value to ensure it's in cache and trigger recalculation if needed
                secondary_uom_qty = production.secondary_uom_qty
                _logger.info("  - secondary_uom_qty after recalculation: %s", secondary_uom_qty)
                # Update existing moves if they were created with wrong values
                # This happens when quantity was changed before saving
                _logger.info("  - Checking existing moves: %s moves found", len(production.move_finished_ids))
                for move in production.move_finished_ids:
                    _logger.info("  - Move %s: product_id=%s, production.product_id=%s, secondary_uom_id=%s, secondary_uom_qty=%s, product_uom_qty=%s", 
                                move.id, move.product_id.id if move.product_id else False, 
                                production.product_id.id if production.product_id else False,
                                move.secondary_uom_id.id if move.secondary_uom_id else False,
                                move.secondary_uom_qty, move.product_uom_qty)
                    if move.product_id == production.product_id:
                        # Set secondary_uom_id if missing
                        if not move.secondary_uom_id and production.secondary_uom_id:
                            _logger.info("  - Setting move %s secondary_uom_id to %s", move.id, production.secondary_uom_id.id)
                            move.secondary_uom_id = production.secondary_uom_id.id
                        # Recalculate secondary_uom_qty for the move based on current production values
                        if production.secondary_uom_id and production.product_qty and move.product_uom_qty:
                            ratio = move.product_uom_qty / production.product_qty
                            move_secondary_uom_qty = secondary_uom_qty * ratio
                            _logger.info("  - Calculated move secondary_uom_qty: %s (ratio: %s, current: %s)", 
                                        move_secondary_uom_qty, ratio, move.secondary_uom_qty)
                            if abs(move.secondary_uom_qty - move_secondary_uom_qty) > 0.01:
                                _logger.info("  - Updating move %s secondary_uom_qty from %s to %s", move.id, move.secondary_uom_qty, move_secondary_uom_qty)
                                move.secondary_uom_qty = move_secondary_uom_qty
                            else:
                                _logger.info("  - Move %s secondary_uom_qty is already correct", move.id)
                        else:
                            _logger.info("  - Move %s: missing secondary_uom_id, product_qty or move.product_uom_qty", move.id)
                    else:
                        _logger.info("  - Move %s: not main product", move.id)
        return super().action_confirm()
