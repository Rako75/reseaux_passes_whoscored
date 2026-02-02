import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.font_manager as fm
from mplsoccer import VerticalPitch, Pitch
from bs4 import BeautifulSoup
from PIL import Image
import os
import re
import json
import time
import requests
import shutil
from io import BytesIO
from datetime import datetime

# --- CONFIGURATION DE LA PAGE (DESIGN) ---
st.set_page_config(
    page_title="Premier League Analyst Pro • 2025/26",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONSTANTES ---
DATA_FOLDER = "premier_league_data_2025_2026"
URLS_FILE = "whoscored_urls_premierleague.txt"
FONT_PATH = "Montserrat-Regular.ttf"

# Création du dossier data s'il n'existe pas
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# --- LOGOS DES CLUBS PREMIER LEAGUE ---
PREMIER_LEAGUE_CLUBS = {
    'Arsenal': 'https://resources.premierleague.com/premierleague/badges/50/t3.png',
    'Aston Villa': 'https://resources.premierleague.com/premierleague/badges/50/t7.png',
    'Bournemouth': 'https://resources.premierleague.com/premierleague/badges/50/t91.png',
    'Brentford': 'https://resources.premierleague.com/premierleague/badges/50/t94.png',
    'Brighton': 'https://resources.premierleague.com/premierleague/badges/50/t36.png',
    'Chelsea': 'https://resources.premierleague.com/premierleague/badges/50/t8.png',
    'Crystal Palace': 'https://resources.premierleague.com/premierleague/badges/50/t31.png',
    'Everton': 'https://resources.premierleague.com/premierleague/badges/50/t11.png',
    'Fulham': 'https://resources.premierleague.com/premierleague/badges/50/t54.png',
    'Ipswich': 'https://resources.premierleague.com/premierleague/badges/50/t40.png',
    'Leicester': 'https://resources.premierleague.com/premierleague/badges/50/t13.png',
    'Liverpool': 'https://resources.premierleague.com/premierleague/badges/50/t14.png',
    'Man City': 'https://resources.premierleague.com/premierleague/badges/50/t43.png',
    'Man Utd': 'https://resources.premierleague.com/premierleague/badges/50/t1.png',
    'Newcastle': 'https://resources.premierleague.com/premierleague/badges/50/t4.png',
    'Nott\'m Forest': 'https://resources.premierleague.com/premierleague/badges/50/t17.png',
    'Southampton': 'https://resources.premierleague.com/premierleague/badges/50/t20.png',
    'Tottenham': 'https://resources.premierleague.com/premierleague/badges/50/t6.png',
    'West Ham': 'https://resources.premierleague.com/premierleague/badges/50/t21.png',
    'Wolves': 'https://resources.premierleague.com/premierleague/badges/50/t39.png',
}

# --- STYLE CSS ULTRA MODERNE ---
# Remplacez la section CSS (ligne ~66-280) par ce code amélioré :

# Remplacez la section CSS (ligne ~66-280) par ce design minimaliste professionnel :

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* ========== BASE MINIMALISTE ========== */
    .stApp {
        background: #ffffff;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #1a1a1a;
    }
    
    /* ========== TYPOGRAPHIE CLEAN ========== */
    h1 {
        color: #1a1a1a !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
        font-size: 2.5rem !important;
        margin-bottom: 0.5rem !important;
        line-height: 1.2;
    }
    
    h2 {
        color: #1a1a1a !important;
        font-weight: 600 !important;
        font-size: 1.5rem !important;
        margin-top: 3rem !important;
        margin-bottom: 1rem !important;
        letter-spacing: -0.01em;
    }
    
    h3 {
        color: #4a4a4a !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        margin-bottom: 0.75rem !important;
    }
    
    p, .stMarkdown {
        color: #6a6a6a;
        line-height: 1.6;
        font-weight: 400;
    }
    
    /* ========== CARTES MINIMALISTES ========== */
    .stat-card {
        background: #ffffff;
        border: 1px solid #e8e8e8;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 0.75rem 0;
        transition: all 0.2s ease;
    }
    
    .stat-card:hover {
        border-color: #1a1a1a;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    
    .stat-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a1a;
        line-height: 1.2;
        letter-spacing: -0.02em;
    }
    
    .stat-label {
        color: #8a8a8a;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        margin-top: 0.25rem;
    }
    
    /* ========== BOUTONS PROFESSIONNELS ========== */
    .stButton>button {
        width: 100%;
        background: #1a1a1a;
        color: #ffffff;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.9rem;
        padding: 0.75rem 1.5rem;
        transition: all 0.2s ease;
        letter-spacing: 0.01em;
    }
    
    .stButton>button:hover {
        background: #000000;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    .stButton>button:active {
        transform: translateY(0);
    }
    
    /* ========== SIDEBAR ÉPURÉE ========== */
    [data-testid="stSidebar"] {
        background: #fafafa;
        border-right: 1px solid #e8e8e8;
    }
    
    [data-testid="stSidebar"] h2 {
        color: #1a1a1a !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #6a6a6a;
    }
    
    /* ========== TABS MINIMALISTES ========== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: transparent;
        border-bottom: 1px solid #e8e8e8;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        border-radius: 0;
        color: #8a8a8a;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        font-size: 0.9rem;
        transition: all 0.2s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: #1a1a1a;
        background: #fafafa;
    }
    
    .stTabs [aria-selected="true"] {
        color: #1a1a1a !important;
        border-bottom-color: #1a1a1a !important;
        background: transparent !important;
    }
    
    /* ========== MÉTRIQUES STREAMLIT ========== */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a1a;
        letter-spacing: -0.02em;
    }
    
    [data-testid="stMetricLabel"] {
        color: #8a8a8a !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.75rem;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.85rem;
    }
    
    /* ========== INPUTS CLEAN ========== */
    .stSelectbox > div > div,
    .stTextInput > div > div {
        background: #ffffff;
        border: 1px solid #e8e8e8;
        border-radius: 6px;
        color: #1a1a1a;
        transition: all 0.2s ease;
        font-weight: 500;
    }
    
    .stSelectbox > div > div:hover,
    .stTextInput > div > div:hover {
        border-color: #1a1a1a;
    }
    
    .stSelectbox > div > div:focus-within,
    .stTextInput > div > div:focus-within {
        border-color: #1a1a1a;
        box-shadow: 0 0 0 1px #1a1a1a;
    }
    
    /* ========== RADIO BUTTONS ========== */
    .stRadio > div {
        background: transparent;
        padding: 0;
    }
    
    .stRadio label {
        color: #1a1a1a !important;
        font-weight: 500;
        padding: 0.5rem 0;
    }
    
    .stRadio [role="radiogroup"] label:hover {
        background: #fafafa;
    }
    
    /* ========== EXPANDER MINIMAL ========== */
    .streamlit-expanderHeader {
        background: #fafafa;
        border: 1px solid #e8e8e8;
        border-radius: 6px;
        font-weight: 600;
        color: #1a1a1a !important;
        transition: all 0.2s ease;
    }
    
    .streamlit-expanderHeader:hover {
        background: #f0f0f0;
        border-color: #1a1a1a;
    }
    
    /* ========== ALERTES PROPRES ========== */
    .stAlert {
        background: #fafafa;
        border: 1px solid #e8e8e8;
        border-radius: 6px;
        color: #1a1a1a;
        border-left-width: 3px;
    }
    
    .stSuccess {
        border-left-color: #22c55e !important;
        background: #f0fdf4 !important;
    }
    
    .stError {
        border-left-color: #ef4444 !important;
        background: #fef2f2 !important;
    }
    
    .stWarning {
        border-left-color: #f59e0b !important;
        background: #fffbeb !important;
    }
    
    .stInfo {
        border-left-color: #3b82f6 !important;
        background: #eff6ff !important;
    }
    
    /* ========== DATAFRAMES ========== */
    .dataframe {
        background: #ffffff !important;
        border: 1px solid #e8e8e8 !important;
        border-radius: 6px !important;
        font-size: 0.9rem;
    }
    
    .dataframe thead tr th {
        background: #fafafa !important;
        color: #1a1a1a !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.75rem;
        border-bottom: 1px solid #e8e8e8 !important;
    }
    
    .dataframe tbody tr {
        border-bottom: 1px solid #f0f0f0 !important;
    }
    
    .dataframe tbody tr:hover {
        background: #fafafa !important;
    }
    
    /* ========== SCROLLBAR MINIMAL ========== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #fafafa;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #d0d0d0;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #1a1a1a;
    }
    
    /* ========== BADGE PREMIUM ========== */
    .premium-badge {
        display: inline-block;
        background: #1a1a1a;
        color: #ffffff;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-left: 0.75rem;
        vertical-align: middle;
    }
    
    /* ========== LOGOS CLUBS SUBTLE ========== */
    .club-logo {
        width: 40px;
        height: 40px;
        opacity: 0.4;
        transition: opacity 0.2s ease;
        filter: grayscale(100%);
    }
    
    .club-logo:hover {
        opacity: 1;
        filter: grayscale(0%);
    }
    
    /* ========== SPINNER ========== */
    .stSpinner > div {
        border-top-color: #1a1a1a !important;
        border-right-color: #1a1a1a !important;
    }
    
    /* ========== DIVIDERS ========== */
    hr {
        margin: 2.5rem 0;
        border: none;
        height: 1px;
        background: #e8e8e8;
    }
    
    /* ========== DOWNLOAD BUTTON ========== */
    .stDownloadButton > button {
        background: #ffffff;
        color: #1a1a1a;
        border: 1px solid #1a1a1a;
        border-radius: 6px;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        transition: all 0.2s ease;
    }
    
    .stDownloadButton > button:hover {
        background: #1a1a1a;
        color: #ffffff;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* ========== CONTAINERS ========== */
    .element-container {
        margin-bottom: 1rem;
    }
    
    /* ========== HEADERS CLEAN ========== */
    header[data-testid="stHeader"] {
        background: transparent;
    }
    
    /* ========== FOCUS STATES ========== */
    *:focus-visible {
        outline: 2px solid #1a1a1a;
        outline-offset: 2px;
    }
    
    /* ========== SELECTIONS ========== */
    ::selection {
        background: #1a1a1a;
        color: #ffffff;
    }
    
    /* ========== IMAGES ========== */
    img {
        border-radius: 4px;
    }
    
    /* ========== RESPONSIVE ========== */
    @media (max-width: 768px) {
        h1 {
            font-size: 2rem !important;
        }
        
        h2 {
            font-size: 1.3rem !important;
        }
        
        .stat-value {
            font-size: 2rem;
        }
        
        .stButton>button {
            padding: 0.65rem 1.25rem;
        }
    }
    
    /* ========== DARK MODE OVERRIDE (si activé) ========== */
    @media (prefers-color-scheme: dark) {
        .stApp {
            background: #0a0a0a;
            color: #e8e8e8;
        }
        
        h1, h2 {
            color: #ffffff !important;
        }
        
        h3 {
            color: #d0d0d0 !important;
        }
        
        p, .stMarkdown {
            color: #a0a0a0;
        }
        
        .stat-card {
            background: #1a1a1a;
            border-color: #2a2a2a;
        }
        
        .stat-card:hover {
            border-color: #ffffff;
        }
        
        .stat-value {
            color: #ffffff;
        }
        
        .stButton>button {
            background: #ffffff;
            color: #0a0a0a;
        }
        
        .stButton>button:hover {
            background: #e8e8e8;
        }
        
        [data-testid="stSidebar"] {
            background: #0f0f0f;
            border-right-color: #2a2a2a;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            border-bottom-color: #2a2a2a;
        }
        
        .stTabs [aria-selected="true"] {
            color: #ffffff !important;
            border-bottom-color: #ffffff !important;
        }
        
        .stSelectbox > div > div,
        .stTextInput > div > div {
            background: #1a1a1a;
            border-color: #2a2a2a;
            color: #e8e8e8;
        }
        
        .dataframe {
            background: #1a1a1a !important;
            border-color: #2a2a2a !important;
        }
        
        .dataframe thead tr th {
            background: #0f0f0f !important;
            color: #ffffff !important;
        }
        
        hr {
            background: #2a2a2a;
        }
        
        ::-webkit-scrollbar-track {
            background: #0f0f0f;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #3a3a3a;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #ffffff;
        }
    }
    </style>
    """, unsafe_allow_html=True)
# --- FONCTIONS UTILITAIRES ---

@st.cache_resource
def load_fonts():
    """Charge la police personnalisée ou utilise le défaut."""
    try:
        if os.path.exists(FONT_PATH):
            return fm.FontProperties(fname=FONT_PATH)
    except:
        pass
    return fm.FontProperties(family='sans-serif')

FONT_PROP = load_fonts()

@st.cache_data(ttl=300)
def get_club_logo(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=3)
        if resp.status_code == 200:
            return Image.open(BytesIO(resp.content))
    except:
        pass
    return None

def display_club_logos():
    """Affiche le carousel de logos des clubs"""
    cols = st.columns(20)
    for idx, (club, url) in enumerate(list(PREMIER_LEAGUE_CLUBS.items())):
        with cols[idx % 20]:
            logo = get_club_logo(url)
            if logo:
                st.image(logo, width=30, use_container_width=False)
    st.markdown("---")

def load_match_list():
    matches = []
    if not os.path.exists(URLS_FILE):
        return []
    
    with open(URLS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        header_match = re.search(r'^Match (\d+) - (.+)', line)
        
        if header_match:
            mid = header_match.group(1)
            title = header_match.group(2)
            url = None
            
            for j in range(1, 4):
                if i + j < len(lines):
                    next_line = lines[i+j].strip()
                    if next_line.startswith("https://") and mid in next_line:
                        url = next_line
                        break
            
            if url:
                gameweek = (len(matches) // 10) + 1 
                matches.append({
                    'id': mid, 
                    'title': title, 
                    'url': url,
                    'gameweek': gameweek,
                    'filename': f"{mid}.html"
                })
        i += 1
    return matches

# --- CLASSES LOGIQUE MÉTIER (INCHANGÉES) ---

class StreamlitDownloader:
    def download_match(self, url, filename):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        
        filepath = os.path.join(DATA_FOLDER, filename)
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        system_chromedriver = shutil.which("chromedriver")
        if system_chromedriver:
            service = Service(system_chromedriver)
        else:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
            except Exception as e:
                st.error(f"❌ Impossible de configurer le driver : {e}")
                return False

        driver = None
        try:
            driver = webdriver.Chrome(service=service, options=options)
            with st.spinner(f"🌍 Connexion à WhoScored..."):
                driver.get(url)
                time.sleep(6)
                content = driver.page_source
                if "Incapsula" in content or "challenge" in content.lower():
                    st.warning("🛡️ Vérification de sécurité détectée...")
                    time.sleep(12)
                    content = driver.page_source
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            return True
        except Exception as e:
            st.error(f"❌ Erreur Selenium : {str(e)}")
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

class MatchParser:
    def __init__(self, html_path):
        self.html_path = html_path
        self.soup = None
        self.data = self._load_data()

    def _load_data(self):
        try:
            with open(self.html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.soup = BeautifulSoup(content, 'html.parser')
            
            regex1 = r"require\.config\.params\[\"args\"\]\s*=\s*({.*?});"
            match1 = re.search(regex1, content, re.DOTALL)
            if match1:
                return self._clean_and_parse_json(match1.group(1))
            
            regex2 = r"matchCentreData:\s*({.*?}),\s*matchCentreEventTypeJson"
            match2 = re.search(regex2, content, re.DOTALL)
            if match2:
                return {'matchCentreData': self._clean_and_parse_json(match2.group(1))}
            
            scripts = self.soup.find_all('script')
            for script in scripts:
                script_text = script.string
                if script_text and 'matchCentreData' in script_text:
                    match3 = re.search(r'matchCentreData["\']?\s*:\s*({.*?})\s*[,}]', script_text, re.DOTALL)
                    if match3:
                        return {'matchCentreData': self._clean_and_parse_json(match3.group(1))}
            
            all_matches = re.finditer(r'({[^{}]*"home"[^{}]*"away"[^{}]*"events"[^{}]*})', content)
            for match in all_matches:
                try:
                    parsed = self._clean_and_parse_json(match.group(1))
                    if 'home' in parsed and 'away' in parsed and 'events' in parsed:
                        return {'matchCentreData': parsed}
                except:
                    continue
            raise ValueError("❌ JSON de données introuvable")
        except Exception as e:
            raise ValueError(f"❌ Erreur de parsing : {e}")

    def _clean_and_parse_json(self, json_str):
        keys_to_quote = ['matchId', 'matchCentreData', 'matchCentreEventTypeJson', 'formationIdNameMappings', 'home', 'away', 'score', 'htScore', 'ftScore', 'etScore', 'pkScore', 'events', 'playerIdNameDictionary', 'teamId', 'name', 'managerName', 'players', 'playerId', 'shirtNo', 'position', 'isFirstEleven', 'age', 'height', 'weight', 'isManOfTheMatch', 'stats', 'ratings', 'type', 'displayName', 'outcomeType', 'qualifiers', 'satisfiedEventsTypes', 'x', 'y', 'endX', 'endY', 'id', 'eventId', 'minute', 'second', 'teamFormation', 'formations', 'startTime', 'venueName', 'attendance', 'weatherCode', 'elapsed', 'statusCode', 'periodCode']
        for key in keys_to_quote:
            json_str = re.sub(rf'\b{key}\s*:', f'"{key}":', json_str)
        json_str = re.sub(r'\bundefined\b', 'null', json_str)
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON invalide : {e}")

    def get_all_data(self):
        if 'matchCentreData' not in self.data:
            raise ValueError("Structure incorrecte : 'matchCentreData' manquant")
        mc = self.data['matchCentreData']
        if 'home' not in mc or 'away' not in mc:
            raise ValueError("Données des équipes manquantes")
        
        match_info = {
            'score': mc.get('score', 'N/A'),
            'venue': mc.get('venueName', 'Stade Inconnu'),
            'startTime': mc.get('startTime', ''),
            'attendance': mc.get('attendance', 'N/A'),
            'htScore': mc.get('htScore', 'N/A'),
        }
        
        fmt_divs = self.soup.find_all('div', class_='formation')
        formations = [d.get_text(strip=True) for d in fmt_divs]
        
        teams = {
            'home': {'id': mc['home'].get('teamId', 0), 'name': mc['home'].get('name', 'Équipe Domicile'), 'manager': mc['home'].get('managerName', 'N/A'), 'formation': formations[0] if len(formations) > 0 else 'N/A'},
            'away': {'id': mc['away'].get('teamId', 0), 'name': mc['away'].get('name', 'Équipe Extérieur'), 'manager': mc['away'].get('managerName', 'N/A'), 'formation': formations[1] if len(formations) > 1 else 'N/A'}
        }
        
        logos = {}
        emblems = self.soup.find_all('div', class_='team-emblem')
        for i, emblem in enumerate(emblems[:2]):
            img = emblem.find('img')
            if img and img.get('src'):
                url = img['src']
                if url.startswith('//'): url = 'https:' + url
                logos[i] = url
        return mc, match_info, teams, logos

class PassNetworkEngine:
    def process(self, mc):
        if 'events' not in mc: raise ValueError("Aucun événement trouvé")
        events = pd.DataFrame(mc['events'])
        
        players_list = []
        for side in ['home', 'away']:
            if side not in mc or 'teamId' not in mc[side]: continue
            tid = mc[side]['teamId']
            if 'players' in mc[side]:
                for p in mc[side]['players']:
                    p['teamId'] = tid
                    players_list.append(p)
        
        if not players_list: raise ValueError("Aucun joueur trouvé")
        df_players = pd.DataFrame(players_list)
        
        for col in ['endX', 'endY', 'x', 'y']:
            if col not in events.columns: events[col] = 0.0
        
        if 'type' not in events.columns: events['type'] = None
        if 'outcomeType' not in events.columns: events['outcomeType'] = None
            
        events['type'] = events['type'].apply(lambda x: x.get('displayName') if isinstance(x, dict) else x)
        events['outcomeType'] = events['outcomeType'].apply(lambda x: x.get('displayName') if isinstance(x, dict) else x)
        
        events['next_teamId'] = events['teamId'].shift(-1)
        events['next_playerId'] = events['playerId'].shift(-1)
        mask = (events['type'] == 'Pass') & (events['outcomeType'] == 'Successful') & (events['teamId'] == events['next_teamId'])
        events.loc[mask, 'receiverId'] = events.loc[mask, 'next_playerId']
        return events, df_players

    def get_network(self, team_id, events, players, min_passes=3):
        starters = players[(players['teamId'] == team_id) & (players['isFirstEleven'] == True)]
        starter_ids = starters['playerId'].unique()
        
        if len(starter_ids) == 0: return pd.DataFrame(), pd.DataFrame(columns=['playerId', 'name', 'shirtNo', 'position', 'x', 'y', 'count'])
        
        team_events = events[(events['teamId'] == team_id) & (events['playerId'].isin(starter_ids))]
        if team_events.empty: return pd.DataFrame(), pd.DataFrame(columns=['playerId', 'name', 'shirtNo', 'position', 'x', 'y', 'count'])
        
        avg_locs = team_events.groupby('playerId').agg({'x':'mean', 'y':'mean', 'id':'count'}).rename(columns={'id':'count'})
        avg_locs = avg_locs.merge(players[['playerId', 'name', 'shirtNo', 'position']], on='playerId')
        
        passes = team_events[(team_events['type'] == 'Pass') & (team_events['outcomeType'] == 'Successful') & (team_events['receiverId'].notna()) & (team_events['receiverId'].isin(starter_ids))].copy()
        if passes.empty: return pd.DataFrame(), avg_locs
        
        passes['pair'] = passes.apply(lambda r: tuple(sorted([r['playerId'], r['receiverId']])), axis=1)
        pass_counts = passes.groupby('pair').size().reset_index(name='pass_count')
        pass_counts = pass_counts[pass_counts['pass_count'] >= min_passes]
        
        network = []
        for _, row in pass_counts.iterrows():
            p1, p2 = row['pair']
            if p1 in avg_locs['playerId'].values and p2 in avg_locs['playerId'].values:
                l1 = avg_locs[avg_locs['playerId'] == p1].iloc[0]
                l2 = avg_locs[avg_locs['playerId'] == p2].iloc[0]
                network.append({'player1': l1['name'], 'player2': l2['name'], 'x_start': l1['x'], 'y_start': l1['y'], 'x_end': l2['x'], 'y_end': l2['y'], 'pass_count': row['pass_count']})
        
        return pd.DataFrame(network), avg_locs

class DashboardVisualizer:
    def create_dashboard(self, match_info, teams, home_net, home_nodes, away_net, away_nodes, home_logo_url, away_logo_url):
        home_logo_img = self._get_logo_from_url(home_logo_url)
        away_logo_img = self._get_logo_from_url(away_logo_url)
        stats = {'home': {}, 'away': {}}
        return self.draw_dashboard(match_info, teams, stats, home_net, home_nodes, away_net, away_nodes, home_logo_img, away_logo_img, output_file=None)
    
    def _get_logo_from_url(self, url):
        if not url: return None
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, stream=True, timeout=5)
            if resp.status_code == 200: return Image.open(BytesIO(resp.content))
        except: return None
        return None

    def draw_dashboard(self, match_info, teams, stats, home_net, home_nodes, away_net, away_nodes, home_logo_img, away_logo_img, output_file=None):
        STYLE = {'background': '#0E1117', 'text_color': '#FFFFFF', 'sub_text': '#A0A0A0', 'home_color': '#00BFFF', 'away_color': '#FF4B4B', 'line_color': '#2B313E', 'font_prop': FONT_PROP, 'legend_blue': '#5DADEC'}

        fig = plt.figure(figsize=(24, 22), facecolor=STYLE['background'])
        gs = gridspec.GridSpec(4, 3, width_ratios=[1, 0.05, 1], height_ratios=[0.08, 0.04, 0.68, 0.20])

        ax_header = fig.add_subplot(gs[0, :])
        self._draw_header(ax_header, match_info, teams, home_logo_img, away_logo_img, STYLE)

        ax_legend = fig.add_subplot(gs[1, :])
        self._draw_legend(ax_legend, STYLE)

        ax_home = fig.add_subplot(gs[2, 0])
        self._draw_pass_map(ax_home, home_net, home_nodes, STYLE['home_color'], STYLE)

        ax_arrow = fig.add_subplot(gs[2, 1])
        self._draw_direction_arrow(ax_arrow, STYLE)

        ax_away = fig.add_subplot(gs[2, 2])
        self._draw_pass_map(ax_away, away_net, away_nodes, STYLE['away_color'], STYLE, flip=False)

        ax_lineup_home = fig.add_subplot(gs[3, 0])
        self._draw_lineup(ax_lineup_home, home_nodes, STYLE['home_color'], teams['home']['name'], STYLE)

        ax_lineup_away = fig.add_subplot(gs[3, 2])
        self._draw_lineup(ax_lineup_away, away_nodes, STYLE['away_color'], teams['away']['name'], STYLE)

        fig.text(0.5, 0.01, "Données: WhoScored/Opta | Visualisation: Advanced Python Analysis", ha='center', color=STYLE['sub_text'], fontsize=12, fontproperties=STYLE['font_prop'])
        plt.tight_layout()
        plt.subplots_adjust(top=0.95, hspace=0.02, wspace=0.02)
        
        if output_file:
            plt.savefig(output_file, facecolor=STYLE['background'], dpi=300, bbox_inches='tight')
            plt.close(fig)
        return fig

    def _draw_header(self, ax, match_info, teams, home_logo, away_logo, STYLE):
        ax.axis('off')
        if home_logo:
            ib_home = OffsetImage(home_logo, zoom=0.9)
            ab_home = AnnotationBbox(ib_home, (0.10, 0.5), frameon=False, xycoords='axes fraction', box_alignment=(0.5, 0.5))
            ax.add_artist(ab_home)
        if away_logo:
            ib_away = OffsetImage(away_logo, zoom=0.9)
            ab_away = AnnotationBbox(ib_away, (0.90, 0.5), frameon=False, xycoords='axes fraction', box_alignment=(0.5, 0.5))
            ax.add_artist(ab_away)

        start_time = match_info.get('startTime', '')
        date_display = start_time[:10] if len(start_time) >= 10 else 'Date inconnue'
        date_venue = f"{date_display} | {match_info.get('venue', 'Stade Inconnu')}"
        ax.text(0.5, 0.90, date_venue, ha='center', va='center', color=STYLE['sub_text'], fontsize=14, fontproperties=STYLE['font_prop'])
        score_txt = str(match_info.get('score', 'N/A')).replace(' : ', '-')
        ax.text(0.5, 0.50, score_txt, ha='center', va='center', fontsize=65, weight='bold', color='white', fontproperties=STYLE['font_prop'])
        ax.text(0.5, 0.25, "Score final", ha='center', va='center', fontsize=14, weight='bold', color=STYLE['sub_text'], fontproperties=STYLE['font_prop'])
        ax.text(0.35, 0.65, teams['home']['name'].upper(), ha='right', va='center', fontsize=30, weight='bold', color=STYLE['home_color'], fontproperties=STYLE['font_prop'])
        ax.text(0.65, 0.65, teams['away']['name'].upper(), ha='left', va='center', fontsize=30, weight='bold', color=STYLE['away_color'], fontproperties=STYLE['font_prop'])
        home_sub = f"{teams['home'].get('manager', 'N/A')}\n({teams['home'].get('formation', 'N/A')})"
        away_sub = f"{teams['away'].get('manager', 'N/A')}\n({teams['away'].get('formation', 'N/A')})"
        ax.text(0.35, 0.35, home_sub, ha='right', va='center', fontsize=16, color=STYLE['sub_text'], weight='normal', fontproperties=STYLE['font_prop'])
        ax.text(0.65, 0.35, away_sub, ha='left', va='center', fontsize=16, color=STYLE['sub_text'], weight='normal', fontproperties=STYLE['font_prop'])

    def _draw_pass_map(self, ax, net_df, nodes_df, color, STYLE, flip=False):
        pitch = VerticalPitch(pitch_type='opta', pitch_color=STYLE['background'], line_color=STYLE['line_color'], linewidth=1.5)
        pitch.draw(ax=ax)
        if not net_df.empty: net_df = net_df.copy()
        if not nodes_df.empty: nodes_df = nodes_df.copy()
        if flip:
             net_df['x_start'] = 100 - net_df['x_start']; net_df['y_start'] = 100 - net_df['y_start']
             net_df['x_end'] = 100 - net_df['x_end']; net_df['y_end'] = 100 - net_df['y_end']
             nodes_df['x'] = 100 - nodes_df['x']; nodes_df['y'] = 100 - nodes_df['y']
        if not net_df.empty:
            max_pass = net_df['pass_count'].max()
            if max_pass > 0:
                width = (net_df['pass_count'] / max_pass * 12)
                pitch.lines(net_df['x_start'], net_df['y_start'], net_df['x_end'], net_df['y_end'], lw=width, ax=ax, color=color, alpha=0.5, zorder=2)
        if not nodes_df.empty:
            max_count = nodes_df['count'].max()
            if max_count > 0:
                for i, row in nodes_df.iterrows():
                    size = (row['count'] / max_count) * 1500
                    pitch.scatter(row['x'], row['y'], s=size, color=STYLE['background'], edgecolors=color, linewidth=2, zorder=3, ax=ax)
                    pitch.annotate(row['shirtNo'], xy=(row['x'], row['y']), va='center', ha='center', color='white', fontsize=12, weight='bold', zorder=4, ax=ax, fontproperties=STYLE['font_prop'])

    def _draw_direction_arrow(self, ax, STYLE):
        ax.axis('off'); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.annotate('', xy=(0.7, 0.95), xytext=(0.7, 0.05), arrowprops=dict(facecolor='white', edgecolor='white', width=1.5, headwidth=8, headlength=10), xycoords='axes fraction', textcoords='axes fraction')
        ax.text(0.3, 0.5, "Sens du jeu", rotation=90, ha='center', va='center', color='white', fontsize=14, weight='bold', fontproperties=STYLE['font_prop'])

    def _draw_lineup(self, ax, nodes_df, color, team_name, STYLE):
        ax.axis('off')
        if nodes_df.empty: return
        nodes_df = nodes_df.copy()
        nodes_df['shirtNoInt'] = pd.to_numeric(nodes_df['shirtNo'], errors='coerce').fillna(999).astype(int)
        lineup = nodes_df.sort_values('shirtNoInt')
        y_start = 0.96; y_step = 0.12
        half = (len(lineup) + 1) // 2
        col1 = lineup.iloc[:half]; col2 = lineup.iloc[half:]
        y_pos = y_start
        for _, row in col1.iterrows():
            txt = f"{row['shirtNo']} - {row['name']}"
            ax.text(0.20, y_pos, txt, color='white', fontsize=13, ha='left', fontproperties=STYLE['font_prop'])
            y_pos -= y_step
        y_pos = y_start
        for _, row in col2.iterrows():
            txt = f"{row['shirtNo']} - {row['name']}"
            ax.text(0.60, y_pos, txt, color='white', fontsize=13, ha='left', fontproperties=STYLE['font_prop'])
            y_pos -= y_step

    def _draw_legend(self, ax, STYLE):
        ax.axis('off'); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        legend_y = 0.4
        ax.text(0.15, legend_y, "Peu de passes", ha='right', va='center', color='white', fontsize=12, weight='bold', fontproperties=STYLE['font_prop'])
        sizes = [80, 200, 400, 700]; x_start = 0.17; x_spacing = 0.03
        for i, s in enumerate(sizes): ax.scatter(x_start + (i * x_spacing), legend_y, s=s, color=STYLE['background'], edgecolors=STYLE['legend_blue'], linewidth=1.5)
        ax.text(x_start + (len(sizes) * x_spacing) + 0.0005, legend_y, "Beaucoup de passes", ha='left', va='center', color='white', fontsize=12, weight='bold', fontproperties=STYLE['font_prop'])
        right_start = 0.55
        ax.text(right_start, legend_y, "Combine peu", ha='right', va='center', color='white', fontsize=12, weight='bold', fontproperties=STYLE['font_prop'])
        widths = [1, 3, 6]; line_length = 0.04; line_spacing = 0.01; current_x = right_start + 0.02
        for w in widths: ax.plot([current_x, current_x + line_length], [legend_y, legend_y], color='white', lw=w); current_x += line_length + line_spacing
        ax.text(current_x + 0.01, legend_y, "Combine beaucoup", ha='left', va='center', color='white', fontsize=12, weight='bold', fontproperties=STYLE['font_prop'])

# --- FONCTION PRINCIPALE (UI MODERNISÉE) ---

def main():
    # Header Design
    st.markdown('<h1>⚽ Premier League Analyst <span class="premium-badge">PRO</span></h1>', unsafe_allow_html=True)
    st.markdown("*Analyse tactique avancée propulsée par l'IA et les données Opta*")
    
    display_club_logos() # Carousel

    # SIDEBAR
    st.sidebar.markdown("### 🛠️ Panneau de contrôle")
    st.sidebar.markdown("---")
    
    mode = st.sidebar.radio(
        "Mode de Sélection",
        ["📅 Calendrier / Journées", "🌐 URL Personnalisée"],
        label_visibility="collapsed"
    )

    selected_match_data = None
    needs_download = False
    
    if mode == "📅 Calendrier / Journées":
        matches = load_match_list()
        if not matches:
            st.error(f"📁 Fichier '{URLS_FILE}' introuvable")
        else:
            df_matches = pd.DataFrame(matches)
            gameweeks = sorted(df_matches['gameweek'].unique())
            sel_gw = st.sidebar.selectbox("🏆 Sélectionner une Journée", gameweeks, format_func=lambda x: f"Gameweek {x}")
            
            gw_matches = df_matches[df_matches['gameweek'] == sel_gw]
            match_options = {f"{r['title']}": r.to_dict() for _, r in gw_matches.iterrows()}
            
            sel_match_key = st.sidebar.selectbox("⚽ Sélectionner un Match", list(match_options.keys()))
            selected_match_data = match_options[sel_match_key]
            
            file_path = os.path.join(DATA_FOLDER, selected_match_data['filename'])
            if os.path.exists(file_path):
                st.sidebar.success("✅ Données disponibles")
                needs_download = False
            else:
                st.sidebar.warning("☁️ À télécharger")
                needs_download = True

    elif mode == "🌐 URL Personnalisée":
        url_input = st.sidebar.text_input("🔗 Coller l'URL WhoScored ici")
        if url_input:
            match_id = re.search(r'/matches/(\d+)/', url_input)
            if match_id:
                mid = match_id.group(1)
                selected_match_data = {'id': mid, 'title': f"Match #{mid}", 'url': url_input, 'filename': f"{mid}.html"}
                file_path = os.path.join(DATA_FOLDER, selected_match_data['filename'])
                needs_download = not os.path.exists(file_path)
            else:
                st.sidebar.error("❌ URL invalide")

    if selected_match_data is not None:
        st.markdown(f"## {selected_match_data['title']}")
        
        if needs_download:
            st.info("💾 Les données ne sont pas en cache local. Cliquez ci-dessous pour lancer l'analyse.")
            if st.button("🚀 Télécharger et Analyser le Match", type="primary"):
                downloader = StreamlitDownloader()
                success = downloader.download_match(selected_match_data['url'], selected_match_data['filename'])
                if success:
                    st.success("✅ Téléchargement réussi !")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Échec du téléchargement")
        else:
            file_path = os.path.join(DATA_FOLDER, selected_match_data['filename'])
            try:
                with st.spinner("🔍 Analyse tactique en cours..."):
                    parser = MatchParser(file_path)
                    mc, match_info, teams, logos = parser.get_all_data()
                    
                    engine = PassNetworkEngine()
                    events, players = engine.process(mc)
                    home_net, home_nodes = engine.get_network(teams['home']['id'], events, players)
                    away_net, away_nodes = engine.get_network(teams['away']['id'], events, players)
                
                # VISUALISATION
                st.markdown("---")
                with st.spinner("🎨 Génération de la visualisation HD..."):
                    viz = DashboardVisualizer()
                    fig = viz.create_dashboard(match_info, teams, home_net, home_nodes, away_net, away_nodes, logos.get(0), logos.get(1))
                    
                    st.pyplot(fig, use_container_width=True)
                    
                    # Bouton de téléchargement
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        buf = BytesIO()
                        fig.savefig(buf, format="png", facecolor='#0E1117', bbox_inches='tight', dpi=300)
                        st.download_button(
                            label="💾 Télécharger l'image (Haute Résolution)",
                            data=buf.getvalue(),
                            file_name=f"PassNetwork_{selected_match_data['id']}_HD.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    plt.close(fig)

            except Exception as e:
                st.error(f"❌ Erreur d'analyse : {e}")
                if st.button("🗑️ Effacer le cache corrompu"):
                    os.remove(file_path)
                    st.rerun()

    else:
        st.markdown("### 👋 Bienvenue")
        st.info("Sélectionnez un match dans le menu de gauche pour commencer.")
    
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #666; font-size: 0.8rem;'>Analysis Tool v2.0 • Data via WhoScored/Opta</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
