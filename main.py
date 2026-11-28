from __future__ import annotations

import datetime as dt
from typing import Dict, List, Literal, Optional

import swisseph as swe
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator


SIGN_NAMES = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena",
]
SIGN_ENGLISH = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
]
TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
]
PLANET_IDS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,
}
VIMSHOTTARI_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIMSHOTTARI_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}


class BirthDetails(BaseModel):
    name: Optional[str] = Field(default=None, max_length=80)
    gender: Optional[Literal["male", "female", "other"]] = None
    day: int = Field(ge=1, le=31)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=1800, le=2200)
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59, default=0)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    timezone: float = Field(default=5.5, ge=-14, le=14)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value and value.strip() else None


class MatchDetails(BaseModel):
    bride: BirthDetails
    groom: BirthDetails


app = FastAPI(
    title="Divya Astro API",
    description="Astrology calculations for kundli, Panchang, dashas, compatibility and yogas.",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

swe.set_sid_mode(swe.SIDM_LAHIRI)


def utc_julian_day(data: BirthDetails) -> float:
    try:
        local = dt.datetime(data.year, data.month, data.day, data.hour, data.minute)
        utc = local - dt.timedelta(hours=data.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid birth date: {exc}") from exc
    return swe.julday(
        utc.year, utc.month, utc.day,
        utc.hour + utc.minute / 60 + utc.second / 3600,
    )


def sign_info(longitude: float) -> Dict:
    longitude = longitude % 360
    index = int(longitude // 30)
    degree = longitude % 30
    return {
        "longitude": round(longitude, 4),
        "sign": SIGN_NAMES[index],
        "sign_english": SIGN_ENGLISH[index],
        "sign_number": index + 1,
        "degree_in_sign": round(degree, 4),
    }


def house_of(sign_number: int, lagna_number: int) -> int:
    return (sign_number - lagna_number) % 12 + 1


def get_chart(data: BirthDetails) -> Dict:
    jd = utc_julian_day(data)
    ayanamsa = swe.get_ayanamsa_ut(jd)

    planets: Dict[str, Dict] = {}
    for name, pid in PLANET_IDS.items():
        pos, _ = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)
        planets[name] = sign_info(pos[0])

    rahu_longitude = planets["Rahu"]["longitude"]
    planets["Ketu"] = sign_info((rahu_longitude + 180) % 360)

    cusps, ascmc = swe.houses(jd, data.lat, data.lon, b"P")
    lagna_longitude = (ascmc[0] - ayanamsa) % 360
    lagna = sign_info(lagna_longitude)

    return {
        "jd_ut": round(jd, 6),
        "ayanamsa": round(ayanamsa, 4),
        "lagna": lagna,
        "planets": planets,
        "houses": {
            str(index + 1): sign_info(cusps[index])[ "sign"]
            for index in range(12)
        },
    }


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def web_app():
    return HTMLResponse(APP_HTML)


@app.get("/api")
def api_status():
    return {
        "status": "running",
        "name": "Divya Astro API",
        "version": "2.0.0",
        "documentation": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "divya-astro-api"}


@app.post("/kundli")
def get_kundli(data: BirthDetails):
    chart = get_chart(data)
    lagna = chart["lagna"]
    moon = chart["planets"]["Moon"]
    moon_longitude = moon["longitude"]
    nakshatra_number = int(moon_longitude // (360 / 27))
    return {
        "name": data.name,
        "birth": {
            "date": f"{data.year:04d}-{data.month:02d}-{data.day:02d}",
            "time": f"{data.hour:02d}:{data.minute:02d}",
            "timezone_offset": data.timezone,
            "latitude": data.lat,
            "longitude": data.lon,
        },
        "lagna": lagna["sign"],
        "lagna_english": lagna["sign_english"],
        "lagna_longitude": lagna["longitude"],
        "ayanamsa": chart["ayanamsa"],
        "moon_sign": moon["sign"],
        "moon_nakshatra": NAKSHATRA_NAMES[nakshatra_number],
        "planets": chart["planets"],
        "houses": chart["houses"],
    }


@app.post("/panchang")
def get_panchang(data: BirthDetails):
    jd = utc_julian_day(data)
    moon_pos, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)
    sun_pos, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)
    moon_longitude = moon_pos[0] % 360
    sun_longitude = sun_pos[0] % 360
    elongation = (moon_longitude - sun_longitude) % 360

    tithi_index = int(elongation // 12)
    paksha = "Shukla" if tithi_index < 15 else "Krishna"
    tithi_name = TITHI_NAMES[tithi_index % 15]
    nakshatra_index = int(moon_longitude // (360 / 27))
    pada = int((moon_longitude % (360 / 27)) // (360 / 27 / 4)) + 1

    sunrise = None
    sunset = None
    try:
        geopos = (data.lon, data.lat, 0)
        jd_start = swe.julday(data.year, data.month, data.day, 0)
        sunrise_jd = swe.rise_trans(jd_start, swe.SUN, swe.CALC_RISE, geopos, 0, 0)[1][0]
        sunset_jd = swe.rise_trans(jd_start, swe.SUN, swe.CALC_SET, geopos, 0, 0)[1][0]
        sunrise = _jd_to_local_clock(sunrise_jd, data.timezone)
        sunset = _jd_to_local_clock(sunset_jd, data.timezone)
    except (RuntimeError, swe.Error):
        pass

    return {
        "date": f"{data.year:04d}-{data.month:02d}-{data.day:02d}",
        "tithi": tithi_name,
        "tithi_number": tithi_index + 1,
        "paksha": paksha,
        "nakshatra": NAKSHATRA_NAMES[nakshatra_index],
        "nakshatra_pada": pada,
        "sunrise": sunrise,
        "sunset": sunset,
        "moon_longitude": round(moon_longitude, 4),
        "sun_longitude": round(sun_longitude, 4),
    }


def _jd_to_local_clock(jd: float, timezone: float) -> str:
    year, month, day, decimal_hour = swe.revjul(jd)
    local_hour = decimal_hour + timezone
    hour = int(local_hour) % 24
    minute = int(round((local_hour % 1) * 60)) % 60
    return f"{hour:02d}:{minute:02d}"


@app.post("/vimsottari-dasha")
def get_vimshottari_dasha(data: BirthDetails):
    chart = get_chart(data)
    moon_longitude = chart["planets"]["Moon"]["longitude"]
    nakshatra_index = int(moon_longitude // (360 / 27))
    nakshatra_lord = [
        "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"
    ][nakshatra_index % 9]
    elapsed_fraction = (moon_longitude % (360 / 27)) / (360 / 27)
    start_period_years = VIMSHOTTARI_YEARS[nakshatra_lord] * (1 - elapsed_fraction)

    start_index = VIMSHOTTARI_ORDER.index(nakshatra_lord)
    sequence = []
    cursor = dt.date(data.year, data.month, data.day)
    for offset in range(9):
        lord = VIMSHOTTARI_ORDER[(start_index + offset) % 9]
        years = start_period_years if offset == 0 else VIMSHOTTARI_YEARS[lord]
        end = cursor + dt.timedelta(days=round(years * 365.2425))
        sequence.append({
            "mahadasha": lord,
            "start": cursor.isoformat(),
            "end": end.isoformat(),
            "years": round(years, 2),
        })
        cursor = end

    return {
        "system": "Vimshottari",
        "moon_nakshatra": NAKSHATRA_NAMES[nakshatra_index],
        "birth_dasha_lord": nakshatra_lord,
        "sequence": sequence,
    }


@app.post("/spiritual-karmic")
def spiritual_karmic(data: BirthDetails):
    chart = get_chart(data)
    planets = chart["planets"]
    lagna_number = chart["lagna"]["sign_number"]

    eligible = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"]
    atmakaraka = max(
        eligible,
        key=lambda name: planets[name]["degree_in_sign"],
    )
    rahu_house = house_of(planets["Rahu"]["sign_number"], lagna_number)
    ketu_house = house_of(planets["Ketu"]["sign_number"], lagna_number)
    moon_house = house_of(planets["Moon"]["sign_number"], lagna_number)
    jupiter_house = house_of(planets["Jupiter"]["sign_number"], lagna_number)

    score = 0
    indicators = []
    if ketu_house in [5, 8, 12]:
        score += 25
        indicators.append(f"Ketu in {ketu_house}th house - natural detachment")
    if moon_house in [5, 8, 9, 12]:
        score += 15
        indicators.append(f"Moon in {moon_house}th house - intuitive mind")
    if jupiter_house in [1, 9, 12]:
        score += 20
        indicators.append(f"Jupiter in {jupiter_house}th house - dharma and guidance")
    if chart["lagna"]["sign"] in ["Vrischika", "Meena", "Karka"]:
        score += 15
        indicators.append("Water-sign Lagna - intuitive temperament")
    if planets["Moon"]["sign"] == planets["Ketu"]["sign"]:
        score += 15
        indicators.append("Moon-Ketu conjunction - strong spiritual introspection")

    level = "Deep spiritual potential" if score >= 70 else "Spiritual seeker" if score >= 40 else "Material focus with later spiritual growth"
    meanings = {
        "Sun": "Leadership, responsibility and ego discipline",
        "Moon": "Emotional maturity and healthy detachment",
        "Mars": "Controlled courage and purposeful action",
        "Mercury": "Clear, ethical and useful communication",
        "Jupiter": "Wisdom, teaching and dharma",
        "Venus": "Love, beauty and balanced relationships",
        "Saturn": "Discipline, service and patient karma",
        "Rahu": "Transform desire into purposeful ambition",
    }
    return {
        "atmakaraka": atmakaraka,
        "atmakaraka_degree": planets[atmakaraka]["degree_in_sign"],
        "atmakaraka_meaning": meanings[atmakaraka],
        "rahu_house": rahu_house,
        "ketu_house": ketu_house,
        "rahu_sign": planets["Rahu"]["sign"],
        "ketu_sign": planets["Ketu"]["sign"],
        "karmic_pattern": f"Rahu in the {rahu_house}th house points toward growth in that life area; Ketu in the {ketu_house}th house suggests familiar past-life habits.",
        "spiritual_score": min(score, 100),
        "spiritual_level": level,
        "spiritual_indicators": indicators,
        "remedies": [
            "Meditate or sit in silence for 10 minutes daily",
            "Practice gratitude and honest speech",
            "Donate food or help someone in need regularly",
            "Avoid fear-based or superstitious decisions",
        ],
    }


@app.post("/divisional/{division}")
def get_divisional(division: int, data: BirthDetails):
    supported = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, 60]
    if division not in supported:
        raise HTTPException(status_code=422, detail=f"Supported divisions: {supported}")
    chart = get_chart(data)
    planets = {}
    for name, info in chart["planets"].items():
        longitude = info["longitude"]
        sign_index = int(longitude // 30)
        degree = longitude % 30
        if division == 1:
            d_sign = sign_index
        elif division == 2:
            d_sign = sign_index if degree < 15 else (sign_index + 6) % 12
        elif division == 9:
            sign_odd = sign_index % 2 == 0
            start = sign_index if sign_odd else (sign_index + 8) % 12
            pada = int(degree // (30 / 9))
            d_sign = (start + pada) % 12
        else:
            pada = int(degree // (30 / division))
            d_sign = (sign_index + pada) % 12
        planets[name] = {
            "d1_sign": info["sign"],
            f"d{division}_sign": SIGN_NAMES[d_sign],
            f"d{division}_sign_number": d_sign + 1,
        }
    meanings = {
        1: "Rashi - body and life", 2: "Hora - wealth", 3: "Drekkana - siblings",
        4: "Chaturthamsha - property", 7: "Saptamsha - children",
        9: "Navamsha - marriage and dharma", 10: "Dashamsha - career",
        12: "Dwadashamsha - parents", 60: "Shashtiamsha - past-life karma",
    }
    return {
        "division": f"D{division}",
        "meaning": meanings.get(division, f"Divisional chart D{division}"),
        "lagna_d1": chart["lagna"]["sign"],
        "planets": planets,
    }


@app.post("/divisional-all")
def get_all_divisional(data: BirthDetails):
    divisions = [1, 2, 3, 7, 9, 10, 12, 60]
    return {
        "divisions": {f"D{division}": get_divisional(division, data) for division in divisions}
    }


@app.post("/chara-dasha")
def get_chara_dasha(data: BirthDetails):
    chart = get_chart(data)
    lagna_number = chart["lagna"]["sign_number"]
    forward = lagna_number % 2 == 1
    movable = {1, 4, 7, 10}
    fixed = {2, 5, 8, 11}
    sequence = []
    birth = dt.date(data.year, data.month, data.day)
    cursor = birth
    for index in range(12):
        sign_number = ((lagna_number - 1 + index if forward else lagna_number - 1 - index) % 12) + 1
        years = 12 if sign_number in movable else 11 if sign_number in fixed else 10
        end = cursor + dt.timedelta(days=round(years * 365.2425))
        sequence.append({
            "sign": SIGN_NAMES[sign_number - 1],
            "sign_number": sign_number,
            "start": cursor.isoformat(),
            "end": end.isoformat(),
            "years": years,
        })
        cursor = end
    return {
        "system": "Jaimini Chara Dasha",
        "starting_sign": chart["lagna"]["sign"],
        "direction": "forward" if forward else "backward",
        "sequence": sequence,
    }


@app.post("/sade-sati")
def get_sade_sati(data: BirthDetails):
    chart = get_chart(data)
    moon_number = chart["planets"]["Moon"]["sign_number"]
    jd_today = swe.julday(dt.date.today().year, dt.date.today().month, dt.date.today().day, 0)
    saturn_pos, _ = swe.calc_ut(jd_today, swe.SATURN, swe.FLG_SIDEREAL)
    saturn_number = int(saturn_pos[0] // 30) + 1
    difference = (saturn_number - moon_number) % 12
    phases = {
        11: ("Sade Sati Phase 1 - Rising", "IN SADE SATI", 35),
        0: ("Sade Sati Phase 2 - Peak", "IN SADE SATI", 90),
        1: ("Sade Sati Phase 3 - Setting", "IN SADE SATI", 55),
    }
    phase, status, score = phases.get(
        difference,
        ("Not in Sade Sati now", "NOT IN SADE SATI", 0),
    )
    return {
        "moon_sign": chart["planets"]["Moon"]["sign"],
        "natal_saturn_sign": chart["planets"]["Saturn"]["sign"],
        "current_transit_saturn_sign": SIGN_NAMES[saturn_number - 1],
        "status": status,
        "phase": phase,
        "intensity_score": score,
        "remedies": [
            "Maintain discipline and honest conduct",
            "Help elderly people and vulnerable workers",
            "Avoid impulsive spending and major speculation",
        ],
    }


@app.post("/ashtakavarga")
def get_ashtakavarga(data: BirthDetails):
    chart = get_chart(data)
    planets = chart["planets"]
    lagna_number = chart["lagna"]["sign_number"]
    sarva = {}
    for sign_number in range(1, 13):
        points = 24
        for name, info in planets.items():
            distance = (info["sign_number"] - sign_number) % 12 + 1
            if name in ["Jupiter", "Venus", "Mercury", "Moon"] and distance in [1, 2, 4, 5, 7, 9, 10, 11]:
                points += 1
            elif name in ["Sun", "Mars", "Saturn"] and distance in [3, 6, 10, 11]:
                points += 1
        sarva[SIGN_NAMES[sign_number - 1]] = min(points, 56)

    bhinna = {}
    for planet in ["Sun", "Jupiter", "Saturn"]:
        bhinna[planet] = {
            sign: min(8, sarva[sign] // 4)
            for sign in SIGN_NAMES
        }
    total = sum(sarva.values())
    return {
        "system": "Indicative Ashtakavarga",
        "sarvashtakavarga_total": total,
        "sarvashtakavarga_per_sign": sarva,
        "bhinnashtakavarga_sample": bhinna,
        "best_signs": sorted(sarva, key=sarva.get, reverse=True)[:3],
        "weak_signs": sorted(sarva, key=sarva.get)[:3],
        "lagna_sign": chart["lagna"]["sign"],
        "disclaimer": "This is a simplified screening, not a substitute for traditional full bindu-table Ashtakavarga.",
    }


@app.post("/yogas")
def get_yogas(data: BirthDetails):
    chart = get_chart(data)
    planets = chart["planets"]
    lagna_number = chart["lagna"]["sign_number"]
    houses = {name: house_of(info["sign_number"], lagna_number) for name, info in planets.items()}

    found = []
    missing = []
    moon_house = houses["Moon"]
    jupiter_house = houses["Jupiter"]
    if abs(jupiter_house - moon_house) in [0, 3, 6, 9]:
        found.append({"name": "Gaja Kesari Yoga", "meaning": "Jupiter and Moon in a strong angular relationship."})
    else:
        missing.append("Gaja Kesari Yoga")
    if planets["Sun"]["sign"] == planets["Mercury"]["sign"]:
        found.append({"name": "Budha-Aditya Yoga", "meaning": "Sun and Mercury together; strong intellect and communication."})
    if planets["Moon"]["sign"] == planets["Mars"]["sign"]:
        found.append({"name": "Chandra-Mangala Yoga", "meaning": "Moon and Mars together; wealth through action."})
    if planets["Jupiter"]["sign"] == planets["Ketu"]["sign"]:
        found.append({"name": "Guru-Ketu Yoga", "meaning": "Jupiter and Ketu together; philosophical and spiritual inclination."})

    exalted = {"Mars": "Makara", "Mercury": "Kanya", "Jupiter": "Karka", "Venus": "Meena", "Saturn": "Tula"}
    own = {
        "Mars": ["Mesha", "Vrischika"], "Mercury": ["Mithuna", "Kanya"],
        "Jupiter": ["Dhanu", "Meena"], "Venus": ["Vrishabha", "Tula"],
        "Saturn": ["Makara", "Kumbha"],
    }
    names = {"Mars": "Ruchaka", "Mercury": "Bhadra", "Jupiter": "Hamsa", "Venus": "Malavya", "Saturn": "Shasha"}
    for planet in own:
        if houses[planet] in [1, 4, 7, 10] and (planets[planet]["sign"] == exalted[planet] or planets[planet]["sign"] in own[planet]):
            found.append({"name": f"{names[planet]} Mahapurusha Yoga", "meaning": f"{planet} is strong in a Kendra."})

    return {
        "total_yogas_found": len(found),
        "yogas_found": found,
        "yogas_not_present_sample": missing,
        "disclaimer": "Yoga analysis is indicative and should be confirmed through divisional charts and overall chart strength.",
    }


@app.post("/match")
def match_compatibility(data: MatchDetails):
    bride_chart = get_chart(data.bride)
    groom_chart = get_chart(data.groom)
    bride_moon = bride_chart["planets"]["Moon"]
    groom_moon = groom_chart["planets"]["Moon"]
    bride_number = bride_moon["sign_number"]
    groom_number = groom_moon["sign_number"]
    distance = (groom_number - bride_number) % 12 + 1

    # A practical compatibility screening based on Moon signs and Nakshatra distance.
    nakshatra_index = lambda longitude: int(longitude // (360 / 27))
    bride_nak = nakshatra_index(bride_moon["longitude"])
    groom_nak = nakshatra_index(groom_moon["longitude"])
    nakshatra_distance = (groom_nak - bride_nak) % 27
    nakshatra_score = 8 if nakshatra_distance not in [6, 9, 18] else 4
    sign_score = 8 if distance in [2, 3, 5, 6, 7, 11] else 5
    points = nakshatra_score + sign_score

    return {
        "bride_moon_sign": bride_moon["sign"],
        "groom_moon_sign": groom_moon["sign"],
        "moon_sign_distance": distance,
        "ashtakoota_screening_points": points,
        "maximum_screening_points": 16,
        "result": "Good" if points >= 12 else "Average" if points >= 8 else "Needs detailed review",
        "suggestion": "Discuss communication, family expectations, health and finances before taking a final decision.",
        "disclaimer": "This is a simplified compatibility screening, not a complete 36-Guna matching system.",
    }


@app.post("/ultra-full-reading")
def ultra_full_reading(data: BirthDetails):
    chart = get_kundli(data)
    return {
        "profile": chart,
        "panchang": get_panchang(data),
        "vimsottari_dasha": get_vimshottari_dasha(data),
        "chara_dasha": get_chara_dasha(data),
        "divisional_charts": get_all_divisional(data),
        "spiritual_karmic": spiritual_karmic(data),
        "sade_sati": get_sade_sati(data),
        "ashtakavarga": get_ashtakavarga(data),
        "yogas": get_yogas(data),
    }


APP_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Divya Astro</title>
  <style>
    :root { --gold:#f6c85f; --ink:#20130a; --cream:#fff8e8; }
    * { box-sizing:border-box }
    body { margin:0; font-family:Inter,Segoe UI,sans-serif; color:var(--ink); background:linear-gradient(135deg,#fffaf0,#f7e4b8); }
    header { padding:18px 24px; display:flex; justify-content:space-between; align-items:center; background:#29170d; color:white }
    header strong { color:var(--gold); font-size:21px }
    main { max-width:1100px; margin:auto; padding:56px 20px }
    .hero { text-align:center; margin-bottom:36px }
    .hero h1 { font-size:48px; margin:10px 0 }
    .hero p { color:#715f4d; font-size:18px }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px }
    .card { background:white; border:1px solid #ead8aa; border-radius:18px; padding:22px; box-shadow:0 14px 36px rgba(89,57,20,.08) }
    .card b { display:block; color:#9a6708; margin-bottom:8px }
    a.button { display:inline-block; margin:10px 6px; padding:12px 18px; border-radius:999px; background:var(--gold); color:#3a250d; text-decoration:none; font-weight:700 }
    footer { text-align:center; padding:24px; color:#806d55 }
  </style>
</head>
<body>
  <header><strong>✦ Divya Astro</strong><span>Complete Astrology API</span></header>
  <main>
    <section class="hero">
      <h1>Your cosmic guide</h1>
      <p>Kundli, Panchang, Vimshottari Dasha, divisional charts and compatibility reports.</p>
      <a class="button" href="/docs">Open API Console</a>
      <a class="button" href="/health">Check Status</a>
    </section>
    <section class="grid">
      <div class="card"><b>Birth Chart</b><span>Sidereal Lagna, planets and houses using Lahiri ayanamsa.</span></div>
      <div class="card"><b>Panchang</b><span>Tithi, Nakshatra, Pada and sunrise/sunset calculations.</span></div>
      <div class="card"><b>Dasha</b><span>Vimshottari and Jaimini Chara Dasha timelines.</span></div>
      <div class="card"><b>Compatibility</b><span>Moon-sign and Nakshatra compatibility screening.</span></div>
    </section>
  </main>
  <footer>Astrology calculations are a guidance tool, not a substitute for professional advice.</footer>
</body>
</html>
"""
