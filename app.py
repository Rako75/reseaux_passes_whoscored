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
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
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
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
    
    /* Fond global avec gradient */
    .stApp {
        background: linear-gradient(135deg, #0E1117 0%, #1a1f2e 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Titres modernes */
    h1 {
        background: linear-gradient(90deg, #00FF85 0%, #00D9FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900 !important;
        letter-spacing: -1px;
        font-size: 3.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    h2 {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        border-left: 4px solid #00FF85;
        padding-left: 1rem;
        margin-top: 2rem !important;
    }
    
    h3 {
        color: #B8B8B8 !important;
        font-weight: 600 !important;
        font-size: 1.3rem !important;
    }
    
    /* Cartes stats modernes avec glassmorphism */
    .stat-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    
    .stat-card:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(0, 255, 133, 0.3);
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0, 255, 133, 0.1);
    }
    
    .stat-value {
        font-size: 2.5rem;
        font-weight: 900;
        background: linear-gradient(135deg, #00FF85 0%, #00D9FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.2;
    }
    
    .stat-label {
        color: #888;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    
    /* Boutons premium */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #38003c 0%, #2d0031 100%);
        color: #00FF85;
        border: 2px solid #00FF85;
        border-radius: 12px;
        font-weight: 700;
        font-size: 1rem;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 15px rgba(0, 255, 133, 0.2);
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #00FF85 0%, #00D9FF 100%);
        color: #000;
        border-color: #00D9FF;
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 255, 133, 0.4);
    }
    
    /* Sidebar élégante */
    .css-1d391kg {
        background: rgba(14, 17, 23, 0.95);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Tabs modernes */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        color: #888;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #00FF85 0%, #00D9FF 100%);
        color: #000 !important;
        border-color: transparent;
    }
    
    /* Métriques Streamlit */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 900;
        background: linear-gradient(135deg, #00FF85 0%, #00D9FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Dataframes élégants */
    .dataframe {
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
    }
    
    /* Expander moderne */
    .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        font-weight: 600;
    }
    
    /* Messages d'alerte glassmorphism */
    .stAlert {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        color: white;
    }
    
    /* Scrollbar personnalisée */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.02);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(0, 255, 133, 0.3);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(0, 255, 133, 0.5);
    }
    
    /* Animation de chargement */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    .loading {
        animation: pulse 2s ease-in-out infinite;
    }
    
    /* Badge Premium */
    .premium-badge {
        display: inline-block;
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
        color: #000;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-left: 0.5rem;
    }
    
    /* Club logo carousel */
    .club-logo {
        width: 40px;
        height: 40px;
        opacity: 0.6;
        transition: all 0.3s ease;
        margin: 0 0.5rem;
        filter: grayscale(50%);
    }
    
    .club-logo:hover {
        opacity: 1;
        transform: scale(1.2);
        filter: grayscale(0%);
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
    """Télécharge et cache un logo de club"""
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
    st.markdown("---")
    
    # Créer une grille pour les logos
    cols = st.columns(20)
    for idx, (club, url) in enumerate(list(PREMIER_LEAGUE_CLUBS.items())):
        with cols[idx % 20]:
            logo = get_club_logo(url)
            if logo:
                st.image(logo, width=40, use_container_width=False)
    
    st.markdown("---")

def load_match_list():
    """Charge la liste des matchs depuis le fichier texte."""
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

# --- CLASSES LOGIQUE MÉTIER ---

class StreamlitDownloader:
    """Téléchargeur robuste compatible Streamlit Cloud & Linux."""
    
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
    """Parse le HTML pour extraire le JSON caché avec plusieurs méthodes."""
    def __init__(self, html_path):
        self.html_path = html_path
        self.soup = None
        self.data = self._load_data()

    def _load_data(self):
        try:
            with open(self.html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.soup = BeautifulSoup(content, 'html.parser')
            
            # MÉTHODE 1 : Regex classique
            regex1 = r"require\.config\.params\[\"args\"\]\s*=\s*({.*?});"
            match1 = re.search(regex1, content, re.DOTALL)
            
            if match1:
                json_str = match1.group(1)
                return self._clean_and_parse_json(json_str)
            
            # MÉTHODE 2 : matchCentreData direct
            regex2 = r"matchCentreData:\s*({.*?}),\s*matchCentreEventTypeJson"
            match2 = re.search(regex2, content, re.DOTALL)
            
            if match2:
                json_str = match2.group(1)
                parsed = self._clean_and_parse_json(json_str)
                return {'matchCentreData': parsed}
            
            # MÉTHODE 3 : Scripts
            scripts = self.soup.find_all('script')
            for script in scripts:
                script_text = script.string
                if script_text and 'matchCentreData' in script_text:
                    match3 = re.search(r'matchCentreData["\']?\s*:\s*({.*?})\s*[,}]', script_text, re.DOTALL)
                    if match3:
                        json_str = match3.group(1)
                        parsed = self._clean_and_parse_json(json_str)
                        return {'matchCentreData': parsed}
            
            # MÉTHODE 4 : Recherche agressive
            all_matches = re.finditer(r'({[^{}]*"home"[^{}]*"away"[^{}]*"events"[^{}]*})', content)
            for match in all_matches:
                try:
                    json_str = match.group(1)
                    parsed = self._clean_and_parse_json(json_str)
                    if 'home' in parsed and 'away' in parsed and 'events' in parsed:
                        return {'matchCentreData': parsed}
                except:
                    continue
            
            raise ValueError("❌ JSON de données introuvable")
            
        except Exception as e:
            raise ValueError(f"❌ Erreur de parsing : {e}")

    def _clean_and_parse_json(self, json_str):
        """Nettoie et parse une chaîne JSON"""
        keys_to_quote = [
            'matchId', 'matchCentreData', 'matchCentreEventTypeJson', 'formationIdNameMappings',
            'home', 'away', 'score', 'htScore', 'ftScore', 'etScore', 'pkScore',
            'events', 'playerIdNameDictionary', 'teamId', 'name', 'managerName',
            'players', 'playerId', 'shirtNo', 'position', 'isFirstEleven',
            'age', 'height', 'weight', 'isManOfTheMatch', 'stats', 'ratings',
            'type', 'displayName', 'outcomeType', 'qualifiers', 'satisfiedEventsTypes',
            'x', 'y', 'endX', 'endY', 'id', 'eventId', 'minute', 'second',
            'teamFormation', 'formations', 'startTime', 'venueName', 'attendance',
            'weatherCode', 'elapsed', 'statusCode', 'periodCode'
        ]
        
        for key in keys_to_quote:
            json_str = re.sub(rf'\b{key}\s*:', f'"{key}":', json_str)
        
        json_str = re.sub(r'\bundefined\b', 'null', json_str)
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            st.warning(f"⚠️ Erreur JSON : {e}")
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
        
        # Formations
        fmt_divs = self.soup.find_all('div', class_='formation')
        formations = [d.get_text(strip=True) for d in fmt_divs]
        
        teams = {
            'home': {
                'id': mc['home'].get('teamId', 0), 
                'name': mc['home'].get('name', 'Équipe Domicile'),
                'manager': mc['home'].get('managerName', 'N/A'),
                'formation': formations[0] if len(formations) > 0 else 'N/A'
            },
            'away': {
                'id': mc['away'].get('teamId', 0), 
                'name': mc['away'].get('name', 'Équipe Extérieur'),
                'manager': mc['away'].get('managerName', 'N/A'),
                'formation': formations[1] if len(formations) > 1 else 'N/A'
            }
        }
        
        # Logos URLs
        logos = {}
        emblems = self.soup.find_all('div', class_='team-emblem')
        for i, emblem in enumerate(emblems[:2]):
            img = emblem.find('img')
            if img and img.get('src'):
                url = img['src']
                if url.startswith('//'):
                    url = 'https:' + url
                logos[i] = url

        return mc, match_info, teams, logos

class PassNetworkEngine:
    """Calcule les réseaux de passes."""
    def process(self, mc):
        if 'events' not in mc:
            raise ValueError("Aucun événement trouvé")
        
        events = pd.DataFrame(mc['events'])
        
        # Extraction joueurs
        players_list = []
        for side in ['home', 'away']:
            if side not in mc or 'teamId' not in mc[side]:
                continue
            tid = mc[side]['teamId']
            if 'players' in mc[side]:
                for p in mc[side]['players']:
                    p['teamId'] = tid
                    players_list.append(p)
        
        if not players_list:
            raise ValueError("Aucun joueur trouvé")
        
        df_players = pd.DataFrame(players_list)
        
        # Sécurisation des colonnes
        for col in ['endX', 'endY', 'x', 'y']:
            if col not in events.columns: 
                events[col] = 0.0
        
        if 'type' not in events.columns:
            events['type'] = None
        if 'outcomeType' not in events.columns:
            events['outcomeType'] = None
            
        # Nettoyage types
        events['type'] = events['type'].apply(lambda x: x.get('displayName') if isinstance(x, dict) else x)
        events['outcomeType'] = events['outcomeType'].apply(lambda x: x.get('displayName') if isinstance(x, dict) else x)
        
        # Identifier receveur
        events['next_teamId'] = events['teamId'].shift(-1)
        events['next_playerId'] = events['playerId'].shift(-1)
        mask = (events['type'] == 'Pass') & (events['outcomeType'] == 'Successful') & (events['teamId'] == events['next_teamId'])
        events.loc[mask, 'receiverId'] = events.loc[mask, 'next_playerId']
        
        return events, df_players

    def get_network(self, team_id, events, players, min_passes=3):
        starters = players[(players['teamId'] == team_id) & (players['isFirstEleven'] == True)]
        starter_ids = starters['playerId'].unique()
        
        if len(starter_ids) == 0:
            return pd.DataFrame(), pd.DataFrame(columns=['playerId', 'name', 'shirtNo', 'position', 'x', 'y', 'count'])
        
        team_events = events[(events['teamId'] == team_id) & (events['playerId'].isin(starter_ids))]
        
        if team_events.empty:
            return pd.DataFrame(), pd.DataFrame(columns=['playerId', 'name', 'shirtNo', 'position', 'x', 'y', 'count'])
        
        # Positions moyennes
        avg_locs = team_events.groupby('playerId').agg({'x':'mean', 'y':'mean', 'id':'count'}).rename(columns={'id':'count'})
        avg_locs = avg_locs.merge(players[['playerId', 'name', 'shirtNo', 'position']], on='playerId')
        
        # Calcul des passes
        passes = team_events[
            (team_events['type'] == 'Pass') & 
            (team_events['outcomeType'] == 'Successful') & 
            (team_events['receiverId'].notna()) &
            (team_events['receiverId'].isin(starter_ids))
        ].copy()
        
        if passes.empty:
            return pd.DataFrame(), avg_locs
        
        passes['pair'] = passes.apply(lambda r: tuple(sorted([r['playerId'], r['receiverId']])), axis=1)
        pass_counts = passes.groupby('pair').size().reset_index(name='pass_count')
        pass_counts = pass_counts[pass_counts['pass_count'] >= min_passes]
        
        network = []
        for _, row in pass_counts.iterrows():
            p1, p2 = row['pair']
            if p1 in avg_locs['playerId'].values and p2 in avg_locs['playerId'].values:
                l1 = avg_locs[avg_locs['playerId'] == p1].iloc[0]
                l2 = avg_locs[avg_locs['playerId'] == p2].iloc[0]
                network.append({
                    'player1': l1['name'], 'player2': l2['name'],
                    'x_start': l1['x'], 'y_start': l1['y'],
                    'x_end': l2['x'], 'y_end': l2['y'],
                    'pass_count': row['pass_count']
                })
        
        return pd.DataFrame(network), avg_locs

class AdvancedAnalytics:
    """Analyses avancées des matchs"""
    
    @staticmethod
    def calculate_team_stats(events, team_id, players):
        """Calcule les statistiques détaillées d'une équipe"""
        team_events = events[events['teamId'] == team_id]
        
        # Stats de base
        total_passes = len(team_events[team_events['type'] == 'Pass'])
        successful_passes = len(team_events[(team_events['type'] == 'Pass') & (team_events['outcomeType'] == 'Successful')])
        pass_accuracy = (successful_passes / total_passes * 100) if total_passes > 0 else 0
        
        # Tirs
        shots = len(team_events[team_events['type'].isin(['MissedShots', 'SavedShot', 'Goal', 'ShotOnPost'])])
        shots_on_target = len(team_events[team_events['type'].isin(['SavedShot', 'Goal'])])
        goals = len(team_events[team_events['type'] == 'Goal'])
        
        # Possession par tiers
        def_third = len(team_events[(team_events['type'] == 'Pass') & (team_events['x'] < 33.3)])
        mid_third = len(team_events[(team_events['type'] == 'Pass') & (team_events['x'] >= 33.3) & (team_events['x'] < 66.6)])
        att_third = len(team_events[(team_events['type'] == 'Pass') & (team_events['x'] >= 66.6)])
        
        # Duels
        duels = len(team_events[team_events['type'].isin(['Aerial', 'Tackle', 'Challenge'])])
        duels_won = len(team_events[(team_events['type'].isin(['Aerial', 'Tackle', 'Challenge'])) & 
                                     (team_events['outcomeType'] == 'Successful')])
        
        return {
            'passes': total_passes,
            'pass_accuracy': round(pass_accuracy, 1),
            'shots': shots,
            'shots_on_target': shots_on_target,
            'goals': goals,
            'def_third_passes': def_third,
            'mid_third_passes': mid_third,
            'att_third_passes': att_third,
            'duels': duels,
            'duels_won': duels_won,
            'duel_success': round((duels_won / duels * 100) if duels > 0 else 0, 1)
        }
    
    @staticmethod
    def get_player_performance(events, players, team_id):
        """Analyse la performance individuelle des joueurs"""
        team_events = events[events['teamId'] == team_id]
        team_players = players[players['teamId'] == team_id]
        
        player_stats = []
        for _, player in team_players.iterrows():
            player_events = team_events[team_events['playerId'] == player['playerId']]
            
            passes = len(player_events[player_events['type'] == 'Pass'])
            successful_passes = len(player_events[(player_events['type'] == 'Pass') & 
                                                   (player_events['outcomeType'] == 'Successful')])
            
            player_stats.append({
                'name': player['name'],
                'number': player['shirtNo'],
                'position': player['position'],
                'passes': passes,
                'pass_accuracy': round((successful_passes / passes * 100) if passes > 0 else 0, 1),
                'touches': len(player_events),
                'isStarter': player['isFirstEleven']
            })
        
        return pd.DataFrame(player_stats).sort_values('touches', ascending=False)
    
    @staticmethod
    def create_heatmap_data(events, team_id):
        """Crée les données pour une heatmap"""
        team_events = events[(events['teamId'] == team_id) & (events['x'].notna()) & (events['y'].notna())]
        
        # Diviser le terrain en grille 10x10
        team_events['x_bin'] = pd.cut(team_events['x'], bins=10, labels=False)
        team_events['y_bin'] = pd.cut(team_events['y'], bins=10, labels=False)
        
        heatmap = team_events.groupby(['x_bin', 'y_bin']).size().reset_index(name='count')
        
        return heatmap
    
    @staticmethod
    def analyze_passing_network_centrality(network_df, nodes_df):
        """Analyse la centralité du réseau de passes"""
        if network_df.empty or nodes_df.empty:
            return pd.DataFrame()
        
        # Calculer le degré (nombre de connexions) pour chaque joueur
        player_connections = {}
        
        for _, row in network_df.iterrows():
            p1, p2 = row['player1'], row['player2']
            player_connections[p1] = player_connections.get(p1, 0) + 1
            player_connections[p2] = player_connections.get(p2, 0) + 1
        
        centrality_data = []
        for player, connections in player_connections.items():
            player_data = nodes_df[nodes_df['name'] == player]
            if not player_data.empty:
                centrality_data.append({
                    'name': player,
                    'connections': connections,
                    'touches': player_data.iloc[0]['count'],
                    'number': player_data.iloc[0]['shirtNo']
                })
        
        return pd.DataFrame(centrality_data).sort_values('connections', ascending=False)

class DashboardVisualizer:
    """Gère le rendu graphique - Version exacte du pipeline"""

    def create_dashboard(self, match_info, teams, home_net, home_nodes, away_net, away_nodes, home_logo_url, away_logo_url):
        """Méthode principale"""
        
        home_logo_img = self._get_logo_from_url(home_logo_url)
        away_logo_img = self._get_logo_from_url(away_logo_url)
        
        stats = {'home': {}, 'away': {}}
        
        return self.draw_dashboard(
            match_info, teams, stats,
            home_net, home_nodes,
            away_net, away_nodes,
            home_logo_img, away_logo_img,
            output_file=None
        )
    
    def _get_logo_from_url(self, url):
        """Télécharge image depuis URL"""
        if not url:
            return None
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, stream=True, timeout=5)
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content))
                return img
        except:
            return None
        return None

    def draw_dashboard(self, match_info, teams, stats,
                       home_net, home_nodes,
                       away_net, away_nodes,
                       home_logo_img, away_logo_img,
                       output_file=None):
        """Méthode de dessin principale - CODE EXACT DU PIPELINE"""

        STYLE = {
            'background': '#0E1117',
            'text_color': '#FFFFFF',
            'sub_text': '#A0A0A0',
            'home_color': '#00BFFF',
            'away_color': '#FF4B4B',
            'line_color': '#2B313E',
            'font_prop': FONT_PROP,
            'legend_blue': '#5DADEC'
        }

        fig = plt.figure(figsize=(24, 22), facecolor=STYLE['background'])
        gs = gridspec.GridSpec(4, 3, width_ratios=[1, 0.05, 1], height_ratios=[0.08, 0.04, 0.68, 0.20])

        # HEADER
        ax_header = fig.add_subplot(gs[0, :])
        self._draw_header(ax_header, match_info, teams, home_logo_img, away_logo_img, STYLE)

        # LÉGENDE
        ax_legend = fig.add_subplot(gs[1, :])
        self._draw_legend(ax_legend, STYLE)

        # TERRAINS
        ax_home = fig.add_subplot(gs[2, 0])
        self._draw_pass_map(ax_home, home_net, home_nodes, STYLE['home_color'], STYLE)

        ax_arrow = fig.add_subplot(gs[2, 1])
        self._draw_direction_arrow(ax_arrow, STYLE)

        ax_away = fig.add_subplot(gs[2, 2])
        self._draw_pass_map(ax_away, away_net, away_nodes, STYLE['away_color'], STYLE, flip=False)

        # COMPOSITIONS
        ax_lineup_home = fig.add_subplot(gs[3, 0])
        self._draw_lineup(ax_lineup_home, home_nodes, STYLE['home_color'], teams['home']['name'], STYLE)

        ax_lineup_away = fig.add_subplot(gs[3, 2])
        self._draw_lineup(ax_lineup_away, away_nodes, STYLE['away_color'], teams['away']['name'], STYLE)

        fig.text(0.5, 0.01, "Données: WhoScored/Opta | Visualisation: Advanced Python Analysis",
                 ha='center', color=STYLE['sub_text'], fontsize=12, fontproperties=STYLE['font_prop'])

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

        ax.text(0.35, 0.65, teams['home']['name'].upper(), ha='right', va='center',
                fontsize=30, weight='bold', color=STYLE['home_color'], fontproperties=STYLE['font_prop'])
        ax.text(0.65, 0.65, teams['away']['name'].upper(), ha='left', va='center',
                fontsize=30, weight='bold', color=STYLE['away_color'], fontproperties=STYLE['font_prop'])

        home_sub = f"{teams['home'].get('manager', 'N/A')}\n({teams['home'].get('formation', 'N/A')})"
        away_sub = f"{teams['away'].get('manager', 'N/A')}\n({teams['away'].get('formation', 'N/A')})"

        ax.text(0.35, 0.35, home_sub, ha='right', va='center',
                fontsize=16, color=STYLE['sub_text'], weight='normal', fontproperties=STYLE['font_prop'])
        ax.text(0.65, 0.35, away_sub, ha='left', va='center',
                fontsize=16, color=STYLE['sub_text'], weight='normal', fontproperties=STYLE['font_prop'])

    def _draw_pass_map(self, ax, net_df, nodes_df, color, STYLE, flip=False):
        pitch = VerticalPitch(pitch_type='opta', pitch_color=STYLE['background'],
                              line_color=STYLE['line_color'], linewidth=1.5)
        pitch.draw(ax=ax)

        if not net_df.empty:
            net_df = net_df.copy()
        if not nodes_df.empty:
            nodes_df = nodes_df.copy()

        if flip:
             net_df['x_start'] = 100 - net_df['x_start']; net_df['y_start'] = 100 - net_df['y_start']
             net_df['x_end'] = 100 - net_df['x_end']; net_df['y_end'] = 100 - net_df['y_end']
             nodes_df['x'] = 100 - nodes_df['x']; nodes_df['y'] = 100 - nodes_df['y']

        if not net_df.empty:
            max_pass = net_df['pass_count'].max()
            if max_pass > 0:
                width = (net_df['pass_count'] / max_pass * 12)
                pitch.lines(net_df['x_start'], net_df['y_start'], net_df['x_end'], net_df['y_end'],
                            lw=width, ax=ax, color=color, alpha=0.5, zorder=2)

        if not nodes_df.empty:
            max_count = nodes_df['count'].max()
            if max_count > 0:
                for i, row in nodes_df.iterrows():
                    size = (row['count'] / max_count) * 1500

                    pitch.scatter(row['x'], row['y'], s=size, color=STYLE['background'],
                                  edgecolors=color, linewidth=2, zorder=3, ax=ax)

                    pitch.annotate(row['shirtNo'], xy=(row['x'], row['y']), va='center', ha='center',
                                   color='white', fontsize=12, weight='bold', zorder=4, ax=ax, fontproperties=STYLE['font_prop'])

    def _draw_direction_arrow(self, ax, STYLE):
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        ax.annotate('', xy=(0.7, 0.95), xytext=(0.7, 0.05),
                    arrowprops=dict(facecolor='white', edgecolor='white', width=1.5, headwidth=8, headlength=10),
                    xycoords='axes fraction', textcoords='axes fraction')

        ax.text(0.3, 0.5, "Sens du jeu", rotation=90, ha='center', va='center',
                color='white', fontsize=14, weight='bold', fontproperties=STYLE['font_prop'])

    def _draw_lineup(self, ax, nodes_df, color, team_name, STYLE):
        ax.axis('off')

        if nodes_df.empty: return

        nodes_df = nodes_df.copy()
        nodes_df['shirtNoInt'] = pd.to_numeric(nodes_df['shirtNo'], errors='coerce').fillna(999).astype(int)
        lineup = nodes_df.sort_values('shirtNoInt')

        y_start = 0.96
        y_step = 0.12

        half = (len(lineup) + 1) // 2
        col1 = lineup.iloc[:half]
        col2 = lineup.iloc[half:]

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
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        legend_y = 0.4

        ax.text(0.15, legend_y, "Peu de passes", ha='right', va='center',
                color='white', fontsize=12, weight='bold', fontproperties=STYLE['font_prop'])

        sizes = [80, 200, 400, 700]
        x_start = 0.17
        x_spacing = 0.03

        for i, s in enumerate(sizes):
            ax.scatter(x_start + (i * x_spacing), legend_y, s=s,
                       color=STYLE['background'], edgecolors=STYLE['legend_blue'], linewidth=1.5)

        ax.text(x_start + (len(sizes) * x_spacing) + 0.0005, legend_y, "Beaucoup de passes", ha='left', va='center',
                color='white', fontsize=12, weight='bold', fontproperties=STYLE['font_prop'])

        right_start = 0.55

        ax.text(right_start, legend_y, "Combine peu", ha='right', va='center',
                color='white', fontsize=12, weight='bold', fontproperties=STYLE['font_prop'])

        widths = [1, 3, 6]
        line_length = 0.04
        line_spacing = 0.01
        current_x = right_start + 0.02

        for w in widths:
            ax.plot([current_x, current_x + line_length], [legend_y, legend_y],
                    color='white', lw=w)
            current_x += line_length + line_spacing

        ax.text(current_x + 0.01, legend_y, "Combine beaucoup", ha='left', va='center',
                color='white', fontsize=12, weight='bold', fontproperties=STYLE['font_prop'])

