from agents.fee_extract import extract_real_fees
from schemas import CostBreakdown, CostLineItem, Listing
from services.daytona import run_cost_model

CHUKAI_TAX_RATE = 0.10  # applied only when a real chukai_months figure is found — it's a tax rate, not a guessed fee


def _line(label_en: str, amount_jpy: int, frequency_en: str) -> CostLineItem:
    return CostLineItem(label_en=label_en, amount_jpy=amount_jpy, frequency_en=frequency_en)


async def audit_cost(listing: Listing) -> CostBreakdown:
    """Computes cost using ONLY values the listing actually states (or that
    an extraction agent found explicitly in its text) — never a fabricated
    default. Any fee that isn't stated is excluded from the total (contributes
    ¥0) and disclosed in `assumptions` as unknown, so upfront_total_jpy and
    effective_monthly_jpy are an honest floor, not a guessed full picture.
    Every fee that IS known (including a legitimately stated ¥0, e.g. "no key
    money") goes into `items` instead, so the UI can show exactly where the
    gap between advertised and effective monthly comes from."""
    items: list[CostLineItem] = []
    unknown: list[str] = []

    items.append(_line("Management fee", listing.kanrihi_jpy, "monthly"))

    if listing.shikikin_months is not None:
        shikikin_jpy = round(listing.shikikin_months * listing.rent_jpy)
        items.append(_line("Security deposit (shikikin)", shikikin_jpy, "one-time"))
    else:
        shikikin_jpy = 0
        unknown.append("Security deposit (shikikin) not stated by this listing — excluded from the total below, actual cost may be higher")

    if listing.reikin_months is not None:
        reikin_jpy = round(listing.reikin_months * listing.rent_jpy)
        items.append(_line("Key money (reikin)", reikin_jpy, "one-time"))
    else:
        reikin_jpy = 0
        unknown.append("Key money (reikin) not stated by this listing — excluded from the total below, actual cost may be higher")

    fees = await extract_real_fees(listing.conditions_text)

    if fees["chukai_months"] is not None:
        chukai_jpy = round(listing.rent_jpy * fees["chukai_months"] * (1 + CHUKAI_TAX_RATE))
        items.append(_line("Agency fee", chukai_jpy, "one-time"))
    else:
        chukai_jpy = 0
        unknown.append("Agency fee not stated by this listing — excluded from the total below, actual cost may be higher")

    if fees["hoshou_initial_jpy"] is not None:
        hoshou_initial_jpy = fees["hoshou_initial_jpy"]
        items.append(_line("Guarantor company — initial fee", hoshou_initial_jpy, "one-time"))
    else:
        hoshou_initial_jpy = 0
        unknown.append("Guarantor company initial fee not stated by this listing — excluded from the total below, actual cost may be higher")

    if fees["hoshou_annual_jpy"] is not None:
        hoshou_annual_jpy = fees["hoshou_annual_jpy"]
        items.append(_line("Guarantor company — annual renewal", hoshou_annual_jpy, "per year"))
    else:
        hoshou_annual_jpy = 0
        unknown.append("Guarantor company renewal fee not stated by this listing — excluded from the total below, actual cost may be higher")

    if fees["kasai_hoken_jpy"] is not None:
        kasai_hoken_jpy = fees["kasai_hoken_jpy"]
        items.append(_line("Fire insurance", kasai_hoken_jpy, "one-time"))
    else:
        kasai_hoken_jpy = 0
        unknown.append("Fire insurance not stated by this listing — excluded from the total below, actual cost may be higher")

    if fees["kagi_koukan_jpy"] is not None:
        kagi_koukan_jpy = fees["kagi_koukan_jpy"]
        items.append(_line("Key exchange", kagi_koukan_jpy, "one-time"))
    else:
        kagi_koukan_jpy = 0
        unknown.append("Key exchange fee not stated by this listing — excluded from the total below, actual cost may be higher")

    if fees["koushinryou_months"] is not None:
        koushinryou_jpy = round(listing.rent_jpy * fees["koushinryou_months"])
        items.append(_line("Lease renewal fee", koushinryou_jpy, "at each renewal"))
    else:
        koushinryou_jpy = 0
        unknown.append("Lease renewal fee not stated by this listing — excluded from the total below, actual cost may be higher")

    result, ran_in_sandbox = await run_cost_model(
        rent_jpy=listing.rent_jpy,
        kanrihi_jpy=listing.kanrihi_jpy,
        shikikin_jpy=shikikin_jpy,
        reikin_jpy=reikin_jpy,
        chukai_jpy=chukai_jpy,
        hoshou_initial_jpy=hoshou_initial_jpy,
        hoshou_annual_jpy=hoshou_annual_jpy,
        kasai_hoken_jpy=kasai_hoken_jpy,
        kagi_koukan_jpy=kagi_koukan_jpy,
        koushinryou_jpy=koushinryou_jpy,
    )
    if not ran_in_sandbox:
        unknown.append("Daytona sandbox unavailable — cost computed locally instead")

    advertised = listing.rent_jpy
    effective = result["effective_monthly_jpy"]
    markup_percent = ((effective / advertised) - 1) * 100 if advertised else 0.0

    return CostBreakdown(
        listing_id=listing.id,
        advertised_monthly_jpy=advertised,
        upfront_total_jpy=result["upfront_total_jpy"],
        effective_monthly_jpy=effective,
        markup_percent=round(markup_percent, 1),
        items=items,
        assumptions=unknown,
    )
