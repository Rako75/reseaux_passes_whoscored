import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.font_manager as fm
from mplsoccer import VerticalPitch
from bs4 import BeautifulSoup
from PIL import Image
import os
import re
import json
import time
import requests
from io import BytesIO

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Premier League Analyst 25/26",
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

# --- STYLE CSS PERSONNALISÉ ---
st.markdown("""
    <style>
    .main {
        background-color: #0E1117;
    }
    h1, h2, h3 {
        color: #FFFFFF;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        height: 3em;
    }
    /* Style des métriques */
    div[data-testid="metric-container"] {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #333;
    }
    /* Messages */
    .stAlert {
        background-color: #1E1E1E;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS UTILITAIRES (Loaders, Parsers) ---

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
        # Regex pour "Match 123456 - Equipe A vs Equipe B"
        header_match = re.search(r'^Match (\d+) - (.+)', line)
        
        if header_match:
            mid = header_match.group(1)
            title = header_match.group(2)
            url = None
            
            # Chercher l'URL dans les 3 lignes suivantes
            for j in range(1, 4):
                if i + j < len(lines):
                    next_line = lines[i+j].strip()
                    if next_line.startswith("https://") and mid in next_line:
                        url = next_line
                        break
            
            if url:
                # Estimation de la journée (Gameweek) basée sur l'index grossier
                # On suppose 10 matchs par journée
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

# --- CLASSES DE LOGIQUE MÉTIER ---

class StreamlitDownloader:
    """Téléchargeur optimisé pour Streamlit Cloud (Chromium system)"""
    def download_match(self, url, filename):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        
        filepath = os.path.join(DATA_FOLDER, filename)
        
        # Configuration des options Chrome pour l'environnement Cloud/Docker
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        # Tentative de localisation automatique ou fallback system
        try:
            # Essai standard (local)
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        except:
            # Fallback Streamlit Cloud (Chromium installé via packages.txt)
            service = Service("/usr/bin/chromedriver")

        driver = None
        try:
            driver = webdriver.Chrome(service=service, options=options)
            
            with st.spinner(f"📥 Récupération des données tactiques..."):
                driver.get(url)
                time.sleep(4) # Attente JS
                
                content = driver.page_source
                if "Incapsula" in content:
                    st.warning("⚠️ Protection détectée. Nouvelle tentative...")
                    time.sleep(10)
                    content = driver.page_source
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            
            return True
        except Exception as e:
            st.error(f"Erreur Selenium : {e}")
            return False
        finally:
            if driver:
                driver.quit()

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
            regex = r"require\.config\.params\[\"args\"\]\s*=\s*({.*?});"
            match = re.search(regex, content, re.DOTALL)
            if not match: raise ValueError("JSON introuvable")
            json_str = match.group(1)
            # Nettoyage JS -> JSON
            for key in ['matchId', 'matchCentreData', 'matchCentreEventTypeJson', 'formationIdNameMappings']:
                json_str = json_str.replace(key, f'"{key}"')
            return json.loads(json_str)
        except Exception as e:
            raise ValueError(f"Parsing failed: {e}")

    def get_all_data(self):
        """Récupère tout en un appel pour simplifier"""
        mc = self.data['matchCentreData']
        
        # Infos Match
        match_info = {
            'score': mc['score'],
            'venue': mc.get('venueName', 'Unknown'),
            'startTime': mc.get('startTime', ''),
        }
        
        # Équipes & Formations
        fmt_divs = self.soup.find_all('div', class_='formation')
        home_fmt = fmt_divs[0].get_text(strip=True) if len(fmt_divs) > 0 else 'N/A'
        away_fmt = fmt_divs[1].get_text(strip=True) if len(fmt_divs) > 1 else 'N/A'
        
        teams = {
            'home': {
                'id': mc['home']['teamId'], 'name': mc['home']['name'],
                'manager': mc['home'].get('managerName', ''),
                'formation': home_fmt
            },
            'away': {
                'id': mc['away']['teamId'], 'name': mc['away']['name'],
                'manager': mc['away'].get('managerName', ''),
                'formation': away_fmt
            }
        }
        
        # Logos URLs (Scraping léger)
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
        events = pd.DataFrame(mc['events'])
        players_list = []
        for side in ['home', 'away']:
            tid = mc[side]['teamId']
            for p in mc[side]['players']:
                p['teamId'] = tid
                players_list.append(p)
        df_players = pd.DataFrame(players_list)
        
        # Nettoyage Events
        if 'endX' not in events.columns: events['endX'] = 0.0
        if 'endY' not in events.columns: events['endY'] = 0.0
        events['type'] = events['type'].apply(lambda x: x.get('displayName'))
        events['outcomeType'] = events['outcomeType'].apply(lambda x: x.get('displayName'))
        
        # Identifier receveur
        events['next_teamId'] = events['teamId'].shift(-1)
        events['next_playerId'] = events['playerId'].shift(-1)
        mask = (events['type'] == 'Pass') & (events['outcomeType'] == 'Successful') & (events['teamId'] == events['next_teamId'])
        events.loc[mask, 'receiverId'] = events.loc[mask, 'next_playerId']
        
        return events, df_players

    def get_network(self, team_id, events, players, min_passes=3):
        starters = players[(players['teamId'] == team_id) & (players['isFirstEleven'] == True)]
        starter_ids = starters['playerId'].unique()
        
        # Positions moyennes
        team_events = events[(events['teamId'] == team_id) & (events['playerId'].isin(starter_ids))]
        avg_locs = team_events.groupby('playerId').agg({'x':'mean', 'y':'mean', 'id':'count'}).rename(columns={'id':'count'})
        avg_locs = avg_locs.merge(players[['playerId', 'name', 'shirtNo', 'position']], on='playerId')
        
        # Passes entre titulaires uniquement
        passes = team_events[(team_events['type'] == 'Pass') & (team_events['outcomeType'] == 'Successful') & (team_events['receiverId'].isin(starter_ids))].copy()
        passes['pair'] = passes.apply(lambda r: tuple(sorted([r['playerId'], r['receiverId']])), axis=1)
        pass_counts = passes.groupby('pair').size().reset_index(name='pass_count')
        pass_counts = pass_counts[pass_counts['pass_count'] >= min_passes]
        
        network = []
        for _, row in pass_counts.iterrows():
            p1, p2 = row['pair']
            # Vérification de sécurité
            if p1 in avg_locs['playerId'].values and p2 in avg_locs['playerId'].values:
                l1 = avg_locs[avg_locs['playerId'] == p1].iloc[0]
                l2 = avg_locs[avg_locs['playerId'] == p2].iloc[0]
                network.append({
                    'x_start': l1['x'], 'y_start': l1['y'],
                    'x_end': l2['x'], 'y_end': l2['y'],
                    'pass_count': row['pass_count']
                })
        
        return pd.DataFrame(network), avg_locs

class DashboardVisualizer:
    def create_dashboard(self, match_info, teams, home_net, home_nodes, away_net, away_nodes, home_logo_url, away_logo_url):
        # Configuration des couleurs
        STYLE = {
            'background': '#0E1117', 'text': 'white', 'sub': '#A0A0A0',
            'home': '#00BFFF', 'away': '#FF4B4B', 'line': '#2B313E'
        }
        
        fig = plt.figure(figsize=(24, 22), facecolor=STYLE['background'])
        gs = gridspec.GridSpec(4, 3, width_ratios=[1, 0.05, 1], height_ratios=[0.08, 0.04, 0.68, 0.20])
        
        # --- HEADER ---
        ax_h = fig.add_subplot(gs[0, :])
        ax_h.axis('off')
        
        # Score
        ax_h.text(0.5, 0.5, match_info['score'].replace(' : ', '-'), ha='center', va='center', fontsize=60, color='white', weight='bold', fontproperties=FONT_PROP)
        
        # Noms
        ax_h.text(0.35, 0.65, teams['home']['name'].upper(), ha='right', fontsize=30, color=STYLE['home'], weight='bold', fontproperties=FONT_PROP)
        ax_h.text(0.65, 0.65, teams['away']['name'].upper(), ha='left', fontsize=30, color=STYLE['away'], weight='bold', fontproperties=FONT_PROP)
        
        # Managers & Formations
        ax_h.text(0.35, 0.35, f"{teams['home']['manager']} ({teams['home']['formation']})", ha='right', fontsize=14, color=STYLE['sub'], fontproperties=FONT_PROP)
        ax_h.text(0.65, 0.35, f"{teams['away']['manager']} ({teams['away']['formation']})", ha='left', fontsize=14, color=STYLE['sub'], fontproperties=FONT_PROP)

        # Logos via URL
        def add_logo(url, x_pos):
            try:
                if url:
                    resp = requests.get(url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
                    if resp.status_code == 200:
                        img = Image.open(BytesIO(resp.content))
                        im = OffsetImage(img, zoom=0.8)
                        ab = AnnotationBbox(im, (x_pos, 0.5), frameon=False, xycoords='axes fraction')
                        ax_h.add_artist(ab)
            except: pass
            
        add_logo(home_logo_url, 0.10)
        add_logo(away_logo_url, 0.90)

        # --- TERRAINS ---
        def draw_pitch(ax, net, nodes, color):
            pitch = VerticalPitch(pitch_type='opta', pitch_color=STYLE['background'], line_color=STYLE['line'], linewidth=2)
            pitch.draw(ax=ax)
            
            if not net.empty:
                max_width = net['pass_count'].max()
                width = (net['pass_count'] / max_width * 10)
                pitch.lines(net['x_start'], net['y_start'], net['x_end'], net['y_end'], lw=width, ax=ax, color=color, alpha=0.6, zorder=2)
            
            if not nodes.empty:
                # Normalisation de la taille des noeuds
                max_size = nodes['count'].max()
                sizes = (nodes['count'] / max_size) * 1000
                pitch.scatter(nodes['x'], nodes['y'], s=sizes, color=STYLE['background'], edgecolors=color, linewidth=2, zorder=3, ax=ax)
                for _, row in nodes.iterrows():
                    pitch.annotate(row['shirtNo'], (row['x'], row['y']), va='center', ha='center', color='white', fontsize=10, weight='bold', ax=ax, fontproperties=FONT_PROP)

        ax_home = fig.add_subplot(gs[2, 0])
        draw_pitch(ax_home, home_net, home_nodes, STYLE['home'])
        
        ax_away = fig.add_subplot(gs[2, 2])
        draw_pitch(ax_away, away_net, away_nodes, STYLE['away'])
        
        # Flèche sens du jeu
        ax_arrow = fig.add_subplot(gs[2, 1])
        ax_arrow.axis('off')
        ax_arrow.arrow(0.5, 0.1, 0, 0.8, fc='white', ec='white', width=0.05, head_width=0.3, head_length=0.1)
        ax_arrow.text(0.5, 0.05, "Attaque", ha='center', color='white', fontproperties=FONT_PROP)
        
        # Légende
        ax_legend = fig.add_subplot(gs[1, :])
        ax_legend.axis('off')
        ax_legend.text(0.5, 0.5,
