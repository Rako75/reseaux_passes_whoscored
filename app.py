import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import to_rgba, LinearSegmentedColormap
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.font_manager as fm
from matplotlib.lines import Line2D
from mplsoccer import VerticalPitch, Pitch
from bs4 import BeautifulSoup
from PIL import Image
import os
import re
import json
import time
import requests
import shutil
import warnings
from io import BytesIO

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Premier League Mega Dashboard • 2025/26",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONSTANTES & PATHS ---
DATA_FOLDER = "premier_league_data_2025_2026"
URLS_FILE = "whoscored_urls_premierleague.txt"
CUSTOM_FONT_PATH = "Montserrat-Regular.ttf"

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# --- STYLE CSS (DARK MODE) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* FORCE DARK MODE */
    .stApp { background: #0E1117; font-family: 'Inter', sans-serif; color: #FFFFFF; }
    h1 { color: #FFFFFF !important; font-weight: 700 !important; font-size: 2.5rem !important; letter-spacing: -0.02em; }
    h2 { color: #FFFFFF !important; font-weight: 600 !important; margin-top: 2rem !important; }
    p, label, .stMarkdown { color: #A0A0A0 !important; }
    
    /* Boutons */
    .stButton>button {
        width: 100%; background: #1F2937; color: #FFFFFF; border: 1px solid #374151; border-radius: 6px;
        font-weight: 600; padding: 0.75rem 1.5rem; transition: all 0.2s ease;
    }
    .stButton>button:hover { background: #374151; border-color: #4B5563; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    .stButton>button:active { background: #111827; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #161B22; border-right: 1px solid #30363D; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #FFFFFF !important; }
    [data-testid="stSidebar"] label { color: #A0A0A0 !important; }
    
    /* Inputs Dark */
    .stTextInput>div>div, .stSelectbox>div>div {
        background-color: #0D1117 !important;
        color: #FFFFFF !important;
        border: 1px solid #30363D !important;
    }
    .stTextInput>div>div:focus-within, .stSelectbox>div>div:focus-within {
        border-color: #58A6FF !important;
    }

    /* Cards & Containers */
    .stat-card { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 1.5rem; transition: all 0.2s ease; }
    .stat-card:hover { border-color: #58A6FF; }
    
    /* Metrics */
    [data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; color: #FFFFFF; }
    [data-testid="stMetricLabel"] { color: #A0A0A0 !important; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }
    
    /* Spinners & Alerts */
    .stSpinner > div { border-top-color: #FFFFFF !important; }
    .stSuccess { border-left-color: #238636 !important; background: #0D1117 !important; color: #E6FFFA !important; border: 1px solid #238636; }
    .stError { border-left-color: #DA3633 !important; background: #0D1117 !important; color: #FFEBE9 !important; border: 1px solid #DA3633; }
    .stInfo { border-left-color: #58A6FF !important; background: #0D1117 !important; color: #DBEDFF !important; border: 1px solid #58A6FF; }
    .stWarning { border-left-color: #D29922 !important; background: #0D1117 !important; color: #FFF8C5 !important; border: 1px solid #D29922; }

    /* Premium Badge */
    .premium-badge { display: inline-block; background: #FFFFFF; color: #0E1117; padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; margin-left: 0.75rem; }
    </style>
""", unsafe_allow_html=True)

# --- GESTION POLICES & STYLE GRAPHIQUE ---
@st.cache_resource
def get_fonts():
    try:
        if os.path.exists(CUSTOM_FONT_PATH):
            prop = fm.FontProperties(fname=CUSTOM_FONT_PATH)
            bold = fm.FontProperties(fname=CUSTOM_FONT_PATH, weight='bold')
            return prop, bold
    except:
        pass
    return fm.FontProperties(family='sans-serif'), fm.FontProperties(family='sans-serif', weight='bold')

FONT_PROP, FONT_BOLD = get_fonts()

STYLE = {
    'background': '#0E1117',
    'text_color': '#FFFFFF',
    'sub_text': '#A0A0A0',
    'home_color': '#00BFFF',
    'away_color': '#FF4B4B',
    'line_color': '#2B313E',
    'legend_blue': '#5DADEC',
    'font_prop': FONT_PROP,
    'font_bold': FONT_BOLD
}

# --- CLASSES UTILITAIRES (DOWNLOADER & PARSER) ---

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
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        driver = None
        
        # 1. Tentative avec Selenium Manager natif (Recommandé pour Chrome récents > 114)
        try:
            driver = webdriver.Chrome(options=options)
        except Exception as e_native:
            # 2. Fallback avec webdriver_manager si le natif échoue
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except Exception as e_manager:
                st.error(f"❌ Erreur Driver : Impossible d'initialiser Chrome.\nNative Error: {e_native}\nManager Error: {e_manager}")
                return False

        if not driver:
             return False

        try:
            with st.spinner(f"🌍 Connexion à WhoScored : {url}"):
                driver.get(url)
                time.sleep(5)
                content = driver.page_source
                
                # Check Incapsula
                if "Incapsula" in content or "challenge" in content.lower():
                    st.warning("🛡️ Protection détectée, tentative d'attente...")
                    time.sleep(15)
                    content = driver.page_source
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            
            return True
        except Exception as e:
            st.error(f"❌ Erreur Selenium pendant le téléchargement : {str(e)}")
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
        self.mc = self.data['matchCentreData']
        self.events = pd.DataFrame(self.mc['events'])
        
        # Nettoyage
        for col in ['x', 'y', 'endX', 'endY']:
            if col not in self.events.columns: self.events[col] = 0.0
            
        def safe_get_name(x): return x.get('displayName') if isinstance(x, dict) else None
        def safe_get_id(x):
            try: return int(x.get('value')) if isinstance(x, dict) else -1
            except: return -1

        self.events['type_name'] = self.events['type'].apply(safe_get_name)
        self.events['type_id'] = self.events['type'].apply(safe_get_id)
        self.events['outcome_name'] = self.events['outcomeType'].apply(safe_get_name)
        self.events['outcome_id'] = self.events['outcomeType'].apply(safe_get_id)
        self.events['teamId'] = pd.to_numeric(self.events['teamId'], errors='coerce').fillna(0).astype(int)

    def _load_data(self):
        with open(self.html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.soup = BeautifulSoup(content, 'html.parser')
        
        # STRATÉGIE MULTI-REGEX (ordre de priorité)
        patterns = [
            r"require\.config\.params\[\"args\"\]\s*=\s*(\{.*?\});",
            r"var\s+matchCentreData\s*=\s*(\{.*?\});",
            r"matchCentreData:\s*(\{.*?\}),?\s*matchCentreEventTypeJson",
            r"\"matchCentreData\":\s*(\{.*?\}),?\s*\"matchCentreEventTypeJson\""
        ]
        
        json_str = None
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, content, re.DOTALL)
            if match:
                json_str = match.group(1)
                if i >= 2:
                    json_str = '{"matchCentreData": ' + json_str + '}'
                break
        
        if not json_str:
            fallback = re.search(r'(\{[^{}]*"events"\s*:\s*\[[^]]*\][^{}]*"home"\s*:\s*\{.*?\})', content, re.DOTALL)
            if fallback:
                json_str = '{"matchCentreData": ' + fallback.group(1) + '}'
            else:
                debug_path = self.html_path.replace('.html', '_DEBUG.html')
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(content[:50000])
                raise ValueError(f"❌ JSON data not found. Saved debug file: {debug_path}")

        # --- NETTOYAGE ROBUSTE ET SÉLECTIF ---
        # Au lieu de tout remplacer (ce qui casse les URLs http:), on cible les clés spécifiques de WhoScored.
        
        keys_to_quote = [
            'matchId', 'matchCentreData', 'matchCentreEventTypeJson', 'formationIdNameMappings', 
            'home', 'away', 'score', 'htScore', 'ftScore', 'etScore', 'pkScore', 'events', 
            'playerIdNameDictionary', 'teamId', 'name', 'managerName', 'players', 'playerId', 
            'shirtNo', 'position', 'isFirstEleven', 'age', 'height', 'weight', 'isManOfTheMatch', 
            'stats', 'ratings', 'type', 'displayName', 'outcomeType', 'qualifiers', 
            'satisfiedEventsTypes', 'x', 'y', 'endX', 'endY', 'id', 'eventId', 'minute', 
            'second', 'teamFormation', 'formations', 'startTime', 'venueName', 'attendance', 
            'weatherCode', 'elapsed', 'statusCode', 'periodCode', 'expandedMinute', 'period', 
            'type', 'outcomeType', 'cardType', 'isTouch', 'blockingPlayerId', 'isGoal', 
            'relatedEventId', 'relatedPlayerId', 'goalMouthZ', 'goalMouthY', 'isShot',
            'field', 'countryName', 'shortName', 'teamName', 'regionName', 'subbedOutPlayerId',
            'subbedInPlayerId', 'officialName', 'firstName', 'lastName', 'incidents'
        ]

        # 1. Remplacement des clés spécifiques uniquement
        for key in keys_to_quote:
            # \b = limite de mot, \s* = espaces optionnels
            json_str = re.sub(rf'\b{key}\s*:', f'"{key}":', json_str)

        # 2. Nettoyage générique prudent
        json_str = re.sub(r'\bundefined\b', 'null', json_str)
        # On remplace les quotes simples par des doubles pour être compatible JSON
        # Cela suppose que les valeurs string sont entourées de ' ' dans le JS source
        json_str = json_str.replace("'", '"')
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # Tentative de rattrapage : suppression des virgules finales invalides en JSON
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            try:
                return json.loads(json_str)
            except:
                # Affichage d'un extrait de l'erreur pour aider au debug
                raise ValueError(f"❌ JSON parsing failed: {str(e)[:100]}")

    def get_match_info(self):
        home_fmt, away_fmt = 'N/A', 'N/A'
        if self.soup:
            divs = self.soup.find_all('div', class_='formation')
            if len(divs) >= 2:
                home_fmt = divs[0].get_text(strip=True)
                away_fmt = divs[1].get_text(strip=True)
        
        try: h_id = int(self.mc['home']['teamId'])
        except: h_id = 0
        try: a_id = int(self.mc['away']['teamId'])
        except: a_id = 0
            
        return {
            'score': self.mc['score'],
            'venue': self.mc.get('venueName', 'Stade Inconnu'),
            'date': self.mc.get('startTime', '')[:10],
            'home': {'name': self.mc['home']['name'], 'manager': self.mc['home'].get('managerName',''), 'formation': home_fmt, 'id': h_id},
            'away': {'name': self.mc['away']['name'], 'manager': self.mc['away'].get('managerName',''), 'formation': away_fmt, 'id': a_id}
        }

    def get_players(self):
        players = []
        for side in ['home', 'away']:
            try: tid = int(self.mc[side]['teamId'])
            except: tid = 0
            for p in self.mc[side]['players']:
                p['teamId'] = tid
                players.append(p)
        return pd.DataFrame(players)

    def get_logos(self):
        logos = {}
        if self.soup:
            emblems = self.soup.find_all('div', class_='team-emblem')
            for i, e in enumerate(emblems[:2]):
                img = e.find('img')
                if img and img.get('src'):
                    url = img['src']
                    if url.startswith('//'): url = 'https:' + url
                    logos[i] = url
        return logos

    def get_formation_from_html(self):
        grids = {}
        if not self.soup: return grids
        fields = self.soup.find_all('div', class_='pitch-field')
        for field in fields:
            tid = field.get('data-team-id')
            side = field.get('data-field')
            if not tid: continue
            try: tid = int(tid)
            except: continue
            
            players_pos = []
            player_divs = field.find_all('div', class_='player')
            for p in player_divs:
                pid = p.get('data-player-id')
                if not pid: continue
                style = p.get('style', '')
                x_opta, y_opta = 50.0, 50.0
                
                if side == 'home':
                    l_match = re.search(r'left\s*:\s*([\d\.]+)%', style)
                    b_match = re.search(r'bottom\s*:\s*([\d\.]+)%', style)
                    if l_match: x_opta = float(l_match.group(1))
                    if b_match: y_opta = float(b_match.group(1))
                elif side == 'away':
                    r_match = re.search(r'right\s*:\s*([\d\.]+)%', style)
                    t_match = re.search(r'top\s*:\s*([\d\.]+)%', style)
                    if r_match: x_opta = 100.0 - float(r_match.group(1))
                    if t_match: y_opta = float(t_match.group(1))
                
                players_pos.append({'playerId': int(pid), 'x': x_opta, 'y': y_opta})
            
            if players_pos: grids[tid] = pd.DataFrame(players_pos)
        return grids

# --- ANALYTICS ENGINE (LE CERVEAU) ---

class AnalyticsEngine:
    def __init__(self, events_df, players_df, home_id, away_id, formation_grids=None):
        self.events = events_df
        self.players = players_df
        self.home_id = int(home_id)
        self.away_id = int(away_id)
        self.formation_grids = formation_grids if formation_grids else {}

        # CALCUL DU xG (Simplifié)
        shot_ids = [10, 13, 14, 15, 16] # Blocked, Miss, Post, Saved, Goal
        if 'xg' not in self.events.columns:
            self.events['dist_goal'] = np.sqrt((100 - self.events['x'])**2 + (50 - self.events['y'])**2)
            self.events['xg'] = np.where(self.events['type_id'].isin(shot_ids),
                                         15 / (self.events['dist_goal'] + 5), 0)
            self.events.loc[self.events['xg'] > 0.99, 'xg'] = 0.99

    def get_pass_network(self, team_id):
        starters = self.players[(self.players['teamId'] == team_id) & (self.players['isFirstEleven'] == True)]
        if starters.empty: starters = self.players[self.players['teamId'] == team_id].head(11)
        starter_ids = starters['playerId'].unique()

        passes = self.events[
            (self.events['teamId'] == team_id) &
            (self.events['type_name'] == 'Pass') &
            (self.events['outcome_name'] == 'Successful') &
            (self.events['playerId'].isin(starter_ids))
        ].copy()

        passes['receiverId'] = self.events['playerId'].shift(-1)
        # Drop passes with no receiver or receiver not in starters
        passes = passes[passes['receiverId'].isin(starter_ids)]

        avg_locs = passes.groupby('playerId').agg({'x': 'mean', 'y': 'mean', 'id': 'count'}).rename(columns={'id': 'count'}).reset_index()
        avg_locs = avg_locs.merge(starters[['playerId', 'name', 'shirtNo', 'position']], on='playerId', how='inner')

        passes['pair'] = passes.apply(lambda x: tuple(sorted([x['playerId'], x['receiverId']])), axis=1)
        pass_counts = passes.groupby('pair').size().reset_index(name='pass_count')
        pass_counts = pass_counts[pass_counts['pass_count'] >= 3]

        network = []
        for _, row in pass_counts.iterrows():
            p1, p2 = row['pair']
            if p1 in avg_locs['playerId'].values and p2 in avg_locs['playerId'].values:
                l1 = avg_locs[avg_locs['playerId']==p1].iloc[0]
                l2 = avg_locs[avg_locs['playerId']==p2].iloc[0]
                network.append({'x_start': l1['x'], 'y_start': l1['y'], 'x_end': l2['x'], 'y_end': l2['y'], 'pass_count': row['pass_count']})

        player_list = avg_locs.sort_values('shirtNo', key=lambda x: pd.to_numeric(x, errors='coerce'))
        return pd.DataFrame(network), avg_locs, player_list

    def get_formation_positions(self, team_id):
        starters = self.players[(self.players['teamId'] == team_id) & (self.players['isFirstEleven'] == True)]
        if starters.empty: starters = self.players[self.players['teamId'] == team_id].head(11)
        
        # Priorité : Grille extraite du HTML (CSS positions)
        if team_id in self.formation_grids:
            grid = self.formation_grids[team_id]
            if 'playerId' in grid.columns:
                formation = starters.merge(grid, on='playerId', how='inner')
                if not formation.empty: return formation

        # Fallback : Moyenne des positions
        starter_ids = starters['playerId'].unique()
        team_events = self.events[(self.events['teamId'] == team_id) & (self.events['playerId'].isin(starter_ids))]
        avg_locs = team_events.groupby('playerId').agg({'x': 'mean', 'y': 'mean'}).reset_index()
        return starters.merge(avg_locs, on='playerId', how='left').dropna(subset=['x', 'y'])

    def get_xg_flow(self):
        shot_ids = [10, 13, 14, 15, 16]
        shots = self.events[self.events['type_id'].isin(shot_ids)].copy()
        
        if 'name' not in shots.columns and not self.players.empty:
             if 'playerId' in shots.columns:
                 shots = shots.merge(self.players[['playerId', 'name']], on='playerId', how='left')

        shots['minute'] = shots['minute'].astype(int)
        max_min = max(95, shots['minute'].max() + 1)
        minutes = range(0, max_min)
        home_xg, away_xg = [0.0], [0.0]
        h_cum, a_cum = 0.0, 0.0
        
        for m in minutes:
            h_min = shots[(shots['teamId'] == self.home_id) & (shots['minute'] == m)]['xg'].sum()
            a_min = shots[(shots['teamId'] == self.away_id) & (shots['minute'] == m)]['xg'].sum()
            h_cum += h_min; a_cum += a_min
            home_xg.append(h_cum); away_xg.append(a_cum)
            
        return minutes, home_xg[:-1], away_xg[:-1], shots

    def get_actions(self, team_id):
        mask = (self.events['teamId'] == team_id) & \
               (self.events['outcome_name'] == 'Successful') & \
               (~self.events['type_name'].isin(['SubstitutionOn', 'SubstitutionOff', 'Card', 'Start', 'End']))
        return self.events[mask][['x', 'y']]

    def get_all_shots(self):
         shot_ids = [10, 13, 14, 15, 16]
         shots = self.events[self.events['type_id'].isin(shot_ids)].copy()
         shots['size'] = 50 + (shots['xg'] * 500)
         return shots

    def get_possession(self):
        h_pass = len(self.events[(self.events['teamId'] == self.home_id) & (self.events['type_name'] == 'Pass')])
        a_pass = len(self.events[(self.events['teamId'] == self.away_id) & (self.events['type_name'] == 'Pass')])
        total = h_pass + a_pass
        if total == 0: return 50, 50
        return round(h_pass/total*100), round(a_pass/total*100)

    def get_comprehensive_stats(self):
        stats = []
        def count_id(tid, type_ids, outcome_val=None):
            mask = (self.events['teamId'] == tid) & (self.events['type_id'].isin(type_ids))
            if outcome_val is not None: mask &= (self.events['outcome_id'] == outcome_val)
            return len(self.events[mask])
        
        def count_name(tid, type_names, outcome=None):
            mask = (self.events['teamId'] == tid) & (self.events['type_name'].isin(type_names))
            if outcome: mask &= (self.events['outcome_name'] == outcome)
            return len(self.events[mask])

        # 1. Buts
        stats.append({'label': 'Buts', 'home': count_id(self.home_id, [16]), 'away': count_id(self.away_id, [16]), 'type': 'int'})
        # 2. xG
        h_xg = self.events[self.events['teamId'] == self.home_id]['xg'].sum()
        a_xg = self.events[self.events['teamId'] == self.away_id]['xg'].sum()
        stats.append({'label': 'Expected Goals (xG)', 'home': h_xg, 'away': a_xg, 'type': 'float'})
        # 3. Tirs
        total_shots = [10, 13, 14, 15, 16]; target = [15, 16]
        stats.append({'label': 'Tirs Totaux', 'home': count_id(self.home_id, total_shots), 'away': count_id(self.away_id, total_shots), 'type': 'int'})
        stats.append({'label': 'Tirs Cadrés', 'home': count_id(self.home_id, target), 'away': count_id(self.away_id, target), 'type': 'int'})
        # 4. Possession
        h_poss, a_poss = self.get_possession()
        stats.append({'label': 'Possession (%)', 'home': h_poss, 'away': a_poss, 'type': 'percent'})
        # 5. Passes
        h_pass, a_pass = count_name(self.home_id, ['Pass']), count_name(self.away_id, ['Pass'])
        stats.append({'label': 'Passes', 'home': h_pass, 'away': a_pass, 'type': 'int'})
        h_acc = (count_name(self.home_id, ['Pass'], 'Successful') / h_pass * 100) if h_pass > 0 else 0
        a_acc = (count_name(self.away_id, ['Pass'], 'Successful') / a_pass * 100) if a_pass > 0 else 0
        stats.append({'label': 'Précision Passes (%)', 'home': h_acc, 'away': a_acc, 'type': 'percent'})
        # Autres
        stats.append({'label': 'Dribbles Réussis', 'home': count_name(self.home_id, ['TakeOn'], 'Successful'), 'away': count_name(self.away_id, ['TakeOn'], 'Successful'), 'type': 'int'})
        stats.append({'label': 'Duels Aériens', 'home': count_name(self.home_id, ['Aerial'], 'Successful'), 'away': count_name(self.away_id, ['Aerial'], 'Successful'), 'type': 'int'})
        stats.append({'label': 'Tacles', 'home': count_name(self.home_id, ['Tackle']), 'away': count_name(self.away_id, ['Tackle']), 'type': 'int'})
        stats.append({'label': 'Interceptions', 'home': count_name(self.home_id, ['Interception']), 'away': count_name(self.away_id, ['Interception']), 'type': 'int'})
        stats.append({'label': 'Dégagements', 'home': count_name(self.home_id, ['Clearance']), 'away': count_name(self.away_id, ['Clearance']), 'type': 'int'})
        stats.append({'label': 'Ballons Récupérés', 'home': count_name(self.home_id, ['BallRecovery']), 'away': count_name(self.away_id, ['BallRecovery']), 'type': 'int'})
        stats.append({'label': 'Cartons Jaunes', 'home': count_name(self.home_id, ['Card'], 'Successful'), 'away': count_name(self.away_id, ['Card'], 'Successful'), 'type': 'int'})

        return pd.DataFrame(stats)

# --- MEGA VISUALIZER (MATPLOTLIB) ---

class MegaDashboard:
    def draw(self, match_info, analytics, home_logo_img, away_logo_img):
        fig = plt.figure(figsize=(24, 25), facecolor=STYLE['background'])
        gs = gridspec.GridSpec(2, 3, width_ratios=[1, 1.2, 1], height_ratios=[0.08, 0.92])
        gs.update(wspace=0.15, hspace=0.02)

        # Calculs des données
        nodes_h = analytics.get_formation_positions(match_info['home']['id'])
        nodes_a = analytics.get_formation_positions(match_info['away']['id'])
        net_h_main, nodes_h_main, list_h = analytics.get_pass_network(match_info['home']['id'])
        net_a_main, nodes_a_main, list_a = analytics.get_pass_network(match_info['away']['id'])
        stats_df = analytics.get_comprehensive_stats()
        mins, h_xg, a_xg, shots_data = analytics.get_xg_flow()

        # === 1. HEADER ===
        ax_header = fig.add_subplot(gs[0, :])
        self._draw_header(ax_header, match_info, home_logo_img, away_logo_img)

        # === 2. COLONNE GAUCHE (HOME) ===
        gs_left = gridspec.GridSpecFromSubplotSpec(3, 1, subplot_spec=gs[1, 0], height_ratios=[0.35, 0.35, 0.30])
        self._draw_pass_network(fig.add_subplot(gs_left[0]), net_h_main, nodes_h_main, STYLE['home_color'])
        self._draw_heatmap(fig.add_subplot(gs_left[1]), analytics.get_actions(match_info['home']['id']), STYLE['home_color'], "Zones d'activité")
        self._draw_player_list(fig.add_subplot(gs_left[2]), list_h)

        # === 3. COLONNE DROITE (AWAY) ===
        gs_right = gridspec.GridSpecFromSubplotSpec(3, 1, subplot_spec=gs[1, 2], height_ratios=[0.35, 0.35, 0.30])
        self._draw_pass_network(fig.add_subplot(gs_right[0]), net_a_main, nodes_a_main, STYLE['away_color'], flip=True)
        self._draw_heatmap(fig.add_subplot(gs_right[1]), analytics.get_actions(match_info['away']['id']), STYLE['away_color'], "Zones d'activité")
        self._draw_player_list(fig.add_subplot(gs_right[2]), list_a)

        # === 4. COLONNE CENTRALE (STATS & CHARTS) ===
        gs_center = gridspec.GridSpecFromSubplotSpec(3, 1, subplot_spec=gs[1, 1], height_ratios=[0.60, 0.25, 0.15])
        self._draw_duel_stats_large(fig.add_subplot(gs_center[0]), stats_df)
        self._draw_shotmap(fig.add_subplot(gs_center[1]), analytics.get_all_shots(), match_info['home']['id'], match_info['away']['id'])
        self._draw_xg_flow(fig.add_subplot(gs_center[2]), mins, h_xg, a_xg, shots_data, match_info)

        return fig

    def _draw_header(self, ax, info, h_logo, a_logo):
        ax.axis('off')
        ax.text(0.35, 0.70, info['home']['name'], ha='right', va='center', fontsize=24, color=STYLE['home_color'], fontproperties=STYLE['font_bold'])
        ax.text(0.35, 0.50, f"{info['home']['manager']}", ha='right', va='center', fontsize=16, color=STYLE['sub_text'], fontproperties=STYLE['font_prop'])
        ax.text(0.35, 0.30, f"({info['home']['formation']})", ha='right', va='center', fontsize=12, color=STYLE['sub_text'], fontproperties=STYLE['font_prop'])

        if h_logo:
            ab = AnnotationBbox(OffsetImage(h_logo, zoom=1.2), (0.05, 0.60), frameon=False, xycoords='axes fraction', box_alignment=(0.5,0.5))
            ax.add_artist(ab)

        ax.text(0.65, 0.70, info['away']['name'], ha='left', va='center', fontsize=24, color=STYLE['away_color'], fontproperties=STYLE['font_bold'])
        ax.text(0.65, 0.50, f"{info['away']['manager']}", ha='left', va='center', fontsize=16, color=STYLE['sub_text'], fontproperties=STYLE['font_prop'])
        ax.text(0.65, 0.30, f"({info['away']['formation']})", ha='left', va='center', fontsize=12, color=STYLE['sub_text'], fontproperties=STYLE['font_prop'])

        if a_logo:
            ab = AnnotationBbox(OffsetImage(a_logo, zoom=1.2), (0.95, 0.60), frameon=False, xycoords='axes fraction', box_alignment=(0.5,0.5))
            ax.add_artist(ab)

        score = str(info['score']).replace(' : ', ' - ')
        ax.text(0.5, 0.60, score, ha='center', va='center', fontsize=36, color=STYLE['text_color'], fontproperties=STYLE['font_bold'])
        ax.text(0.5, 0.85, f"{info['date']} | {info['venue']}", ha='center', fontsize=12, color=STYLE['sub_text'], fontproperties=STYLE['font_prop'])

    def _draw_duel_stats_large(self, ax, df):
        ax.set_facecolor(STYLE['background'])
        ax.axis('off')
        df = df.iloc[::-1].reset_index(drop=True)
        ax.set_ylim(-1, len(df))
        ax.set_xlim(-1.1, 1.1)
        
        for i, row in df.iterrows():
            val_h, val_a = row['home'], row['away']
            m_val = max(val_h, val_a) if max(val_h, val_a) > 0 else 1
            w_h, w_a = (val_h/m_val)*0.6, (val_a/m_val)*0.6
            gap = 0.45
            
            ax.barh(i, -w_h, left=-gap, height=0.65, color=STYLE['home_color'], alpha=1.0 if val_h>=val_a else 0.5)
            ax.barh(i, w_a, left=gap, height=0.65, color=STYLE['away_color'], alpha=1.0 if val_a>=val_h else 0.5)
            
            ax.text(0, i, row['label'], ha='center', va='center', fontsize=14, color=STYLE['text_color'], fontproperties=STYLE['font_bold'])
            
            str_h = f"{val_h:.2f}" if row['type']=='float' else (f"{val_h:.1f}%" if row['type']=='percent' else str(int(val_h)))
            str_a = f"{val_a:.2f}" if row['type']=='float' else (f"{val_a:.1f}%" if row['type']=='percent' else str(int(val_a)))
            
            ax.text(-gap - w_h - 0.05, i, str_h, ha='right', va='center', fontsize=16, color=STYLE['home_color'], fontproperties=STYLE['font_bold'])
            ax.text(gap + w_a + 0.05, i, str_a, ha='left', va='center', fontsize=16, color=STYLE['away_color'], fontproperties=STYLE['font_bold'])

    def _draw_pass_network(self, ax, net, nodes, color, flip=False):
        pitch = VerticalPitch(pitch_type='opta', pitch_color=STYLE['background'], line_color=STYLE['line_color'])
        pitch.draw(ax=ax)
        if not net.empty:
            width = net['pass_count'] / net['pass_count'].max() * 8
            pitch.lines(net['x_start'], net['y_start'], net['x_end'], net['y_end'], lw=width, ax=ax, color=color, alpha=0.6, zorder=2)
        if not nodes.empty:
            pitch.scatter(nodes['x'], nodes['y'], s=nodes['count']*15, color=STYLE['background'], edgecolors=color, linewidth=2, zorder=3, ax=ax)
            for _, row in nodes.iterrows():
                pitch.annotate(row['shirtNo'], (row['x'], row['y']), ax=ax, color='white', ha='center', va='center', fontsize=9, weight='bold', zorder=4)

    def _draw_heatmap(self, ax, actions, color, title):
        pitch = VerticalPitch(pitch_type='opta', pitch_color=STYLE['background'], line_color=STYLE['line_color'])
        pitch.draw(ax=ax)
        rgb = to_rgba(color)[:3]
        cmap = LinearSegmentedColormap.from_list("custom", [(rgb[0], rgb[1], rgb[2], 0), (rgb[0], rgb[1], rgb[2], 1)])
        if not actions.empty:
            pitch.kdeplot(actions['x'], actions['y'], ax=ax, cmap=cmap, fill=True, levels=50, thresh=0.05)
        ax.set_title(title, fontsize=12, color=STYLE['sub_text'], fontproperties=STYLE['font_prop'])

    def _draw_player_list(self, ax, player_df):
        ax.axis('off')
        if player_df.empty: return
        y_pos = 1.1
        for _, row in player_df.head(15).iterrows():
            ax.text(0.30, y_pos, str(row['shirtNo']), fontsize=12, ha='right', va='top', color=STYLE['sub_text'], fontproperties=STYLE['font_bold'])
            ax.text(0.45, y_pos, str(row['name']), fontsize=12, ha='left', va='top', color=STYLE['text_color'], fontproperties=STYLE['font_prop'])
            y_pos -= 0.065

    def _draw_shotmap(self, ax, shots, home_id, away_id):
        pitch = Pitch(pitch_type='opta', pitch_color=STYLE['background'], line_color=STYLE['line_color'])
        pitch.draw(ax=ax)
        h_shots = shots[shots['teamId'] == home_id]
        if not h_shots.empty:
            pitch.scatter(h_shots['x'], h_shots['y'], s=h_shots['size'], edgecolors=STYLE['home_color'], c='none', ax=ax, alpha=0.7)
            goals = h_shots[h_shots['type_name']=='Goal']
            pitch.scatter(goals['x'], goals['y'], s=goals['size'], c=STYLE['home_color'], marker='*', ax=ax, zorder=5)
        a_shots = shots[shots['teamId'] == away_id]
        if not a_shots.empty:
            pitch.scatter(100-a_shots['x'], 100-a_shots['y'], s=a_shots['size'], edgecolors=STYLE['away_color'], c='none', ax=ax, alpha=0.7)
            goals = a_shots[a_shots['type_name']=='Goal']
            pitch.scatter(100-goals['x'], 100-goals['y'], s=goals['size'], c=STYLE['away_color'], marker='*', ax=ax, zorder=5)
        ax.set_title("Shotmap", fontsize=14, color=STYLE['sub_text'], fontproperties=STYLE['font_prop'])

    def _draw_xg_flow(self, ax, mins, h_xg, a_xg, shots, info):
        ax.set_facecolor(STYLE['background'])
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(STYLE['sub_text']); ax.spines['bottom'].set_color(STYLE['sub_text'])
        ax.tick_params(axis='both', colors='white')
        ax.step(mins, h_xg, where='post', color=STYLE['home_color'], linewidth=2, label='Home')
        ax.step(mins, a_xg, where='post', color=STYLE['away_color'], linewidth=2, label='Away')
        ax.set_title("xG Flow", fontsize=14, color=STYLE['sub_text'], fontproperties=STYLE['font_prop'])
        ax.grid(axis='y', linestyle='--', alpha=0.3)

# --- APPLICATION PRINCIPALE ---

def load_match_list():
    matches = []
    if not os.path.exists(URLS_FILE): return []
    with open(URLS_FILE, 'r', encoding='utf-8') as f: lines = f.readlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        header = re.search(r'^Match (\d+) - (.+)', line)
        if header:
            mid, title = header.group(1), header.group(2)
            url = None
            for j in range(1, 4):
                if i+j < len(lines):
                    next_l = lines[i+j].strip()
                    if next_l.startswith("https://") and mid in next_l:
                        url = next_l; break
            if url:
                matches.append({'id': mid, 'title': title, 'url': url, 'filename': f"{mid}.html"})
        i += 1
    return matches

@st.cache_data
def get_club_logo(url):
    try:
        if not url: return None
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=3)
        return Image.open(BytesIO(r.content)) if r.status_code == 200 else None
    except: return None

def main():
    st.markdown('<h1>⚽ Premier League Analyst <span class="premium-badge">MEGA</span></h1>', unsafe_allow_html=True)
    st.markdown("*Tableau de bord complet : xG, Stats Duel, Pass Networks, Heatmaps, Shotmaps*")

    # SIDEBAR
    st.sidebar.markdown("### 🛠️ Panneau de contrôle")
    mode = st.sidebar.radio("Mode", ["📅 Calendrier", "🌐 URL Personnalisée"], label_visibility="collapsed")
    
    selected_match = None
    needs_dl = False
    
    if mode == "📅 Calendrier":
        matches = load_match_list()
        if not matches:
            st.sidebar.error(f"Fichier '{URLS_FILE}' introuvable.")
        else:
            options = {m['title']: m for m in matches}
            sel = st.sidebar.selectbox("Choisir un match", list(options.keys()))
            selected_match = options[sel]
            path = os.path.join(DATA_FOLDER, selected_match['filename'])
            if os.path.exists(path):
                st.sidebar.success("✅ Données disponibles")
            else:
                st.sidebar.warning("☁️ À télécharger")
                needs_dl = True
                
    elif mode == "🌐 URL Personnalisée":
        url = st.sidebar.text_input("Coller URL WhoScored")
        if url:
            mid = re.search(r'/matches/(\d+)/', url)
            if mid:
                selected_match = {'id': mid.group(1), 'title': f"Match {mid.group(1)}", 'url': url, 'filename': f"{mid.group(1)}.html"}
                path = os.path.join(DATA_FOLDER, selected_match['filename'])
                needs_dl = not os.path.exists(path)
            else:
                st.sidebar.error("URL invalide")

    if selected_match:
        st.markdown(f"## {selected_match['title']}")
        
        if needs_dl:
            if st.button("🚀 Télécharger et Analyser", type="primary"):
                dl = StreamlitDownloader()
                if dl.download_match(selected_match['url'], selected_match['filename']):
                    st.success("Téléchargement réussi !")
                    st.rerun()
        else:
            path = os.path.join(DATA_FOLDER, selected_match['filename'])
            try:
                with st.spinner("🔍 Analyse tactique en cours..."):
                    parser = MatchParser(path)
                    info = parser.get_match_info()
                    form_grids = parser.get_formation_from_html()
                    engine = AnalyticsEngine(parser.events, parser.get_players(), info['home']['id'], info['away']['id'], form_grids)
                    
                    # Récupération Logos
                    logos = parser.get_logos()
                    h_img = get_club_logo(logos.get(0))
                    a_img = get_club_logo(logos.get(1))
                    
                    # Génération Dashboard
                    viz = MegaDashboard()
                    fig = viz.draw(info, engine, h_img, a_img)
                    
                    st.pyplot(fig, use_container_width=True)
                    
                    # Download
                    buf = BytesIO()
                    fig.savefig(buf, format="png", facecolor=STYLE['background'], bbox_inches='tight', dpi=300)
                    st.download_button("💾 Télécharger le Mega Dashboard (HD)", data=buf.getvalue(), file_name=f"MegaStats_{selected_match['id']}.png", mime="image/png")
                    
                    plt.close(fig)
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")
                # st.exception(e) # Décommenter pour debug

if __name__ == "__main__":
    main()
