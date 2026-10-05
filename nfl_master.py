import streamlit as st
import pandas as pd
import nfl_data_py as nfl
import inspect


def _stretch(fn):
    """Streamlit 버전에 맞는 '가로 꽉 채우기' 인자 반환 (use_container_width 폐지 대응)"""
    try:
        if 'width' in inspect.signature(fn).parameters:
            return {'width': 'stretch'}
    except (TypeError, ValueError):
        pass
    return {'use_container_width': True}

# ==========================================
# 페이지 기본 세팅 및 다크 테마 / 행별 카드 박스 CSS 주입
# ==========================================
st.set_page_config(page_title="NFL 전력 분석 대시보드", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* 전체 배경 강제 다크모드 */
    .stApp { background-color: #0E1117 !important; color: #FAFAFA !important; }
    
    /* 상단 연도/주차 셀렉트박스 강제 다크 테마화 */
    div[data-testid="stSelectbox"] label p { color: #FAFAFA !important; font-size: 15px !important; font-weight: bold !important; }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div { background-color: #1E1E1E !important; color: #FAFAFA !important; border: 1px solid #444 !important; }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] span { color: #FAFAFA !important; }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] svg { fill: #FAFAFA !important; }

    /* ==========================================
       1. 매치업 선택 카드 UI (독립된 카드 전체 클릭 방식)
       ========================================== */
    /* 매치업 버튼 자체를 60px짜리 거대한 카드 형태로 스타일링 */
    div[data-testid="stColumn"] div[data-testid="stButton"] > button {
        height: 60px !important;
        background-color: #1E1E1E !important;
        border: 1px solid #333 !important;
        border-radius: 10px !important;
        transition: 0.2s !important;
        padding: 0 !important;
        position: relative;
        z-index: 1; /* 로고 뒤에 위치하지만 클릭 이벤트는 받음 */
    }
    
    /* 카드에 마우스 오버 시 하이라이트 효과 */
    div[data-testid="stColumn"] div[data-testid="stButton"] > button:hover {
        border-color: #28a745 !important;
        background-color: #252830 !important;
        box-shadow: 0 4px 10px rgba(40, 167, 69, 0.4) !important;
    }
    
    /* 버튼 내부의 텍스트(투명문자)는 공간을 차지하지 않도록 완전 삭제 */
    div[data-testid="stColumn"] div[data-testid="stButton"] p {
        display: none !important; 
    }

    /* ==========================================
       2. 하단 스탯 행 (Basic Stats 등) 뚜렷한 카드화
       ========================================== */
    /* 행 카드: render_stat이 st.container(key="statrow-N")로 만든 컨테이너를 클래스(st-key-statrow*)로 지정.
       (data-testid는 Streamlit 버전마다 바뀌어서 사용하지 않음 / :not(:has()) 는 같은 클래스가 겹쳐 붙어도 한 번만 적용되게 함)
       행 간격 = Streamlit 기본 gap(1rem) + margin-bottom(-0.5rem) = 약 0.5rem. 더 좁히려면 -0.5rem을 더 작게(-0.7rem) */
    div[class*="st-key-statrow"]:not(:has(div[class*="st-key-statrow"])) {
        box-sizing: border-box;
        border-radius: 12px;
        background-color: #161922;
        border: 1px solid #2C313C;
        padding: 0.45rem 1rem;
        margin-bottom: -0.5rem;
        box-shadow: 0 3px 5px rgba(0, 0, 0, 0.35);
        transition: background-color 0.2s ease-in-out, border-color 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    div[class*="st-key-statrow"]:not(:has(div[class*="st-key-statrow"])):hover {
        background-color: #1B1E28;
        border-color: #28a745;
        box-shadow: 0 5px 10px rgba(40, 167, 69, 0.15);
    }

    /* ==========================================
       3. 팝업창 버튼 및 본체 스타일링
       ========================================== */
    div[data-testid="stPopover"] button {
        background-color: transparent !important; border: none !important; box-shadow: none !important;
        padding: 0 !important; display: block !important; width: 100%; color: transparent !important; margin-top: 0 !important;
    }
    div[data-testid="stPopover"] button:hover, div[data-testid="stPopover"] button:active, div[data-testid="stPopover"] button:focus {
        background-color: transparent !important; border: none !important; box-shadow: none !important; color: transparent !important;
    }
    div[data-testid="stPopover"] button svg { display: none !important; opacity: 0 !important; width: 0 !important; height: 0 !important; }
    div[data-testid="stPopover"] button p {
        color: #EEE !important; font-size: 15px !important; font-weight: bold !important; margin: 0 !important; text-align: center !important;
    }
    div[data-testid="stPopover"] button:hover p { color: #28a745 !important; }
    div[data-testid="stPopoverBody"] { background-color: #1E1E1E !important; border: 1px solid #444 !important; color: #FAFAFA !important; }

    /* ==========================================
       4. 섹션 이동 핸들 (st.segmented_control)
       - 버전별 testid 차이를 대비해 선택 상태는 여러 셀렉터를 함께 지정
       ========================================== */
    div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"] {
        background-color: #1E1E1E !important; border: 1px solid #333 !important; color: #CCC !important;
    }
    div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"] p { color: #CCC !important; font-weight: bold !important; }
    div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"]:hover { border-color: #28a745 !important; }
    div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"],
    div[data-testid="stButtonGroup"] button[aria-checked="true"],
    div[data-testid="stButtonGroup"] button[aria-pressed="true"] {
        background-color: #28a745 !important; border: 1px solid #28a745 !important; color: #FFFFFF !important;
    }
    div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] p,
    div[data-testid="stButtonGroup"] button[aria-checked="true"] p,
    div[data-testid="stButtonGroup"] button[aria-pressed="true"] p { color: #FFFFFF !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 0-0단계: 팀 로고 데이터 로드
# ==========================================
@st.cache_data(ttl=3600*24)
def load_team_logos():
    desc = nfl.import_team_desc()
    return desc[['team_abbr', 'team_logo_espn', 'team_color']].set_index('team_abbr').to_dict('index')

try:
    team_logos = load_team_logos()
except Exception:
    team_logos = {}  # 실패 결과는 캐시되지 않으므로 다음 실행 때 재시도됨

# ==========================================
# 0-1단계: 스케줄 로드
# ==========================================
@st.cache_data(ttl=600)
def load_schedule(year):
    return nfl.import_schedules([year])


def get_schedule(year):
    try:
        return load_schedule(year)
    except Exception:
        return pd.DataFrame()

# ==========================================
# 0-2단계: 연도별 데이터 로드 및 마스터 엔진 
# ==========================================
DIVISION_DICT = {
    'WAS': ('NFC', '동부'), 'DAL': ('NFC', '동부'), 'PHI': ('NFC', '동부'), 'NYG': ('NFC', '동부'),
    'SF': ('NFC', '서부'), 'SEA': ('NFC', '서부'), 'LAR': ('NFC', '서부'), 'LA': ('NFC', '서부'), 'ARI': ('NFC', '서부'),
    'GB': ('NFC', '북부'), 'MIN': ('NFC', '북부'), 'CHI': ('NFC', '북부'), 'DET': ('NFC', '북부'),
    'TB': ('NFC', '남부'), 'NO': ('NFC', '남부'), 'ATL': ('NFC', '남부'), 'CAR': ('NFC', '남부'),
    'BUF': ('AFC', '동부'), 'MIA': ('AFC', '동부'), 'NE': ('AFC', '동부'), 'NYJ': ('AFC', '동부'),
    'KC': ('AFC', '서부'), 'LAC': ('AFC', '서부'), 'DEN': ('AFC', '서부'), 'LV': ('AFC', '서부'),
    'BAL': ('AFC', '북부'), 'CIN': ('AFC', '북부'), 'CLE': ('AFC', '북부'), 'PIT': ('AFC', '북부'),
    'HOU': ('AFC', '남부'), 'IND': ('AFC', '남부'), 'JAX': ('AFC', '남부'), 'TEN': ('AFC', '남부')
}

@st.cache_data(ttl=3600)
def load_and_calculate_stats(year):
    url = f"https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{year}.csv.gz"
    pbp = pd.read_csv(url, compression='gzip', low_memory=False)
    if 'season_type' in pbp.columns:
        pbp = pbp[pbp['season_type'] == 'REG'].copy()  # 플레이오프 제외
    pbp_clean = pbp[pbp['play_type'].isin(['pass', 'run'])].copy()
    
    sched = get_schedule(year)
    if not sched.empty and 'game_type' in sched.columns:
        sched = sched[sched['game_type'] == 'REG']  # 플레이오프 제외
    sched = sched.dropna(subset=['home_score', 'away_score']) if not sched.empty else pd.DataFrame()
        
    teams = [t for t in pbp_clean['posteam'].dropna().unique() if isinstance(t, str)]
    team_data_list = []
    
    for team_abbr in teams:
        wins = losses = ties = pf = pa = 0
        if not sched.empty:
            home_games = sched[sched['home_team'] == team_abbr]
            away_games = sched[sched['away_team'] == team_abbr]
            wins += len(home_games[home_games['home_score'] > home_games['away_score']])
            losses += len(home_games[home_games['home_score'] < home_games['away_score']])
            ties += len(home_games[home_games['home_score'] == home_games['away_score']])
            pf += home_games['home_score'].sum()
            pa += home_games['away_score'].sum()
            wins += len(away_games[away_games['away_score'] > away_games['home_score']])
            losses += len(away_games[away_games['away_score'] < away_games['home_score']])
            ties += len(away_games[away_games['away_score'] == away_games['home_score']])
            pf += away_games['away_score'].sum()
            pa += away_games['home_score'].sum()
            
        total_games = wins + losses + ties
        if total_games == 0:
            record_str, win_pct, avg_pf, avg_pa = "0승 0패", 0.5, 0.0, 0.0
        else:
            record_str = f"{wins}승 {losses}패" if ties == 0 else f"{wins}승 {losses}패 {ties}무"
            win_pct = (wins + (ties * 0.5)) / total_games
            avg_pf = float(pf / total_games)
            avg_pa = float(pa / total_games)

        offense = pbp_clean[pbp_clean['posteam'] == team_abbr]
        defense = pbp_clean[pbp_clean['defteam'] == team_abbr]
        games_played = offense['game_id'].nunique()
        if games_played == 0: games_played = 1
        
        team_penalties = pbp[pbp['penalty_team'] == team_abbr]
        penalties_cnt = float(team_penalties['penalty'].sum() / games_played)
        penalties_yds = float(team_penalties['penalty_yards'].sum() / games_played)
        
        giveaways = int(offense['interception'].sum() + offense['fumble_lost'].sum())
        takeaways = int(defense['interception'].sum() + defense['fumble_lost'].sum())
        to_margin = takeaways - giveaways
        
        off_pass = offense[offense['play_type'] == 'pass']
        off_run = offense[offense['play_type'] == 'run']
        def_pass = defense[defense['play_type'] == 'pass']
        def_run = defense[defense['play_type'] == 'run']
        
        pass_yds = off_pass['yards_gained'].sum() / games_played
        run_yds = off_run['yards_gained'].sum() / games_played
        tot_yds = pass_yds + run_yds
        pass_tds_tot = int(offense['pass_touchdown'].sum())
        run_tds_tot = int(offense['rush_touchdown'].sum())
        pass_tds = pass_tds_tot / games_played
        run_tds = run_tds_tot / games_played
        
        def_pass_yds = def_pass['yards_gained'].sum() / games_played
        def_run_yds = def_run['yards_gained'].sum() / games_played
        def_tot_yds = def_pass_yds + def_run_yds
        def_pass_tds_tot = int(defense['pass_touchdown'].sum())
        def_run_tds_tot = int(defense['rush_touchdown'].sum())
        def_pass_tds = def_pass_tds_tot / games_played
        def_run_tds = def_run_tds_tot / games_played
        
        def_tds_tot = int(defense[defense['td_team'] == team_abbr]['touchdown'].sum())
        def_tds = def_tds_tot / games_played
        st_plays = pbp[(pbp['td_team'] == team_abbr) & (pbp['play_type'].isin(['punt', 'kickoff', 'field_goal']))]
        st_tds_tot = int(st_plays['touchdown'].sum())
        st_tds = st_tds_tot / games_played
        
        off_epa = float(offense['epa'].mean()) if not offense.empty else 0.0
        def_epa = float(defense['epa'].mean()) if not defense.empty else 0.0
        pass_success = float(off_pass['success'].mean() * 100) if not off_pass.empty else 0.0
        run_success = float(off_run['success'].mean() * 100) if not off_run.empty else 0.0
        pass_ratio = float(len(off_pass) / len(offense) * 100) if len(offense) > 0 else 0.0
        run_ratio = float(len(off_run) / len(offense) * 100) if len(offense) > 0 else 0.0
        
        # 다운 컨버전은 nflverse의 converted/failed 컬럼 사용 (EPA 기반 'success'와 다름)
        def _conv(df, kind):
            conv = int(df[f'{kind}_down_converted'].sum())
            fail = int(df[f'{kind}_down_failed'].sum())
            return conv, conv + fail

        off_3rd_succ, off_3rd_att = _conv(offense, 'third')
        off_4th_succ, off_4th_att = _conv(offense, 'fourth')
        def_3rd_allowed, def_3rd_att = _conv(defense, 'third')
        def_4th_allowed, def_4th_att = _conv(defense, 'fourth')
        def_3rd_stop_cnt = def_3rd_att - def_3rd_allowed
        def_4th_stop_cnt = def_4th_att - def_4th_allowed

        off_3rd_success = float(off_3rd_succ / off_3rd_att * 100) if off_3rd_att > 0 else 0.0
        off_4th_success = float(off_4th_succ / off_4th_att * 100) if off_4th_att > 0 else 0.0
        def_3rd_stop = float(def_3rd_stop_cnt / def_3rd_att * 100) if def_3rd_att > 0 else 0.0
        def_4th_stop = float(def_4th_stop_cnt / def_4th_att * 100) if def_4th_att > 0 else 0.0
        
        def _drive_count(df):
            # drive 번호는 경기 안에서만 유니크 -> (game_id, drive) 쌍으로 계산
            return df.dropna(subset=['drive'])[['game_id', 'drive']].drop_duplicates().shape[0]

        rz_off = offense[offense['yardline_100'] <= 20]
        rz_off_drives = _drive_count(rz_off)
        rz_off_td_drives = _drive_count(rz_off[rz_off['td_team'] == team_abbr])  # 공격팀 본인이 넣은 TD만
        rz_off_pct = float(rz_off_td_drives / rz_off_drives * 100) if rz_off_drives > 0 else 0.0

        rz_def = defense[defense['yardline_100'] <= 20]
        rz_def_drives = _drive_count(rz_def)
        rz_def_td_drives = _drive_count(rz_def[rz_def['td_team'] == rz_def['posteam']])  # 상대 공격팀이 넣은 TD만 (수비 TD 제외)
        rz_def_pct = float(rz_def_td_drives / rz_def_drives * 100) if rz_def_drives > 0 else 0.0
        
        qb_stat = off_pass['epa'].mean() if not off_pass.empty else 0
        rb_stat = off_run['epa'].mean() if not off_run.empty else 0
        wr_df = off_pass[off_pass['pass_location'].isin(['left', 'right'])]
        wr_stat = wr_df['epa'].mean() if not wr_df.empty else 0
        te_df = off_pass[off_pass['pass_location'] == 'middle']
        te_stat = te_df['epa'].mean() if not te_df.empty else 0
        ol_stat = ((off_pass['sack'] + off_pass['qb_hit']).clip(upper=1)).mean() if not off_pass.empty else 0
        dl_stat = ((def_pass['sack'] + def_pass['qb_hit']).clip(upper=1)).mean() if not def_pass.empty else 0
        sec_stat = def_pass['epa'].mean() if not def_pass.empty else 0
        lb_stat = def_run['epa'].mean() if not def_run.empty else 0
        
        team_data_list.append({
            'team': team_abbr,
            'record_str': record_str, 'win_pct': win_pct, 'avg_pf': avg_pf, 'avg_pa': avg_pa,
            'tot_yds': tot_yds, 'def_tot_yds': def_tot_yds, 
            'to_margin': to_margin, 'takeaways': takeaways, 'giveaways': giveaways,
            'penalties_cnt': penalties_cnt, 'penalties_yds': penalties_yds,
            'pass_yds': pass_yds, 'def_pass_yds': def_pass_yds, 
            'pass_tds': pass_tds, 'pass_tds_tot': pass_tds_tot, 'def_pass_tds': def_pass_tds, 'def_pass_tds_tot': def_pass_tds_tot,
            'run_yds': run_yds, 'def_run_yds': def_run_yds, 
            'run_tds': run_tds, 'run_tds_tot': run_tds_tot, 'def_run_tds': def_run_tds, 'def_run_tds_tot': def_run_tds_tot,
            'def_tds': def_tds, 'def_tds_tot': def_tds_tot, 'st_tds': st_tds, 'st_tds_tot': st_tds_tot,
            'off_epa': off_epa, 'def_epa': def_epa,
            'pass_success': pass_success, 'run_success': run_success, 'pass_ratio': pass_ratio, 'run_ratio': run_ratio,
            'off_3rd_success': off_3rd_success, 'def_3rd_stop': def_3rd_stop,
            'off_4th_success': off_4th_success, 'def_4th_stop': def_4th_stop,
            'off_3rd_att': off_3rd_att, 'off_3rd_succ': off_3rd_succ,
            'off_4th_att': off_4th_att, 'off_4th_succ': off_4th_succ,
            'def_3rd_att': def_3rd_att, 'def_3rd_stop_cnt': def_3rd_stop_cnt,
            'def_4th_att': def_4th_att, 'def_4th_stop_cnt': def_4th_stop_cnt,
            'rz_off_pct': rz_off_pct, 'rz_off_drives': rz_off_drives, 'rz_off_td_drives': rz_off_td_drives,
            'rz_def_pct': rz_def_pct, 'rz_def_drives': rz_def_drives, 'rz_def_td_drives': rz_def_td_drives,
            'qb': qb_stat, 'rb': rb_stat, 'wr': wr_stat, 'te': te_stat,
            'ol': ol_stat, 'dl': dl_stat, 'lb': lb_stat, 'sec': sec_stat
        })
        
    df = pd.DataFrame(team_data_list).set_index('team')
    
    desc_cols = ['avg_pf', 'tot_yds', 'to_margin', 'pass_yds', 'pass_tds', 'run_yds', 'run_tds', 
                 'def_tds', 'st_tds', 'off_epa', 'pass_success', 'run_success', 'pass_ratio', 'run_ratio', 
                 'off_3rd_success', 'def_3rd_stop', 'off_4th_success', 'def_4th_stop', 'rz_off_pct',
                 'qb', 'rb', 'wr', 'te', 'dl']
    asc_cols = ['avg_pa', 'def_tot_yds', 'def_pass_yds', 'def_pass_tds', 'def_run_yds', 'def_run_tds', 
                'def_epa', 'penalties_cnt', 'penalties_yds', 'rz_def_pct', 'ol', 'lb', 'sec']
    
    for col in desc_cols:
        df[f'{col}_rank'] = df[col].rank(ascending=False, method='min').fillna(len(df)).astype(int)
    for col in asc_cols:
        df[f'{col}_rank'] = df[col].rank(ascending=True, method='min').fillna(len(df)).astype(int)
        
    df['conf'] = df.index.map(lambda x: DIVISION_DICT.get(x, ('', ''))[0])
    df['div'] = df.index.map(lambda x: DIVISION_DICT.get(x, ('', ''))[1])
    df['div_rank'] = df.groupby(['conf', 'div'])['win_pct'].rank(ascending=False, method='min').astype(int)
        
    return df

# ==========================================
# 레이아웃 1. 상단 컨트롤
# ==========================================
st.markdown("<h1 style='text-align: center; color: #FAFAFA; font-weight: 800; font-size: 40px; margin-top: -30px;'>🏈 NFL Advanced Analytics</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888; font-size: 14px; margin-bottom: 30px; letter-spacing: 1px;'>Powered by nflverse</p>", unsafe_allow_html=True)

ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1, 1, 1, 1])
with ctrl_col2:
    selected_year = st.selectbox("🗓️ 시즌 (Year)", [2026, 2025, 2024], index=0)

sched_df = get_schedule(selected_year)
if not sched_df.empty:
    available_weeks = sorted(sched_df['week'].dropna().astype(int).unique())
else:
    available_weeks = [1]
    
with ctrl_col3:
    selected_week = st.selectbox("🏆 주차 (Week)", available_weeks, index=0)

if 'current_year' not in st.session_state or st.session_state['current_year'] != selected_year:
    st.session_state['current_year'] = selected_year
    st.session_state['selected_matchup'] = None
if 'current_week' not in st.session_state or st.session_state['current_week'] != selected_week:
    st.session_state['current_week'] = selected_week
    st.session_state['selected_matchup'] = None

st.divider()

# ==========================================
# 매치업 카드 오버레이 HTML (종료된 경기는 점수 표시)
# ==========================================
# 오버레이 세로 위치 보정값(px). 스크린샷 실측 기준 기존 -76px에서 약 9px 아래로 쳐져 있어 -85px로 보정.
# 그래도 위/아래로 어긋나 보이면 이 값만 1~2px씩 조절하세요. (더 작게(-87) = 위로, 더 크게(-83) = 아래로)
CARD_OVERLAY_OFFSET = -85
WEEKDAY_KO = ['월', '화', '수', '목', '금', '토', '일']

def schedule_label(row):
    """미진행 경기 카드 하단용 일정 문구. 예: '10/12(일) 13:00 ET' (정보가 없으면 빈 문자열)"""
    gd, gt = row.get('gameday'), row.get('gametime')
    if pd.isna(gd):
        return ""
    try:
        d = pd.to_datetime(gd)
    except Exception:
        return ""
    label = f"{d.month}/{d.day}({WEEKDAY_KO[d.weekday()]})"
    if pd.notna(gt) and str(gt).strip():
        label += f" {str(gt).strip()[:5]} ET"
    return label

def matchup_card_html(row, away_logo, home_logo):
    a_score, h_score = row.get('away_score'), row.get('home_score')
    score_a = score_h = footer = ""
    footer_text = ""

    if pd.notna(a_score) and pd.notna(h_score):
        # 종료된 경기: 점수 + FINAL
        a, h = int(a_score), int(h_score)
        a_col, a_wt = ("#FFFFFF", 800) if a >= h else ("#9AA0A6", 600)
        h_col, h_wt = ("#FFFFFF", 800) if h >= a else ("#9AA0A6", 600)
        score_a = f"<span style='font-size:20px;font-weight:{a_wt};color:{a_col};margin:0 8px 0 10px;'>{a}</span>"
        score_h = f"<span style='font-size:20px;font-weight:{h_wt};color:{h_col};margin:0 10px 0 8px;'>{h}</span>"
        ot = row.get('overtime')
        footer_text = "FINAL/OT" if pd.notna(ot) and int(ot) == 1 else "FINAL"
    else:
        # 아직 진행되지 않은 경기: 하단에 일정
        footer_text = schedule_label(row)

    # 하단 문구가 있으면 그 공간만큼 로고/점수 줄을 위로 올림 (없으면 카드 정중앙)
    pad_bottom = 10 if footer_text else 0
    if footer_text:
        footer = f"<div style='position:absolute;bottom:3px;left:0;right:0;text-align:center;font-size:10px;font-weight:600;letter-spacing:0.5px;color:#8B8F98;'>{footer_text}</div>"

    # 주의: HTML 안에 빈 줄이 생기면 마크다운이 블록을 끊을 수 있어서 한 줄로 이어 붙임
    return (
        f"<div style='pointer-events:none; margin-top:{CARD_OVERLAY_OFFSET}px; height:60px; box-sizing:border-box; "
        f"padding-bottom:{pad_bottom}px; display:flex; align-items:center; justify-content:center; "
        "position:relative; z-index:10;'>"
        f"<img src='{away_logo}' width='32'>{score_a}"
        "<span style='font-size:13px;font-weight:bold;color:#777;margin:0 4px;'>@</span>"
        f"{score_h}<img src='{home_logo}' width='32'>{footer}"
        "</div>"
    )

# ==========================================
# 레이아웃 2. 매치업 선택 카드 그리드 (버그 완벽 수정본)
# ==========================================
st.markdown(f"<h3 style='text-align: center; color: #CCC; margin-bottom: 30px;'>{selected_year} Season - Week {selected_week} Matchups</h3>", unsafe_allow_html=True)

if not sched_df.empty:
    week_games = sched_df[sched_df['week'] == selected_week].reset_index(drop=True)
    if not week_games.empty:
        # 8열(2줄) 콤팩트 배치
        cols = st.columns(8)
        for i, row in week_games.iterrows():
            away, home = row['away_team'], row['home_team']
            away_logo = team_logos.get(away, {}).get('team_logo_espn', '')
            home_logo = team_logos.get(home, {}).get('team_logo_espn', '')
            
            with cols[i % 8]:
                # 1. 뼈대가 되는 진짜 '클릭 버튼' 렌더링 (CSS를 통해 60px 카드로 형태 변환 완료)
                if st.button(" ", key=f"btn_{away}_{home}", **_stretch(st.button)):
                    st.session_state['selected_matchup'] = f"{away} @ {home}"
                
                # 2. 버튼 위에 로고(+종료된 경기는 점수)를 끌어올려서 덮어쓰기
                st.markdown(matchup_card_html(row, away_logo, home_logo), unsafe_allow_html=True)
                    
        if st.session_state['selected_matchup'] is None:
            st.session_state['selected_matchup'] = f"{week_games.iloc[0]['away_team']} @ {week_games.iloc[0]['home_team']}"
            
        away_team, home_team = st.session_state['selected_matchup'].split(" @ ")
    else:
        st.warning(f"{selected_year} 시즌 {selected_week}주차에 예정된 경기가 없습니다.")
        st.stop()
else:
    st.error("스케줄 데이터를 불러올 수 없습니다.")
    st.stop()

st.divider()

# ==========================================
# 레이아웃 3. 대형 팀 로고 헤더 & 경기 정보
# ==========================================
matchup_info = sched_df[(sched_df['week'] == selected_week) & (sched_df['away_team'] == away_team) & (sched_df['home_team'] == home_team)]
if not matchup_info.empty:
    stadium_name = matchup_info.iloc[0].get('stadium', 'TBD')
    gameday = matchup_info.iloc[0].get('gameday', 'TBD')
    gametime = matchup_info.iloc[0].get('gametime', 'TBD')
    st.markdown(f"<div style='text-align: center; color: #CCC; font-size: 32px; font-weight: bold; margin-bottom: 30px; letter-spacing: 1.5px;'>🏟️ {stadium_name} &nbsp; | &nbsp; ⏰ {gameday} {gametime} (ET)</div>", unsafe_allow_html=True)

away_logo_hd = team_logos.get(away_team, {}).get('team_logo_espn', '')
home_logo_hd = team_logos.get(home_team, {}).get('team_logo_espn', '')

logo_col1, logo_col2, logo_col3 = st.columns([1, 0.2, 1])
with logo_col1:
    st.markdown(f"<div style='text-align: right;'><img src='{away_logo_hd}' width='180'></div>", unsafe_allow_html=True)
with logo_col2:
    st.markdown("<h1 style='text-align: center; margin-top: 60px; color: #888;'>@</h1>", unsafe_allow_html=True)
with logo_col3:
    st.markdown(f"<div style='text-align: left;'><img src='{home_logo_hd}' width='180'></div>", unsafe_allow_html=True)

with st.spinner(f'{selected_year} 시즌 전체 리그 데이터를 불러오고 있습니다...'):
    try:
        full_df = load_and_calculate_stats(selected_year)
    except Exception as e:
        st.error(f"{selected_year} 시즌 play-by-play 데이터를 불러오지 못했습니다. (시즌 데이터가 아직 없거나 네트워크 오류) / {e}")
        st.stop()
    
    missing = [t for t in (away_team, home_team) if t not in full_df.index]
    away_data = full_df.loc[away_team].to_dict() if away_team in full_df.index else {}
    home_data = full_df.loc[home_team].to_dict() if home_team in full_df.index else {}
    if missing:
        st.warning(f"{', '.join(missing)} 팀의 {selected_year} 시즌 데이터가 아직 없습니다. 해당 팀 수치는 0 또는 '-'로 표시됩니다.")

# ==========================================
# 팝업 및 카드박스 렌더링 헬퍼 함수
# ==========================================
_row_counter = [0]  # 스크립트가 재실행될 때마다 0으로 초기화됨 -> 행 키가 매번 같은 순서로 부여됨

def _row_container():
    """스탯 한 행을 담는 컨테이너. key를 주면 st-key-statrow-N 클래스가 붙어 CSS로 카드 스타일링 가능."""
    _row_counter[0] += 1
    try:
        return st.container(key=f"statrow-{_row_counter[0]}")
    except TypeError:  # key를 지원하지 않는 구버전 -> 기본 테두리 컨테이너로 대체
        return st.container(border=True)

def render_stat(label, away_val, away_str, away_rank_str, home_val, home_str, home_rank_str, higher_is_better=True, is_percent=False, stat_key=None):
    if pd.isna(away_val) or pd.isna(home_val):
        color_a = color_h = "#888888"
    elif away_val == home_val or higher_is_better is None:
        color_a = color_h = "#888888"
    elif (away_val > home_val and higher_is_better) or (away_val < home_val and not higher_is_better):
        color_a = "#28a745"
        color_h = "#dc3545"
    else:
        color_a = "#dc3545" 
        color_h = "#28a745" 
        
    def build_html(val, string, rank_str, color):
        html = f"<div style='text-align: center;'>"
        html += f"<span style='font-size: 20px; font-weight: bold; color: {color};'>{string}</span>"
        if rank_str and not pd.isna(val):
            html += f" <span style='font-size: 13px; color: #AAAAAA;'>({rank_str})</span>" 
        if is_percent and not pd.isna(val):
            bar_width = min(max(val, 0), 100)
            html += f"<div style='width: 100%; background-color: #333; border-radius: 4px; margin-top: 5px; height: 6px;'>"
            html += f"<div style='width: {bar_width}%; background-color: {color}; height: 6px; border-radius: 4px;'></div>"
            html += f"</div>"
        html += "</div>"
        return html
        
    with _row_container():
        col1, col2, col3 = st.columns([1, 1.2, 1], vertical_alignment="center")
        with col1:
            st.markdown(build_html(away_val, away_str, away_rank_str, color_a), unsafe_allow_html=True)
        with col2:
            if stat_key:
                with st.popover(label, **_stretch(st.popover)):
                    html_content = "<div style='background-color: #1E1E1E; padding: 20px; border-radius: 10px; color: #FAFAFA;'>"
                    if stat_key == 'record':
                        html_content += f"<h3 style='text-align:center; margin-top:0; color: #FAFAFA;'>🏆 {selected_year} NFL 지구별 전체 순위</h3>"
                        for conf in ['AFC', 'NFC']:
                            html_content += f"<h4 style='color:#28a745; border-bottom: 2px solid #444; padding-bottom: 5px; margin-top: 20px;'>{conf}</h4>"
                            html_content += "<div style='display: flex; justify-content: space-between; gap: 10px;'>"
                            divs = ['동부', '서부', '남부', '북부']
                            for div in divs:
                                html_content += "<div style='flex: 1; min-width: 0;'>"
                                html_content += f"<div style='color:#AAA; font-size:14px; font-weight:bold; margin-bottom:10px;'>{div}</div>"
                                div_df = full_df[(full_df['conf'] == conf) & (full_df['div'] == div)].sort_values(by=['win_pct', 'avg_pf'], ascending=[False, False])
                                for idx, row in div_df.iterrows():
                                    text_color = "#28a745" if idx in [away_team, home_team] else "#FAFAFA"
                                    html_content += f"<div style='font-size:14px; margin-bottom:6px; color:{text_color}; white-space: nowrap;'><b>{idx}</b> &nbsp; <span style='color:#888;'>{row['record_str']}</span></div>"
                                html_content += "</div>"
                            html_content += "</div>"
                    else:
                        html_content += f"<h4 style='text-align:center; color:#FAFAFA; margin-top:0;'>📊 {label} (전체 순위)</h4>"
                        rank_col = f"{stat_key}_rank"
                        sorted_df = full_df.sort_values(by=[rank_col, 'win_pct'], ascending=[True, False])
                        
                        html_content += "<table style='width:100%; text-align:center; font-size:15px; border-collapse: collapse; color:#FAFAFA;'>"
                        html_content += "<tr style='border-bottom: 2px solid #555;'><th style='padding:8px;'>순위</th><th>팀</th><th>수치</th></tr>"
                        for _, row in sorted_df.iterrows():
                            team = row.name
                            rank = int(row[rank_col])
                            val = row[stat_key]
                            
                            if is_percent: val_str = f"{val:.1f}%"
                            elif 'margin' in stat_key: val_str = f"{int(val):+d}"
                            elif stat_key in ('ol', 'dl'): val_str = f"{val * 100:.1f}%"
                            elif 'epa' in stat_key or stat_key in ('qb', 'rb', 'wr', 'te', 'lb', 'sec'): val_str = f"{val:+.3f}"
                            elif 'tds' in stat_key: val_str = f"{val:.1f}개"
                            elif float(val).is_integer(): val_str = f"{int(val)}"
                            else: val_str = f"{val:.1f}"
                            
                            bg_color = "rgba(40, 167, 69, 0.15)" if team in [away_team, home_team] else "transparent"
                            text_color = "#28a745" if team in [away_team, home_team] else "#FAFAFA"
                            
                            html_content += f"<tr style='background-color: {bg_color}; border-bottom: 1px solid #333;'>"
                            html_content += f"<td style='padding:8px;'>{rank}</td><td style='font-weight:bold; color:{text_color};'>{team}</td><td>{val_str}</td>"
                            html_content += "</tr>"
                        html_content += "</table>"
                    html_content += "</div>"
                    st.markdown(html_content, unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align: center; font-weight: bold; font-size: 15px; color: #EEE;'>{label}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(build_html(home_val, home_str, home_rank_str, color_h), unsafe_allow_html=True)

# ==========================================
# 하단 UI 렌더링 
# ==========================================
SECTIONS = ["📌 Basic", "⚔️ 공수 상세", "📊 성향·성공률", "🛡 유닛 순위"]

def _seg_width_kwargs():
    try:
        if 'width' in inspect.signature(st.segmented_control).parameters:
            return {'width': 'stretch'}
    except (TypeError, ValueError, AttributeError):
        pass
    return {}

def section_nav(options, key):
    """섹션 이동 핸들. segmented_control 미지원(구버전)이면 가로 라디오로 대체."""
    if hasattr(st, "segmented_control"):
        return st.segmented_control("섹션", options, default=options[0], key=key,
                                    label_visibility="collapsed", **_seg_width_kwargs())
    return st.radio("섹션", options, horizontal=True, key=key, label_visibility="collapsed")

_choice = section_nav(SECTIONS, key="active_section")
if _choice:  # 같은 버튼을 다시 눌러 선택이 해제(None)돼도 마지막 섹션을 유지
    st.session_state['_last_section'] = _choice
section = st.session_state.get('_last_section', SECTIONS[0])

if section == SECTIONS[0]:
    st.subheader("📌 1. Basic Stats (시즌 누적 & 득실 및 페널티)")
    away_div_str = f"{away_data.get('conf', '')} {away_data.get('div', '')} {away_data.get('div_rank', 0):.0f}위"
    home_div_str = f"{home_data.get('conf', '')} {home_data.get('div', '')} {home_data.get('div_rank', 0):.0f}위"
    render_stat("시즌 성적", away_data.get('win_pct', 0), away_data.get('record_str', '0승 0패'), away_div_str, home_data.get('win_pct', 0), home_data.get('record_str', '0승 0패'), home_div_str, True, False, stat_key='record')
    render_stat("평균 득점 (PF)", away_data.get('avg_pf', 0), f"{away_data.get('avg_pf', 0):.1f}", f"{away_data.get('avg_pf_rank', 0):.0f}위", home_data.get('avg_pf', 0), f"{home_data.get('avg_pf', 0):.1f}", f"{home_data.get('avg_pf_rank', 0):.0f}위", True, False, stat_key='avg_pf')
    render_stat("평균 실점 (PA)", away_data.get('avg_pa', 0), f"{away_data.get('avg_pa', 0):.1f}", f"{away_data.get('avg_pa_rank', 0):.0f}위", home_data.get('avg_pa', 0), f"{home_data.get('avg_pa', 0):.1f}", f"{home_data.get('avg_pa_rank', 0):.0f}위", False, False, stat_key='avg_pa')
    render_stat("경기당 총 획득 야드", away_data.get('tot_yds', 0), f"{away_data.get('tot_yds', 0):.1f}", f"{away_data.get('tot_yds_rank', 0):.0f}위", home_data.get('tot_yds', 0), f"{home_data.get('tot_yds', 0):.1f}", f"{home_data.get('tot_yds_rank', 0):.0f}위", True, False, stat_key='tot_yds')
    render_stat("경기당 총 허용 야드", away_data.get('def_tot_yds', 0), f"{away_data.get('def_tot_yds', 0):.1f}", f"{away_data.get('def_tot_yds_rank', 0):.0f}위", home_data.get('def_tot_yds', 0), f"{home_data.get('def_tot_yds', 0):.1f}", f"{home_data.get('def_tot_yds_rank', 0):.0f}위", False, False, stat_key='def_tot_yds')

    away_to_str = f"{int(away_data.get('to_margin', 0)):+d} ({away_data.get('takeaways', 0)}개 획득/{away_data.get('giveaways', 0)}개 허용)"
    home_to_str = f"{int(home_data.get('to_margin', 0)):+d} ({home_data.get('takeaways', 0)}개 획득/{home_data.get('giveaways', 0)}개 허용)"
    render_stat("턴오버 마진", away_data.get('to_margin', 0), away_to_str, f"{away_data.get('to_margin_rank', 0):.0f}위", home_data.get('to_margin', 0), home_to_str, f"{home_data.get('to_margin_rank', 0):.0f}위", True, False, stat_key='to_margin')

    render_stat("평균 페널티 수", away_data.get('penalties_cnt', 0), f"{away_data.get('penalties_cnt', 0):.1f}개", f"{away_data.get('penalties_cnt_rank', 0):.0f}위", home_data.get('penalties_cnt', 0), f"{home_data.get('penalties_cnt', 0):.1f}개", f"{home_data.get('penalties_cnt_rank', 0):.0f}위", False, False, stat_key='penalties_cnt')
    render_stat("평균 페널티 야드", away_data.get('penalties_yds', 0), f"{away_data.get('penalties_yds', 0):.1f}yds", f"{away_data.get('penalties_yds_rank', 0):.0f}위", home_data.get('penalties_yds', 0), f"{home_data.get('penalties_yds', 0):.1f}yds", f"{home_data.get('penalties_yds_rank', 0):.0f}위", False, False, stat_key='penalties_yds')

if section == SECTIONS[1]:
    st.subheader("⚔️ 2. Offense & Defense Details (공수 세부 상성 및 효율성)")
    render_stat("패싱 야드 (Offense)", away_data.get('pass_yds', 0), f"{away_data.get('pass_yds', 0):.1f}", f"{away_data.get('pass_yds_rank', 0):.0f}위", home_data.get('pass_yds', 0), f"{home_data.get('pass_yds', 0):.1f}", f"{home_data.get('pass_yds_rank', 0):.0f}위", True, False, stat_key='pass_yds')
    render_stat("패스 허용 야드 (Defense)", away_data.get('def_pass_yds', 0), f"{away_data.get('def_pass_yds', 0):.1f}", f"{away_data.get('def_pass_yds_rank', 0):.0f}위", home_data.get('def_pass_yds', 0), f"{home_data.get('def_pass_yds', 0):.1f}", f"{home_data.get('def_pass_yds_rank', 0):.0f}위", False, False, stat_key='def_pass_yds')
    away_p_td = f"{away_data.get('pass_tds', 0):.1f}개 ({away_data.get('pass_tds_tot', 0)}개)"
    home_p_td = f"{home_data.get('pass_tds', 0):.1f}개 ({home_data.get('pass_tds_tot', 0)}개)"
    render_stat("패싱 TD (Offense)", away_data.get('pass_tds', 0), away_p_td, f"{away_data.get('pass_tds_rank', 0):.0f}위", home_data.get('pass_tds', 0), home_p_td, f"{home_data.get('pass_tds_rank', 0):.0f}위", True, False, stat_key='pass_tds')
    away_dp_td = f"{away_data.get('def_pass_tds', 0):.1f}개 ({away_data.get('def_pass_tds_tot', 0)}개)"
    home_dp_td = f"{home_data.get('def_pass_tds', 0):.1f}개 ({home_data.get('def_pass_tds_tot', 0)}개)"
    render_stat("패스 허용 TD (Defense)", away_data.get('def_pass_tds', 0), away_dp_td, f"{away_data.get('def_pass_tds_rank', 0):.0f}위", home_data.get('def_pass_tds', 0), home_dp_td, f"{home_data.get('def_pass_tds_rank', 0):.0f}위", False, False, stat_key='def_pass_tds')
    st.markdown("<br>", unsafe_allow_html=True)
    render_stat("러싱 야드 (Offense)", away_data.get('run_yds', 0), f"{away_data.get('run_yds', 0):.1f}", f"{away_data.get('run_yds_rank', 0):.0f}위", home_data.get('run_yds', 0), f"{home_data.get('run_yds', 0):.1f}", f"{home_data.get('run_yds_rank', 0):.0f}위", True, False, stat_key='run_yds')
    render_stat("러싱 허용 야드 (Defense)", away_data.get('def_run_yds', 0), f"{away_data.get('def_run_yds', 0):.1f}", f"{away_data.get('def_run_yds_rank', 0):.0f}위", home_data.get('def_run_yds', 0), f"{home_data.get('def_run_yds', 0):.1f}", f"{home_data.get('def_run_yds_rank', 0):.0f}위", False, False, stat_key='def_run_yds')
    away_r_td = f"{away_data.get('run_tds', 0):.1f}개 ({away_data.get('run_tds_tot', 0)}개)"
    home_r_td = f"{home_data.get('run_tds', 0):.1f}개 ({home_data.get('run_tds_tot', 0)}개)"
    render_stat("러싱 TD (Offense)", away_data.get('run_tds', 0), away_r_td, f"{away_data.get('run_tds_rank', 0):.0f}위", home_data.get('run_tds', 0), home_r_td, f"{home_data.get('run_tds_rank', 0):.0f}위", True, False, stat_key='run_tds')
    away_dr_td = f"{away_data.get('def_run_tds', 0):.1f}개 ({away_data.get('def_run_tds_tot', 0)}개)"
    home_dr_td = f"{home_data.get('def_run_tds', 0):.1f}개 ({home_data.get('def_run_tds_tot', 0)}개)"
    render_stat("러싱 허용 TD (Defense)", away_data.get('def_run_tds', 0), away_dr_td, f"{away_data.get('def_run_tds_rank', 0):.0f}위", home_data.get('def_run_tds', 0), home_dr_td, f"{home_data.get('def_run_tds_rank', 0):.0f}위", False, False, stat_key='def_run_tds')
    st.markdown("<br>", unsafe_allow_html=True)
    away_def_td = f"{away_data.get('def_tds', 0):.1f}개 ({away_data.get('def_tds_tot', 0)}개)"
    home_def_td = f"{home_data.get('def_tds', 0):.1f}개 ({home_data.get('def_tds_tot', 0)}개)"
    render_stat("디펜시브 TD (수비팀 득점)", away_data.get('def_tds', 0), away_def_td, f"{away_data.get('def_tds_rank', 0):.0f}위", home_data.get('def_tds', 0), home_def_td, f"{home_data.get('def_tds_rank', 0):.0f}위", True, False, stat_key='def_tds')
    away_st_td = f"{away_data.get('st_tds', 0):.1f}개 ({away_data.get('st_tds_tot', 0)}개)"
    home_st_td = f"{home_data.get('st_tds', 0):.1f}개 ({home_data.get('st_tds_tot', 0)}개)"
    render_stat("스페셜팀 TD (리턴 득점)", away_data.get('st_tds', 0), away_st_td, f"{away_data.get('st_tds_rank', 0):.0f}위", home_data.get('st_tds', 0), home_st_td, f"{home_data.get('st_tds_rank', 0):.0f}위", True, False, stat_key='st_tds')
    render_stat("Offensive EPA / Play", away_data.get('off_epa', 0), f"{away_data.get('off_epa', 0):+.3f}", f"{away_data.get('off_epa_rank', 0):.0f}위", home_data.get('off_epa', 0), f"{home_data.get('off_epa', 0):+.3f}", f"{home_data.get('off_epa_rank', 0):.0f}위", True, False, stat_key='off_epa')
    render_stat("Defensive EPA / Play", away_data.get('def_epa', 0), f"{away_data.get('def_epa', 0):+.3f}", f"{away_data.get('def_epa_rank', 0):.0f}위", home_data.get('def_epa', 0), f"{home_data.get('def_epa', 0):+.3f}", f"{home_data.get('def_epa_rank', 0):.0f}위", False, False, stat_key='def_epa')

if section == SECTIONS[2]:
    st.subheader("📊 3. Tendency & Success Rate (성향 및 성공률)")
    away_rz_off_str = f"{away_data.get('rz_off_pct', 0):.1f}% ({away_data.get('rz_off_td_drives', 0)}TD/{away_data.get('rz_off_drives', 0)}회 진입)"
    home_rz_off_str = f"{home_data.get('rz_off_pct', 0):.1f}% ({home_data.get('rz_off_td_drives', 0)}TD/{home_data.get('rz_off_drives', 0)}회 진입)"
    render_stat("레드존 공격 성공률 (Offense RZ%)", away_data.get('rz_off_pct', 0), away_rz_off_str, f"{away_data.get('rz_off_pct_rank', 0):.0f}위", home_data.get('rz_off_pct', 0), home_rz_off_str, f"{home_data.get('rz_off_pct_rank', 0):.0f}위", True, True, stat_key='rz_off_pct')

    away_rz_def_str = f"{away_data.get('rz_def_pct', 0):.1f}% ({away_data.get('rz_def_td_drives', 0)}TD/{away_data.get('rz_def_drives', 0)}회 허용)"
    home_rz_def_str = f"{home_data.get('rz_def_pct', 0):.1f}% ({home_data.get('rz_def_td_drives', 0)}TD/{home_data.get('rz_def_drives', 0)}회 허용)"
    render_stat("레드존 수비 허용률 (Defense RZ%)", away_data.get('rz_def_pct', 0), away_rz_def_str, f"{away_data.get('rz_def_pct_rank', 0):.0f}위", home_data.get('rz_def_pct', 0), home_rz_def_str, f"{home_data.get('rz_def_pct_rank', 0):.0f}위", False, True, stat_key='rz_def_pct')
    st.markdown("<br>", unsafe_allow_html=True)

    away_3rd_off_str = f"{away_data.get('off_3rd_success', 0):.1f}% ({away_data.get('off_3rd_att', 0):.0f}회 시도 / {away_data.get('off_3rd_succ', 0):.0f}회 성공)"
    home_3rd_off_str = f"{home_data.get('off_3rd_success', 0):.1f}% ({home_data.get('off_3rd_att', 0):.0f}회 시도 / {home_data.get('off_3rd_succ', 0):.0f}회 성공)"
    render_stat("3rd Down 성공률 (Offense)", away_data.get('off_3rd_success', 0), away_3rd_off_str, f"{away_data.get('off_3rd_success_rank', 0):.0f}위", home_data.get('off_3rd_success', 0), home_3rd_off_str, f"{home_data.get('off_3rd_success_rank', 0):.0f}위", True, True, stat_key='off_3rd_success')
    away_3rd_def_str = f"{away_data.get('def_3rd_stop', 0):.1f}% ({away_data.get('def_3rd_att', 0):.0f}회 시도 / {away_data.get('def_3rd_stop_cnt', 0):.0f}회 저지)"
    home_3rd_def_str = f"{home_data.get('def_3rd_stop', 0):.1f}% ({home_data.get('def_3rd_att', 0):.0f}회 시도 / {home_data.get('def_3rd_stop_cnt', 0):.0f}회 저지)"
    render_stat("3rd Down 저지율 (Defense)", away_data.get('def_3rd_stop', 0), away_3rd_def_str, f"{away_data.get('def_3rd_stop_rank', 0):.0f}위", home_data.get('def_3rd_stop', 0), home_3rd_def_str, f"{home_data.get('def_3rd_stop_rank', 0):.0f}위", True, True, stat_key='def_3rd_stop')
    st.markdown("<br>", unsafe_allow_html=True)

    away_4th_off_str = f"{away_data.get('off_4th_success', 0):.1f}% ({away_data.get('off_4th_att', 0):.0f}회 시도 / {away_data.get('off_4th_succ', 0):.0f}회 성공)"
    home_4th_off_str = f"{home_data.get('off_4th_success', 0):.1f}% ({home_data.get('off_4th_att', 0):.0f}회 시도 / {home_data.get('off_4th_succ', 0):.0f}회 성공)"
    render_stat("4th Down 성공률 (Offense)", away_data.get('off_4th_success', 0), away_4th_off_str, f"{away_data.get('off_4th_success_rank', 0):.0f}위", home_data.get('off_4th_success', 0), home_4th_off_str, f"{home_data.get('off_4th_success_rank', 0):.0f}위", True, True, stat_key='off_4th_success')
    away_4th_def_str = f"{away_data.get('def_4th_stop', 0):.1f}% ({away_data.get('def_4th_att', 0):.0f}회 시도 / {away_data.get('def_4th_stop_cnt', 0):.0f}회 저지)"
    home_4th_def_str = f"{home_data.get('def_4th_stop', 0):.1f}% ({home_data.get('def_4th_att', 0):.0f}회 시도 / {home_data.get('def_4th_stop_cnt', 0):.0f}회 저지)"
    render_stat("4th Down 저지율 (Defense)", away_data.get('def_4th_stop', 0), away_4th_def_str, f"{away_data.get('def_4th_stop_rank', 0):.0f}위", home_data.get('def_4th_stop', 0), home_4th_def_str, f"{home_data.get('def_4th_stop_rank', 0):.0f}위", True, True, stat_key='def_4th_stop')
    st.markdown("<br>", unsafe_allow_html=True)

    render_stat("패스 성공률 (Success Rate)", away_data.get('pass_success', 0), f"{away_data.get('pass_success', 0):.1f}%", f"{away_data.get('pass_success_rank', 0):.0f}위", home_data.get('pass_success', 0), f"{home_data.get('pass_success', 0):.1f}%", f"{home_data.get('pass_success_rank', 0):.0f}위", True, True, stat_key='pass_success')
    render_stat("러싱 성공률 (Success Rate)", away_data.get('run_success', 0), f"{away_data.get('run_success', 0):.1f}%", f"{away_data.get('run_success_rank', 0):.0f}위", home_data.get('run_success', 0), f"{home_data.get('run_success', 0):.1f}%", f"{home_data.get('run_success_rank', 0):.0f}위", True, True, stat_key='run_success')
    render_stat("패스 시도 비율 (Pass Ratio)", away_data.get('pass_ratio', 0), f"{away_data.get('pass_ratio', 0):.1f}%", f"{away_data.get('pass_ratio_rank', 0):.0f}위", home_data.get('pass_ratio', 0), f"{home_data.get('pass_ratio', 0):.1f}%", f"{home_data.get('pass_ratio_rank', 0):.0f}위", None, True, stat_key='pass_ratio')
    render_stat("러싱 시도 비율 (Run Ratio)", away_data.get('run_ratio', 0), f"{away_data.get('run_ratio', 0):.1f}%", f"{away_data.get('run_ratio_rank', 0):.0f}위", home_data.get('run_ratio', 0), f"{home_data.get('run_ratio', 0):.1f}%", f"{home_data.get('run_ratio_rank', 0):.0f}위", None, True, stat_key='run_ratio')

if section == SECTIONS[3]:
    st.subheader("🛡 4. Positional Unit Strength (유닛별 리그 순위)")
    render_stat("Quarterback (QB)", away_data.get('qb_rank', 0), f"{away_data.get('qb_rank', 0):.0f}위", None, home_data.get('qb_rank', 0), f"{home_data.get('qb_rank', 0):.0f}위", None, False, stat_key='qb')
    render_stat("Running Back (RB)", away_data.get('rb_rank', 0), f"{away_data.get('rb_rank', 0):.0f}위", None, home_data.get('rb_rank', 0), f"{home_data.get('rb_rank', 0):.0f}위", None, False, stat_key='rb')
    render_stat("Wide Receiver (WR)", away_data.get('wr_rank', 0), f"{away_data.get('wr_rank', 0):.0f}위", None, home_data.get('wr_rank', 0), f"{home_data.get('wr_rank', 0):.0f}위", None, False, stat_key='wr')
    render_stat("Tight End (TE)", away_data.get('te_rank', 0), f"{away_data.get('te_rank', 0):.0f}위", None, home_data.get('te_rank', 0), f"{home_data.get('te_rank', 0):.0f}위", None, False, stat_key='te')
    st.markdown("<br>", unsafe_allow_html=True)
    render_stat("Offensive Line (OL)", away_data.get('ol_rank', 0), f"{away_data.get('ol_rank', 0):.0f}위", None, home_data.get('ol_rank', 0), f"{home_data.get('ol_rank', 0):.0f}위", None, False, stat_key='ol')
    render_stat("Defensive Line (DL / EDGE)", away_data.get('dl_rank', 0), f"{away_data.get('dl_rank', 0):.0f}위", None, home_data.get('dl_rank', 0), f"{home_data.get('dl_rank', 0):.0f}위", None, False, stat_key='dl')
    render_stat("Linebacker (LB)", away_data.get('lb_rank', 0), f"{away_data.get('lb_rank', 0):.0f}위", None, home_data.get('lb_rank', 0), f"{home_data.get('lb_rank', 0):.0f}위", None, False, stat_key='lb')
    render_stat("Secondary (CB / S)", away_data.get('sec_rank', 0), f"{away_data.get('sec_rank', 0):.0f}위", None, home_data.get('sec_rank', 0), f"{home_data.get('sec_rank', 0):.0f}위", None, False, stat_key='sec')
