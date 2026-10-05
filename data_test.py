import nfl_data_py as nfl
import pandas as pd

# 1. 2025 시즌 Play-by-Play 데이터 로드 (연도 무관하게 변수명 통일)
print("데이터를 불러오는 중입니다...")
pbp_data = nfl.import_pbp_data([2025])

# 2. 분석을 위한 데이터 클렌징
pbp_clean = pbp_data[pbp_data['play_type'].isin(['pass', 'run'])].copy()

# 3. 특정 팀의 공격 지표를 추출하는 함수
def get_offensive_stats(team_abbr, df):
    offense_df = df[df['posteam'] == team_abbr]
    
    if offense_df.empty:
        return None
    
    total_plays = len(offense_df)
    epa_per_play = offense_df['epa'].mean()
    success_rate = offense_df['success'].mean() * 100
    
    pass_plays = len(offense_df[offense_df['play_type'] == 'pass'])
    run_plays = len(offense_df[offense_df['play_type'] == 'run'])
    pass_ratio = (pass_plays / total_plays) * 100
    run_ratio = (run_plays / total_plays) * 100
    
    return {
        "Team": team_abbr,
        "EPA/Play": round(epa_per_play, 3),
        "Success Rate (%)": round(success_rate, 1),
        "Pass Ratio (%)": round(pass_ratio, 1),
        "Run Ratio (%)": round(run_ratio, 1)
    }

# 4. 워싱턴과 댈러스 데이터 추출 테스트
was_stats = get_offensive_stats("WAS", pbp_clean)
dal_stats = get_offensive_stats("DAL", pbp_clean)

# 결과 출력
print("\n--- 2025 시즌 공격 세부 지표 ---")
print(was_stats)
print(dal_stats)