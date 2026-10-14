from shop.models import Product


class Cart:
    KEY = "cart"

    def __init__(self, request):
        self.request = request
        self.session = request.session
        self.data = self.session.get(self.KEY, {})

    def _save(self):
        self.session[self.KEY] = self.data
        self.session.modified = True

    def set(self, product_id, qty):
        pid = str(product_id)
        if qty <= 0:
            self.data.pop(pid, None)
        else:
            self.data[pid] = min(int(qty), 500)
        self._save()

    def add(self, product_id, qty=1):
        self.set(product_id, int(self.data.get(str(product_id), 0)) + int(qty))

    def clear(self):
        self.data = {}
        self._save()

    def __len__(self):
        return sum(int(q) for q in self.data.values())

    def lines(self):
        """List of dicts with product, qty, unit_price, line_total, wholesale, hint."""
        if not self.data:
            return []
        products = {str(p.pk): p for p in Product.objects.active().filter(pk__in=self.data.keys())}
        out, changed = [], False
        for pid, qty in list(self.data.items()):
            p = products.get(pid)
            if not p or p.stock <= 0:
                self.data.pop(pid)
                changed = True
                continue
            qty = min(int(qty), p.stock)
            if qty != int(self.data[pid]):
                self.data[pid] = qty
                changed = True
            unit, wholesale = p.price_for(self.request.user, qty)
            hint = ""
            if p.wholesale_price and not wholesale:
                if p.is_wholesale_buyer(self.request.user):
                    need = p.wholesale_min_qty - qty
                    hint = f"Add {need} more to get the wholesale price of ₹{p.wholesale_price:,.0f}"
                else:
                    hint = "Wholesale rates are available for verified business accounts"
            out.append({"product": p, "qty": qty, "unit_price": unit, "line_total": unit * qty, "wholesale": wholesale, "hint": hint})
        if changed:
            self._save()
        return out
