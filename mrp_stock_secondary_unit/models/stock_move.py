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
                    # Always set secondary_uom_id from production order first
                    # Always recalculate secondary_uom_qty to ensure it's correct
                    if move.product_uom_qty and move.product_uom and move.product_id:
                        # Calculate directly using product's base UoM (like sale_order_secondary_unit)
                        secondary_uom = move.production_id.secondary_uom_id
                        factor = secondary_uom.factor
                        secondary_uom_record = secondary_uom.uom_id
                        product_base_uom = move.product_id.uom_id
                        # First convert from move UoM to product's base UoM
                        if move.product_uom.category_id == product_base_uom.category_id:
                            base_qty = move.product_uom._compute_quantity(
                                move.product_uom_qty, product_base_uom
                            )
                            # Then convert from product's base UoM to secondary UoM base, then apply factor
                            if product_base_uom.category_id == secondary_uom_record.category_id:
                                converted_qty = product_base_uom._compute_quantity(
                                    base_qty, secondary_uom_record
                                )
                                calculated_qty = converted_qty * factor
                            else:
                                calculated_qty = 0.0
                        # Fallback: try direct conversion if categories match
                        elif move.product_uom.category_id == secondary_uom_record.category_id:
                            converted_qty = move.product_uom._compute_quantity(
                                move.product_uom_qty, secondary_uom_record
                            )
                            calculated_qty = converted_qty * factor
                        else:
                            calculated_qty = 0.0
                        # Use write to ensure both values are saved together
                        move.write({
                            "secondary_uom_id": secondary_uom.id,
                            "secondary_uom_qty": calculated_qty,
                        })
                    else:
                        # Even if no quantity, set the secondary_uom_id
                        move.secondary_uom_id = move.production_id.secondary_uom_id.id
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
        """Transfer secondary unit when creating moves from MO."""
        moves = super().create(vals_list)
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
                    # Always set secondary_uom_id from production order first
                    # Always recalculate secondary_uom_qty to ensure it's correct
                    if move.product_uom_qty and move.product_uom and move.product_id:
                        # Calculate directly using product's base UoM (like sale_order_secondary_unit)
                        secondary_uom = move.production_id.secondary_uom_id
                        factor = secondary_uom.factor
                        secondary_uom_record = secondary_uom.uom_id
                        product_base_uom = move.product_id.uom_id
                        # First convert from move UoM to product's base UoM
                        if move.product_uom.category_id == product_base_uom.category_id:
                            base_qty = move.product_uom._compute_quantity(
                                move.product_uom_qty, product_base_uom
                            )
                            # Then convert from product's base UoM to secondary UoM base, then apply factor
                            if product_base_uom.category_id == secondary_uom_record.category_id:
                                converted_qty = product_base_uom._compute_quantity(
                                    base_qty, secondary_uom_record
                                )
                                calculated_qty = converted_qty * factor
                            else:
                                calculated_qty = 0.0
                        # Fallback: try direct conversion if categories match
                        elif move.product_uom.category_id == secondary_uom_record.category_id:
                            converted_qty = move.product_uom._compute_quantity(
                                move.product_uom_qty, secondary_uom_record
                            )
                            calculated_qty = converted_qty * factor
                        else:
                            calculated_qty = 0.0
                        # Use write to ensure both values are saved together
                        move.write({
                            "secondary_uom_id": secondary_uom.id,
                            "secondary_uom_qty": calculated_qty,
                        })
                    else:
                        # Even if no quantity, set the secondary_uom_id
                        move.secondary_uom_id = move.production_id.secondary_uom_id.id
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

