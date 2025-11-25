# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_confirm(self, merge=True, merge_into=False):
        """Transfer secondary unit info when confirming moves from MO and Unbuild."""
        moves = super()._action_confirm(merge=merge, merge_into=merge_into)
        # Update secondary unit for moves related to manufacturing orders and unbuild
        for move in moves:
            # For finished products and byproducts from production order
            if move.production_id:
                # Check if it's a byproduct (different from main product)
                if move.product_id != move.production_id.product_id:
                    # For byproducts - get from product if not already set
                    if not move.secondary_uom_id and move.product_id:
                        if hasattr(move.product_id.product_tmpl_id, "secondary_uom_ids"):
                            secondary_uom = move.product_id.product_tmpl_id.secondary_uom_ids[:1]
                            if secondary_uom:
                                move.secondary_uom_id = secondary_uom.id
                                if secondary_uom.factor:
                                    move.secondary_uom_qty = move.product_uom_qty / secondary_uom.factor
                # For main finished product - use production order secondary unit
                elif move.production_id.secondary_uom_id:
                    if not move.secondary_uom_id:
                        move.secondary_uom_id = move.production_id.secondary_uom_id.id
                    if not move.secondary_uom_qty and move.production_id.secondary_uom_qty:
                        move.secondary_uom_qty = move.production_id.secondary_uom_qty
                    elif not move.secondary_uom_qty and move.secondary_uom_id.factor:
                        move.secondary_uom_qty = move.product_uom_qty / move.secondary_uom_id.factor
            # For moves from unbuild orders
            elif move.unbuild_id and hasattr(move.unbuild_id, "secondary_uom_id"):
                if move.unbuild_id.secondary_uom_id and not move.secondary_uom_id:
                    move.secondary_uom_id = move.unbuild_id.secondary_uom_id.id
                    if move.unbuild_id.secondary_uom_qty:
                        move.secondary_uom_qty = move.unbuild_id.secondary_uom_qty
                    elif move.secondary_uom_id.factor:
                        move.secondary_uom_qty = move.product_uom_qty / move.secondary_uom_id.factor
            # For raw materials - get from product if not already set
            elif move.raw_material_production_id and not move.secondary_uom_id:
                if move.product_id and hasattr(move.product_id.product_tmpl_id, "secondary_uom_ids"):
                    secondary_uom = move.product_id.product_tmpl_id.secondary_uom_ids[:1]
                    if secondary_uom:
                        move.secondary_uom_id = secondary_uom.id
                        if secondary_uom.factor:
                            move.secondary_uom_qty = move.product_uom_qty / secondary_uom.factor
        return moves

    @api.model_create_multi
    def create(self, vals_list):
        """Set secondary unit when creating moves from MO and Unbuild."""
        moves = super().create(vals_list)
        for move in moves:
            # For finished products and byproducts from production order
            if move.production_id:
                # Check if it's a byproduct (different from main product)
                if move.product_id != move.production_id.product_id:
                    # For byproducts - get from product if not already set
                    if not move.secondary_uom_id and move.product_id:
                        if hasattr(move.product_id.product_tmpl_id, "secondary_uom_ids"):
                            secondary_uom = move.product_id.product_tmpl_id.secondary_uom_ids[:1]
                            if secondary_uom:
                                move.secondary_uom_id = secondary_uom.id
                                if secondary_uom.factor:
                                    move.secondary_uom_qty = move.product_uom_qty / secondary_uom.factor
                # For main finished product - use production order secondary unit
                elif move.production_id.secondary_uom_id:
                    if not move.secondary_uom_id:
                        move.secondary_uom_id = move.production_id.secondary_uom_id.id
                    if not move.secondary_uom_qty:
                        if move.production_id.secondary_uom_qty:
                            move.secondary_uom_qty = move.production_id.secondary_uom_qty
                        elif move.secondary_uom_id.factor:
                            move.secondary_uom_qty = move.product_uom_qty / move.secondary_uom_id.factor
            # For moves from unbuild orders
            elif move.unbuild_id and hasattr(move.unbuild_id, "secondary_uom_id"):
                if move.unbuild_id.secondary_uom_id and not move.secondary_uom_id:
                    move.secondary_uom_id = move.unbuild_id.secondary_uom_id.id
                    if move.unbuild_id.secondary_uom_qty:
                        move.secondary_uom_qty = move.unbuild_id.secondary_uom_qty
                    elif move.secondary_uom_id.factor:
                        move.secondary_uom_qty = move.product_uom_qty / move.secondary_uom_id.factor
            # For raw materials
            elif move.raw_material_production_id and not move.secondary_uom_id:
                if move.product_id and hasattr(move.product_id.product_tmpl_id, "secondary_uom_ids"):
                    secondary_uom = move.product_id.product_tmpl_id.secondary_uom_ids[:1]
                    if secondary_uom:
                        move.secondary_uom_id = secondary_uom.id
                        if secondary_uom.factor:
                            move.secondary_uom_qty = move.product_uom_qty / secondary_uom.factor
        return moves

