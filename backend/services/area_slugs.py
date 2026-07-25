"""Resolves free-text area input (English or Japanese, anywhere in Japan) to a
searchable HOME'S/SUUMO URL.

Coverage is tiered, and that tiering is deliberate:
  - Tokyo's 23 special wards: precise ward-level URLs (both sites confirmed
    working — see services/parsers/*). This is where the hand-built fallback
    corpus (services/corpus.py) also lives, since it's Tokyo-only real data.
  - Every other prefecture: precise city/ward-level slugs are NOT hand-mapped
    (Japan has ~1,700 municipalities with inconsistent slug patterns — e.g.
    Osaka's wards are "{prefecture}_{ward}-city" on HOME'S, not "{ward}-city"
    like Tokyo's special wards). Instead we use the PREFECTURE-level page,
    confirmed working on both sites for Tokyo/Osaka/Fukuoka/Hokkaido during
    spec-writing. This gives real, live, nationwide coverage without a
    precision claim we can't back up.
  - There is no local fallback corpus outside Tokyo. If live search fails for
    a non-Tokyo area, search_agent.find_candidates reports "no_data" rather
    than silently returning Tokyo rows mislabeled as the requested area.
"""
import re
from dataclasses import dataclass

PREFECTURE_ROMAJI: dict[str, str] = {
    "北海道": "hokkaido", "青森県": "aomori", "岩手県": "iwate", "宮城県": "miyagi",
    "秋田県": "akita", "山形県": "yamagata", "福島県": "fukushima", "茨城県": "ibaraki",
    "栃木県": "tochigi", "群馬県": "gunma", "埼玉県": "saitama", "千葉県": "chiba",
    "東京都": "tokyo", "神奈川県": "kanagawa", "新潟県": "niigata", "富山県": "toyama",
    "石川県": "ishikawa", "福井県": "fukui", "山梨県": "yamanashi", "長野県": "nagano",
    "岐阜県": "gifu", "静岡県": "shizuoka", "愛知県": "aichi", "三重県": "mie",
    "滋賀県": "shiga", "京都府": "kyoto", "大阪府": "osaka", "兵庫県": "hyogo",
    "奈良県": "nara", "和歌山県": "wakayama", "鳥取県": "tottori", "島根県": "shimane",
    "岡山県": "okayama", "広島県": "hiroshima", "山口県": "yamaguchi", "徳島県": "tokushima",
    "香川県": "kagawa", "愛媛県": "ehime", "高知県": "kochi", "福岡県": "fukuoka",
    "佐賀県": "saga", "長崎県": "nagasaki", "熊本県": "kumamoto", "大分県": "oita",
    "宮崎県": "miyazaki", "鹿児島県": "kagoshima", "沖縄県": "okinawa",
}

# Precise ward-level mapping — Tokyo's 23 special wards only (see module docstring).
TOKYO_WARD_ROMAJI: dict[str, str] = {
    "千代田区": "chiyoda", "中央区": "chuo", "港区": "minato", "新宿区": "shinjuku",
    "文京区": "bunkyo", "台東区": "taito", "墨田区": "sumida", "江東区": "koto",
    "品川区": "shinagawa", "目黒区": "meguro", "大田区": "ota", "世田谷区": "setagaya",
    "渋谷区": "shibuya", "中野区": "nakano", "杉並区": "suginami", "豊島区": "toshima",
    "北区": "kita", "荒川区": "arakawa", "板橋区": "itabashi", "練馬区": "nerima",
    "足立区": "adachi", "葛飾区": "katsushika", "江戸川区": "edogawa",
}

_ROMAJI_TO_PREFECTURE = {v: k for k, v in PREFECTURE_ROMAJI.items()}
_ROMAJI_TO_WARD = {v: k for k, v in TOKYO_WARD_ROMAJI.items()}


@dataclass(frozen=True)
class ResolvedArea:
    prefecture_ja: str
    prefecture_romaji: str
    ward_ja: str | None = None  # set only when precisely mapped (Tokyo wards today)

    @property
    def is_precise(self) -> bool:
        return self.ward_ja is not None

    @property
    def label(self) -> str:
        return f"{self.prefecture_ja}{self.ward_ja}" if self.ward_ja else self.prefecture_ja


def resolve_area(text: str) -> ResolvedArea | None:
    """Best-effort match of free text (English or Japanese) to a searchable area,
    anywhere in Japan. Ward-level precision only for Tokyo; everything else
    resolves to its prefecture. Returns None if nothing matches."""
    if not text:
        return None
    normalized = text.strip().lower()

    # Tokyo ward — precise path, checked first since it's more specific.
    for ward_ja, romaji in TOKYO_WARD_ROMAJI.items():
        if ward_ja in text or romaji in normalized:
            return ResolvedArea(prefecture_ja="東京都", prefecture_romaji="tokyo", ward_ja=ward_ja)

    # Any other prefecture — prefecture-level only.
    for pref_ja, romaji in PREFECTURE_ROMAJI.items():
        stripped_ja = re.sub(r"[都道府県]$", "", pref_ja)
        if pref_ja in text or stripped_ja in text or romaji in normalized:
            if pref_ja == "東京都":
                return ResolvedArea(prefecture_ja=pref_ja, prefecture_romaji=romaji)
            return ResolvedArea(prefecture_ja=pref_ja, prefecture_romaji=romaji)
    return None


def homes_url(area: ResolvedArea) -> str:
    if area.is_precise and area.prefecture_ja == "東京都":
        return f"https://www.homes.co.jp/chintai/tokyo/{TOKYO_WARD_ROMAJI[area.ward_ja]}-city/list/"
    return f"https://www.homes.co.jp/chintai/{area.prefecture_romaji}/list/"


def suumo_url(area: ResolvedArea) -> str:
    if area.is_precise and area.prefecture_ja == "東京都":
        return f"https://suumo.jp/chintai/tokyo/sc_{TOKYO_WARD_ROMAJI[area.ward_ja]}/"
    return f"https://suumo.jp/chintai/{area.prefecture_romaji}/"
