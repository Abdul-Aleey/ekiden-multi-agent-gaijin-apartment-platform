from agents.fee_extract import extract_real_fees
from schemas import CostBreakdown, CostLineItem, Listing
from services.daytona import LEASE_MONTHS, run_cost_model

CHUKAI_TAX_RATE = 0.10  # applied only when a real chukai_months figure is found — it's a tax rate, not a guessed fee


def _line(label_en: str, amount_jpy: int) -> CostLineItem:
    return CostLineItem(label_en=label_en, amount_jpy=amount_jpy)


async def audit_cost(listing: Listing) -> CostBreakdown:
    """Computes cost using ONLY values the listing actually states (or that
    an extraction agent found explicitly in its text) — never a fabricated
    default. Any fee that isn't stated contributes ¥0 to every total below and
    is disclosed in `assumptions` instead of appearing as a line item, so every
    total is an honest floor, not a guessed full picture.

    Three separate, non-overlapping breakdowns, each guaranteed (by using the
    exact same per-fee amounts in both the item list and the total) to sum
    exactly to its own total:
      - upfront_items -> upfront_total_jpy: paid once, at move-in.
      - effective_monthly_items -> effective_monthly_jpy: ongoing monthly cost,
        amortizing the one-time move-in fees over a standard LEASE_MONTHS lease.
      - renewal_items: periodic costs after move-in (guarantor renewal, lease
        renewal fee) — deliberately excluded from both totals above, since
        folding a once-every-few-years cost into "effective monthly" hides it
        rather than disclosing it.
    """
    unknown: list[str] = []

    if listing.shikikin_months is not None:
        shikikin_jpy = round(listing.shikikin_months * listing.rent_jpy)
    else:
        shikikin_jpy = None
        unknown.append("Security deposit (shikikin) not stated by this listing — excluded from the totals below, actual cost may be higher")

    if listing.reikin_months is not None:
        reikin_jpy = round(listing.reikin_months * listing.rent_jpy)
    else:
        reikin_jpy = None
        unknown.append("Key money (reikin) not stated by this listing — excluded from the totals below, actual cost may be higher")

    fees = await extract_real_fees(listing.conditions_text)

    if fees["chukai_months"] is not None:
        chukai_jpy = round(listing.rent_jpy * fees["chukai_months"] * (1 + CHUKAI_TAX_RATE))
    else:
        chukai_jpy = None
        unknown.append("Agency fee not stated by this listing — excluded from the totals below, actual cost may be higher")

    hoshou_initial_jpy = fees["hoshou_initial_jpy"]
    if hoshou_initial_jpy is None:
        unknown.append("Guarantor company initial fee not stated by this listing — excluded from the totals below, actual cost may be higher")

    hoshou_annual_jpy = fees["hoshou_annual_jpy"]
    if hoshou_annual_jpy is None:
        unknown.append("Guarantor company renewal fee not stated by this listing")

    kasai_hoken_jpy = fees["kasai_hoken_jpy"]
    if kasai_hoken_jpy is None:
        unknown.append("Fire insurance not stated by this listing — excluded from the totals below, actual cost may be higher")

    kagi_koukan_jpy = fees["kagi_koukan_jpy"]
    if kagi_koukan_jpy is None:
        unknown.append("Key exchange fee not stated by this listing — excluded from the totals below, actual cost may be higher")

    if fees["koushinryou_months"] is not None:
        koushinryou_jpy = round(listing.rent_jpy * fees["koushinryou_months"])
    else:
        koushinryou_jpy = None
        unknown.append("Lease renewal fee not stated by this listing")

    result, ran_in_sandbox = await run_cost_model(
        rent_jpy=listing.rent_jpy,
        kanrihi_jpy=listing.kanrihi_jpy,
        shikikin_jpy=shikikin_jpy or 0,
        reikin_jpy=reikin_jpy or 0,
        chukai_jpy=chukai_jpy or 0,
        hoshou_initial_jpy=hoshou_initial_jpy or 0,
        kasai_hoken_jpy=kasai_hoken_jpy or 0,
        kagi_koukan_jpy=kagi_koukan_jpy or 0,
    )
    if not ran_in_sandbox:
        unknown.append("Daytona sandbox unavailable — cost computed locally instead")

    upfront_items = [_line("First month rent", listing.rent_jpy), _line("First month management fee", listing.kanrihi_jpy)]
    effective_monthly_items = [_line("Rent", listing.rent_jpy), _line("Management fee", listing.kanrihi_jpy)]
    for label, amount in (
        ("Security deposit (shikikin)", shikikin_jpy),
        ("Key money (reikin)", reikin_jpy),
        ("Agency fee", chukai_jpy),
        ("Guarantor company — initial fee", hoshou_initial_jpy),
        ("Fire insurance", kasai_hoken_jpy),
        ("Key exchange", kagi_koukan_jpy),
    ):
        if amount is not None:
            upfront_items.append(_line(label, amount))
            effective_monthly_items.append(_line(f"{label}, amortized", round(amount / LEASE_MONTHS)))

    renewal_items = []
    if hoshou_annual_jpy is not None:
        renewal_items.append(_line("Guarantor company — annual renewal", hoshou_annual_jpy))
    if koushinryou_jpy is not None:
        renewal_items.append(_line("Lease renewal fee (at contract renewal)", koushinryou_jpy))

    advertised = listing.rent_jpy
    effective = result["effective_monthly_jpy"]
    markup_percent = ((effective / advertised) - 1) * 100 if advertised else 0.0

    return CostBreakdown(
        listing_id=listing.id,
        advertised_monthly_jpy=advertised,
        upfront_total_jpy=result["upfront_total_jpy"],
        upfront_items=upfront_items,
        effective_monthly_jpy=effective,
        effective_monthly_items=effective_monthly_items,
        renewal_items=renewal_items,
        markup_percent=round(markup_percent, 1),
        assumptions=unknown,
    )
