"""
clean_and_feature_engineer.py
=============================
Executes post-database Data Cleaning and Feature Engineering by extracting
records directly from the populated relational database and computing domain
metrics, physical biometrics, career ratios, and scouting profiles.

Outputs all cleaned & feature-engineered datasets into a dedicated new directory:
'clean_and_engineered_data/' (or custom directory).
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np


class PostDBDataCleanerAndFeatureEngineer:
    def __init__(self, db_path='Data Base/nba_analytics.db', output_dir='clean_and_engineered_data'):
        self.db_path = db_path
        self.output_dir = output_dir

    def extract_from_database(self):
        """
        Extract clean base tables from the relational database via SQL.
        """
        print(f"[Post-DB Pipeline] Connecting to database: '{self.db_path}'...")
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at: {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        totals = pd.read_sql("SELECT * FROM totals", conn)
        advanced = pd.read_sql("SELECT * FROM advanced", conn)
        players = pd.read_sql("SELECT * FROM players", conn)
        teams_all = pd.read_sql("SELECT * FROM teams_all_season", conn)
        seasons = pd.read_sql("SELECT * FROM seasons", conn)
        mjt = pd.read_sql("SELECT * FROM mjt", conn)
        salaries = pd.read_sql("SELECT * FROM salaries", conn) if 'salaries' in [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()] else pd.DataFrame()
        conn.close()

        print(f"  -> Retrieved Totals: {totals.shape}, Advanced: {advanced.shape}, Players: {players.shape}")
        return {
            'totals': totals,
            'advanced': advanced,
            'players': players,
            'teams_all': teams_all,
            'seasons': seasons,
            'mjt': mjt,
            'salaries': salaries
        }

    def clean_extracted_data(self, data):
        """
        Perform second-tier data cleaning on extracted database tables:
        - Handle multi-team stint duplicate management
        - Impute 0/0 division anomalies
        - Standardize naming and position formatting
        """
        print("[Post-DB Pipeline] Executing rigorous data cleaning on database tables...")
        totals = data['totals'].copy()
        advanced = data['advanced'].copy()
        players = data['players'].copy()

        # Deduplicate and standardize player positions
        totals['Pos'] = totals['Pos'].fillna('Unknown').astype(str).str.strip()
        totals['Primary_Pos'] = totals['Pos'].apply(lambda x: x.split('-')[0] if '-' in x else x)

        # Standardize awards column
        totals['Awards'] = totals['Awards'].fillna('')

        # Fill percentages with 0.0 where attempts were zero
        for col in ['FG%', '3P%', '2P%', 'eFG%', 'FT%']:
            if col in totals.columns:
                totals[col] = pd.to_numeric(totals[col], errors='coerce').fillna(0.0)

        for col in ['PER', 'TS%', '3PAr', 'FTr', 'USG%', 'OWS', 'DWS', 'WS', 'WS/48', 'OBPM', 'DBPM', 'BPM', 'VORP']:
            if col in advanced.columns:
                advanced[col] = pd.to_numeric(advanced[col], errors='coerce').fillna(0.0)

        # Multi-team stint flag
        totals['Is_Multi_Team_Aggregate'] = totals['Team'].str.contains(r'^\d+TM$|TOT', na=False)

        return {
            'totals': totals,
            'advanced': advanced,
            'players': players,
            'teams_all': data['teams_all'],
            'seasons': data['seasons'],
            'mjt': data['mjt'],
            'salaries': data['salaries']
        }

    def engineer_player_features(self, data):
        """
        Engineer comprehensive domain features across physical, career,
        rate-efficiency, and impact metrics.
        """
        print("[Post-DB Pipeline] Engineering domain features for player master dataset...")
        totals = data['totals']
        advanced = data['advanced']
        players = data['players']

        # Join totals and advanced
        adv_cols = ['Season', 'Player_Clean', 'Team', 'PER', 'TS%', '3PAr', 'FTr', 'USG%', 'OWS', 'DWS', 'WS', 'WS/48', 'OBPM', 'DBPM', 'BPM', 'VORP']
        adv_cols = [c for c in adv_cols if c in advanced.columns]
        
        merged = pd.merge(
            totals,
            advanced[adv_cols],
            on=['Season', 'Player_Clean', 'Team'],
            how='left'
        )

        # Join player biometrics
        p_cols = ['Player_Clean', 'Ht_CM', 'Wt_KG', 'Birth_Date_DT']
        p_cols = [c for c in p_cols if c in players.columns]
        merged = pd.merge(merged, players[p_cols], on='Player_Clean', how='left')

        # 1. Biometric & Physical Features
        merged['Agility_Metric'] = merged['Ht_CM'] / merged['Wt_KG']
        # BMI = weight (kg) / (height (m))^2
        h_meters = merged['Ht_CM'] / 100.0
        merged['BMI'] = merged['Wt_KG'] / (h_meters ** 2)
        merged['BMI'] = merged['BMI'].round(2)
        merged['Agility_Metric'] = merged['Agility_Metric'].round(4)

        # 2. Career & Innate Ability Features
        # Experience estimated from age if exp column not directly present
        if 'Exp' in merged.columns and merged['Exp'].notnull().any():
            exp_series = pd.to_numeric(merged['Exp'], errors='coerce').fillna(merged['Age'] - 20)
        else:
            exp_series = (merged['Age'] - 20).clip(lower=0)
        merged['Exp_Numeric'] = exp_series.clip(lower=0)
        merged['Innate_Ability'] = (merged['Exp_Numeric'] / merged['Age'].replace(0, np.nan)).round(4)

        # Career Phase Categorization
        def assign_career_phase(exp):
            if pd.isna(exp):
                return 'Unknown'
            if exp <= 1:
                return 'Rookie'
            elif exp <= 4:
                return 'Developing'
            elif exp <= 9:
                return 'Prime'
            else:
                return 'Veteran'

        merged['Career_Phase'] = merged['Exp_Numeric'].apply(assign_career_phase)

        # 3. Rate & Efficiency Metrics (Per-Minute Stats)
        mp = merged['MP'].replace(0, np.nan)
        merged['PTS_Per_Min'] = (merged['PTS'] / mp).round(4)
        merged['TRB_Per_Min'] = (merged['TRB'] / mp).round(4)
        merged['AST_Per_Min'] = (merged['AST'] / mp).round(4)
        merged['STL_Per_Min'] = (merged['STL'] / mp).round(4)
        merged['BLK_Per_Min'] = (merged['BLK'] / mp).round(4)
        merged['TOV_Per_Min'] = (merged['TOV'] / mp).round(4)

        # Assist to Turnover Ratio
        tov_safe = merged['TOV'].apply(lambda x: 1 if x == 0 else x)
        merged['AST_TOV_Ratio'] = (merged['AST'] / tov_safe).round(2)

        # True Shooting % (if not in advanced, or recomputed)
        fga = merged['FGA']
        fta = merged['FTA']
        ts_denom = 2 * (fga + 0.44 * fta)
        merged['Calculated_TS_Pct'] = (merged['PTS'] / ts_denom.replace(0, np.nan)).round(4)

        # Effective Field Goal %
        merged['Calculated_eFG_Pct'] = ((merged['FG'] + 0.5 * merged['3P']) / fga.replace(0, np.nan)).round(4)

        # Win Shares Per Game
        g_safe = merged['G'].replace(0, np.nan)
        if 'WS' in merged.columns:
            merged['WS_Per_Game'] = (merged['WS'] / g_safe).round(4)
        else:
            merged['WS_Per_Game'] = 0.0

        # 4. Award & Elite Flags
        awards_str = merged['Awards'].astype(str)
        merged['Is_All_Star'] = awards_str.str.contains('AS', na=False).astype(int)
        merged['Is_All_NBA'] = awards_str.str.contains(r'NBA[123]', regex=True, na=False).astype(int)
        merged['Is_All_Defensive'] = awards_str.str.contains(r'DEF[12]', regex=True, na=False).astype(int)

        # MVP Rank Extraction
        def extract_mvp_rank(aw):
            m = pd.Series(aw).str.extract(r'MVP-(\d+)')
            val = m[0].values[0]
            return int(val) if pd.notna(val) else np.nan

        merged['MVP_Rank'] = [extract_mvp_rank(a) for a in awards_str]

        # Fill NAs in rate columns
        for c in ['PTS_Per_Min', 'TRB_Per_Min', 'AST_Per_Min', 'STL_Per_Min', 'BLK_Per_Min', 'TOV_Per_Min', 'AST_TOV_Ratio', 'Calculated_TS_Pct', 'Calculated_eFG_Pct', 'WS_Per_Game']:
            merged[c] = merged[c].fillna(0.0)

        return merged

    def engineer_point_guard_scouting(self, master_df, mjt_df):
        """
        Build specialized Point Guard scouting profile answering Bootcamp PDF Question 3:
        Rank Point Guards based on Michael Jordan Trophy appearances, MVP points,
        and playmaking metrics for team acquisition recommendations.
        """
        print("[Post-DB Pipeline] Building Point Guard MVP Scouting Profiles...")
        # Filter PG records
        pg_mask = master_df['Pos'].str.contains('PG', na=False) | (master_df['Primary_Pos'] == 'PG')
        pg_df = master_df[pg_mask].copy()

        # Join with MJT
        mjt_clean = mjt_df.copy()
        if 'Rank_Numeric' not in mjt_clean.columns:
            mjt_clean['Rank_Numeric'] = pd.to_numeric(mjt_clean['Rank'].astype(str).str.replace('T', '', regex=False), errors='coerce')

        # Aggregate across historical career
        pg_scout = []
        for player_name, group in pg_df.groupby('Player_Clean'):
            seasons_played = group['Season'].nunique()
            mjt_rows = mjt_clean[mjt_clean['Player_Clean'] == player_name]
            mjt_appearances = len(mjt_rows)
            
            total_first_votes = pd.to_numeric(mjt_rows['First'], errors='coerce').sum() if mjt_appearances > 0 else 0
            total_pts_won = pd.to_numeric(mjt_rows['Pts Won'], errors='coerce').sum() if mjt_appearances > 0 else 0
            total_share = pd.to_numeric(mjt_rows['Share'], errors='coerce').sum() if mjt_appearances > 0 else 0.0

            avg_pts = group['PTS_Per_Min'].mean() * 36 # Per 36 min equivalent
            avg_ast = group['AST_Per_Min'].mean() * 36
            avg_trb = group['TRB_Per_Min'].mean() * 36
            avg_ast_tov = group['AST_TOV_Ratio'].mean()
            avg_ws = group['WS'].mean() if 'WS' in group.columns else 0.0
            avg_per = group['PER'].mean() if 'PER' in group.columns else 0.0
            agility = group['Agility_Metric'].dropna().mean()

            # Scouting Score = Weighted composite metric
            scouting_score = (
                mjt_appearances * 20.0 +
                total_share * 50.0 +
                avg_ws * 3.0 +
                avg_ast * 1.5 +
                avg_pts * 0.8
            )

            recent_season = group['Season'].max()

            pg_scout.append({
                'Player': player_name,
                'Primary_Position': 'PG',
                'Last_Active_Season': recent_season,
                'Seasons_Played': seasons_played,
                'MJT_Appearances': mjt_appearances,
                'Total_First_Place_Votes': int(total_first_votes),
                'Total_MVP_Points_Won': int(total_pts_won),
                'Total_MVP_Share': round(float(total_share), 4),
                'Avg_PTS_Per_36': round(float(avg_pts), 1),
                'Avg_AST_Per_36': round(float(avg_ast), 1),
                'Avg_TRB_Per_36': round(float(avg_trb), 1),
                'Avg_AST_TOV_Ratio': round(float(avg_ast_tov), 2),
                'Avg_Win_Shares': round(float(avg_ws), 2),
                'Avg_PER': round(float(avg_per), 1),
                'Agility_Index': round(float(agility), 4) if pd.notna(agility) else None,
                'Scouting_Score': round(float(scouting_score), 2)
            })

        scout_df = pd.DataFrame(pg_scout)
        scout_df = scout_df.sort_values(by='Scouting_Score', ascending=False).reset_index(drop=True)
        scout_df['Scouting_Rank'] = scout_df.index + 1
        return scout_df

    def engineer_team_features(self, teams_all_df, seasons_df):
        """
        Engineer team performance and contextual metrics:
        - Net Rating (ORtg - DRtg)
        - Win Percentage
        - Pace Classification
        - Championship Flag
        """
        print("[Post-DB Pipeline] Engineering team analytics and performance features...")
        df = teams_all_df.copy()
        df['W'] = pd.to_numeric(df['W'], errors='coerce')
        df['L'] = pd.to_numeric(df['L'], errors='coerce')
        df['ORtg'] = pd.to_numeric(df['ORtg'], errors='coerce')
        df['DRtg'] = pd.to_numeric(df['DRtg'], errors='coerce')
        df['Pace'] = pd.to_numeric(df['Pace'], errors='coerce')
        df['SRS'] = pd.to_numeric(df['SRS'], errors='coerce')

        # Win Percentage
        total_games = df['W'] + df['L']
        df['Win_Pct'] = (df['W'] / total_games.replace(0, np.nan)).round(4)

        # Net Rating
        df['Net_Rating'] = (df['ORtg'] - df['DRtg']).round(2)

        # Pace Style
        pace_mean = df['Pace'].mean()
        def classify_pace(p):
            if pd.isna(p):
                return 'Unknown'
            if p >= pace_mean + 2.0:
                return 'Fast-Paced'
            elif p <= pace_mean - 2.0:
                return 'Slow-Paced'
            return 'Balanced'

        df['Pace_Style'] = df['Pace'].apply(classify_pace)

        # Champion Flag
        champions = {}
        for idx, row in seasons_df.iterrows():
            if pd.notna(row['Season']) and pd.notna(row['Champion']):
                champions[str(row['Season']).strip()] = str(row['Champion']).strip()

        df['Champion_Flag'] = [
            1 if champions.get(str(s).strip()) == str(t).strip() else 0
            for s, t in zip(df['Season'], df['Team_Clean'])
        ]

        return df

    def run_and_export(self):
        """
        Executes end-to-end post-DB cleaning & feature engineering,
        and saves all datasets and relational SQLite database to the new directory.
        """
        print("=" * 75)
        print("STARTING POST-DATABASE FEATURE ENGINEERING & DATA CLEANING")
        print(f"Target Output Directory: '{self.output_dir}/'")
        print("=" * 75)

        os.makedirs(self.output_dir, exist_ok=True)

        # 1. Extraction from Database
        raw_db_data = self.extract_from_database()

        # 2. Data Cleaning
        cleaned_db_data = self.clean_extracted_data(raw_db_data)

        # 3. Player Feature Engineering
        player_master = self.engineer_player_features(cleaned_db_data)

        # 4. Point Guard Scouting Features
        pg_scouting = self.engineer_point_guard_scouting(player_master, cleaned_db_data['mjt'])

        # 5. Team Feature Engineering
        team_master = self.engineer_team_features(cleaned_db_data['teams_all'], cleaned_db_data['seasons'])

        # 6. Export to CSV in the New Directory
        print(f"\n[Post-DB Pipeline] Exporting engineered datasets to '{self.output_dir}/'...")
        
        # Player Master Features
        pm_path = os.path.join(self.output_dir, 'player_master_features.csv')
        player_master.to_csv(pm_path, index=False)
        print(f"  -> Saved {player_master.shape} to: {pm_path}")

        # Point Guard Scouting Candidates
        pg_path = os.path.join(self.output_dir, 'pg_scouting_candidates.csv')
        pg_scouting.to_csv(pg_path, index=False)
        print(f"  -> Saved {pg_scouting.shape} to: {pg_path}")

        # Team Master Features
        tm_path = os.path.join(self.output_dir, 'team_master_features.csv')
        team_master.to_csv(tm_path, index=False)
        print(f"  -> Saved {team_master.shape} to: {tm_path}")

        # Cleaned Base Tables
        cleaned_totals_path = os.path.join(self.output_dir, 'cleaned_player_season_stats.csv')
        cleaned_db_data['totals'].to_csv(cleaned_totals_path, index=False)
        print(f"  -> Saved {cleaned_db_data['totals'].shape} to: {cleaned_totals_path}")

        cleaned_mjt_path = os.path.join(self.output_dir, 'cleaned_mvp_voting.csv')
        cleaned_db_data['mjt'].to_csv(cleaned_mjt_path, index=False)
        print(f"  -> Saved {cleaned_db_data['mjt'].shape} to: {cleaned_mjt_path}")

        # 7. Create Dedicated SQLite Database in the New Directory
        db_out_path = os.path.join(self.output_dir, 'nba_clean_and_engineered.db')
        print(f"\n[Post-DB Pipeline] Building dedicated SQLite database: '{db_out_path}'...")
        conn = sqlite3.connect(db_out_path)
        player_master.to_sql('player_master_features', conn, if_exists='replace', index=False)
        pg_scouting.to_sql('pg_scouting_candidates', conn, if_exists='replace', index=False)
        team_master.to_sql('team_master_features', conn, if_exists='replace', index=False)
        cleaned_db_data['totals'].to_sql('cleaned_player_season_stats', conn, if_exists='replace', index=False)
        cleaned_db_data['mjt'].to_sql('cleaned_mvp_voting', conn, if_exists='replace', index=False)
        conn.close()
        print(f"  -> SQLite Database successfully generated at: {db_out_path}")

        # 8. Generate Comprehensive Data Dictionary
        dict_path = os.path.join(self.output_dir, 'DATA_DICTIONARY.md')
        with open(dict_path, 'w', encoding='utf-8') as f:
            f.write(f"""# 📖 NBA Clean & Engineered Data Dictionary
