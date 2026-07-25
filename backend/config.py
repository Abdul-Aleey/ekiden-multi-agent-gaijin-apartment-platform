import os

from dotenv import load_dotenv

load_dotenv()

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

LIVE_SEARCH_TIMEOUT_S = float(os.environ.get("LIVE_SEARCH_TIMEOUT_S", "8.0"))
LIVE_SEARCH_USER_AGENT = os.environ.get(
    "LIVE_SEARCH_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
)

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
CORPUS_DB_PATH = os.path.join(DATA_DIR, "listings.sqlite")
BENCHMARKS_PATH = os.path.join(DATA_DIR, "benchmarks.json")
UR_PROPERTIES_PATH = os.path.join(DATA_DIR, "ur_properties.json")
GUARANTOR_COMPANIES_PATH = os.path.join(DATA_DIR, "guarantor_companies.json")

DAYTONA_API_KEY = os.environ.get("DAYTONA_API_KEY")
DAYTONA_BASE_URL = os.environ.get("DAYTONA_BASE_URL")
