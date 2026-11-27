from fastapi import FastAPI
from pydantic import BaseModel
import swisseph as swe

app = FastAPI(title="My Free Astro API")

class BirthDetails(BaseModel):
    day: int
    month: int
    year: int
    hour: int
    minute: int
    lat: float
    lon: float
    timezone: float = 5.5

@app.get("/")
def home():
    return {"status": "API is running", "message": "Your free astrology API is working!"}

@app.post("/kundli")
def get_kundli(data: BirthDetails):
    # Convert to Julian Day (astronomy time)
    time_decimal = data.hour + data.minute/60 - data.timezone
    jd = swe.julday(data.year, data.month, data.day, time_decimal)
    
    # Use Lahiri Ayanamsa - Indian standard
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ayanamsa = swe.get_ayanamsa_ut(jd)
    
    # Planet names
    planets = {}
    planet_list = [
        ("Sun", swe.SUN),
        ("Moon", swe.MOON),
        ("Mars", swe.MARS),
        ("Mercury", swe.MERCURY),
        ("Jupiter", swe.JUPITER),
        ("Venus", swe.VENUS),
        ("Saturn", swe.SATURN),
        ("Rahu", swe.MEAN_NODE),
    ]
    
    for name, pid in planet_list:
        pos, _ = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)
        longitude = pos[0]
        sign_num = int(longitude // 30) + 1
        sign_names = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]
        planets[name] = {
            "longitude": round(longitude, 2),
            "sign": sign_names[sign_num-1],
            "degree_in_sign": round(longitude % 30, 2)
        }
    
    # Ketu is always opposite Rahu
    rahu_long = planets["Rahu"]["longitude"]
    ketu_long = (rahu_long + 180) % 360
    sign_names = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]
    ketu_sign = int(ketu_long // 30) + 1
    planets["Ketu"] = {
        "longitude": round(ketu_long, 2),
        "sign": sign_names[ketu_sign-1],
        "degree_in_sign": round(ketu_long % 30, 2)
    }

    # Lagna / Ascendant
    cusps, ascmc = swe.houses(jd, data.lat, data.lon, b'P')
    lagna_tropical = ascmc[0]
    lagna_sidereal = lagna_tropical - ayanamsa
    if lagna_sidereal < 0:
        lagna_sidereal += 360
    lagna_sign_num = int(lagna_sidereal // 30) + 1

    return {
        "lagna": sign_names[lagna_sign_num-1],
        "lagna_longitude": round(lagna_sidereal, 2),
        "ayanamsa": round(ayanamsa, 2),
        "moon_sign": planets["Moon"]["sign"],
        "planets": planets
    }

@app.post("/panchang")
def get_panchang(data: BirthDetails):
    jd = swe.julday(data.year, data.month, data.day, 0)
    moon, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)
    sun, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)
    diff = (moon[0] - sun[0]) % 360
    tithi = int(diff // 12) + 1
    nakshatra_num = int((moon[0] % 360) // (360/27)) + 1
    nakshatra_names = ["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
    return {
        "tithi_number": tithi,
        "moon_nakshatra": nakshatra_names[nakshatra_num-1],
        "moon_longitude": round(moon[0], 2)
    }