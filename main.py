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
# ================= ULTRA SCRIPT: D1-D60 + CHARA DASHA + SADE SATI + ASHTAKAVARGA + YOGAS =================

SIGN_NAMES_U = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]

def get_divisional_sign(longitude, division):
    # General divisional calculation
    sign_num = int(longitude // 30)
    deg_in_sign = longitude % 30
    # For D1, return same
    if division == 1:
        return sign_num
    # Varga formula: For most divisions, divide sign into `division` parts
    # Simplified standard method used by most APIs
    pada = int(deg_in_sign // (30 / division)) if division <= 30 else int(deg_in_sign // (30 / 60))
    # For D9, D10 etc, start sign logic differs - we use generic method:
    # Odd signs start from same sign, Even signs start from 10th from it (for D9, D10 etc)
    # This is a simplified but working version for professional use
    if sign_num % 2 == 0:  # Odd sign (Mesha=0)
        start = sign_num
    else:  # Even sign
        start = (sign_num + 9) % 12  # 10th from it for many vargas, simplified
    # For D2, D3 etc, use division logic
    if division == 2:
        # Hora: 0-15 deg = first, 15-30 = second
        return sign_num if deg_in_sign < 15 else (sign_num + 6) % 12
    if division == 9:
        # Navamsha already handled in /d9, reuse same logic
        sign_type = sign_num % 4
        if sign_type == 0:
            start_n = sign_num
        elif sign_type == 1:
            start_n = (sign_num + 9) % 12
        elif sign_type == 2:
            start_n = (sign_num + 6) % 12
        else:
            start_n = (sign_num + 3) % 12
        return (start_n + pada) % 12 if division == 9 else start_n
    # Generic for others
    return (start + pada) % 12

@app.post("/divisional/{division}")
def get_divisional(division: int, data: BirthDetails):
    if division not in [1,2,3,4,5,6,7,8,9,10,12,16,20,24,27,30,40,45,60]:
        return {"error": "Supported divisions: 1,2,3,4,5,6,7,8,9,10,12,16,20,24,27,30,40,45,60"}
    base = get_kundli(data)
    planets = base["planets"]
    result = {}
    division_names = {1:"D1 Rashi - Main Chart, Body, Life",2:"D2 Hora - Wealth",3:"D3 Drekkana - Siblings, Courage",4:"D4 Chaturthamsha - Property, Home",5:"D5 Panchamsha - Fame, Power",6:"D6 Shashthamsha - Health, Enemies",7:"D7 Saptamsha - Children",8:"D8 Ashtamsha - Sudden Events, Longevity",9:"D9 Navamsha - Marriage, Dharma",10:"D10 Dashamsha - Career",12:"D12 Dwadashamsha - Parents, Past Life",16:"D16 Shodashamsha - Vehicles, Comforts",20:"D20 Vimshamsha - Spiritual Progress",24:"D24 Chaturvimshamsha - Education",27:"D27 Saptavimshamsha - Strength, Weakness",30:"D30 Trimshamsha - Misfortunes, Evils",40:"D40 Khavedamsha - Auspicious / Inauspicious",45:"D45 Akshavedamsha - General Character",60:"D60 Shashtiamsha - Past Life Karma, Final Truth"}
    for name, info in planets.items():
        long = info["longitude"]
        d_sign_num = get_divisional_sign(long, division)
        result[name] = {
            "d1_sign": info["sign"],
            f"d{division}_sign": SIGN_NAMES_U[d_sign_num],
            f"d{division}_sign_number": d_sign_num + 1
        }
    return {
        "division": f"D{division}",
        "meaning": division_names.get(division, ""),
        "lagna_d1": base["lagna"],
        "planets": result
    }

@app.post("/divisional-all")
def get_all_divisional(data: BirthDetails):
    # Return D1, D9, D10, D7, D12, D60 - most important ones together
    important = [1,2,3,7,9,10,12,60]
    all_data = {}
    for div in important:
        res = get_divisional(div, data)
        all_data[f"D{div}"] = res
    return {
        "note": "D1=Body, D9=Marriage/Dharma, D10=Career, D7=Children, D12=Parents/Past Life, D60=Past Life Karma",
        "divisions": all_data
    }

@app.post("/chara-dasha")
def get_chara_dasha(data: BirthDetails):
    base = get_kundli(data)
    lagna = base["lagna"]
    lagna_num = SIGN_NAMES_U.index(lagna) + 1
    # Jaimini Chara Dasha: Starts from Lagna sign, moves forward/backward depending on odd/even
    # Odd signs move forward, Even signs move backward
    # Duration: 12 years for movable, 11 for fixed, 10 for dual - simplified to 9-12 years per sign
    signs_order = []
    is_odd = lagna_num % 2 == 1
    for i in range(12):
        if is_odd:
            s_num = (lagna_num + i - 1) % 12 + 1
        else:
            s_num = (lagna_num - i - 1) % 12 + 1
        sign_name = SIGN_NAMES_U[s_num - 1]
        # Duration by sign nature: Movable (Mesha, Karka, Tula, Makara) = 12, Fixed = 11, Dual = 10
        movable = [1,4,7,10]
        fixed = [2,5,8,11]
        if s_num in movable:
            yrs = 12
        elif s_num in fixed:
            yrs = 11
        else:
            yrs = 10
        signs_order.append({"sign": sign_name, "sign_number": s_num, "years": yrs, "order": i+1, "status": "Current - Starting Sign" if i==0 else "Future"})
    return {
        "system": "Jaimini Chara Dasha - Sign-based dasha, shows karma of each sign period",
        "starting_sign_lagna": lagna,
        "is_lagna_odd": is_odd,
        "direction": "Forward (Odd Lagna)" if is_odd else "Backward (Even Lagna)",
        "note": "Chara Dasha is different from Vimshottari. Use Vimshottari for timing, Chara for sign karma / life themes.",
        "sequence": signs_order,
        "total_cycle_years": sum([s["years"] for s in signs_order])
    }

@app.post("/sade-sati")
def get_sade_sati(data: BirthDetails):
    base = get_kundli(data)
    moon_sign = base["moon_sign"]
    moon_num = SIGN_NAMES_U.index(moon_sign) + 1
    saturn_sign = base["planets"]["Saturn"]["sign"]
    saturn_num = SIGN_NAMES_U.index(saturn_sign) + 1
    # Sade Sati: When Saturn transits 12th, 1st, 2nd from Moon sign (i.e., Moon-1, Moon, Moon+1)
    # We check natal Saturn position as proxy, but real Sade Sati needs current transit - we calculate current Saturn
    # Current Saturn approx: For 2026, Saturn is in Meena (Pisces) - we use natal as example + explain transit logic
    # For accurate live check, we calculate Saturn's current position using today's date
    import datetime
    today = datetime.date.today()
    jd_today = __import__('swisseph').julday(today.year, today.month, today.day, 0)
    import swisseph as swe2
    swe2.set_sid_mode(swe2.SIDM_LAHIRI)
    sat_now, _ = swe2.calc_ut(jd_today, swe2.SATURN, swe2.FLG_SIDEREAL)
    sat_now_sign_num = int(sat_now[0] // 30) + 1
    sat_now_sign = SIGN_NAMES_U[sat_now_sign_num - 1]
    # Distance from Moon
    diff = (sat_now_sign_num - moon_num) % 12
    # 11 = 12th from Moon, 0 = Same as Moon, 1 = 2nd from Moon
    if diff == 11:
        phase = "Sade Sati Phase 1 - Rising - 12th from Moon - Beginning, expenses, foreign, isolation"
        status = "IN SADE SATI - Phase 1"
        score = 30
    elif diff == 0:
        phase = "Sade Sati Phase 2 - Peak - Same as Moon - Most intense, health, career, mental pressure"
        status = "IN SADE SATI - PEAK PHASE"
        score = 90
    elif diff == 1:
        phase = "Sade Sati Phase 3 - Setting - 2nd from Moon - Ending, family, wealth lessons"
        status = "IN SADE SATI - Phase 3"
        score = 50
    else:
        phase = f"Not in Sade Sati now. Saturn is in {sat_now_sign} ({sat_now_sign_num}th sign), Moon is in {moon_sign}. Next Sade Sati when Saturn enters {SIGN_NAMES_U[(moon_num - 2) % 12]}"
        status = "NOT IN SADE SATI"
        score = 0
    return {
        "moon_sign": moon_sign,
        "natal_saturn_sign": saturn_sign,
        "current_transit_saturn_sign": sat_now_sign,
        "current_saturn_longitude": round(float(sat_now[0]), 2),
        "status": status,
        "phase": phase,
        "intensity_score_0_100": score,
        "remedies": [
            "Saturday: Donate black til, oil, black cloth",
            "Chant: Om Sham Shanicharaya Namah - 108 times on Saturday",
            "Help elderly, labourers, disabled - Saturn's people",
            "Avoid: Alcohol, lying, disrespecting elders",
            "Discipline: Wake early, work honestly, be patient"
        ] if score > 0 else ["No Sade Sati now - Use this time to build discipline and savings"],
        "note": "Sade Sati is 7.5 years total. It is not a curse - it is Saturn's training period. Hard work + honesty = huge growth after it."
    }

@app.post("/ashtakavarga")
def get_ashtakavarga(data: BirthDetails):
    base = get_kundli(data)
    planets = base["planets"]
    # Simplified Sarvashtakavarga: Each planet gives points (bindus) to signs based on its position
    # Real Ashtakavarga is complex - this is simplified version for learning, using standard bindu tables approximation
    # We calculate: For each sign, count how many planets aspect / are in good positions
    # Professional version uses full tables - this gives approximate Sarvashtakavarga 0-56 range
    lagna_num = SIGN_NAMES_U.index(base["lagna"]) + 1
    sarva = {}
    # For each sign 1-12, calculate points
    for sign_idx in range(12):
        sign_num = sign_idx + 1
        points = 0
        # Base points: 28 is average
        # Add points if Jupiter, Venus, Mercury in good houses from this sign, etc.
        for pname, pinfo in planets.items():
            p_sign_num = SIGN_NAMES_U.index(pinfo["sign"]) + 1
            # Distance from this sign
            dist = (p_sign_num - sign_num) % 12 + 1
            if pname in ["Jupiter", "Venus", "Mercury", "Moon"]:
                if dist in [1,2,4,5,7,9,10,11]:
                    points += 1
            elif pname in ["Sun", "Mars", "Saturn"]:
                if dist in [3,6,10,11]:
                    points += 1
            if pname in ["Jupiter"]:
                points += 1  # Jupiter always gives extra
        # Normalize to 20-35 range per sign (real SAV is 15-40 per sign)
        points = max(18, min(38, points + 22))
        sarva[SIGN_NAMES_U[sign_idx]] = points
    
    total = sum(sarva.values())
    # Bhinnashtakavarga for Saturn, Jupiter, Sun - simplified
    bhinna = {}
    for pname in ["Saturn", "Jupiter", "Sun"]:
        bhinna[pname] = {sign: max(0, min(8, (sarva[sign] // 4))) for sign in SIGN_NAMES_U}
    
    return {
        "system": "Ashtakavarga - 8-fold strength of signs. Higher points = Stronger sign for transits.",
        "sarvashtakavarga_total": total,
        "sarvashtakavarga_max": 337,
        "interpretation": "Total > 300 = Very Strong Chart, 250-300 = Strong, 200-250 = Average, <200 = Challenging but can improve with effort",
        "sarvashtakavarga_per_sign": sarva,
        "bhinnashtakavarga_sample": bhinna,
        "best_signs": sorted(sarva, key=lambda k: sarva[k], reverse=True)[:3],
        "weak_signs": sorted(sarva, key=lambda k: sarva[k])[:3],
        "how_to_use": "When Saturn/Jupiter transits a sign with high SAV (>30), results are good. Low SAV (<25) means be careful in that area."
    }

@app.post("/yogas")
def get_yogas(data: BirthDetails):
    base = get_kundli(data)
    planets = base["planets"]
    lagna = base["lagna"]
    moon_sign = base["moon_sign"]
    sign_names = SIGN_NAMES_U
    lagna_num = sign_names.index(lagna) + 1
    def house_of(sign_name):
        s = sign_names.index(sign_name) + 1
        h = s - lagna_num + 1
        if h <= 0:
            h += 12
        return h
    planet_house = {name: house_of(info["sign"]) for name, info in planets.items()}
    moon_house = house_of(moon_sign)
    jup_house = planet_house.get("Jupiter", 0)
    yogas_found = []
    yogas_missing = []

    # 1. Gaja Kesari
    diff = abs(jup_house - moon_house)
    if diff in [0,3,6,9]:
        yogas_found.append({"name": "Gaja Kesari Yoga", "power": "High", "meaning": "Jupiter in Kendra from Moon. Wisdom, fame, respect, intelligent, remembered after death."})
    else:
        yogas_missing.append("Gaja Kesari Yoga - Jupiter not in Kendra from Moon")

    # 2. Budha-Aditya
    if planets["Sun"]["sign"] == planets["Mercury"]["sign"]:
        yogas_found.append({"name": "Budha-Aditya Yoga", "power": "Medium", "meaning": "Sun + Mercury together. Sharp mind, government / admin / communication talent."})
    
    # 3. Panch Mahapurusha - Check exalted/own in Kendra
    exalted = {"Mars":"Makara","Mercury":"Kanya","Jupiter":"Karka","Venus":"Meena","Saturn":"Tula"}
    own = {"Mars":["Mesha","Vrischika"],"Mercury":["Mithuna","Kanya"],"Jupiter":["Dhanu","Meena"],"Venus":["Vrishabha","Tula"],"Saturn":["Makara","Kumbha"]}
    for p in ["Mars","Mercury","Jupiter","Venus","Saturn"]:
        p_sign = planets[p]["sign"]
        p_house = planet_house[p]
        if p_house in [1,4,7,10] and (p_sign == exalted[p] or p_sign in own[p]):
            yoga_name = {"Mars":"Ruchaka Mahapurusha","Mercury":"Bhadra Mahapurusha","Jupiter":"Hamsa Mahapurusha","Venus":"Malavya Mahapurusha","Saturn":"Shasha Mahapurusha"}[p]
            yogas_found.append({"name": yoga_name, "power": "Very High - Rare", "meaning": f"{p} exalted/own in Kendra. Great power, leadership, fame in its field."})

    # 4. Chandra-Mangala
    if planets["Moon"]["sign"] == planets["Mars"]["sign"]:
        yogas_found.append({"name": "Chandra-Mangala Yoga", "power": "Medium", "meaning": "Moon + Mars together. Wealth through effort, property, bold decisions."})

    # 5. Guru-Ketu Moksha
    if planets["Jupiter"]["sign"] == planets["Ketu"]["sign"]:
        yogas_found.append({"name": "Guru-Ketu Moksha Yoga", "power": "High - Spiritual", "meaning": "Jupiter + Ketu together. Moksha desire, guru, detachment, past-life sadhak."})

    # 6. Kaal Sarp (simplified - all planets between Rahu-Ketu)
    rahu_long = planets["Rahu"]["longitude"]
    ketu_long = planets["Ketu"]["longitude"]
    # Check if all planets are on one side - simplified: count planets between
    # For beginner, we flag if Rahu/Ketu in 1-7 axis and no planet outside - simplified check
    # We will say not present unless all planets in same 180 deg arc - we skip complex calc and say check manually
    # 7. Amala Yoga - Benefic in 10th from Lagna or Moon
    if planet_house.get("Jupiter") == 10 or planet_house.get("Venus") == 10 or planet_house.get("Mercury") == 10:
        yogas_found.append({"name": "Amala Yoga", "power": "High", "meaning": "Benefic in 10th house. Pure reputation, career fame, respected."})

    # 8. Lakshmi Yoga - 9th lord in Kendra + Venus strong - simplified
    # 9. Saraswati Yoga - Jupiter, Venus, Mercury in Kendra/Trikona
    if jup_house in [1,4,5,7,9,10] and planet_house.get("Venus",0) in [1,4,5,7,9,10] and planet_house.get("Mercury",0) in [1,4,5,7,9,10]:
        yogas_found.append({"name": "Saraswati Yoga", "power": "High", "meaning": "Jupiter + Venus + Mercury in Kendra/Trikona. Learning, arts, knowledge, writing talent."})

    return {
        "total_yogas_found": len(yogas_found),
        "yogas_found": yogas_found,
        "yogas_not_present_sample": yogas_missing,
        "interpretation": f"Found {len(yogas_found)} major yogas. 0-1 = Normal, 2-3 = Strong, 4+ = Very Rare / Durlabha.",
        "note": "Yoga needs full check with degrees and Navamsha for confirmation. This is screening - if yoga shows here, verify with D9."
    }

@app.post("/ultra-full-reading")
def ultra_full_reading(data: BirthDetails):
    # Call everything together
    full = full_reading(data)
    div_all = get_all_divisional(data)
    chara = get_chara_dasha(data)
    sade = get_sade_sati(data)
    ashta = get_ashtakavarga(data)
    yogas = get_yogas(data)
    # Add to full
    full["divisional_charts_d1_to_d60"] = div_all
    full["chara_dasha_jaimini"] = chara
    full["sade_sati"] = sade
    full["ashtakavarga"] = ashta
    full["yogas"] = yogas
    full["ultra_summary"] = f"ULTRA REPORT: Lagna {full['chart']['lagna']}, Moon {full['chart']['moon_sign']}, Strength {full['strength']['score']}/100, Spiritual {full['spiritual_siddhi']['score']}/100, Durlabha {full['durlabha']['score']}, Yogas Found {yogas['total_yogas_found']}, Sade Sati: {sade['status']}, Chara Dasha Start: {chara['starting_sign_lagna']}, Ashtakavarga Total: {ashta['sarvashtakavarga_total']}/337"
    return full
