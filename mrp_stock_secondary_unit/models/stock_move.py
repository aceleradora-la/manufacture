# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_confirm(self, merge=True, merge_into=False):
        """Transfer secondary unit info when confirming moves from MO."""
        moves = super()._action_confirm(merge=merge, merge_into=merge_into)
        # Update secondary unit for moves related to manufacturing orders
        for move in moves:
            # For finished products and byproducts from production order
            if move.production_id:
                # Check if it's a byproduct (different from main product)
                if move.product_id != move.production_id.product_id:
                    # For byproducts - get from product if not already set
                    if not move.secondary_uom_id and move.product_id:
                        # Try to get secondary_uom_ids directly from product (if available)
                        # Otherwise fall back to product_tmpl_id
                        secondary_uom = False
                        if hasattr(move.product_id, "secondary_uom_ids") and move.product_id.secondary_uom_ids:
                            secondary_uom = move.product_id.secondary_uom_ids[:1]
                        elif hasattr(move.product_id.product_tmpl_id, "secondary_uom_ids"):
                            secondary_uom = move.product_id.product_tmpl_id.secondary_uom_ids[:1]
                        if secondary_uom:
                                move.secondary_uom_id = secondary_uom.id
                                # Calculate secondary_uom_qty
                                if move.product_uom_qty:
                                    move.secondary_uom_qty = move._calculate_secondary_uom_qty()
                # For main finished product - use production order secondary unit
                elif move.production_id.secondary_uom_id:
                    # Always set secondary_uom_id from production order
                    # Copy secondary_uom_qty from production order, scaling proportionally
                    # Convert both quantities to same UoM for accurate ratio calculation
                    # Ensure production secondary_uom_qty is calculated
                    production = move.production_id
                    production_secondary_uom_qty = production.secondary_uom_qty
                    if not production_secondary_uom_qty and production.product_qty and production.product_uom_id:
                        # Force calculation if not available
                        production._onchange_helper_product_uom_for_secondary()
                        production_secondary_uom_qty = production.secondary_uom_qty
                    secondary_uom_qty = 0.0
                    if production_secondary_uom_qty:
                        if move.production_id.product_qty and move.product_uom_qty:
                            # Convert move qty to production order UoM for accurate ratio
                            if move.product_uom.category_id == move.production_id.product_uom_id.category_id:
                                move_qty_in_prod_uom = move.product_uom._compute_quantity(
                                    move.product_uom_qty, move.production_id.product_uom_id
                                )
                                ratio = move_qty_in_prod_uom / move.production_id.product_qty
                            else:
                                # Fallback: direct ratio (may be inaccurate)
                                ratio = move.product_uom_qty / move.production_id.product_qty
                            secondary_uom_qty = production_secondary_uom_qty * ratio
                        else:
                            secondary_uom_qty = production_secondary_uom_qty
                    # Only update if not already set (from _get_move_finished_values) or if it's 0
                    # This preserves values set in _get_move_finished_values and avoids unnecessary writes
                    # that could cause move splitting
                    if not move.secondary_uom_id or move.secondary_uom_id.id != move.production_id.secondary_uom_id.id:
                        move.secondary_uom_id = move.production_id.secondary_uom_id.id
                    # Only update secondary_uom_qty if it's not already set or is 0
                    # This preserves values from _get_move_finished_values
                    if not move.secondary_uom_qty or abs(move.secondary_uom_qty) < 0.0001:
                        if abs(secondary_uom_qty) > 0.0001:
                            move.secondary_uom_qty = secondary_uom_qty
            # For raw materials - get from product if not already set
            elif move.raw_material_production_id and not move.secondary_uom_id:
                if move.product_id and hasattr(move.product_id.product_tmpl_id, "secondary_uom_ids"):
                    secondary_uom = move.product_id.product_tmpl_id.secondary_uom_ids[:1]
                    if secondary_uom:
                        move.secondary_uom_id = secondary_uom.id
                        # Calculate secondary_uom_qty
                        if move.product_uom_qty:
                            move.secondary_uom_qty = move._calculate_secondary_uom_qty()
        return moves

    @api.model_create_multi
    def create(self, vals_list):
        """Transfer secondary unit when creating moves from MO.
        
        Note: We rely on _get_move_finished_values to set the initial values.
        We only set values here if they weren't set by _get_move_finished_values
        to avoid interfering with move merging.
        """
        moves = super().create(vals_list)
        # Only set values for byproducts and raw materials here
        # Main finished product values should come from _get_move_finished_values
        for move in moves:
            # For byproducts - get from product if not already set
            if move.production_id and move.product_id != move.production_id.product_id:
                if not move.secondary_uom_id and move.product_id:
                    # Try to get secondary_uom_ids directly from product (if available)
                    # Otherwise fall back to product_tmpl_id
                    secondary_uom = False
                    if hasattr(move.product_id, "secondary_uom_ids") and move.product_id.secondary_uom_ids:
                        secondary_uom = move.product_id.secondary_uom_ids[:1]
                    elif hasattr(move.product_id.product_tmpl_id, "secondary_uom_ids"):
                        secondary_uom = move.product_id.product_tmpl_id.secondary_uom_ids[:1]
                    if secondary_uom:
                        move.secondary_uom_id = secondary_uom.id
                        # Calculate secondary_uom_qty
                        if move.product_uom_qty:
                            move.secondary_uom_qty = move._calculate_secondary_uom_qty()
            # For raw materials
            elif move.raw_material_production_id and not move.secondary_uom_id:
                if move.product_id and hasattr(move.product_id.product_tmpl_id, "secondary_uom_ids"):
                    secondary_uom = move.product_id.product_tmpl_id.secondary_uom_ids[:1]
                    if secondary_uom:
                        move.secondary_uom_id = secondary_uom.id
                        # Calculate secondary_uom_qty
                        if move.product_uom_qty:
                            move.secondary_uom_qty = move._calculate_secondary_uom_qty()
        return moves

