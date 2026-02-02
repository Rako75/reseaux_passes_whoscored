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
import shutil
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
    /* Fond global sombre */
    .stApp {
        background-color: #0E1117;
    }
    /* Titres */
    h1, h2, h3 {
        color: #FFFFFF !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    /* Boutons */
    .stButton>button {
        width: 100%;
        background-color: #38003c; /* Violet PL */
        color: #00FF85; /* Vert fluo PL */
        border: 1px solid #00FF85;
        border-radius: 5px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #00FF85;
        color: #38003c;
        border-color: white;
    }
    /* Messages d'alerte */
    .stAlert {
        background-color: #1E1E1E;
        color: white;
        border: 1px solid #333;
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
        # Regex pour capturer l'ID et le Titre
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
                # Estimation de la journée (Gameweek) basée sur l'ordre
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
        
        # --- CONFIGURATION CHROME ---
        options = Options()
        options.add_argument("--headless=new") # Mode sans interface graphique
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # --- DÉTECTION DU DRIVER SYSTÈME (La clé du succès sur Cloud) ---
        # On cherche le binaire 'chromedriver' installé par packages.txt
        system_chromedriver = shutil.which("chromedriver")
        
        if system_chromedriver:
            # Cas : Streamlit Cloud / Linux avec paquets installés
            service = Service(system_chromedriver)
        else:
            # Cas : Local (Windows/Mac) sans driver système -> on utilise le manager
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
            except Exception as e:
                st.error(f"❌ Impossible de configurer le driver : {e}")
                return False

        driver = None
        try:
            driver = webdriver.Chrome(service=service, options=options)
            
            with st.spinner(f"🌍 Connexion à WhoScored pour récupérer les données..."):
                driver.get(url)
                time.sleep(6) # Attente chargement initial augmentée
                
                # Gestion Anti-bot basique
                content = driver.page_source
                if "Incapsula" in content or "challenge" in content.lower():
                    st.warning("🛡️ Vérification de sécurité détectée, attente prolongée...")
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
            
            # MÉTHODE 1 : Regex classique (require.config.params)
            regex1 = r"require\.config\.params\[\"args\"\]\s*=\s*({.*?});"
            match1 = re.search(regex1, content, re.DOTALL)
            
            if match1:
                json_str = match1.group(1)
                return self._clean_and_parse_json(json_str)
            
            # MÉTHODE 2 : Recherche de matchCentreData directement
            regex2 = r"matchCentreData:\s*({.*?}),\s*matchCentreEventTypeJson"
            match2 = re.search(regex2, content, re.DOTALL)
            
            if match2:
                json_str = match2.group(1)
                # Dans ce cas, on reconstruit la structure attendue
                parsed = self._clean_and_parse_json(json_str)
                return {'matchCentreData': parsed}
            
            # MÉTHODE 3 : Recherche dans les balises script
            scripts = self.soup.find_all('script')
            for script in scripts:
                script_text = script.string
                if script_text and 'matchCentreData' in script_text:
                    # Essayer d'extraire le JSON
                    match3 = re.search(r'matchCentreData["\']?\s*:\s*({.*?})\s*[,}]', script_text, re.DOTALL)
                    if match3:
                        json_str = match3.group(1)
                        parsed = self._clean_and_parse_json(json_str)
                        return {'matchCentreData': parsed}
            
            # MÉTHODE 4 : Recherche plus agressive dans tout le HTML
            all_matches = re.finditer(r'({[^{}]*"home"[^{}]*"away"[^{}]*"events"[^{}]*})', content)
            for match in all_matches:
                try:
                    json_str = match.group(1)
                    parsed = self._clean_and_parse_json(json_str)
                    if 'home' in parsed and 'away' in parsed and 'events' in parsed:
                        return {'matchCentreData': parsed}
                except:
                    continue
            
            raise ValueError("❌ Impossible de trouver le JSON de données. Le format de la page a peut-être changé.")
            
        except Exception as e:
            raise ValueError(f"❌ Erreur de parsing : {e}")

    def _clean_and_parse_json(self, json_str):
        """Nettoie et parse une chaîne JSON-like en vraie structure JSON."""
        # Liste des clés connues à quoter
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
            # Remplacer key: par "key": (sans quotes autour)
            json_str = re.sub(rf'\b{key}\s*:', f'"{key}":', json_str)
        
        # Remplacer les undefined par null
        json_str = re.sub(r'\bundefined\b', 'null', json_str)
        
        # Nettoyer les virgules en trop
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # Dernier recours : mode debug
            st.warning(f"⚠️ Erreur JSON détectée : {e}")
            st.text_area("JSON problématique (500 premiers caractères)", json_str[:500])
            raise ValueError(f"JSON invalide après nettoyage : {e}")

    def get_all_data(self):
        if 'matchCentreData' not in self.data:
            raise ValueError("Structure de données incorrecte : 'matchCentreData' manquant")
        
        mc = self.data['matchCentreData']
        
        # Vérifications de sécurité
        if 'home' not in mc or 'away' not in mc:
            raise ValueError("Données des équipes manquantes dans matchCentreData")
        
        match_info = {
            'score': mc.get('score', 'N/A'),
            'venue': mc.get('venueName', 'Stade Inconnu'),
            'startTime': mc.get('startTime', ''),
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
                # Correction des URLs relatives
                url = img['src']
                if url.startswith('//'):
                    url = 'https:' + url
                logos[i] = url

        return mc, match_info, teams, logos

class PassNetworkEngine:
    """Calcule les réseaux de passes."""
    def process(self, mc):
        if 'events' not in mc:
            raise ValueError("Aucun événement trouvé dans les données du match")
        
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
            raise ValueError("Aucun joueur trouvé dans les données")
        
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
        
        # Identifier receveur (passe réussie vers coéquipier)
        events['next_teamId'] = events['teamId'].shift(-1)
        events['next_playerId'] = events['playerId'].shift(-1)
        mask = (events['type'] == 'Pass') & (events['outcomeType'] == 'Successful') & (events['teamId'] == events['next_teamId'])
        events.loc[mask, 'receiverId'] = events.loc[mask, 'next_playerId']
        
        return events, df_players

    def get_network(self, team_id, events, players, min_passes=3):
        # 1. Filtrer titulaires uniquement
        starters = players[(players['teamId'] == team_id) & (players['isFirstEleven'] == True)]
        starter_ids = starters['playerId'].unique()
        
        if len(starter_ids) == 0:
            return pd.DataFrame(), pd.DataFrame(columns=['playerId', 'name', 'shirtNo', 'position', 'x', 'y', 'count'])
        
        # 2. Filtrer events de l'équipe et des titulaires
        team_events = events[(events['teamId'] == team_id) & (events['playerId'].isin(starter_ids))]
        
        if team_events.empty:
            return pd.DataFrame(), pd.DataFrame(columns=['playerId', 'name', 'shirtNo', 'position', 'x', 'y', 'count'])
        
        # 3. Positions moyennes
        avg_locs = team_events.groupby('playerId').agg({'x':'mean', 'y':'mean', 'id':'count'}).rename(columns={'id':'count'})
        avg_locs = avg_locs.merge(players[['playerId', 'name', 'shirtNo', 'position']], on='playerId')
        
        # 4. Calcul des passes
        passes = team_events[
            (team_events['type'] == 'Pass') & 
            (team_events['outcomeType'] == 'Successful') & 
            (team_events['receiverId'].notna()) &
            (team_events['receiverId'].isin(starter_ids))
        ].copy()
        
        if passes.empty:
            return pd.DataFrame(), avg_locs
        
        # Clé unique pour la paire de joueurs (triée pour éviter doublons A->B et B->A si on veut du non-orienté)
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

class DashboardVisualizer:
    """Gère le rendu graphique - Version exacte du pipeline"""

    def create_dashboard(self, match_info, teams, home_net, home_nodes, away_net, away_nodes, home_logo_url, away_logo_url):
        """Méthode principale - Adapte les paramètres pour draw_dashboard"""
        
        # Récupération des images de logos depuis les URLs
        home_logo_img = self._get_logo_from_url(home_logo_url)
        away_logo_img = self._get_logo_from_url(away_logo_url)
        
        # Stats vides (non utilisées dans ce contexte Streamlit)
        stats = {'home': {}, 'away': {}}
        
        # Appel de la méthode de dessin principale
        return self.draw_dashboard(
            match_info, teams, stats,
            home_net, home_nodes,
            away_net, away_nodes,
            home_logo_img, away_logo_img,
            output_file=None  # Pas de sauvegarde, on retourne la figure
        )
    
    def _get_logo_from_url(self, url):
        """Télécharge et retourne l'image PIL depuis une URL"""
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

        # Layout: Taille augmentée (24x22)
        fig = plt.figure(figsize=(24, 22), facecolor=STYLE['background'])

        # GridSpec: 4 Lignes
        # Width ratios: [1, 0.05, 1] - Colonne centrale (0.05) très fine pour rapprocher les visuels
        gs = gridspec.GridSpec(4, 3, width_ratios=[1, 0.05, 1], height_ratios=[0.08, 0.04, 0.68, 0.20])

        # --- HEADER (Toute la largeur) ---
        ax_header = fig.add_subplot(gs[0, :])
        self._draw_header(ax_header, match_info, teams, home_logo_img, away_logo_img, STYLE)

        # --- LÉGENDE (Au-dessus des terrains - Style The Athletic) ---
        ax_legend = fig.add_subplot(gs[1, :])
        self._draw_legend(ax_legend, STYLE)

        # --- TERRAIN DOMICILE (Gauche, Vertical) ---
        ax_home = fig.add_subplot(gs[2, 0])
        self._draw_pass_map(ax_home, home_net, home_nodes, STYLE['home_color'], STYLE)

        # --- FLÈCHE SENS DU JEU (Centre) ---
        ax_arrow = fig.add_subplot(gs[2, 1])
        self._draw_direction_arrow(ax_arrow, STYLE)

        # --- TERRAIN EXTÉRIEUR (Droite, Vertical) ---
        ax_away = fig.add_subplot(gs[2, 2])
        self._draw_pass_map(ax_away, away_net, away_nodes, STYLE['away_color'], STYLE, flip=False)

        # --- COMPOSITIONS (Bas - Row 3) ---
        ax_lineup_home = fig.add_subplot(gs[3, 0])
        self._draw_lineup(ax_lineup_home, home_nodes, STYLE['home_color'], teams['home']['name'], STYLE)

        ax_lineup_away = fig.add_subplot(gs[3, 2])
        self._draw_lineup(ax_lineup_away, away_nodes, STYLE['away_color'], teams['away']['name'], STYLE)

        # Footer
        fig.text(0.5, 0.01, "Données: WhoScored/Opta | Visualisation: Advanced Python Analysis",
                 ha='center', color=STYLE['sub_text'], fontsize=12, fontproperties=STYLE['font_prop'])

        # Réduction drastique de hspace/wspace pour le rapprochement
        plt.tight_layout()
        plt.subplots_adjust(top=0.95, hspace=0.02, wspace=0.02)
        
        if output_file:
            plt.savefig(output_file, facecolor=STYLE['background'], dpi=300, bbox_inches='tight')
            plt.close(fig)
        
        return fig

    def _draw_header(self, ax, match_info, teams, home_logo, away_logo, STYLE):
        ax.axis('off')

        # Logos positionnés via OffsetImage (ZOOM 0.9 pour plus grand)
        if home_logo:
            ib_home = OffsetImage(home_logo, zoom=0.9)
            ab_home = AnnotationBbox(ib_home, (0.10, 0.5), frameon=False, xycoords='axes fraction', box_alignment=(0.5, 0.5))
            ax.add_artist(ab_home)

        if away_logo:
            ib_away = OffsetImage(away_logo, zoom=0.9)
            ab_away = AnnotationBbox(ib_away, (0.90, 0.5), frameon=False, xycoords='axes fraction', box_alignment=(0.5, 0.5))
            ax.add_artist(ab_away)

        # Info Match
        start_time = match_info.get('startTime', '')
        date_display = start_time[:10] if len(start_time) >= 10 else 'Date inconnue'
        date_venue = f"{date_display} | {match_info.get('venue', 'Stade Inconnu')}"
        ax.text(0.5, 0.90, date_venue, ha='center', va='center', color=STYLE['sub_text'], fontsize=14, fontproperties=STYLE['font_prop'])

        # Score (Position descendue à 0.50)
        score_txt = str(match_info.get('score', 'N/A')).replace(' : ', '-')
        ax.text(0.5, 0.50, score_txt, ha='center', va='center', fontsize=65, weight='bold', color='white', fontproperties=STYLE['font_prop'])
        ax.text(0.5, 0.25, "Score final", ha='center', va='center', fontsize=14, weight='bold', color=STYLE['sub_text'], fontproperties=STYLE['font_prop'])

        # Noms des équipes (Position remontée à 0.65)
        ax.text(0.35, 0.65, teams['home']['name'].upper(), ha='right', va='center',
                fontsize=30, weight='bold', color=STYLE['home_color'], fontproperties=STYLE['font_prop'])
        ax.text(0.65, 0.65, teams['away']['name'].upper(), ha='left', va='center',
                fontsize=30, weight='bold', color=STYLE['away_color'], fontproperties=STYLE['font_prop'])

        # --- AJOUT: Entraîneur et Formation (Position descendue à 0.35) ---
        home_sub = f"{teams['home'].get('manager', 'N/A')}\n({teams['home'].get('formation', 'N/A')})"
        away_sub = f"{teams['away'].get('manager', 'N/A')}\n({teams['away'].get('formation', 'N/A')})"

        ax.text(0.35, 0.35, home_sub, ha='right', va='center',
                fontsize=16, color=STYLE['sub_text'], weight='normal', fontproperties=STYLE['font_prop'])
        ax.text(0.65, 0.35, away_sub, ha='left', va='center',
                fontsize=16, color=STYLE['sub_text'], weight='normal', fontproperties=STYLE['font_prop'])

    def _draw_pass_map(self, ax, net_df, nodes_df, color, STYLE, flip=False):
        # Utilisation de VerticalPitch pour un terrain vertical
        pitch = VerticalPitch(pitch_type='opta', pitch_color=STYLE['background'],
                              line_color=STYLE['line_color'], linewidth=1.5)
        pitch.draw(ax=ax)

        # Copie pour éviter la modification des DataFrames originaux
        if not net_df.empty:
            net_df = net_df.copy()
        if not nodes_df.empty:
            nodes_df = nodes_df.copy()

        # Plus besoin d'inverser les coordonnées manuellement pour VerticalPitch
        if flip:
             net_df['x_start'] = 100 - net_df['x_start']; net_df['y_start'] = 100 - net_df['y_start']
             net_df['x_end'] = 100 - net_df['x_end']; net_df['y_end'] = 100 - net_df['y_end']
             nodes_df['x'] = 100 - nodes_df['x']; nodes_df['y'] = 100 - nodes_df['y']

        if not net_df.empty:
            max_pass = net_df['pass_count'].max()
            if max_pass > 0:
                width = (net_df['pass_count'] / max_pass * 12) # Plus épais
                pitch.lines(net_df['x_start'], net_df['y_start'], net_df['x_end'], net_df['y_end'],
                            lw=width, ax=ax, color=color, alpha=0.5, zorder=2)

        # Dessiner les noeuds (Uniquement Numéro)
        if not nodes_df.empty:
            max_count = nodes_df['count'].max()
            if max_count > 0:
                for i, row in nodes_df.iterrows():
                    size = (row['count'] / max_count) * 1500 # Taille = Volume

                    # Cercle du joueur
                    pitch.scatter(row['x'], row['y'], s=size, color=STYLE['background'],
                                  edgecolors=color, linewidth=2, zorder=3, ax=ax)

                    # Numéro uniquement
                    pitch.annotate(row['shirtNo'], xy=(row['x'], row['y']), va='center', ha='center',
                                   color='white', fontsize=12, weight='bold', zorder=4, ax=ax, fontproperties=STYLE['font_prop'])

    def _draw_direction_arrow(self, ax, STYLE):
        """Dessine la flèche 'Sens du jeu' style The Athletic"""
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        # Flèche verticale sur toute la hauteur
        ax.annotate('', xy=(0.7, 0.95), xytext=(0.7, 0.05),
                    arrowprops=dict(facecolor='white', edgecolor='white', width=1.5, headwidth=8, headlength=10),
                    xycoords='axes fraction', textcoords='axes fraction')

        # Texte vertical à gauche de la flèche
        # x=0.3 pour être à gauche de la flèche (qui est à x=0.7)
        ax.text(0.3, 0.5, "Sens du jeu", rotation=90, ha='center', va='center',
                color='white', fontsize=14, weight='bold', fontproperties=STYLE['font_prop'])

    def _draw_lineup(self, ax, nodes_df, color, team_name, STYLE):
        """Affiche la liste des joueurs (Numéro - Nom)"""
        ax.axis('off')

        # Préparer les données
        if nodes_df.empty: return

        # Convertir shirtNo en int pour le tri, gérer les cas non numériques
        nodes_df = nodes_df.copy()
        nodes_df['shirtNoInt'] = pd.to_numeric(nodes_df['shirtNo'], errors='coerce').fillna(999).astype(int)
        lineup = nodes_df.sort_values('shirtNoInt')

        # Affichage en 2 colonnes mais recentré (0.20 et 0.60) pour rester dans la largeur du terrain
        # y_start légèrement descendu pour ne pas être trop haut
        y_start = 0.96
        y_step = 0.12

        half = (len(lineup) + 1) // 2
        col1 = lineup.iloc[:half]
        col2 = lineup.iloc[half:]

        # Colonne Gauche (Alignée visuellement avec le terrain)
        y_pos = y_start
        for _, row in col1.iterrows():
            txt = f"{row['shirtNo']} - {row['name']}"
            ax.text(0.20, y_pos, txt, color='white', fontsize=13, ha='left', fontproperties=STYLE['font_prop'])
            y_pos -= y_step

        # Colonne Droite (Alignée visuellement avec le terrain)
        y_pos = y_start
        for _, row in col2.iterrows():
            txt = f"{row['shirtNo']} - {row['name']}"
            ax.text(0.60, y_pos, txt, color='white', fontsize=13, ha='left', fontproperties=STYLE['font_prop'])
            y_pos -= y_step

    def _draw_legend(self, ax, STYLE):
        """Dessine la légende horizontale style 'The Athletic'"""
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        legend_y = 0.4

        # --- PARTIE GAUCHE: VOLUME DE PASSES (Cercles) ---
        # Texte gauche
        ax.text(0.15, legend_y, "Peu de passes", ha='right', va='center',
                color='white', fontsize=12, weight='bold', fontproperties=STYLE['font_prop'])

        # 4 Cercles de taille croissante
        sizes = [80, 200, 400, 700]
        x_start = 0.17
        x_spacing = 0.03

        for i, s in enumerate(sizes):
            # Cercle bleu creux (fond background, bordure bleue style Athletic)
            ax.scatter(x_start + (i * x_spacing), legend_y, s=s,
                       color=STYLE['background'], edgecolors=STYLE['legend_blue'], linewidth=1.5)

        # Texte droite cercles
        ax.text(x_start + (len(sizes) * x_spacing) + 0.0005, legend_y, "Beaucoup de passes", ha='left', va='center',
                color='white', fontsize=12, weight='bold', fontproperties=STYLE['font_prop'])

        # --- PARTIE DROITE: INTENSITÉ (Lignes) ---
        # Centre droit start
        right_start = 0.55

        # Texte gauche lignes
        ax.text(right_start, legend_y, "Combine peu", ha='right', va='center',
                color='white', fontsize=12, weight='bold', fontproperties=STYLE['font_prop'])

        # 3 Lignes d'épaisseur croissante
        widths = [1, 3, 6]
        line_length = 0.04
        line_spacing = 0.01
        current_x = right_start + 0.02

        for w in widths:
            ax.plot([current_x, current_x + line_length], [legend_y, legend_y],
                    color='white', lw=w)
            current_x += line_length + line_spacing

        # Texte droite lignes
        ax.text(current_x + 0.01, legend_y, "Combine beaucoup", ha='left', va='center',
                color='white', fontsize=12, weight='bold', fontproperties=STYLE['font_prop'])

# --- FONCTION PRINCIPALE ---

def main():
    st.title("⚽ Premier League Dashboard 2025-2026")
    st.markdown("---")

    # --- SIDEBAR ---
    st.sidebar.header("Paramètres")
    mode = st.sidebar.radio("Mode de Sélection", ["📅 Calendrier / Journées", "🌐 URL Personnalisée"])

    selected_match_data = None
    needs_download = False
    
    # 1. Mode Calendrier
    if mode == "📅 Calendrier / Journées":
        matches = load_match_list()
        
        if not matches:
            st.error(f"Fichier '{URLS_FILE}' introuvable ou vide.")
        else:
            df_matches = pd.DataFrame(matches)
            gameweeks = sorted(df_matches['gameweek'].unique())
            
            sel_gw = st.sidebar.selectbox("Choisir la Journée (GW)", gameweeks)
            
            # Filtrer les matchs
            gw_matches = df_matches[df_matches['gameweek'] == sel_gw]
            
            # CRUCIAL : Conversion en dict pour éviter l'erreur de Truth Value sur Series Pandas
            match_options = {
                f"{r['title']} (Match #{r['id']})": r.to_dict() 
                for _, r in gw_matches.iterrows()
            }
            
            sel_match_key = st.sidebar.selectbox("Choisir le Match", list(match_options.keys()))
            selected_match_data = match_options[sel_match_key]
            
            # Vérification fichier local
            file_path = os.path.join(DATA_FOLDER, selected_match_data['filename'])
            if os.path.exists(file_path):
                st.sidebar.success("✅ Données disponibles localement")
                needs_download = False
            else:
                st.sidebar.warning("☁️ Données à télécharger")
                needs_download = True

    # 2. Mode URL
    elif mode == "🌐 URL Personnalisée":
        url_input = st.sidebar.text_input("Coller l'URL WhoScored (Match Centre)")
        if url_input:
            match_id = re.search(r'/matches/(\d+)/', url_input)
            if match_id:
                mid = match_id.group(1)
                selected_match_data = {
                    'id': mid,
                    'title': f"Match Personnalisé {mid}",
                    'url': url_input,
                    'filename': f"{mid}.html"
                }
                file_path = os.path.join(DATA_FOLDER, selected_match_data['filename'])
                if os.path.exists(file_path):
                    st.sidebar.success("✅ Données disponibles")
                    needs_download = False
                else:
                    needs_download = True
            else:
                st.sidebar.error("URL invalide. Assurez-vous qu'elle contient '/matches/ID/'")

    # 3. Logique d'affichage et Téléchargement
    if selected_match_data is not None:
        st.header(f"{selected_match_data['title']}")
        
        if needs_download:
            st.info(f"Les données pour le match {selected_match_data['id']} ne sont pas présentes sur le serveur.")
            if st.button("🚀 Télécharger et Analyser (Mode Live)", type="primary"):
                downloader = StreamlitDownloader()
                success = downloader.download_match(selected_match_data['url'], selected_match_data['filename'])
                if success:
                    st.success("Téléchargement réussi ! Analyse en cours...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Échec du téléchargement. Veuillez réessayer.")
        else:
            # Le fichier existe -> Analyse
            file_path = os.path.join(DATA_FOLDER, selected_match_data['filename'])
            
            try:
                # 1. Parsing
                with st.spinner("🔍 Analyse du fichier HTML..."):
                    parser = MatchParser(file_path)
                    mc, match_info, teams, logos = parser.get_all_data()
                
                # 2. Calculs
                with st.spinner("⚙️ Calcul des réseaux de passes..."):
                    engine = PassNetworkEngine()
                    events, players = engine.process(mc)
                    
                    home_net, home_nodes = engine.get_network(teams['home']['id'], events, players)
                    away_net, away_nodes = engine.get_network(teams['away']['id'], events, players)
                
                # 3. Affichage Onglets
                tab1, tab2 = st.tabs(["📊 Pass Network & Dashboard", "📈 Statistiques Détaillées"])
                
                with tab1:
                    with st.spinner("🎨 Génération de la visualisation tactique..."):
                        viz = DashboardVisualizer()
                        fig = viz.create_dashboard(
                            match_info, teams, 
                            home_net, home_nodes, 
                            away_net, away_nodes, 
                            logos.get(0), logos.get(1)
                        )
                        st.pyplot(fig)
                        
                        # Bouton Download
                        buf = BytesIO()
                        fig.savefig(buf, format="png", facecolor='#0E1117', bbox_inches='tight', dpi=150)
                        st.download_button(
                            label="💾 Télécharger la visualisation HD",
                            data=buf.getvalue(),
                            file_name=f"PassNetwork_{selected_match_data['id']}.png",
                            mime="image/png"
                        )
                        plt.close(fig)

                with tab2:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"🏠 {teams['home']['name']}")
                        st.caption(f"Formation: {teams['home']['formation']} | Manager: {teams['home']['manager']}")
                        if not home_nodes.empty:
                            display_df = home_nodes[['name', 'shirtNo', 'count', 'position']].copy()
                            display_df.columns = ['Joueur', 'N°', 'Actions', 'Poste']
                            st.dataframe(
                                display_df.sort_values('Actions', ascending=False), 
                                hide_index=True, 
                                use_container_width=True
                            )
                        else:
                            st.info("Aucune donnée disponible")
                            
                    with col2:
                        st.subheader(f"✈️ {teams['away']['name']}")
                        st.caption(f"Formation: {teams['away']['formation']} | Manager: {teams['away']['manager']}")
                        if not away_nodes.empty:
                            display_df = away_nodes[['name', 'shirtNo', 'count', 'position']].copy()
                            display_df.columns = ['Joueur', 'N°', 'Actions', 'Poste']
                            st.dataframe(
                                display_df.sort_values('Actions', ascending=False), 
                                hide_index=True,
                                use_container_width=True
                            )
                        else:
                            st.info("Aucune donnée disponible")

            except Exception as e:
                st.error(f"❌ Erreur lors de l'analyse : {e}")
                
                # Affichage debug en mode développement
                with st.expander("🔧 Informations de débogage"):
                    st.text(f"Erreur complète: {str(e)}")
                    st.text(f"Type: {type(e).__name__}")
                    
                    if os.path.exists(file_path):
                        st.text(f"Taille du fichier: {os.path.getsize(file_path)} octets")
                        with open(file_path, 'r', encoding='utf-8') as f:
                            preview = f.read(1000)
                        st.text_area("Aperçu HTML (1000 premiers caractères)", preview)
                
                st.info("💡 Le fichier source semble corrompu ou incomplet. Essayez de le retélécharger.")
                
                # Option de suppression pour retélécharger
                if st.button("🗑️ Supprimer le fichier corrompu et retélécharger"):
                    try:
                        os.remove(file_path)
                        st.success("Fichier supprimé. Rechargement de la page...")
                        time.sleep(1)
                        st.rerun()
                    except Exception as del_err:
                        st.error(f"Erreur lors de la suppression : {del_err}")

    else:
        # Message d'accueil
        st.info("👈 Sélectionnez un match dans le menu de gauche pour commencer.")
        
        # Statistiques du cache
        if os.path.exists(DATA_FOLDER):
            cached_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.html')]
            if cached_files:
                st.success(f"📦 {len(cached_files)} match(s) en cache local")
                with st.expander("Voir les matchs en cache"):
                    for f in sorted(cached_files):
                        st.text(f"- {f}")

if __name__ == "__main__":
    main()
