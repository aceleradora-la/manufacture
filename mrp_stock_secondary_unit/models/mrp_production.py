# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _get_move_raw_values(
        self,
        product,
        product_uom_qty,
        product_uom,
        operation_id=False,
        bom_line=False,
    ):
        """Add secondary unit info to raw material moves."""
        values = super()._get_move_raw_values(
            product=product,
            product_uom_qty=product_uom_qty,
            product_uom=product_uom,
            operation_id=operation_id,
            bom_line=bom_line,
        )
        # Get secondary unit from product if available
        if product and hasattr(product.product_tmpl_id, "secondary_uom_ids"):
            secondary_uom = product.product_tmpl_id.secondary_uom_ids[:1]
            if secondary_uom:
                values["secondary_uom_id"] = secondary_uom.id
                if secondary_uom.factor and product_uom_qty:
                    # Calculate secondary quantity considering UoM conversion
                    # product_uom is the UoM used in the move (may differ from product base UoM)
                    # Convert to record if it's an ID
                    if isinstance(product_uom, int):
                        product_uom = self.env["uom.uom"].browse(product_uom)
                    base_uom = product.uom_id
                    secondary_uom_record = secondary_uom.uom_id
                    
                    # If move UoM is same as base UoM, use factor directly
                    if product_uom.id == base_uom.id:
                        values["secondary_uom_qty"] = product_uom_qty * secondary_uom.factor
                    # If secondary UoM is same as move UoM, quantity is the same
                    elif product_uom.id == secondary_uom_record.id:
                        values["secondary_uom_qty"] = product_uom_qty
                    else:
                        # Convert directly from move UoM to secondary UoM
                        # Use category reference unit for conversion
                        category = product_uom.category_id
                        if category and secondary_uom_record.category_id.id == category.id:
                            reference_uoms = category.uom_ids.filtered(lambda u: abs(u.factor - 1.0) < 0.0001)
                            if reference_uoms:
                                reference_uom = reference_uoms[0]
                                if abs(secondary_uom_record.factor - 1.0) < 0.0001:
                                    # Secondary is reference
                                    values["secondary_uom_qty"] = product_uom_qty * product_uom.factor
                                else:
                                    # Convert through reference
                                    if secondary_uom_record.factor:
                                        values["secondary_uom_qty"] = (
                                            product_uom_qty * product_uom.factor / secondary_uom_record.factor
                                        )
                                    else:
                                        values["secondary_uom_qty"] = 0.0
                            else:
                                # Fallback: direct conversion
                                values["secondary_uom_qty"] = product_uom._compute_quantity(
                                    product_uom_qty, secondary_uom_record, rounding_method='HALF-UP'
                                )
                        else:
                            # Fallback: direct conversion
                            values["secondary_uom_qty"] = product_uom._compute_quantity(
                                product_uom_qty, secondary_uom_record, rounding_method='HALF-UP'
                            )
        return values

    def _get_move_finished_values(
        self,
        product_id,
        product_uom_qty,
        product_uom,
        operation_id=False,
        **kwargs
    ):
        """Add secondary unit info to finished product and byproduct moves."""
        # Get byproduct_id from kwargs if present (for byproducts)
        byproduct_id = kwargs.get('byproduct_id', False)
        cost_share = kwargs.get('cost_share', 0)
        
        # Call super - only pass parameters that standard Odoo accepts
        # Standard Odoo signature: (product_id, product_uom_qty, product_uom, operation_id=False)
        # Some modules may add byproduct_id and cost_share, but we handle them via kwargs
        try:
            # Try with all parameters first (in case another module added them)
            values = super()._get_move_finished_values(
                product_id=product_id,
                product_uom_qty=product_uom_qty,
                product_uom=product_uom,
                operation_id=operation_id,
                byproduct_id=byproduct_id,
                cost_share=cost_share,
            )
        except TypeError:
            # Fallback: standard Odoo only accepts 4 parameters
            values = super()._get_move_finished_values(
                product_id=product_id,
                product_uom_qty=product_uom_qty,
                product_uom=product_uom,
                operation_id=operation_id,
            )
        
        # Get product record (product_id can be an ID or a record)
        if isinstance(product_id, int):
            product = self.env["product.product"].browse(product_id)
        else:
            product = product_id
        
        # For byproducts, get secondary unit from byproduct product itself
        if byproduct_id:
            if product and hasattr(product.product_tmpl_id, "secondary_uom_ids"):
                secondary_uom = product.product_tmpl_id.secondary_uom_ids[:1]
                if secondary_uom:
                    values["secondary_uom_id"] = secondary_uom.id
                    if secondary_uom.factor and product_uom_qty:
                        # Calculate secondary quantity considering UoM conversion
                        # Convert to record if it's an ID
                        if isinstance(product_uom, int):
                            product_uom = self.env["uom.uom"].browse(product_uom)
                        base_uom = product.uom_id
                        secondary_uom_record = secondary_uom.uom_id
                        
                        # If move UoM is same as base UoM, use factor directly
                        if product_uom.id == base_uom.id:
                            values["secondary_uom_qty"] = product_uom_qty * secondary_uom.factor
                        # If secondary UoM is same as move UoM, quantity is the same
                        elif product_uom.id == secondary_uom_record.id:
                            values["secondary_uom_qty"] = product_uom_qty
                        else:
                            # Convert directly from move UoM to secondary UoM
                            category = product_uom.category_id
                            if category and secondary_uom_record.category_id.id == category.id:
                                reference_uoms = category.uom_ids.filtered(lambda u: abs(u.factor - 1.0) < 0.0001)
                                if reference_uoms:
                                    reference_uom = reference_uoms[0]
                                    if abs(secondary_uom_record.factor - 1.0) < 0.0001:
                                        # Secondary is reference
                                        values["secondary_uom_qty"] = product_uom_qty * product_uom.factor
                                    else:
                                        # Convert through reference
                                        if secondary_uom_record.factor:
                                            values["secondary_uom_qty"] = (
                                                product_uom_qty * product_uom.factor / secondary_uom_record.factor
                                            )
                                        else:
                                            values["secondary_uom_qty"] = 0.0
                                else:
                                    # Fallback: direct conversion
                                    values["secondary_uom_qty"] = product_uom._compute_quantity(
                                        product_uom_qty, secondary_uom_record, rounding_method='HALF-UP'
                                    )
                            else:
                                # Fallback: direct conversion
                                values["secondary_uom_qty"] = product_uom._compute_quantity(
                                    product_uom_qty, secondary_uom_record, rounding_method='HALF-UP'
                                )
        # For main finished product, transfer secondary unit from production order
        # Check if it's the main product (not a byproduct)
        elif product and product.id == self.product_id.id and self.secondary_uom_id:
            values["secondary_uom_id"] = self.secondary_uom_id.id
            if self.secondary_uom_qty:
                values["secondary_uom_qty"] = self.secondary_uom_qty
            elif self.secondary_uom_id.factor and product_uom_qty:
                # Calculate secondary quantity considering UoM conversion
                # product_uom is the UoM used in the move (may differ from product base UoM)
                # Convert to record if it's an ID
                if isinstance(product_uom, int):
                    product_uom = self.env["uom.uom"].browse(product_uom)
                base_uom = product.uom_id
                secondary_uom_record = self.secondary_uom_id.uom_id
                
                # If move UoM is same as base UoM, use factor directly
                if product_uom.id == base_uom.id:
                    values["secondary_uom_qty"] = product_uom_qty * self.secondary_uom_id.factor
                # If secondary UoM is same as move UoM, quantity is the same
                elif product_uom.id == secondary_uom_record.id:
                    values["secondary_uom_qty"] = product_uom_qty
                else:
                    # Convert directly from move UoM to secondary UoM
                    category = product_uom.category_id
                    if category and secondary_uom_record.category_id.id == category.id:
                        reference_uoms = category.uom_ids.filtered(lambda u: abs(u.factor - 1.0) < 0.0001)
                        if reference_uoms:
                            reference_uom = reference_uoms[0]
                            if abs(secondary_uom_record.factor - 1.0) < 0.0001:
                                # Secondary is reference
                                values["secondary_uom_qty"] = product_uom_qty * product_uom.factor
                            else:
                                # Convert through reference
                                if secondary_uom_record.factor:
                                    values["secondary_uom_qty"] = (
                                        product_uom_qty * product_uom.factor / secondary_uom_record.factor
                                    )
                                else:
                                    values["secondary_uom_qty"] = 0.0
                        else:
                            # Fallback: direct conversion
                            values["secondary_uom_qty"] = product_uom._compute_quantity(
                                product_uom_qty, secondary_uom_record, rounding_method='HALF-UP'
                            )
                    else:
                        # Fallback: direct conversion
                        values["secondary_uom_qty"] = product_uom._compute_quantity(
                            product_uom_qty, secondary_uom_record, rounding_method='HALF-UP'
                        )
        return values

