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
        background-color: #FF4B4B;
        color: white;
        border-radius: 5px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #FF2B2B;
        border-color: white;
    }
    div[data-testid="metric-container"] {
        background-color: #1E1E1E;
        padding: 10px;
        border-radius: 8px;
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
                # Estimation de la journée (Gameweek)
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
    """Téléchargeur optimisé pour Streamlit Cloud."""
    def download_match(self, url, filename):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        filepath = os.path.join(DATA_FOLDER, filename)
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        # Gestion intelligente du driver (Local vs Cloud)
        service = None
        try:
            # Tentative 1 : Installation automatique (Local)
            service = Service(ChromeDriverManager().install())
        except:
            # Tentative 2 : Chemin système (Streamlit Cloud)
            # Nécessite packages.txt avec chromium et chromium-driver
            service = Service("/usr/bin/chromedriver")

        driver = None
        try:
            driver = webdriver.Chrome(service=service, options=options)
            
            with st.spinner(f"📥 Téléchargement des données tactiques depuis WhoScored..."):
                driver.get(url)
                time.sleep(5)
                
                content = driver.page_source
                if "Incapsula" in content:
                    st.warning("⚠️ Protection anti-bot détectée. Nouvelle tentative...")
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
            if not match: raise ValueError("JSON introuvable dans le HTML")
            
            json_str = match.group(1)
            # Nettoyage JS -> JSON
            for key in ['matchId', 'matchCentreData', 'matchCentreEventTypeJson', 'formationIdNameMappings']:
                json_str = json_str.replace(key, f'"{key}"')
            return json.loads(json_str)
        except Exception as e:
            raise ValueError(f"Parsing failed: {e}")

    def get_all_data(self):
        mc = self.data['matchCentreData']
        
        match_info = {
            'score': mc['score'],
            'venue': mc.get('venueName', 'Unknown'),
            'startTime': mc.get('startTime', ''),
        }
        
        fmt_divs = self.soup.find_all('div', class_='formation')
        formations = [d.get_text(strip=True) for d in fmt_divs]
        
        teams = {
            'home': {
                'id': mc['home']['teamId'], 'name': mc['home']['name'],
                'manager': mc['home'].get('managerName', ''),
                'formation': formations[0] if len(formations) > 0 else 'N/A'
            },
            'away': {
                'id': mc['away']['teamId'], 'name': mc['away']['name'],
                'manager': mc['away'].get('managerName', ''),
                'formation': formations[1] if len(formations) > 1 else 'N/A'
            }
        }
        
        # Extraction URLs Logos
        logos = {}
        emblems = self.soup.find_all('div', class_='team-emblem')
        for i, emblem in enumerate(emblems[:2]):
            img = emblem.find('img')
            if img and img.get('src'):
                logos[i] = img['src'].replace('http:', 'https:') if img['src'].startswith('//') else img['src']

        return mc, match_info, teams, logos

class PassNetworkEngine:
    def process(self, mc):
        events = pd.DataFrame(mc['events'])
        
        # Extraction joueurs
        players_list = []
        for side in ['home', 'away']:
            tid = mc[side]['teamId']
            for p in mc[side]['players']:
                p['teamId'] = tid
                players_list.append(p)
        df_players = pd.DataFrame(players_list)
        
        # Nettoyage Events
        for col in ['endX', 'endY', 'x', 'y']:
            if col not in events.columns: events[col] = 0.0
            
        events['type'] = events['type'].apply(lambda x: x.get('displayName') if isinstance(x, dict) else x)
        events['outcomeType'] = events['outcomeType'].apply(lambda x: x.get('displayName') if isinstance(x, dict) else x)
        
        # Identifier receveur
        events['next_teamId'] = events['teamId'].shift(-1)
        events['next_playerId'] = events['playerId'].shift(-1)
        mask = (events['type'] == 'Pass') & (events['outcomeType'] == 'Successful') & (events['teamId'] == events['next_teamId'])
        events.loc[mask, 'receiverId'] = events.loc[mask, 'next_playerId']
        
        return events, df_players

    def get_network(self, team_id, events, players, min_passes=3):
        # Filtrer titulaires
        starters = players[(players['teamId'] == team_id) & (players['isFirstEleven'] == True)]
        starter_ids = starters['playerId'].unique()
        
        # Filtrer events de l'équipe et des titulaires
        team_events = events[(events['teamId'] == team_id) & (events['playerId'].isin(starter_ids))]
        
        # Positions moyennes
        avg_locs = team_events.groupby('playerId').agg({'x':'mean', 'y':'mean', 'id':'count'}).rename(columns={'id':'count'})
        avg_locs = avg_locs.merge(players[['playerId', 'name', 'shirtNo', 'position']], on='playerId')
        
        # Passes entre titulaires
        passes = team_events[
            (team_events['type'] == 'Pass') & 
            (team_events['outcomeType'] == 'Successful') & 
            (team_events['receiverId'].isin(starter_ids))
        ].copy()
        
        # Création paire unique (toujours triée) pour compter A->B et B->A ensemble ou séparément ?
        # Ici on veut des liens non-dirigés pour l'épaisseur souvent, mais gardons le standard
        passes['pair'] = passes.apply(lambda r: tuple(sorted([r['playerId'], r['receiverId']])), axis=1)
        pass_counts = passes.groupby('pair').size().reset_index(name='pass_count')
        pass_counts = pass_counts[pass_counts['pass_count'] >= min_passes]
        
        network = []
        for _, row in pass_counts.iterrows():
            p1, p2 = row['pair']
            # Vérif existence
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
    def create_dashboard(self, match_info, teams, home_net, home_nodes, away_net, away_nodes, home_logo_url, away_logo_url):
        STYLE = {
            'background': '#0E1117', 'text': 'white', 'sub': '#A0A0A0',
            'home': '#00BFFF', 'away': '#FF4B4B', 'line': '#2B313E'
        }
        
        fig = plt.figure(figsize=(24, 22), facecolor=STYLE['background'])
        gs = gridspec.GridSpec(4, 3, width_ratios=[1, 0.05, 1], height_ratios=[0.08, 0.04, 0.68, 0.20])
        
        # --- HEADER ---
        ax_h = fig.add_subplot(gs[0, :])
        ax_h.axis('off')
        
        # Textes
        score_text = match_info['score'].replace(' : ', '-')
        ax_h.text(0.5, 0.5, score_text, ha='center', va='center', fontsize=60, color='white', weight='bold', fontproperties=FONT_PROP)
        ax_h.text(0.5, 0.9, f"{match_info['startTime'][:10]} | {match_info['venue']}", ha='center', color=STYLE['sub'], fontsize=14, fontproperties=FONT_PROP)
        
        ax_h.text(0.35, 0.65, teams['home']['name'].upper(), ha='right', fontsize=30, color=STYLE['home'], weight='bold', fontproperties=FONT_PROP)
        ax_h.text(0.65, 0.65, teams['away']['name'].upper(), ha='left', fontsize=30, color=STYLE['away'], weight='bold', fontproperties=FONT_PROP)
        
        # Logos via URL
        def add_logo(url, x_pos):
            try:
                if url:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    resp = requests.get(url, headers=headers, stream=True, timeout=5)
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
            
            # Arêtes (Passes)
            if not net.empty:
                max_width = net['pass_count'].max()
                # Éviter division par zéro
                if max_width == 0: max_width = 1
                width = (net['pass_count'] / max_width * 10)
                pitch.lines(net['x_start'], net['y_start'], net['x_end'], net['y_end'], lw=width, ax=ax, color=color, alpha=0.6, zorder=2)
            
            # Noeuds (Joueurs)
            if not nodes.empty:
                max_size = nodes['count'].max()
                if max_size == 0: max_size = 1
                sizes = (nodes['count'] / max_size) * 1000
                pitch.scatter(nodes['x'], nodes['y'], s=sizes, color=STYLE['background'], edgecolors=color, linewidth=2, zorder=3, ax=ax)
                
                for _, row in nodes.iterrows():
                    pitch.annotate(row['shirtNo'], (row['x'], row['y']), va='center', ha='center', color='white', fontsize=10, weight='bold', ax=ax, fontproperties=FONT_PROP)

        ax_home = fig.add_subplot(gs[2, 0])
        draw_pitch(ax_home, home_net, home_nodes, STYLE['home'])
        
        ax_away = fig.add_subplot(gs[2, 2])
        draw_pitch(ax_away, away_net, away_nodes, STYLE['away'])
        
        # Flèche centrale
        ax_arrow = fig.add_subplot(gs[2, 1])
        ax_arrow.axis('off')
        ax_arrow.arrow(0.5, 0.1, 0, 0.8, fc='white', ec='white', width=0.05, head_width=0.3, head_length=0.1)
        
        # --- COMPOSITIONS (Bas) ---
        def draw_lineup(ax, nodes, color):
            ax.axis('off')
            if nodes.empty: return
            
            # Tri par numéro
            nodes['shirtNoInt'] = pd.to_numeric(nodes['shirtNo'], errors='coerce').fillna(999).astype(int)
            lineup = nodes.sort_values('shirtNoInt')
            
            # Affichage 2 colonnes
            half = (len(lineup) + 1) // 2
            col1 = lineup.iloc[:half]
            col2 = lineup.iloc[half:]
            
            y_pos = 0.9
            for _, r in col1.iterrows():
                ax.text(0.1, y_pos, f"{r['shirtNo']} - {r['name']}", color='white', fontsize=12, fontproperties=FONT_PROP)
                y_pos -= 0.12
            
            y_pos = 0.9
            for _, r in col2.iterrows():
                ax.text(0.6, y_pos, f"{r['shirtNo']} - {r['name']}", color='white', fontsize=12, fontproperties=FONT_PROP)
                y_pos -= 0.12

        ax_l_home = fig.add_subplot(gs[3, 0])
        draw_lineup(ax_l_home, home_nodes, STYLE['home'])
        
        ax_l_away = fig.add_subplot(gs[3, 2])
        draw_lineup(ax_l_away, away_nodes, STYLE['away'])

        plt.tight_layout()
        return fig

# --- FONCTION PRINCIPALE ---

def main():
    st.title("⚽ Premier League Dashboard 2025-2026")
    st.markdown("---")

    # --- SIDEBAR ---
    st.sidebar.header("Options de Configuration")
    mode = st.sidebar.radio("Mode de Sélection", ["📅 Calendrier / Journées", "🌐 URL Personnalisée"])

    selected_match_data = None
    needs_download = False
    
    # 1. Sélection via Calendrier
    if mode == "📅 Calendrier / Journées":
        matches = load_match_list()
        
        if not matches:
            st.error(f"Fichier '{URLS_FILE}' introuvable ou vide.")
        else:
            df_matches = pd.DataFrame(matches)
            gameweeks = sorted(df_matches['gameweek'].unique())
            
            sel_gw = st.sidebar.selectbox("Choisir la Journée (GW)", gameweeks)
            
            # Filtre les matchs de la journée
            gw_matches = df_matches[df_matches['gameweek'] == sel_gw]
            
            # === CORRECTION MAJEURE ===
            # Création d'un dictionnaire d'options avec les données converties en dict
            match_options = {
                f"{r['title']} (Match #{r['id']})": r.to_dict() 
                for _, r in gw_matches.iterrows()
            }
            
            sel_match_key = st.sidebar.selectbox("Choisir le Match", list(match_options.keys()))
            selected_match_data = match_options[sel_match_key]
            
            # Vérif locale
            file_path = os.path.join(DATA_FOLDER, selected_match_data['filename'])
            if os.path.exists(file_path):
                st.sidebar.success("✅ Match disponible en local")
                needs_download = False
            else:
                st.sidebar.warning("☁️ Match en ligne (non téléchargé)")
                needs_download = True

    # 2. Sélection via URL
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
                    st.sidebar.success("✅ Match disponible en local")
                    needs_download = False
                else:
                    needs_download = True
            else:
                st.sidebar.error("URL invalide. Doit contenir '/matches/ID/'")

    # 3. Actions et Affichage
    if selected_match_data is not None:
        st.header(f"{selected_match_data['title']}")
        
        if needs_download:
            st.info(f"Le match {selected_match_data['id']} n'est pas encore téléchargé.")
            if st.button("🚀 Télécharger et Analyser maintenant", type="primary"):
                downloader = StreamlitDownloader()
                success = downloader.download_match(selected_match_data['url'], selected_match_data['filename'])
                if success:
                    st.success("Téléchargement réussi ! Rafraîchissement...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Échec du téléchargement.")
        else:
            # Analyse si le fichier est présent
            file_path = os.path.join(DATA_FOLDER, selected_match_data['filename'])
            
            try:
                parser = MatchParser(file_path)
                mc, match_info, teams, logos = parser.get_all_data()
                
                engine = PassNetworkEngine()
                events, players = engine.process(mc)
                
                home_net, home_nodes = engine.get_network(teams['home']['id'], events, players)
                away_net, away_nodes = engine.get_network(teams['away']['id'], events, players)
                
                # Onglets
                tab1, tab2 = st.tabs(["📊 Pass Network", "📈 Stats Joueurs"])
                
                with tab1:
                    with st.spinner("Génération de la visualisation..."):
                        viz = DashboardVisualizer()
                        fig = viz.create_dashboard(
                            match_info, teams, 
                            home_net, home_nodes, 
                            away_net, away_nodes, 
                            logos.get(0), logos.get(1)
                        )
                        st.pyplot(fig)
                        
                        # Bouton téléchargement image
                        buf = BytesIO()
                        fig.savefig(buf, format="png", facecolor='#0E1117', bbox_inches='tight')
                        st.download_button(
                            label="💾 Télécharger l'image HD",
                            data=buf.getvalue(),
                            file_name=f"PassNetwork_{selected_match_data['id']}.png",
                            mime="image/png"
                        )
                        plt.close(fig)

                with tab2:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"Joueurs - {teams['home']['name']}")
                        if not home_nodes.empty:
                            st.dataframe(home_nodes[['name', 'shirtNo', 'count', 'position']].sort_values('count', ascending=False), hide_index=True)
                    with col2:
                        st.subheader(f"Joueurs - {teams['away']['name']}")
                        if not away_nodes.empty:
                            st.dataframe(away_nodes[['name', 'shirtNo', 'count', 'position']].sort_values('count', ascending=False), hide_index=True)

            except Exception as e:
                st.error(f"Erreur lors de l'analyse du fichier : {e}")
                st.warning("Le fichier HTML est peut-être incomplet ou corrompu.")
    else:
        st.info("👈 Veuillez sélectionner un match dans la barre latérale.")

if __name__ == "__main__":
    main()
