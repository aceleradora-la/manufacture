# Copyright 2025 Aceleradora
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MrpUnbuild(models.Model):
    _inherit = "mrp.unbuild"

    secondary_uom_id = fields.Many2one(
        comodel_name="product.secondary.unit",
        string="Secondary UoM",
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
        help="Secondary unit of measure for the product to unbuild",
    )
    secondary_uom_qty = fields.Float(
        string="Secondary Qty",
        digits="Product Unit of Measure",
        help="Quantity in secondary unit of measure",
        store=True,
    )

    @api.onchange("product_id", "product_qty")
    def _onchange_product_id_secondary_unit(self):
        """Update secondary unit when product or quantity changes."""
        if not self.product_id:
            self.secondary_uom_id = False
            self.secondary_uom_qty = 0.0
            return
        # Get secondary unit from product template if available
        if hasattr(self.product_id.product_tmpl_id, "secondary_uom_ids"):
            secondary_uom = self.product_id.product_tmpl_id.secondary_uom_ids[:1]
            if secondary_uom:
                self.secondary_uom_id = secondary_uom
                self._compute_secondary_uom_qty()
        # Try to get from related production order if available
        elif self.mo_id and hasattr(self.mo_id, "secondary_uom_id"):
            if self.mo_id.secondary_uom_id:
                self.secondary_uom_id = self.mo_id.secondary_uom_id
                if self.mo_id.secondary_uom_qty:
                    self.secondary_uom_qty = self.mo_id.secondary_uom_qty

    @api.onchange("secondary_uom_id", "secondary_uom_qty")
    def _onchange_secondary_uom(self):
        """Update product quantity when secondary unit changes."""
        if self.secondary_uom_id and self.secondary_uom_qty:
            factor = self.secondary_uom_id.factor
            if factor:
                self.product_qty = self.secondary_uom_qty * factor

    def _compute_secondary_uom_qty(self):
        """Compute secondary quantity from product quantity."""
        for unbuild in self:
            if (
                unbuild.secondary_uom_id
                and unbuild.product_qty
                and unbuild.secondary_uom_id.factor
            ):
                unbuild.secondary_uom_qty = (
                    unbuild.product_qty / unbuild.secondary_uom_id.factor
                )
            else:
                unbuild.secondary_uom_qty = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """Compute secondary quantity on create and transfer from MO if available."""
        unbuilds = super().create(vals_list)
        for unbuild in unbuilds:
            # Try to get from related production order if available
            if unbuild.mo_id and hasattr(unbuild.mo_id, "secondary_uom_id"):
                if unbuild.mo_id.secondary_uom_id and not unbuild.secondary_uom_id:
                    unbuild.secondary_uom_id = unbuild.mo_id.secondary_uom_id.id
                    if unbuild.mo_id.secondary_uom_qty:
                        unbuild.secondary_uom_qty = unbuild.mo_id.secondary_uom_qty
            # Compute if we have secondary unit but not quantity
            if unbuild.secondary_uom_id and not unbuild.secondary_uom_qty:
                unbuild._compute_secondary_uom_qty()
        return unbuilds

    def write(self, vals):
        """Compute secondary quantity on write."""
        res = super().write(vals)
        if "product_qty" in vals and not vals.get("secondary_uom_qty"):
            for unbuild in self:
                if unbuild.secondary_uom_id:
                    unbuild._compute_secondary_uom_qty()
        return res

    def _generate_move_from_existing_move(
        self, move, factor, location_id, location_dest_id
    ):
        """Add secondary unit info to moves generated from unbuild."""
        result = super()._generate_move_from_existing_move(
            move, factor, location_id, location_dest_id
        )
        # Transfer secondary unit from unbuild order if available
        if self.secondary_uom_id:
            # result can be a move or a dict, handle both cases
            if hasattr(result, 'secondary_uom_id'):
                # It's a move record
                if not result.secondary_uom_id:
                    result.secondary_uom_id = self.secondary_uom_id.id
                if not result.secondary_uom_qty:
                    if self.secondary_uom_qty:
                        # Apply factor to secondary quantity
                        result.secondary_uom_qty = self.secondary_uom_qty * factor
                    elif self.secondary_uom_id.factor and hasattr(result, 'product_uom_qty'):
                        result.secondary_uom_qty = (
                            result.product_uom_qty / self.secondary_uom_id.factor
                        )
            elif isinstance(result, dict):
                # It's a dict of values for creating the move
                if not result.get('secondary_uom_id'):
                    result['secondary_uom_id'] = self.secondary_uom_id.id
                if not result.get('secondary_uom_qty'):
                    if self.secondary_uom_qty:
                        result['secondary_uom_qty'] = self.secondary_uom_qty * factor
                    elif self.secondary_uom_id.factor and result.get('product_uom_qty'):
                        result['secondary_uom_qty'] = (
                            result['product_uom_qty'] / self.secondary_uom_id.factor
                        )
        return result