### دایرکتوری داده‌های پالایش‌شده و ویژگی‌های مهندسی‌شده لیگ NBA (۱۹۸۰ تا ۲۰۲۷)

پوشه `{self.output_dir}` دربرگیرنده خروجی‌های مرحله پس از بارگذاری پایگاه داده (Post-Database) می‌باشد. در این مرحله، داده‌ها مستقیماً از جداول پایگاه‌داده استخراج گردیده و پاکسازی مرحله دوم و مهندسی ویژگی‌های پیشرفته بر روی آن‌ها اعمال شده است.

---

## 📂 فایل‌های موجود در این دایرکتوری

| نام فایل | تعداد رکوردها | تعداد ویژگی‌ها | شرح محتوا |
|:---|:---:|:---:|:---|
| `player_master_features.csv` | {len(player_master):,} | {len(player_master.columns)} | جدول جامع ویژگی‌های بیومتریک، بهره‌وری، پر-مینت، کارایی و جوایز بازیکنان |
| `pg_scouting_candidates.csv` | {len(pg_scouting):,} | {len(pg_scouting.columns)} | رتبه‌بندی و پروفایل استعدادیابی پوینت‌گاردهای لیگ بر اساس حضور در MVP |
| `team_master_features.csv` | {len(team_master):,} | {len(team_master.columns)} | شاخص‌های تحلیلی عملکرد فصلی تیم‌ها (Net Rating، Pace Style، قهرمانی) |
| `cleaned_player_season_stats.csv` | {len(cleaned_db_data['totals']):,} | {len(cleaned_db_data['totals'].columns)} | آمار فصلی بازیکنان با اصلاح انکودینگ و حذف ردیف‌های نامعتبر |
| `cleaned_mvp_voting.csv` | {len(cleaned_db_data['mjt']):,} | {len(cleaned_db_data['mjt'].columns)} | تاریخچه کامل آرای تروفی مایکل جردن با رتبه‌های عددی |
| `nba_clean_and_engineered.db` | - | ۵ جدول | پایگاه داده رابطه‌ای SQLite حاوی تمامی جداول فوق |

