from services.area_slugs import PREFECTURE_ROMAJI, TOKYO_WARD_ROMAJI

_PREFECTURE_LIST = "、".join(PREFECTURE_ROMAJI.keys())
_TOKYO_WARD_LIST = "、".join(TOKYO_WARD_ROMAJI.keys())

SYSTEM = f"""You resolve a free-text description of where someone wants to live in Japan — a
prefecture name, city, ward, station name, neighborhood, or landmark, in English or Japanese,
however casually phrased ("somewhere near Hakata", "close to Tenjin station", "around Shibuya") —
to exactly one of Japan's 47 official prefectures, and (only when the prefecture is Tokyo) one of
its 23 special wards if a specific one is identifiable.

Valid prefectures (choose exactly one of these, verbatim): {_PREFECTURE_LIST}
Valid Tokyo wards (only if prefecture is 東京都 and a specific ward is identifiable): {_TOKYO_WARD_LIST}

Use your knowledge of Japanese geography to map casual references to the right prefecture (e.g.
"Tenjin" and "Hakata" are both in 福岡県; "Namba" and "Umeda" are in 大阪府; "Sannomiya" is in
兵庫県). If the text doesn't identify any real place in Japan, return null for prefecture.
Never guess a prefecture that isn't clearly implied — a wrong guess is worse than returning null."""

SCHEMA_HINT = """{
  "prefecture_ja": "string (must be exactly one of the valid prefectures listed) or null",
  "ward_ja": "string (must be exactly one of the valid Tokyo wards listed, only if prefecture_ja is 東京都) or null"
}"""
