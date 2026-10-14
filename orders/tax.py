from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

TWO = Decimal("0.01")


def q(x):
    return Decimal(x).quantize(TWO, rounding=ROUND_HALF_UP)


def compute(lines, ship_state_code, config, payment_method=None):
    """Price a cart. `lines` come from Cart.lines().

    Returns per-line tax split plus order totals. GST is split into CGST+SGST when the
    delivery state equals the store state, otherwise IGST.
    """
    inclusive = settings.PRICES_INCLUDE_GST
    items, taxable_total, gst_total, goods_total = [], Decimal("0"), Decimal("0"), Decimal("0")
    for ln in lines:
        rate = Decimal(ln["product"].gst_rate)
        gross = ln["line_total"]
        if inclusive:
            taxable = q(gross * 100 / (100 + rate))
            gst = q(gross - taxable)
        else:
            taxable = q(gross)
            gst = q(taxable * rate / 100)
            gross = taxable + gst
        items.append({**ln, "rate": rate, "taxable": taxable, "gst": gst, "gross": gross})
        taxable_total += taxable
        gst_total += gst
        goods_total += gross

    intra = (ship_state_code or config.state_code) == config.state_code
    cgst = q(gst_total / 2) if intra else Decimal("0")
    sgst = (gst_total - cgst) if intra else Decimal("0")
    igst = Decimal("0") if intra else gst_total

    free = goods_total >= config.free_shipping_above
    shipping = Decimal("0") if (free or not items) else (config.shipping_local if intra else config.shipping_national)
    cod_fee = config.cod_fee if payment_method == "cod" else Decimal("0")
    return {
        "items": items, "taxable_total": taxable_total, "gst_total": gst_total, "goods_total": goods_total,
        "cgst": cgst, "sgst": sgst, "igst": igst, "intra": intra,
        "shipping": q(shipping), "cod_fee": q(cod_fee), "free_shipping": free,
        "free_shipping_gap": max(config.free_shipping_above - goods_total, Decimal("0")),
        "free_shipping_pct": int(min(goods_total * 100 / config.free_shipping_above, 100)) if config.free_shipping_above else 100,
        "grand_total": q(goods_total + shipping + cod_fee),
        "inclusive": inclusive,
    }
