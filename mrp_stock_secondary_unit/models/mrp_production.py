# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _get_move_raw_values(
        self,
        product_id,
        product_uom_qty,
        product_uom,
        operation_id=False,
        bom_line=False,
    ):
        """Add secondary unit info to raw material moves."""
        # Handle both product_id (int) and product (recordset) for compatibility
        # with mrp_bom_line_formula_quantity which uses 'product' parameter
        if isinstance(product_id, (int,)):
            product = self.env["product.product"].browse(product_id)
            # Pass product_id to super for standard modules
            values = super()._get_move_raw_values(
                product_id,
                product_uom_qty,
                product_uom,
                operation_id=operation_id,
                bom_line=bom_line,
            )
        else:
            # product_id is actually a product recordset (from formula module)
            product = product_id
            # Pass product as-is to super (formula module expects it)
            values = super()._get_move_raw_values(
                product,
                product_uom_qty,
                product_uom,
                operation_id=operation_id,
                bom_line=bom_line,
            )
        # Get secondary unit from product if available
        # Also check if product_id is in values (some modules may set it)
        if not product and "product_id" in values:
            product = self.env["product.product"].browse(values["product_id"])
        # Try to get secondary_uom_ids directly from product (if available)
        # Otherwise fall back to product_tmpl_id
        secondary_uom = False
        if product:
            if hasattr(product, "secondary_uom_ids") and product.secondary_uom_ids:
                secondary_uom = product.secondary_uom_ids[:1]
            elif hasattr(product.product_tmpl_id, "secondary_uom_ids"):
                secondary_uom = product.product_tmpl_id.secondary_uom_ids[:1]
        if secondary_uom:
                values["secondary_uom_id"] = secondary_uom.id
                # Calculate secondary_uom_qty if product_uom_qty is available
                if "product_uom_qty" in values and values["product_uom_qty"]:
                    # Convert product_uom to recordset if it's an ID
                    if isinstance(product_uom, (int,)):
                        product_uom_record = self.env["uom.uom"].browse(product_uom)
                    else:
                        product_uom_record = product_uom
                    # Calculate secondary quantity using product's base UoM
                    factor = secondary_uom.factor
                    secondary_uom_record = secondary_uom.uom_id
                    product_base_uom = product.uom_id
                    # First convert from move UoM to product's base UoM
                    if product_uom_record.category_id == product_base_uom.category_id:
                        base_qty = product_uom_record._compute_quantity(
                            values["product_uom_qty"], product_base_uom
                        )
                        # Then convert from product's base UoM to secondary UoM base, then apply factor
                        if product_base_uom.category_id == secondary_uom_record.category_id:
                            converted_qty = product_base_uom._compute_quantity(
                                base_qty, secondary_uom_record
                            )
                            values["secondary_uom_qty"] = converted_qty * factor
                        else:
                            values["secondary_uom_qty"] = 0.0
                    # Fallback: try direct conversion if categories match
                    elif product_uom_record.category_id == secondary_uom_record.category_id:
                        converted_qty = product_uom_record._compute_quantity(
                            values["product_uom_qty"], secondary_uom_record
                        )
                        values["secondary_uom_qty"] = converted_qty * factor
                    else:
                        values["secondary_uom_qty"] = 0.0
        return values

    def _get_move_finished_values(
        self,
        product_id,
        product_uom_qty,
        product_uom,
        operation_id=False,
        byproduct_id=False,
        cost_share=0,
    ):
        """Add secondary unit info to finished product moves."""
        values = super()._get_move_finished_values(
            product_id,
            product_uom_qty,
            product_uom,
            operation_id=operation_id,
            byproduct_id=byproduct_id,
            cost_share=cost_share,
        )
        
        # For main finished product, use production order secondary unit
        # Copy directly from production order, like sale_stock_secondary_unit does
        if not byproduct_id and self.secondary_uom_id:
            values["secondary_uom_id"] = self.secondary_uom_id.id
            # Read secondary_uom_qty from production order
            # The value should already be calculated by mrp_production_secondary_unit
            # Just read it directly - if it's 0, it means it wasn't calculated yet
            production_secondary_uom_qty = self.secondary_uom_qty
            # Use the secondary_uom_qty from production order if available
            # Scale proportionally based on quantity ratio (both in same UoM)
            if production_secondary_uom_qty and self.product_qty:
                # Get move quantity (may be in values or parameter)
                move_qty = values.get("product_uom_qty", product_uom_qty)
                # Get move UoM (may be in values or parameter)
                if "product_uom" in values:
                    move_uom = values["product_uom"]
                    if isinstance(move_uom, (int,)):
                        move_uom = self.env["uom.uom"].browse(move_uom)
                elif isinstance(product_uom, (int,)):
                    move_uom = self.env["uom.uom"].browse(product_uom)
                else:
                    move_uom = product_uom
                
                # Convert both quantities to product base UoM for accurate ratio calculation
                product_base_uom = self.product_id.uom_id
                if move_uom and move_uom.category_id == self.product_uom_id.category_id:
                    # Convert move qty to production order UoM
                    move_qty_in_prod_uom = move_uom._compute_quantity(move_qty, self.product_uom_id)
                    # Calculate ratio using same UoM
                    ratio = move_qty_in_prod_uom / self.product_qty
                    values["secondary_uom_qty"] = production_secondary_uom_qty * ratio
                else:
                    # Fallback: use direct ratio (may be inaccurate if UoMs differ)
                    ratio = move_qty / self.product_qty
                    values["secondary_uom_qty"] = production_secondary_uom_qty * ratio
            elif "product_uom_qty" in values and values["product_uom_qty"]:
                # Fallback: calculate if production doesn't have secondary_uom_qty yet
                factor = self.secondary_uom_id.factor
                secondary_uom_record = self.secondary_uom_id.uom_id
                # Get product_uom from values if available, otherwise use parameter
                if "product_uom" in values:
                    if isinstance(values["product_uom"], (int,)):
                        product_uom_record = self.env["uom.uom"].browse(values["product_uom"])
                    else:
                        product_uom_record = values["product_uom"]
                elif isinstance(product_uom, (int,)):
                    product_uom_record = self.env["uom.uom"].browse(product_uom)
                else:
                    product_uom_record = product_uom
                # Convert using product's base UoM (like sale_order_secondary_unit)
                # First get the product
                if isinstance(product_id, (int,)):
                    product = self.env["product.product"].browse(product_id)
                else:
                    product = product_id
                if product and product_uom_record:
                    product_base_uom = product.uom_id
                    # First convert from move UoM to product's base UoM
                    if product_uom_record.category_id == product_base_uom.category_id:
                        base_qty = product_uom_record._compute_quantity(
                            values["product_uom_qty"], product_base_uom
                        )
                        # Then convert from product's base UoM to secondary UoM base, then apply factor
                        if product_base_uom.category_id == secondary_uom_record.category_id:
                            converted_qty = product_base_uom._compute_quantity(
                                base_qty, secondary_uom_record
                            )
                            values["secondary_uom_qty"] = converted_qty * factor
                        else:
                            values["secondary_uom_qty"] = 0.0
                    # Fallback: try direct conversion if categories match
                    elif product_uom_record.category_id == secondary_uom_record.category_id:
                        converted_qty = product_uom_record._compute_quantity(
                            values["product_uom_qty"], secondary_uom_record
                        )
                        values["secondary_uom_qty"] = converted_qty * factor
                    else:
                        values["secondary_uom_qty"] = 0.0
                else:
                    values["secondary_uom_qty"] = 0.0
            else:
                values["secondary_uom_qty"] = 0.0
        # For byproducts, get from product
        elif byproduct_id:
            # product_id can be an ID or a recordset
            if isinstance(product_id, (int,)):
                product = self.env["product.product"].browse(product_id)
            else:
                product = product_id
            if product and hasattr(product.product_tmpl_id, "secondary_uom_ids"):
                secondary_uom = product.product_tmpl_id.secondary_uom_ids[:1]
                if secondary_uom:
                    values["secondary_uom_id"] = secondary_uom.id
        return values

