# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_confirm(self, merge=True, merge_into=False):
        """Transfer secondary unit info when confirming moves from MO."""
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("StockMove _action_confirm() called with merge=%s, merge_into=%s", merge, merge_into)
        moves = super()._action_confirm(merge=merge, merge_into=merge_into)
        _logger.info("StockMove _action_confirm() - After super(), got %s moves", len(moves))
        # Update secondary unit for moves related to manufacturing orders
        for move in moves:
            _logger.info("StockMove _action_confirm() - Processing move %s: product=%s, production_id=%s, secondary_uom_id=%s, secondary_uom_qty=%s, product_uom_qty=%s",
                        move.id, move.product_id.name if move.product_id else None,
                        move.production_id.name if move.production_id else None,
                        move.secondary_uom_id.id if move.secondary_uom_id else False,
                        move.secondary_uom_qty, move.product_uom_qty)
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
                # Values should already be set by _get_move_finished_values
                # Do NOT update here to avoid move splitting
                # If values are missing, they will be set in _get_move_finished_values
                elif move.production_id.secondary_uom_id:
                    # Only set if completely missing (shouldn't happen)
                    if not move.secondary_uom_id:
                        move.secondary_uom_id = move.production_id.secondary_uom_id.id
                    # Do NOT update secondary_uom_qty here - it should come from _get_move_finished_values
                    # Updating here can cause move splitting
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

