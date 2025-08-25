import streamlit as st
import pandas as pd
import requests
import time
import random
import re
import json

# ------------------------------
# HELPERS
# ------------------------------

def loadPage(url):
    """Fetch a page politely with headers."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    time.sleep(random.uniform(1, 2))  # polite delay
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.text


def extract_initial_state(html):
    """Extract and parse the window.INITIAL_STATE JSON from a TFRRS page."""
    match = re.search(r"window\.INITIAL_STATE\s*=\s*({.*});", html, re.DOTALL)
    if not match:
        return None
    data_str = match.group(1)
    try:
        return json.loads(data_str)
    except Exception as e:
        print("JSON parse error:", e)
        return None


def timeToSeconds(time_string):
    try:
        if not time_string or ":" not in time_string:
            return None
        minutes, secMs = time_string.split(":")
        return int(minutes) * 60 + float(secMs)
    except ValueError:
        return None


# ------------------------------
# SCRAPERS
# ------------------------------

def scrapeNames(meet_url):
    html = loadPage(meet_url)
    state = extract_initial_state(html)
    Athletes = []

    if not state:
        st.error("Could not find INITIAL_STATE JSON on meet page")
        return Athletes

    # Explore JSON to see structure
    # st.json(state)   # uncomment if you want to inspect full JSON

    races = state.get("races", [])
    for race in races:
        gender = race.get("gender", "").lower()
        if gender != "men":   # skip women
            continue

        results = race.get("results", [])
        for runner in results:
            team = runner.get("team_name", "")
            if "trinity" not in team.lower():
                continue

            name = runner.get("full_name", "")
            profile_url = runner.get("athlete_url", None)
            course_time = runner.get("mark", None)

            Athletes.append({
                "Name": name,
                "URL": profile_url,
                "AvgTime": None,
                "CourseTime": course_time
            })

    return Athletes


def scrapeAvgTimes(Athletes):
    for row in Athletes:
        if not row['URL']:
            continue

        html = loadPage(row['URL'])
        state = extract_initial_state(html)
        if not state:
            continue

        all_times = []
        races = state.get("races", [])
        for race in races:
            dist = race.get("distance_name", "").lower()
            mark = race.get("mark", None)
            if not dist or not mark:
                continue
            if dist == "8k":
                t = timeToSeconds(mark)
                if t is not None:
                    all_times.append(t)

        if all_times:
            avg_sec = sum(all_times) / len(all_times)
            avg_min = int(avg_sec // 60)
            avg_rem = round(avg_sec % 60, 1)
            avg_str = f"{avg_min}:{avg_rem:04.1f}".replace(".0", "")
        else:
            avg_str = None

        row["AvgTime"] = avg_str

    return Athletes


def computeTeamDiff(Athletes):
    diffs = []
    for row in Athletes:
        if not row["AvgTime"] or not row["CourseTime"]:
            continue
        avg_sec = timeToSeconds(row["AvgTime"])
        course_sec = timeToSeconds(row["CourseTime"])
        if avg_sec and course_sec:
            diffs.append(course_sec - avg_sec)

    if diffs:
        return sum(diffs) / len(diffs)
    return None


# ------------------------------
# STREAMLIT APP
# ------------------------------

st.title("🏃 Trinity XC TFRRS Scraper")
st.write("Paste a TFRRS meet URL below to scrape results for Trinity athletes, "
         "calculate average times, and compare course vs. average performance.")

meet_url = st.text_input("Enter TFRRS Meet URL:")

if meet_url:
    with st.spinner("Scraping data... this may take a minute ⏳"):
        athletes = scrapeNames(meet_url)
        athletes = scrapeAvgTimes(athletes)
        team_diff = computeTeamDiff(athletes)

    if athletes:
        df = pd.DataFrame(athletes)
        st.subheader("Athlete Data")
        st.dataframe(df)
    else:
        st.warning("No Trinity men's athletes found for this meet.")

    if team_diff is not None:
        st.subheader("📊 Team Average Difference")
        st.metric("Avg Difference (sec)", f"{team_diff:.2f}")
