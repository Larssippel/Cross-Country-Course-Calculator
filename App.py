import streamlit as st
import pandas as pd
#from selenium import webdriver
#from selenium.webdriver.chrome.service import Service
#from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import random

# ------------------------------
# SCRAPING FUNCTIONS
# ------------------------------

import requests

def loadPage(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    time.sleep(random.uniform(1, 3))  # polite delay
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.text


def scrapeNames(meet_url):
    html = loadPage(meet_url)
    soup = BeautifulSoup(html, "html.parser")

    Athletes = []

    tables = soup.find_all("table", class_="tablesaw tablesaw-xc table-striped table-bordered table-hover tablesaw-columntoggle")

    for table in tables:
        header = table.find_previous("div", class_="custom-table-title custom-table-title-xc")
        if not header:
            continue

        header_text = header.get_text(strip=True).lower()
        if not header_text.startswith("men"):  # avoids catching "women"
            continue

        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 6:
                continue

            name = cols[1].get_text(strip=True)
            team = cols[3].get_text(strip=True)
            course_time = cols[5].get_text(strip=True)

            if "trinity" in team.lower():
                link_tag = cols[1].find("a")
                profile_url = link_tag['href'] if link_tag else None

                Athletes.append({
                    "Name": name,
                    "URL": profile_url,
                    "AvgTime": None,
                    "CourseTime": course_time
                })

    return Athletes


def timeToSeconds(time_string):
    try:
        if ":" not in time_string:
            return None
        minutes, secMs = time_string.split(":")
        return int(minutes) * 60 + float(secMs)
    except ValueError:
        return None


def scrapeAvgTimes(Athletes):
    for row in Athletes:
        if not row['URL']:
            continue

        html = loadPage(row['URL'])
        soup = BeautifulSoup(html, "html.parser")

        all_times = []

        tables = soup.find_all("table", class_="table table-hover xc")
        for table in tables:
            for race_row in table.find_all("tr"):
                cols = race_row.find_all("td")
                if len(cols) < 2:
                    continue

                distance = cols[0].get_text(strip=True).lower()
                race_time = cols[1].get_text(strip=True)

                if distance == "8k":
                    t = timeToSeconds(race_time)
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
st.write("Paste a TFRRS meet URL below to scrape results for Trinity athletes, calculate average times, and compare course vs. average performance.")

meet_url = st.text_input("Enter TFRRS Meet URL:")

if meet_url:
    with st.spinner("Scraping data... this may take a minute ⏳"):
        athletes = scrapeNames(meet_url)
        athletes = scrapeAvgTimes(athletes)
        team_diff = computeTeamDiff(athletes)

    df = pd.DataFrame(athletes)
    st.subheader("Athlete Data")
    st.dataframe(df)

    if team_diff is not None:
        st.subheader("📊 Team Average Difference")
        st.metric("Avg Difference (sec)", f"{team_diff:.2f}")
