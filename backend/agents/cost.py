from agents.fee_extract import extract_real_fees
from schemas import CostBreakdown, Listing
from services.daytona import run_cost_model

CHUKAI_TAX_RATE = 0.10  # applied only when a real chukai_months figure is found — it's a tax rate, not a guessed fee


async def audit_cost(listing: Listing) -> CostBreakdown:
    """Computes cost using ONLY values the listing actually states (or that
    an extraction agent found explicitly in its text) — never a fabricated
    default. Any fee that isn't stated is excluded from the total (contributes
    ¥0) and disclosed in `assumptions` as unknown, so upfront_total_jpy and
    effective_monthly_jpy are an honest floor, not a guessed full picture."""
    unknown: list[str] = []

    if listing.shikikin_months is not None:
        shikikin_jpy = round(listing.shikikin_months * listing.rent_jpy)
    else:
        shikikin_jpy = 0
        unknown.append("敷金 (shikikin) not stated by this listing — excluded from the total below, actual cost may be higher")

    if listing.reikin_months is not None:
        reikin_jpy = round(listing.reikin_months * listing.rent_jpy)
    else:
        reikin_jpy = 0
        unknown.append("礼金 (reikin) not stated by this listing — excluded from the total below, actual cost may be higher")

    fees = await extract_real_fees(listing.conditions_text)

    if fees["chukai_months"] is not None:
        chukai_jpy = round(listing.rent_jpy * fees["chukai_months"] * (1 + CHUKAI_TAX_RATE))
    else:
        chukai_jpy = 0
        unknown.append("仲介手数料 (agency fee) not stated by this listing — excluded from the total below, actual cost may be higher")

    hoshou_initial_jpy = fees["hoshou_initial_jpy"] or 0
    if fees["hoshou_initial_jpy"] is None:
        unknown.append("保証会社初回費用 (guarantor initial fee) not stated by this listing — excluded from the total below, actual cost may be higher")

    hoshou_annual_jpy = fees["hoshou_annual_jpy"] or 0
    if fees["hoshou_annual_jpy"] is None:
        unknown.append("保証会社更新料 (guarantor renewal fee) not stated by this listing — excluded from the total below, actual cost may be higher")

    kasai_hoken_jpy = fees["kasai_hoken_jpy"] or 0
    if fees["kasai_hoken_jpy"] is None:
        unknown.append("火災保険 (fire insurance) not stated by this listing — excluded from the total below, actual cost may be higher")

    kagi_koukan_jpy = fees["kagi_koukan_jpy"] or 0
    if fees["kagi_koukan_jpy"] is None:
        unknown.append("鍵交換代 (key exchange) not stated by this listing — excluded from the total below, actual cost may be higher")

    if fees["koushinryou_months"] is not None:
        koushinryou_jpy = round(listing.rent_jpy * fees["koushinryou_months"])
    else:
        koushinryou_jpy = 0
        unknown.append("更新料 (renewal fee) not stated by this listing — excluded from the total below, actual cost may be higher")

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
        assumptions=unknown,
    )
