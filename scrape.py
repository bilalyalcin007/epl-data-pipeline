import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from typing import Optional, List

# -------------------------------
# Shared utilities
# -------------------------------

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

def _get_soup(url: str) -> Optional[BeautifulSoup]:
    """Fetch a URL and return BeautifulSoup, or None on failure."""
    try:
        resp = requests.get(url, headers=UA, timeout=20)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"❌ Request failed for {url}: {e}")
        return None

def _first_table(soup: BeautifulSoup, class_name: Optional[str] = None):
    """Return a <table> element, optionally by class name."""
    if soup is None:
        return None
    return soup.find("table", class_=class_name) if class_name else soup.find("table")

def _table_to_df(table, header_override: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Convert an HTML <table> into a DataFrame. If header_override is provided,
    use those column names; otherwise infer from <th> text.
    """
    if table is None:
        return pd.DataFrame()

    # Get headers
    if header_override:
        headers = header_override
    else:
        ths = table.find_all("th")
        headers = [th.get_text(strip=True) for th in ths] if ths else []

    # Build rows
    rows = []
    trs = table.find_all("tr")
    # Skip header row if headers exist
    data_trs = trs[1:] if len(trs) > 1 else trs
    for tr in data_trs:
        tds = tr.find_all("td")
        if not tds:
            continue
        rows.append([td.get_text(strip=True) for td in tds])

    # If no headers detected, create generic ones
    if not headers and rows:
        headers = [f"col_{i+1}" for i in range(len(rows[0]))]

    # Align row lengths with headers
    df = pd.DataFrame(rows, columns=headers[: len(rows[0])] if rows else headers)
    return df

def _clean_common(df: pd.DataFrame) -> pd.DataFrame:
    """Common cleanup across pages."""
    if df.empty:
        return df
    # Drop fully empty unnamed columns
    empty_like = [c for c in df.columns if c.strip() in {"", "#"}]
    df = df.drop(columns=empty_like, errors="ignore")
    # Normalize whitespace/newlines
    df = df.applymap(lambda x: x.replace("\n", " ").strip() if isinstance(x, str) else x)
    return df


# -------------------------------
# 1) Premier League Table (BBC)
# -------------------------------
def league_table() -> pd.DataFrame:
    url = "https://www.bbc.com/sport/football/premier-league/table"
    soup = _get_soup(url)
    table = _first_table(soup)  # BBC class names are dynamic; use first table

    if table is None:
        print("⚠️ BBC league_table: Could not find a table.")
        return pd.DataFrame()

    df = _table_to_df(table)
    df = _clean_common(df)

    # Drop any "Form" style columns if present
    for col in list(df.columns):
        if "Form" in col or "form" in col.lower():
            df = df.drop(columns=[col], errors="ignore")

    return df


# -------------------------------
# 2) Top Scorers (BBC)
# -------------------------------
def top_scorers() -> pd.DataFrame:
    url = "https://www.bbc.com/sport/football/premier-league/top-scorers"
    soup = _get_soup(url)
    table = _first_table(soup)

    if table is None:
        print("⚠️ BBC top_scorers: Could not find a table.")
        return pd.DataFrame()

    df = _table_to_df(table)
    df = _clean_common(df)
    return df


# -------------------------------
# 3) Detailed Top Scorers (WorldFootball)
# -------------------------------
def detail_top() -> pd.DataFrame:
    url = "https://www.worldfootball.net/goalgetter/eng-premier-league-2024-2025/"
    soup = _get_soup(url)
    table = _first_table(soup, class_name="standard_tabelle")

    if table is None:
        print("⚠️ detail_top: table not found (structure may have changed).")
        return pd.DataFrame()

    df = _table_to_df(table)
    df = _clean_common(df)

    # If a "Goals (Penalty)" column exists, split it into Goals and Penalty
    col = next((c for c in df.columns if "Goals" in c and "Penalty" in c), None)
    if col:
        # Extract numeric goals and penalties when present
        goals = df[col].str.extract(r"^(\d+)").iloc[:, 0]
        pens  = df[col].str.extract(r"\((\d+)\)").iloc[:, 0]
        df["Goals"] = goals
        df["Penalty"] = pens
        df = df.drop(columns=[col], errors="ignore")

    df = df.drop(columns=["#"], errors="ignore")
    return df


# -------------------------------
# 4) Player List (WorldFootball)
# -------------------------------
def player_table() -> pd.DataFrame:
    # Pages 1..11 contain the alphabetized player lists for 2023-2024
    urls = [
        f"https://www.worldfootball.net/players_list/eng-premier-league-2023-2024/nach-name/{i}"
        for i in range(1, 12)
    ]

    all_parts = []
    for u in urls:
        soup = _get_soup(u)
        if soup is None:
            continue
        table = _first_table(soup, class_name="standard_tabelle")
        if table is None:
            continue
        part = _table_to_df(table)
        part = _clean_common(part)
        if not part.empty:
            all_parts.append(part)

    if not all_parts:
        print("⚠️ player_table: no data parsed.")
        return pd.DataFrame()

    df = pd.concat(all_parts, ignore_index=True)
    # Drop anonymous empty columns if present
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df = df.drop(columns=[""], errors="ignore")
    return df


# -------------------------------
# 5) All-Time Table (WorldFootball)
# -------------------------------
def all_time_table() -> pd.DataFrame:
    url = "https://www.worldfootball.net/alltime_table/eng-premier-league/pl-only/"
    soup = _get_soup(url)
    table = _first_table(soup, class_name="standard_tabelle")

    if table is None:
        print("⚠️ all_time_table: table not found.")
        return pd.DataFrame()

    # Provide a stable header override because WF sometimes omits TH text in some rows
    headers = ["pos", "#", "Team", "Matches", "Wins", "Draws", "Losses", "Goals", "Dif", "Points"]
    df = _table_to_df(table, header_override=headers)
    df = _clean_common(df)

    df = df.drop(columns=["#"], errors="ignore")
    return df


# -------------------------------
# 6) All-Time Winner Clubs (WorldFootball)
# -------------------------------
def all_time_winner_club() -> pd.DataFrame:
    url = "https://www.worldfootball.net/winner/eng-premier-league/"
    soup = _get_soup(url)
    table = _first_table(soup, class_name="standard_tabelle")

    if table is None:
        print("⚠️ all_time_winner_club: table not found.")
        return pd.DataFrame()

    df = _table_to_df(table)
    df = _clean_common(df)

    # Normalize "Year" column if present
    if "Year" in df.columns:
        df["Year"] = df["Year"].str.replace("\n", " ").str.strip()
    return df


# -------------------------------
# 7) Top Scorers by Season (WorldFootball)
# -------------------------------
def top_scorers_seasons() -> pd.DataFrame:
    url = "https://www.worldfootball.net/top_scorer/eng-premier-league/"
    soup = _get_soup(url)
    table = _first_table(soup, class_name="standard_tabelle")

    if table is None:
        print("⚠️ top_scorers_seasons: table not found.")
        return pd.DataFrame()

    # Provide stable headers (WF sometimes has duplicate "#" cols)
    headers = ["Season", "#", "Top scorer", "#", "Team", "Goals"]
    df = _table_to_df(table, header_override=headers)
    df = _clean_common(df)

    df = df.drop(columns=["#"], errors="ignore")
    # Forward-fill Season down the groups
    if "Season" in df.columns:
        df["Season"] = df["Season"].replace("", np.nan).ffill()
    return df


# -------------------------------
# 8) Goals Per Season (WorldFootball)
# -------------------------------
def goals_per_season() -> pd.DataFrame:
    url = "https://www.worldfootball.net/stats/eng-premier-league/1/"
    soup = _get_soup(url)
    table = _first_table(soup, class_name="standard_tabelle")

    if table is None:
        print("⚠️ goals_per_season: table not found.")
        return pd.DataFrame()

    df = _table_to_df(table)
    df = _clean_common(df)

    # Drop final "Total" row if it exists
    if not df.empty:
        last_row = df.tail(1).iloc[0].astype(str).str.lower().to_list()
        if any("total" in x for x in last_row):
            df = df.iloc[:-1, :]

    # Standardize column names if present
    rename_map = {}
    for c in df.columns:
        if c.strip().lower() == "goals":
            rename_map[c] = "Goals"
        if "Ø" in c or "average" in c.lower():
            rename_map[c] = "Average Goals"
    if rename_map:
        df = df.rename(columns=rename_map)

    df = df.drop(columns=["#"], errors="ignore")
    return df


# -------------------------------
# Local test hook
# -------------------------------
if __name__ == "__main__":
    print("🏆 Premier League Table:")
    print(league_table().head())

    print("\n⚽ Top Scorers:")
    print(top_scorers().head())

    print("\n📊 Detailed Top Scorers:")
    print(detail_top().head())

    print("\n👥 Player List:")
    print(player_table().head())

    print("\n📚 All-Time Table:")
    print(all_time_table().head())

    print("\n🥇 Winner Clubs:")
    print(all_time_winner_club().head())

    print("\n🎯 Top Scorers by Season:")
    print(top_scorers_seasons().head())

    print("\n🎯 Goals Per Season:")
    print(goals_per_season().head())
