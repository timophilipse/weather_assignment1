import requests
import sqlite3
import os

locations = {
    "Aalborg": (57.048, 9.919),
    "Arnhem": (51.98, 5.91111),
    "Tilburg": (51.5555, 5.0913)
}

DB_FILE = "db.sqlite3"

def fetch_weather(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,precipitation_sum,wind_speed_10m_max,daylight_duration"
        "&timezone=Europe%2FCopenhagen"
    )

    response = requests.get(url)
    data = response.json()

    return {
        "date": data["daily"]["time"][1],
        "temperature": data["daily"]["temperature_2m_max"][1],
        "precipitation": data["daily"]["precipitation_sum"][1],
        "wind_speed": data["daily"]["wind_speed_10m_max"][1],
        "daylight": data["daily"]["daylight_duration"][1]
    }

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            location TEXT,
            date TEXT,
            temperature REAL,
            precipitation REAL,
            wind_speed REAL,
            daylight REAL
        )
    """)

    conn.commit()
    conn.close()

def store_data(location, weather):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO weather VALUES (?, ?, ?, ?, ?, ?)
    """, (
        location,
        weather["date"],
        weather["temperature"],
        weather["precipitation"],
        weather["wind_speed"],
        weather["daylight"]
    ))

    conn.commit()
    conn.close()

def collect_weather():
    for name, (lat, lon) in locations.items():
        weather = fetch_weather(lat, lon)
        store_data(name, weather)

def generate_poem():
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        SELECT location, temperature, precipitation, wind_speed, daylight
        FROM weather
    """)

    rows = cur.fetchall()
    conn.close()

    weather_text = "\n".join([
        f"{r[0]}: {r[1]}°C, {r[2]}mm rain, {r[3]} km/h wind, {r[4]/3600:.1f}h daylight"
        for r in rows
    ])

    prompt = f"""
Write a short poetic comparison of the weather for the following locations:

{weather_text}

Requirements:
- First write a creative poem in **English**
- Then write the same poem in **Dutch**
- Compare all locations
- Say where it is nicest tomorrow
- Keep it short and poetic
- Clearly separate the two languages with headings: 'English:' and 'Dutch:'
"""

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=body)

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    data = response.json()

    if "choices" in data:
        poem = data["choices"][0]["message"]["content"]
    else:
        poem = "Error generating poem:\n" + str(data)

    with open("docs/poem.txt", "w", encoding="utf-8") as f:
        f.write(poem)

def main():
    init_db()
    collect_weather()
    generate_poem()

if __name__ == "__main__":
    main()