# --- FONCTION PRINCIPALE ---

def main():
    # Header avec carousel de logos
    st.markdown('<h1>⚽ Premier League Analyst Pro <span class="premium-badge">2025/26</span></h1>', unsafe_allow_html=True)
    st.markdown("*Analyse tactique avancée propulsée par l'IA et les données Opta*")
    
    # Carousel de logos en haut
    display_club_logos()

    # SIDEBAR
    st.sidebar.image("https://resources.premierleague.com/premierleague/photo/2022/12/14/e1b33a1f-be1a-43d8-9a9e-cd2fa9cf011c/premier-league-logo-header.png", 
                     use_container_width=True)
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Navigation")
    
    mode = st.sidebar.radio(
        "Mode de Sélection",
        ["📅 Calendrier / Journées", "🌐 URL Personnalisée"],
        label_visibility="collapsed"
    )

    selected_match_data = None
    needs_download = False
    
    # Mode Calendrier
    if mode == "📅 Calendrier / Journées":
        matches = load_match_list()
        
        if not matches:
            st.error(f"📁 Fichier '{URLS_FILE}' introuvable")
        else:
            df_matches = pd.DataFrame(matches)
            gameweeks = sorted(df_matches['gameweek'].unique())
            
            sel_gw = st.sidebar.selectbox(
                "🏆 Journée",
                gameweeks,
                format_func=lambda x: f"Gameweek {x}"
            )
            
            gw_matches = df_matches[df_matches['gameweek'] == sel_gw]
            
            match_options = {
                f"{r['title']}": r.to_dict() 
                for _, r in gw_matches.iterrows()
            }
            
            sel_match_key = st.sidebar.selectbox("⚽ Match", list(match_options.keys()))
            selected_match_data = match_options[sel_match_key]
            
            file_path = os.path.join(DATA_FOLDER, selected_match_data['filename'])
            if os.path.exists(file_path):
                st.sidebar.success("✅ Données en cache")
                needs_download = False
            else:
                st.sidebar.warning("☁️ Téléchargement requis")
                needs_download = True

    # Mode URL
    elif mode == "🌐 URL Personnalisée":
        url_input = st.sidebar.text_input("🔗 URL WhoScored")
        if url_input:
            match_id = re.search(r'/matches/(\d+)/', url_input)
            if match_id:
                mid = match_id.group(1)
                selected_match_data = {
                    'id': mid,
                    'title': f"Match #{mid}",
                    'url': url_input,
                    'filename': f"{mid}.html"
                }
                file_path = os.path.join(DATA_FOLDER, selected_match_data['filename'])
                needs_download = not os.path.exists(file_path)
            else:
                st.sidebar.error("❌ URL invalide")

    # Logique principale
    if selected_match_data is not None:
        st.markdown(f"## {selected_match_data['title']}")
        
        if needs_download:
            st.info("💾 Les données ne sont pas en cache local")
            if st.button("🚀 Télécharger et Analyser", type="primary"):
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
                with st.spinner("🔍 Parsing des données..."):
                    parser = MatchParser(file_path)
                    mc, match_info, teams, logos = parser.get_all_data()
                
                with st.spinner("⚙️ Calcul des réseaux..."):
                    engine = PassNetworkEngine()
                    events, players = engine.process(mc)
                    
                    home_net, home_nodes = engine.get_network(teams['home']['id'], events, players)
                    away_net, away_nodes = engine.get_network(teams['away']['id'], events, players)
                
                # ONGLETS PRINCIPAUX
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "📊 Pass Network", 
                    "📈 Stats Avancées",
                    "🎯 Performance Joueurs",
                    "🔥 Heatmaps",
                    "🧠 Analyse Réseau"
                ])
                
                # TAB 1: Pass Network
                with tab1:
                    with st.spinner("🎨 Génération du dashboard..."):
                        viz = DashboardVisualizer()
                        fig = viz.create_dashboard(
                            match_info, teams, 
                            home_net, home_nodes, 
                            away_net, away_nodes, 
                            logos.get(0), logos.get(1)
                        )
                        st.pyplot(fig)
                        
                        buf = BytesIO()
                        fig.savefig(buf, format="png", facecolor='#0E1117', bbox_inches='tight', dpi=150)
                        st.download_button(
                            label="💾 Télécharger (HD)",
                            data=buf.getvalue(),
                            file_name=f"PassNetwork_{selected_match_data['id']}.png",
                            mime="image/png"
                        )
                        plt.close(fig)
                
                # TAB 2: Stats Avancées
                with tab2:
                    analytics = AdvancedAnalytics()
                    
                    home_stats = analytics.calculate_team_stats(events, teams['home']['id'], players)
                    away_stats = analytics.calculate_team_stats(events, teams['away']['id'], players)
                    
                    st.markdown("### 📊 Statistiques du Match")
                    
                    # Métriques principales
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "🏠 Passes Domicile",
                            home_stats['passes'],
                            f"{home_stats['pass_accuracy']}% précision"
                        )
                    
                    with col2:
                        st.metric(
                            "✈️ Passes Extérieur",
                            away_stats['passes'],
                            f"{away_stats['pass_accuracy']}% précision"
                        )
                    
                    with col3:
                        st.metric(
                            "🎯 Tirs Domicile",
                            home_stats['shots'],
                            f"{home_stats['shots_on_target']} cadrés"
                        )
                    
                    with col4:
                        st.metric(
                            "🎯 Tirs Extérieur",
                            away_stats['shots'],
                            f"{away_stats['shots_on_target']} cadrés"
                        )
                    
                    # Graphique de possession par tiers
                    st.markdown("### 🗺️ Contrôle Territorial")
                    
                    fig_territory = go.Figure()
                    
                    categories = ['Tiers Défensif', 'Tiers Milieu', 'Tiers Offensif']
                    
                    fig_territory.add_trace(go.Bar(
                        name=teams['home']['name'],
                        x=categories,
                        y=[home_stats['def_third_passes'], home_stats['mid_third_passes'], home_stats['att_third_passes']],
                        marker_color='#00BFFF'
                    ))
                    
                    fig_territory.add_trace(go.Bar(
                        name=teams['away']['name'],
                        x=categories,
                        y=[away_stats['def_third_passes'], away_stats['mid_third_passes'], away_stats['att_third_passes']],
                        marker_color='#FF4B4B'
                    ))
                    
                    fig_territory.update_layout(
                        barmode='group',
                        template='plotly_dark',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'),
                        height=400
                    )
                    
                    st.plotly_chart(fig_territory, use_container_width=True)
                    
                    # Duels
                    st.markdown("### 🥊 Batailles Individuelles")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"#### {teams['home']['name']}")
                        st.metric("Duels gagnés", f"{home_stats['duels_won']}/{home_stats['duels']}", 
                                 f"{home_stats['duel_success']}%")
                    
                    with col2:
                        st.markdown(f"#### {teams['away']['name']}")
                        st.metric("Duels gagnés", f"{away_stats['duels_won']}/{away_stats['duels']}", 
                                 f"{away_stats['duel_success']}%")
                
                # TAB 3: Performance Joueurs
                with tab3:
                    st.markdown("### 👥 Performance Individuelle")
                    
                    analytics = AdvancedAnalytics()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"#### 🏠 {teams['home']['name']}")
                        home_perf = analytics.get_player_performance(events, players, teams['home']['id'])
                        
                        # Filtrer les titulaires
                        starters = home_perf[home_perf['isStarter'] == True]
                        
                        st.dataframe(
                            starters[['number', 'name', 'position', 'touches', 'passes', 'pass_accuracy']]
                            .rename(columns={
                                'number': 'N°',
                                'name': 'Joueur',
                                'position': 'Poste',
                                'touches': 'Touches',
                                'passes': 'Passes',
                                'pass_accuracy': 'Précision %'
                            }),
                            hide_index=True,
                            use_container_width=True
                        )
                    
                    with col2:
                        st.markdown(f"#### ✈️ {teams['away']['name']}")
                        away_perf = analytics.get_player_performance(events, players, teams['away']['id'])
                        
                        starters = away_perf[away_perf['isStarter'] == True]
                        
                        st.dataframe(
                            starters[['number', 'name', 'position', 'touches', 'passes', 'pass_accuracy']]
                            .rename(columns={
                                'number': 'N°',
                                'name': 'Joueur',
                                'position': 'Poste',
                                'touches': 'Touches',
                                'passes': 'Passes',
                                'pass_accuracy': 'Précision %'
                            }),
                            hide_index=True,
                            use_container_width=True
                        )
                
                # TAB 4: Heatmaps
                with tab4:
                    st.markdown("### 🔥 Zones d'Activité")
                    
                    analytics = AdvancedAnalytics()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"#### {teams['home']['name']}")
                        heatmap_data = analytics.create_heatmap_data(events, teams['home']['id'])
                        
                        if not heatmap_data.empty:
                            # Créer une matrice 10x10
                            heatmap_matrix = np.zeros((10, 10))
                            for _, row in heatmap_data.iterrows():
                                if not pd.isna(row['x_bin']) and not pd.isna(row['y_bin']):
                                    x, y = int(row['x_bin']), int(row['y_bin'])
                                    heatmap_matrix[y, x] = row['count']
                            
                            fig_heat = px.imshow(
                                heatmap_matrix,
                                color_continuous_scale='Blues',
                                aspect='auto',
                                labels=dict(color="Activité")
                            )
                            fig_heat.update_layout(
                                template='plotly_dark',
                                paper_bgcolor='rgba(0,0,0,0)',
                                height=400
                            )
                            st.plotly_chart(fig_heat, use_container_width=True)
                    
                    with col2:
                        st.markdown(f"#### {teams['away']['name']}")
                        heatmap_data = analytics.create_heatmap_data(events, teams['away']['id'])
                        
                        if not heatmap_data.empty:
                            heatmap_matrix = np.zeros((10, 10))
                            for _, row in heatmap_data.iterrows():
                                if not pd.isna(row['x_bin']) and not pd.isna(row['y_bin']):
                                    x, y = int(row['x_bin']), int(row['y_bin'])
                                    heatmap_matrix[y, x] = row['count']
                            
                            fig_heat = px.imshow(
                                heatmap_matrix,
                                color_continuous_scale='Reds',
                                aspect='auto',
                                labels=dict(color="Activité")
                            )
                            fig_heat.update_layout(
                                template='plotly_dark',
                                paper_bgcolor='rgba(0,0,0,0)',
                                height=400
                            )
                            st.plotly_chart(fig_heat, use_container_width=True)
                
                # TAB 5: Analyse Réseau
                with tab5:
                    st.markdown("### 🧠 Analyse de Centralité")
                    st.markdown("*Joueurs clés dans la construction du jeu*")
                    
                    analytics = AdvancedAnalytics()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"#### {teams['home']['name']}")
                        centrality = analytics.analyze_passing_network_centrality(home_net, home_nodes)
                        
                        if not centrality.empty:
                            st.dataframe(
                                centrality[['number', 'name', 'connections', 'touches']]
                                .rename(columns={
                                    'number': 'N°',
                                    'name': 'Joueur',
                                    'connections': 'Connexions',
                                    'touches': 'Touches'
                                }),
                                hide_index=True,
                                use_container_width=True
                            )
                            
                            # Graphique
                            fig_cent = go.Figure(data=[
                                go.Bar(
                                    x=centrality['name'][:5],
                                    y=centrality['connections'][:5],
                                    marker_color='#00BFFF'
                                )
                            ])
                            fig_cent.update_layout(
                                title="Top 5 - Connexions",
                                template='plotly_dark',
                                paper_bgcolor='rgba(0,0,0,0)',
                                height=300,
                                showlegend=False
                            )
                            st.plotly_chart(fig_cent, use_container_width=True)
                    
                    with col2:
                        st.markdown(f"#### {teams['away']['name']}")
                        centrality = analytics.analyze_passing_network_centrality(away_net, away_nodes)
                        
                        if not centrality.empty:
                            st.dataframe(
                                centrality[['number', 'name', 'connections', 'touches']]
                                .rename(columns={
                                    'number': 'N°',
                                    'name': 'Joueur',
                                    'connections': 'Connexions',
                                    'touches': 'Touches'
                                }),
                                hide_index=True,
                                use_container_width=True
                            )
                            
                            fig_cent = go.Figure(data=[
                                go.Bar(
                                    x=centrality['name'][:5],
                                    y=centrality['connections'][:5],
                                    marker_color='#FF4B4B'
                                )
                            ])
                            fig_cent.update_layout(
                                title="Top 5 - Connexions",
                                template='plotly_dark',
                                paper_bgcolor='rgba(0,0,0,0)',
                                height=300,
                                showlegend=False
                            )
                            st.plotly_chart(fig_cent, use_container_width=True)

            except Exception as e:
                st.error(f"❌ Erreur d'analyse : {e}")
                
                with st.expander("🔧 Debug"):
                    st.text(f"Erreur: {str(e)}")
                    st.text(f"Type: {type(e).__name__}")
                
                if st.button("🗑️ Supprimer et retélécharger"):
                    try:
                        os.remove(file_path)
                        st.success("✅ Fichier supprimé")
                        time.sleep(1)
                        st.rerun()
                    except Exception as del_err:
                        st.error(f"Erreur : {del_err}")

    else:
        # Page d'accueil
        st.markdown("### 👋 Bienvenue sur Premier League Analyst Pro")
        st.markdown("*Sélectionnez un match dans la barre latérale pour commencer l'analyse*")
        
        if os.path.exists(DATA_FOLDER):
            cached_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.html')]
            if cached_files:
                st.success(f"📦 {len(cached_files)} match(s) en cache")

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; font-size: 0.85rem;'>"
        "Powered by WhoScored/Opta • Built with Streamlit & Python • © 2025"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
