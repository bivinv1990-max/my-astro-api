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
@app.post("/spiritual-karmic")
def spiritual_karmic(data: BirthDetails):
    # First get the basic kundli we already have
    base = get_kundli(data)
    planets = base["planets"]
    lagna_sign = base["lagna"]
    
    sign_names = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]
    lagna_num = sign_names.index(lagna_sign) + 1

    # --- 1. ATMAKARAKA (Soul Planet) - Highest degree in sign ---
    atmakaraka = max(planets, key=lambda p: planets[p]["degree_in_sign"])
    atmakaraka_degree = planets[atmakaraka]["degree_in_sign"]
    
    atma_meaning = {
        "Sun": "Soul lesson: Leadership, ego, father karma. Must learn to shine without dominating.",
        "Moon": "Soul lesson: Emotions, mother, attachment. Must learn emotional detachment.",
        "Mars": "Soul lesson: Anger, courage, action. Must learn controlled power.",
        "Mercury": "Soul lesson: Truth, communication. Must learn to speak truth with kindness.",
        "Jupiter": "Soul lesson: Wisdom, guru, dharma. Must learn to teach and guide.",
        "Venus": "Soul lesson: Love, desire, relationships. Must learn unconditional love.",
        "Saturn": "Soul lesson: Karma, patience, service. Must learn to serve without expecting reward.",
        "Rahu": "Soul lesson: Material obsession from past life. Must learn to balance desire.",
        "Ketu": "Soul lesson: Already completed material lessons. Now needs moksha, detachment, spiritual path."
    }

    # --- 2. RAHU-KETU AXIS ---
    rahu_sign = planets["Rahu"]["sign"]
    ketu_sign = planets["Ketu"]["sign"]
    rahu_num = sign_names.index(rahu_sign) + 1
    ketu_num = sign_names.index(ketu_sign) + 1
    
    # House number from Lagna (1 = Lagna)
    def house_of(sign_num):
        h = sign_num - lagna_num + 1
        if h <= 0:
            h += 12
        return h
    
    rahu_house = house_of(rahu_num)
    ketu_house = house_of(ketu_num)

    ketu_past_life = {
        1: "Past life: Focused too much on self, identity. This life: Learn partnership, listen to others.",
        2: "Past life: Focused on family wealth, speech. This life: Learn hidden truths, transformation (8th house).",
        5: "Past life: Mantra, children, creativity. This life: Learn service, daily work, health discipline.",
        8: "Past life: Occult, secrets, tantra. This life: Learn to live openly, earn, speak truth (2nd house).",
        12: "Past life: Isolation, ashram, foreign. This life: Learn to work in world, serve, fight (6th house).",
        9: "Past life: Dharma, guru, religion. This life: Learn practical communication, effort (3rd house)."
    }
    ketu_text = ketu_past_life.get(ketu_house, f"Past life mastery in {ketu_house}th house area. This life must learn opposite {rahu_house}th house area.")

    # --- 3. SPIRITUAL SCORE ---
    spiritual_score = 0
    indicators = []

    moon_sign = base["moon_sign"]
    moon_num = sign_names.index(moon_sign) + 1
    moon_house = house_of(moon_num)

    # Ketu in 5,8,12 = very spiritual
    if ketu_house in [5, 8, 12]:
        spiritual_score += 25
        indicators.append(f"Ketu in {ketu_house}th house - Past-life sadhak, natural detachment")
    
    # Moon in 5,8,12
    if moon_house in [5, 8, 9, 12]:
        spiritual_score += 15
        indicators.append(f"Moon in {moon_house}th house - Intuitive mind, strong dreams")
    
    # Jupiter in 9,12,1
    jup_sign = planets["Jupiter"]["sign"]
    jup_house = house_of(sign_names.index(jup_sign) + 1)
    if jup_house in [1, 9, 12]:
        spiritual_score += 20
        indicators.append(f"Jupiter in {jup_house}th house - Natural guru, dharma")
    
    # Lagna is Scorpio / Pisces / Cancer (water signs = spiritual)
    if lagna_sign in ["Vrischika", "Meena", "Karka"]:
        spiritual_score += 15
        indicators.append(f"Lagna {lagna_sign} - Water sign, naturally intuitive, occult interest")
    
    # Moon + Ketu close (we check same sign as proxy)
    if planets["Moon"]["sign"] == planets["Ketu"]["sign"]:
        spiritual_score += 15
        indicators.append("Moon + Ketu same sign - Chandra-Ketu Yoga, clairvoyance, feels others energy")
    
    # Cap at 100
    if spiritual_score > 100:
        spiritual_score = 100

    if spiritual_score >= 70:
        spiritual_level = "Born Spiritual - Past-life sadhak, needs guru guidance to not get lost"
    elif spiritual_score >= 40:
        spiritual_level = "Spiritual Seeker - Will have turning point after 30-35, guru will come"
    else:
        spiritual_level = "Material Focused - Spirituality will develop later in life after responsibilities"

    # --- 4. DURLABHA SCORE ---
    durlabha_score = 0
    durlabha_reasons = []

    # Gaja Kesari: Jupiter in Kendra from Moon (1,4,7,10 from Moon)
    diff = abs(jup_house - moon_house)
    if diff in [0, 3, 6, 9]:
        durlabha_score += 1
        durlabha_reasons.append("Gaja Kesari Yoga - Jupiter in Kendra from Moon, wisdom + fame")

    # Guru-Ketu together (same sign)
    if planets["Jupiter"]["sign"] == planets["Ketu"]["sign"]:
        durlabha_score += 1
        durlabha_reasons.append("Guru-Ketu Moksha Yoga - Jupiter + Ketu together, moksha desire")

    # Atmakaraka in Kendra/Trikona
    atma_sign = planets[atmakaraka]["sign"]
    atma_house = house_of(sign_names.index(atma_sign) + 1)
    if atma_house in [1, 4, 5, 7, 9, 10]:
        durlabha_score += 1
        durlabha_reasons.append(f"Atmakaraka {atmakaraka} in {atma_house}th house (Kendra/Trikona) - Soul purpose is strong")

    # Moon in 5th = Purva Punya
    if moon_house == 5:
        durlabha_score += 1
        durlabha_reasons.append("Moon in 5th - Strong Purva Punya, past-life good karma")

    if durlabha_score >= 3:
        durlabha_level = "DURLABHA CHART - Rare, 3+ rare yogas"
    elif durlabha_score == 2:
        durlabha_level = "STRONG CHART - 2 rare yogas"
    elif durlabha_score == 1:
        durlabha_level = "NORMAL STRONG CHART - 1 rare yoga"
    else:
        durlabha_level = "NORMAL CHART - No rare yoga, but can grow with sadhana"

    return {
        "lagna": lagna_sign,
        "moon_sign": moon_sign,
        "atmakaraka": atmakaraka,
        "atmakaraka_degree": atmakaraka_degree,
        "atmakaraka_meaning": atma_meaning.get(atmakaraka, "Soul lesson"),
        "rahu_house": rahu_house,
        "ketu_house": ketu_house,
        "rahu_sign": rahu_sign,
        "ketu_sign": ketu_sign,
        "karmic_pattern": ketu_text,
        "karmic_rule": "Ketu = What you already mastered in past life (don't repeat). Rahu = What you MUST learn in this life.",
        "spiritual_score": spiritual_score,
        "spiritual_level": spiritual_level,
        "spiritual_indicators": indicators,
        "durlabha_score": durlabha_score,
        "durlabha_level": durlabha_level,
        "durlabha_reasons": durlabha_reasons,
        "remedies": [
            "Daily: 10 mins silence / meditation, focus on breath",
            "Mantra: Om Namah Shivaya or Guru mantra (choose one, do daily)",
            "Charity: Donate food / help one person weekly without telling anyone",
            "Avoid: Fear, black magic talk, too many gemstones. Focus on behaviour."
        ]
    }