---

## 📐 فرمول‌ها و متغیرهای کلیدی مهندسی‌شده

### ۱. ویژگی‌های بیومتریک و فیزیکی
- **شاخص چابکی (Agility Metric):**  
  $$Agility = \\frac{{Height\\ (cm)}}{{Weight\\ (kg)}}$$
  *تفسیر: مقادیر بالاتر نشان‌دهنده قامت کشیده‌تر نسبت به وزن و چابکی بالاتر در مانورهای فردی است.*
- **شاخص توده بدنی (BMI):**  
  $$BMI = \\frac{{Weight\\ (kg)}}{{(Height\\ (m))^2}}$$

### ۲. ویژگی‌های شغلی و توانایی ذاتی
- **شاخص توانایی ذاتی (Innate Ability):**  
  $$Innate\\ Ability = \\frac{{Experience\\ (Years)}}{{Age\\ (Years)}}$$
  *تفسیر: نسبت سابقه حضور در لیگ بالاترین سطح نسبت به سن فرد؛ بازتاب‌دهنده سرعت شکوفایی استعداد.*
- **فاز شغلی (Career Phase):**  
  - `Rookie`: سابقه ۰ تا ۱ سال
  - `Developing`: سابقه ۲ تا ۴ سال
  - `Prime`: سابقه ۵ تا ۹ سال
  - `Veteran`: سابقه ۱۰ سال و بیشتر

### ۳. ویژگی‌های کارایی و نرخ تولید در دقیقه (Per-Minute Stats)
- **امتیاز در دقیقه (PTS_Per_Min):** $PTS / MP$
- **پاس گل در دقیقه (AST_Per_Min):** $AST / MP$
- **ریباند در دقیقه (TRB_Per_Min):** $TRB / MP$
- **نسبت پاس گل به ترن‌اور (AST_TOV_Ratio):** $AST / \\max(TOV, 1)$

### ۴. استعدادیابی پوینت‌گارد (Scouting Score)
امتیاز جامع استعدادیابی برای انتخاب برترین پوینت‌گاردهای آماده قهرمانی:
$$Scouting\\ Score = 20 \\times MJT\\_Appearances + 50 \\times Total\\_MVP\\_Share + 3 \\times Win\\_Shares + 1.5 \\times AST\\_Per\\_36 + 0.8 \\times PTS\\_Per\\_36$$
""")
        print(f"  -> Data dictionary documentation written: {dict_path}")

        print("\n" + "=" * 75)
        print("POST-DATABASE CLEANING & FEATURE ENGINEERING COMPLETED!")
        print(f"All files successfully placed in new folder: '{self.output_dir}/'")
        print("=" * 75)


if __name__ == '__main__':
    pipeline = PostDBDataCleanerAndFeatureEngineer()
    pipeline.run_and_export()
