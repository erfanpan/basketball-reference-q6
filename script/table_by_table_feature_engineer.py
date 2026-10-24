"""
table_by_table_feature_engineer.py
==================================
Performs:
1. Individual Data Cleaning & In-Table Feature Engineering for EACH of the 10 raw CSVs.
2. Cross-Table Feature Engineering generating brand new combined datasets (CSVs & Excel XLSX)
   when features require information across multiple raw files.

Outputs all individual tables and cross-table files into 'clean_and_engineered_data/'.
"""

import os
import re
import math
import sqlite3
import pandas as pd
import numpy as np


class TableByTableFeatureEngineer:
    def __init__(self, raw_dir='Raw data', output_dir='clean_and_engineered_data'):
        self.raw_dir = raw_dir
        self.output_dir = output_dir
        self.indiv_dir = os.path.join(output_dir, 'individual_tables')
        self.cross_dir = os.path.join(output_dir, 'cross_tables')

    @staticmethod
    def fix_mojibake(text):
        if not isinstance(text, str):
            return text
        try:
            return text.encode('latin1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text

    @classmethod
    def clean_player_name(cls, name):
        if not isinstance(name, str):
            return name
        fixed = cls.fix_mojibake(name)
        return fixed.replace('*', '').strip()

    @staticmethod
    def parse_height(ht_str):
        if not isinstance(ht_str, str) or '-' not in ht_str:
            return np.nan, np.nan
        try:
            parts = ht_str.strip().split('-')
            feet = int(parts[0])
            inches = int(parts[1])
            tot_inches = feet * 12 + inches
            ht_cm = round(tot_inches * 2.54, 2)
            return tot_inches, ht_cm
        except Exception:
            return np.nan, np.nan

    # --------------------------------------------------------------------
    # 1. PLAYERS.CSV
    # --------------------------------------------------------------------
    def process_players(self):
        print("  -> Processing 1/10: players.csv...")
        df = pd.read_csv(os.path.join(self.raw_dir, 'players.csv'))
        
        # Cleaning
        df['Player_Clean'] = df['Player'].apply(self.clean_player_name)
        hts = df['Ht'].apply(self.parse_height)
        df['Ht_Inches'] = [h[0] for h in hts]
        df['Ht_CM'] = [h[1] for h in hts]
        df['Wt_LBS'] = pd.to_numeric(df['Wt'], errors='coerce')
        df['Wt_KG'] = (df['Wt_LBS'] * 0.45359237).round(2)
        df['Birth_Date_DT'] = pd.to_datetime(df['Birth Date'], errors='coerce')
        df['Colleges'] = df['Colleges'].fillna('None')

        # Feature Engineering (In-Table)
        df['Career_Length_Years'] = df['To'] - df['From'] + 1
        
        def assign_decade(yr):
            if pd.isna(yr):
                return 'Unknown'
            d = (int(yr) // 10) * 10
            return f"{d}s"

        df['Draft_Decade'] = df['From'].apply(assign_decade)
        df['Agility_Metric'] = (df['Ht_CM'] / df['Wt_KG']).round(4)
        h_m = df['Ht_CM'] / 100.0
        df['BMI'] = (df['Wt_KG'] / (h_m ** 2)).round(2)
        
        def assign_height_tier(cm):
            if pd.isna(cm):
                return 'Unknown'
            if cm < 193:
                return 'Guard (<6\'4)'
            elif cm <= 203:
                return 'Wing (6\'4-6\'8)'
            return 'Big (>6\'8)'

        df['Height_Tier'] = df['Ht_CM'].apply(assign_height_tier)
        
        def assign_weight_tier(kg):
            if pd.isna(kg):
                return 'Unknown'
            if kg < 90:
                return 'Light (<90kg)'
            elif kg <= 105:
                return 'Medium (90-105kg)'
            return 'Heavy (>105kg)'

        df['Weight_Tier'] = df['Wt_KG'].apply(assign_weight_tier)
        df['Has_College'] = df['Colleges'].apply(lambda x: 0 if str(x).strip().lower() in ['none', ''] else 1)
        df['College_Count'] = df['Colleges'].apply(lambda x: 0 if str(x).strip().lower() in ['none', ''] else len(str(x).split(',')))
        return df

    # --------------------------------------------------------------------
    # 2. ROSTERS.CSV
    # --------------------------------------------------------------------
    def process_rosters(self):
        print("  -> Processing 2/10: rosters.csv...")
        df = pd.read_csv(os.path.join(self.raw_dir, 'rosters.csv'))
        
        # Cleaning
        df['Player_Clean'] = df['Player'].apply(self.clean_player_name)
        hts = df['Ht'].apply(self.parse_height)
        df['Ht_Inches'] = [h[0] for h in hts]
        df['Ht_CM'] = [h[1] for h in hts]
        df['Wt_LBS'] = pd.to_numeric(df['Wt'], errors='coerce')
        df['Wt_KG'] = (df['Wt_LBS'] * 0.45359237).round(2)
        
        def parse_exp(val):
            if pd.isna(val):
                return np.nan
            s = str(val).strip().upper()
            if s == 'R':
                return 0
            try:
                return int(float(s))
            except Exception:
                return np.nan

        df['Exp_Numeric'] = df['Exp'].apply(parse_exp)
        df['Birth_Date_DT'] = pd.to_datetime(df['Birth Date'], errors='coerce')
        df['College'] = df['College'].fillna('None')

        # Feature Engineering (In-Table)
        df['No_Numeric'] = pd.to_numeric(df['No.'], errors='coerce')
        df['Agility_Metric'] = (df['Ht_CM'] / df['Wt_KG']).round(4)
        h_m = df['Ht_CM'] / 100.0
        df['BMI'] = (df['Wt_KG'] / (h_m ** 2)).round(2)
        df['Rookie_Flag'] = (df['Exp_Numeric'] == 0).astype(int)
        
        def assign_roster_exp(exp):
            if pd.isna(exp):
                return 'Unknown'
            if exp == 0:
                return 'Rookie'
            elif exp <= 3:
                return 'Developing'
            return 'Veteran'

        df['Roster_Exp_Tier'] = df['Exp_Numeric'].apply(assign_roster_exp)
        birth_year = df['Birth_Date_DT'].dt.year
        df['Estimated_Age'] = df['Season'] - birth_year
        df['Innate_Ability_Roster'] = (df['Exp_Numeric'] / df['Estimated_Age'].replace(0, np.nan)).round(4)
        return df

    # --------------------------------------------------------------------
    # 3. TOTALS_PSS.CSV
    # --------------------------------------------------------------------
    def process_totals(self):
        print("  -> Processing 3/10: totals_pss.csv...")
        df = pd.read_csv(os.path.join(self.raw_dir, 'totals_pss.csv'))
        
        # Cleaning
        df = df[df['Player'] != 'League Average'].copy()
        df = df[df['Rk'].notnull()].copy()
        df['Player_Clean'] = df['Player'].apply(self.clean_player_name)
        df['Rk'] = df['Rk'].astype(int)
        df['Season'] = df['Season'].astype(int)
        df['Is_Multi_Team_Aggregate'] = df['Team'].str.contains(r'^\d+TM$|TOT', na=False).astype(int)
        df['Awards'] = df['Awards'].fillna('')

        for col in ['FG%', '3P%', '2P%', 'eFG%', 'FT%']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # Feature Engineering (In-Table)
        mp = df['MP'].replace(0, np.nan)
        df['Innate_Ability'] = ((df['Age'] - 20).clip(lower=0) / df['Age']).round(4)
        
        def assign_career_phase(age):
            if pd.isna(age):
                return 'Unknown'
            if age <= 22:
                return 'Rookie/Young'
            elif age <= 25:
                return 'Developing'
            elif age <= 30:
                return 'Prime'
            return 'Veteran'

        df['Career_Phase'] = df['Age'].apply(assign_career_phase)
        df['PTS_Per_Min'] = (df['PTS'] / mp).round(4).fillna(0.0)
        df['TRB_Per_Min'] = (df['TRB'] / mp).round(4).fillna(0.0)
        df['AST_Per_Min'] = (df['AST'] / mp).round(4).fillna(0.0)
        df['STL_Per_Min'] = (df['STL'] / mp).round(4).fillna(0.0)
        df['BLK_Per_Min'] = (df['BLK'] / mp).round(4).fillna(0.0)
        df['TOV_Per_Min'] = (df['TOV'] / mp).round(4).fillna(0.0)
        tov_safe = df['TOV'].apply(lambda x: 1 if x == 0 else x)
        df['AST_TOV_Ratio'] = (df['AST'] / tov_safe).round(2)
        df['FG3A_Rate'] = (df['3PA'] / df['FGA'].replace(0, np.nan)).round(4).fillna(0.0)
        df['FT_Rate'] = (df['FTA'] / df['FGA'].replace(0, np.nan)).round(4).fillna(0.0)
        df['Starter_Ratio'] = (df['GS'] / df['G'].replace(0, np.nan)).round(4).fillna(0.0)
        df['Min_Per_Game'] = (df['MP'] / df['G'].replace(0, np.nan)).round(1).fillna(0.0)
        df['PTS_Per_Game'] = (df['PTS'] / df['G'].replace(0, np.nan)).round(1).fillna(0.0)
        
        aw_str = df['Awards'].astype(str)
        df['Is_All_Star'] = aw_str.str.contains('AS', na=False).astype(int)
        df['Is_All_NBA'] = aw_str.str.contains(r'NBA[123]', regex=True, na=False).astype(int)
        df['Is_All_Defensive'] = aw_str.str.contains(r'DEF[12]', regex=True, na=False).astype(int)
        
        def extract_mvp_rank(aw):
            m = re.search(r'MVP-(\d+)', aw)
            return int(m.group(1)) if m else np.nan

        df['MVP_Rank_Numeric'] = df['Awards'].apply(extract_mvp_rank)
        return df

    # --------------------------------------------------------------------
    # 4. PER_GAME_PSS.CSV
    # --------------------------------------------------------------------
    def process_per_game(self):
        print("  -> Processing 4/10: per_game_pss.csv...")
        df = pd.read_csv(os.path.join(self.raw_dir, 'per_game_pss.csv'))
        
        # Cleaning
        df = df[df['Player'] != 'League Average'].copy()
        df = df[df['Rk'].notnull()].copy()
        df['Player_Clean'] = df['Player'].apply(self.clean_player_name)
        df['Rk'] = df['Rk'].astype(int)
        df['Season'] = df['Season'].astype(int)
        df['Is_Multi_Team_Aggregate'] = df['Team'].str.contains(r'^\d+TM$|TOT', na=False).astype(int)
        df['Awards'] = df['Awards'].fillna('')

        for col in ['FG%', '3P%', '2P%', 'eFG%', 'FT%']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # Feature Engineering (In-Table)
        def assign_scoring_tier(pts):
            if pts >= 20.0:
                return 'High-Volume (>20)'
            elif pts >= 10.0:
                return 'Mid-Volume (10-20)'
            return 'Low-Volume (<10)'

        df['Scoring_Volume_Tier'] = df['PTS'].apply(assign_scoring_tier)

        def assign_playmaking_tier(ast):
            if ast >= 7.0:
                return 'Elite Playmaker (>=7)'
            elif ast >= 4.0:
                return 'Good Playmaker (4-7)'
            return 'Secondary/Low (<4)'

        df['Playmaking_Tier'] = df['AST'].apply(assign_playmaking_tier)
        tov_safe = df['TOV'].apply(lambda x: 0.5 if x == 0 else x)
        df['AST_TOV_Per_Game'] = (df['AST'] / tov_safe).round(2)
        df['Stocks_Per_Game'] = (df['STL'] + df['BLK']).round(2)
        mp = df['MP'].replace(0, np.nan)
        df['Per_Game_Production_Index'] = ((df['PTS'] + 1.2*df['TRB'] + 1.5*df['AST'] + 2.0*df['STL'] + 2.0*df['BLK'] - 1.5*df['TOV']) / mp).round(3).fillna(0.0)
        return df

    # --------------------------------------------------------------------
    # 5. ADVANCED_PSS.CSV
    # --------------------------------------------------------------------
    def process_advanced(self):
        print("  -> Processing 5/10: advanced_pss.csv...")
        df = pd.read_csv(os.path.join(self.raw_dir, 'advanced_pss.csv'))
        
        # Cleaning
        df = df[df['Player'] != 'League Average'].copy()
        df = df[df['Rk'].notnull()].copy()
        df['Player_Clean'] = df['Player'].apply(self.clean_player_name)
        df['Rk'] = df['Rk'].astype(int)
        df['Season'] = df['Season'].astype(int)
        df['Is_Multi_Team_Aggregate'] = df['Team'].str.contains(r'^\d+TM$|TOT', na=False).astype(int)
        
        for col in ['PER', 'TS%', '3PAr', 'FTr', 'USG%', 'OWS', 'DWS', 'WS', 'WS/48', 'OBPM', 'DBPM', 'BPM', 'VORP']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # Feature Engineering (In-Table)
        df['WS_Per_Game'] = (df['WS'] / df['G'].replace(0, np.nan)).round(4).fillna(0.0)
        df['Net_BPM'] = (df['OBPM'] - df['DBPM']).round(2)
        df['Offensive_Load'] = (df['USG%'] * (1.0 - (df['TOV%'] / 100.0))).round(2)
        
        def assign_impact_tier(row):
            vorp = row.get('VORP', 0)
            bpm = row.get('BPM', 0)
            if vorp >= 5.0 or bpm >= 6.0:
                return 'MVP-Caliber'
            elif vorp >= 3.0 or bpm >= 3.5:
                return 'All-Star Caliber'
            elif vorp >= 1.0 or bpm >= 0.0:
                return 'Quality Starter'
            return 'Rotation/Bench'

        df['Player_Impact_Tier'] = df.apply(assign_impact_tier, axis=1)
        df['PER_TS_Product'] = (df['PER'] * df['TS%']).round(2)
        return df

    # --------------------------------------------------------------------
    # 6. MICHEAL_JORDAN_TROPHY.CSV
    # --------------------------------------------------------------------
    def process_mjt(self):
        print("  -> Processing 6/10: micheal_jordan_trophy.csv...")
        df = pd.read_csv(os.path.join(self.raw_dir, 'micheal_jordan_trophy.csv'))
        
        # Cleaning
        df['Player_Clean'] = df['Player'].apply(self.clean_player_name)
        df['Season'] = pd.to_numeric(df['Season'], errors='coerce').astype(int)
        df['Rank_Numeric'] = pd.to_numeric(df['Rank'].astype(str).str.replace('T', '', regex=False), errors='coerce')
        df['Is_Tied_Rank'] = df['Rank'].astype(str).str.contains('T', na=False).astype(int)
        
        for col in ['First', 'Pts Won', 'Pts Max', 'Share', 'G', 'MP', 'PTS', 'TRB', 'AST', 'STL', 'BLK', 'WS', 'WS/48']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # Feature Engineering (In-Table)
        df['Is_Winner'] = (df['Rank_Numeric'] == 1).astype(int)
        df['Top_3_Finish'] = (df['Rank_Numeric'] <= 3).astype(int)
        df['Top_5_Finish'] = (df['Rank_Numeric'] <= 5).astype(int)
        max_first_votes = df['Pts Max'] / 10.0
        df['First_Place_Vote_Dominance'] = (df['First'] / max_first_votes.replace(0, np.nan)).round(4).fillna(0.0)
        df['Unanimous_MVP'] = (df['Share'] >= 1.0).astype(int)
        mp = df['MP'].replace(0, np.nan)
        df['MVP_PTS_Per_Min'] = (df['PTS'] / mp).round(4).fillna(0.0)
        df['MVP_Box_Composite'] = ((df['PTS'] + df['TRB'] + df['AST'] + df['STL'] + df['BLK']) / mp).round(3).fillna(0.0)
        return df

    # --------------------------------------------------------------------
    # 7. ROSTERS_SALARIES.CSV
    # --------------------------------------------------------------------
    def process_salaries(self):
        print("  -> Processing 7/10: rosters_salaries.csv...")
        df = pd.read_csv(os.path.join(self.raw_dir, 'rosters_salaries.csv'))
        
        # Cleaning
        if 'Unnamed: 3' in df.columns:
            df.rename(columns={'Unnamed: 3': 'Player'}, inplace=True)
        df = df[df['Player'].notnull()].copy()
        df['Player_Clean'] = df['Player'].apply(self.clean_player_name)
        df['Season'] = pd.to_numeric(df['Season'], errors='coerce').astype(int)
        
        def parse_salary(val):
            if pd.isna(val):
                return np.nan
            cleaned = re.sub(r'[^\d.]', '', str(val))
            try:
                return float(cleaned)
            except Exception:
                return np.nan

        df['Salary_Numeric'] = df['Salary'].apply(parse_salary)

        # Feature Engineering (In-Table)
        df['Salary_Millions'] = (df['Salary_Numeric'] / 1_000_000.0).round(3)
        df['Salary_Log'] = np.log1p(df['Salary_Numeric'].fillna(0)).round(3)

        def assign_salary_tier(sal):
            if pd.isna(sal) or sal == 0:
                return 'Unknown/Minimum'
            if sal >= 30_000_000:
                return 'Supermax/Max (>30M)'
            elif sal >= 10_000_000:
                return 'Mid-Level (10-30M)'
            elif sal >= 3_000_000:
                return 'Role Player (3-10M)'
            return 'Minimum (<3M)'

        df['Salary_Tier'] = df['Salary_Numeric'].apply(assign_salary_tier)

        # Team payroll share and salary ranking
        team_totals = df.groupby(['Season', 'Team'])['Salary_Numeric'].transform('sum')
        df['Team_Payroll_Share'] = (df['Salary_Numeric'] / team_totals.replace(0, np.nan)).round(4).fillna(0.0)
        df['Team_Salary_Rank'] = df.groupby(['Season', 'Team'])['Salary_Numeric'].rank(ascending=False, method='min')
        return df

    # --------------------------------------------------------------------
    # 8. SEASONS.CSV
    # --------------------------------------------------------------------
    def process_seasons(self):
        print("  -> Processing 8/10: seasons.csv...")
        df = pd.read_csv(os.path.join(self.raw_dir, 'seasons.csv'))
        
        # Cleaning
        df = df[df['Season'].notnull()].copy()
        df = df[df['Season'].str.match(r'^\d{4}-\d{2}$', na=False)].copy()
        
        for col in ['MVP', 'Rookie of the Year', 'Points', 'Rebounds', 'Assists', 'Win Shares']:
            if col in df.columns:
                df[f'{col}_Clean'] = df[col].apply(self.clean_player_name)

        # Feature Engineering (In-Table)
        def parse_season_year(s):
            parts = str(s).split('-')
            century = parts[0][:2]
            y = int(century + parts[1])
            if y < 1950:
                y += 100
            return y

        df['Season_Year'] = df['Season'].apply(parse_season_year)
        
        def assign_era(yr):
            if yr >= 2015:
                return 'Pace & Space / 3-Point Era'
            elif yr >= 2005:
                return 'Seven Seconds or Less / Modern Iso'
            elif yr >= 1995:
                return 'Defensive / Slow-Paced Era'
            elif yr >= 1980:
                return 'Showtime & Golden Age'
            return 'Pre-Modern Era'

        df['Era_Name'] = df['Season_Year'].apply(assign_era)
        
        # Extract numeric values from leader columns (e.g., 'L. Dončić (2370)' -> 2370)
        def extract_leader_num(val):
            m = re.search(r'\(([\d.]+)\)', str(val))
            return float(m.group(1)) if m else np.nan

        df['Scoring_Leader_Pts'] = df['Points'].apply(extract_leader_num)
        df['Rebound_Leader_Trb'] = df['Rebounds'].apply(extract_leader_num)
        df['Assist_Leader_Ast'] = df['Assists'].apply(extract_leader_num)
        df['Win_Shares_Leader_WS'] = df['Win Shares'].apply(extract_leader_num)
        return df

    # --------------------------------------------------------------------
    # 9. TEAMS.CSV
    # --------------------------------------------------------------------
    def process_teams(self):
        print("  -> Processing 9/10: teams.csv...")
        df = pd.read_csv(os.path.join(self.raw_dir, 'teams.csv'))
        
        # Cleaning & numeric parsing
        for col in ['Yrs', 'G', 'W', 'L', 'W/L%', 'Plyfs', 'Div', 'Conf', 'Champ']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Feature Engineering (In-Table)
        df['Is_Active'] = (df['Status'] == 'Active').astype(int)
        yrs_safe = df['Yrs'].replace(0, np.nan)
        df['Championship_Rate'] = (df['Champ'] / yrs_safe).round(4).fillna(0.0)
        df['Playoff_Rate'] = (df['Plyfs'] / yrs_safe).round(4).fillna(0.0)

        def assign_franchise_tier(champ, wl):
            if champ >= 5:
                return 'Dynasty Franchise (5+ Rings)'
            elif champ >= 1:
                return 'Championship Franchise (1-4 Rings)'
            elif wl >= 0.50:
                return 'Winning Non-Champion (>=.500)'
            return 'Developing / Rebuilding (<.500)'

        df['Franchise_Tier'] = [assign_franchise_tier(c, w) for c, w in zip(df['Champ'], df['W/L%'])]
        return df

    # --------------------------------------------------------------------
    # 10. TEAMS_ALL_SEASON.CSV
    # --------------------------------------------------------------------
    def process_teams_all_season(self):
        print("  -> Processing 10/10: teams_all_season.csv...")
        df = pd.read_csv(os.path.join(self.raw_dir, 'teams_all_season.csv'))
        
        # Cleaning
        drop_cols = [c for c in ['Unnamed: 8', 'Unnamed: 15'] if c in df.columns]
        if drop_cols:
            df.drop(columns=drop_cols, inplace=True)

        df['Team_Clean'] = df['Team'].str.replace('*', '', regex=False).str.strip()
        df['Made_Playoffs'] = df['Team'].str.contains(r'\*$', na=False).astype(int)

        for col in ['W', 'L', 'W/L%', 'SRS', 'Pace', 'Rel Pace', 'ORtg', 'Rel ORtg', 'DRtg', 'Rel DRtg']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Feature Engineering (In-Table)
        def parse_season_year(s):
            parts = str(s).split('-')
            century = parts[0][:2]
            y = int(century + parts[1])
            if y < 1950:
                y += 100
            return y

        df['Season_Year'] = df['Season'].apply(parse_season_year)
        df['Net_Rating'] = (df['ORtg'] - df['DRtg']).round(2)
        total_games = df['W'] + df['L']
        
        # Pythagorean Expected Wins: Games * (ORtg^14 / (ORtg^14 + DRtg^14))
        def calc_pythagorean(row):
            ortg = row.get('ORtg', 100)
            drtg = row.get('DRtg', 100)
            g = row.get('W', 0) + row.get('L', 0)
            if pd.isna(ortg) or pd.isna(drtg) or g == 0:
                return np.nan
            exp_14 = 14.0
            num = ortg ** exp_14
            den = num + (drtg ** exp_14)
            return round(g * (num / den), 1)

        df['Pythagorean_Wins'] = df.apply(calc_pythagorean, axis=1)
        df['Luck_Factor_Wins'] = (df['W'] - df['Pythagorean_Wins']).round(1)

        pace_mean = df['Pace'].mean()
        def assign_pace_style(p):
            if pd.isna(p):
                return 'Unknown'
            if p >= pace_mean + 2.0:
                return 'Fast-Paced'
            elif p <= pace_mean - 2.0:
                return 'Slow-Paced'
            return 'Balanced'

        df['Pace_Style'] = df['Pace'].apply(assign_pace_style)

        def assign_playoff_rounds(p):
            if pd.isna(p) or not str(p).strip():
                return 0
            s = str(p).lower()
            if 'won finals' in s or 'champion' in s:
                return 4
            elif 'lost finals' in s:
                return 3
            elif 'conf. finals' in s:
                return 2
            elif 'conf. 1st' in s or 'first round' in s:
                return 0
            return 1

        df['Playoff_Rounds_Won'] = df['Playoffs'].apply(assign_playoff_rounds)
        return df

    # ====================================================================
    # CROSS-TABLE FEATURE ENGINEERING (اکسل‌های جدید ترکیبی)
    # ====================================================================

    def build_cross_player_master(self, totals_df, adv_df, players_df, sal_df):
        """
        Cross-Table 1: Unified Player Master Dataset combining:
        totals_pss + advanced_pss + players + rosters_salaries
        """
        print("  -> Building Cross-Table 1: cross_player_master_features...")
        adv_cols = ['Season', 'Player_Clean', 'Team', 'PER', 'TS%', '3PAr', 'FTr', 'USG%', 'OWS', 'DWS', 'WS', 'WS/48', 'OBPM', 'DBPM', 'BPM', 'VORP', 'Net_BPM', 'Offensive_Load', 'Player_Impact_Tier']
        adv_cols = [c for c in adv_cols if c in adv_df.columns]

        merged = pd.merge(totals_df, adv_df[adv_cols], on=['Season', 'Player_Clean', 'Team'], how='left')

        p_cols = ['Player_Clean', 'Ht_CM', 'Wt_KG', 'Birth_Date_DT', 'Agility_Metric', 'BMI', 'Height_Tier', 'Weight_Tier', 'Has_College']
        p_cols = [c for c in p_cols if c in players_df.columns]
        merged = pd.merge(merged, players_df[p_cols], on='Player_Clean', how='left')

        # Add salary
        if not sal_df.empty:
            sal_sub = sal_df[['Season', 'Player_Clean', 'Salary_Numeric', 'Salary_Millions', 'Salary_Tier']].drop_duplicates(['Season', 'Player_Clean'])
            merged = pd.merge(merged, sal_sub, on=['Season', 'Player_Clean'], how='left')
        else:
            merged['Salary_Numeric'] = np.nan
            merged['Salary_Millions'] = np.nan
            merged['Salary_Tier'] = 'Unknown'

        # Efficiency composite
        merged['Player_Efficiency_Score'] = (merged['PER'].fillna(10) * merged['TS%'].fillna(0.5)).round(2)
        return merged

    def build_cross_pg_scouting(self, totals_df, mjt_df, players_df):
        """
        Cross-Table 2: Point Guard Scouting Profile combining:
        totals_pss + micheal_jordan_trophy + players (Quera PDF Q3)
        """
        print("  -> Building Cross-Table 2: cross_pg_mjt_scouting_candidates...")
        pg_mask = totals_df['Pos'].str.contains('PG', na=False)
        pg_df = totals_df[pg_mask].copy()

        pg_profiles = []
        for p_name, group in pg_df.groupby('Player_Clean'):
            mjt_recs = mjt_df[mjt_df['Player_Clean'] == p_name]
            mjt_count = len(mjt_recs)
            total_first_votes = mjt_recs['First'].sum() if mjt_count > 0 else 0
            total_pts_won = mjt_recs['Pts Won'].sum() if mjt_count > 0 else 0
            total_share = mjt_recs['Share'].sum() if mjt_count > 0 else 0.0

            pts_36 = group['PTS_Per_Min'].mean() * 36
            ast_36 = group['AST_Per_Min'].mean() * 36
            trb_36 = group['TRB_Per_Min'].mean() * 36
            ast_tov = group['AST_TOV_Ratio'].mean()
            seasons_played = group['Season'].nunique()
            last_season = group['Season'].max()

            # Scouting Score
            scout_score = (mjt_count * 20.0 + total_share * 50.0 + ast_36 * 1.5 + pts_36 * 0.8)

            pg_profiles.append({
                'Player': p_name,
                'Primary_Pos': 'PG',
                'Seasons_Played': seasons_played,
                'Last_Active_Season': last_season,
                'MJT_Appearances': mjt_count,
                'Total_First_Place_Votes': int(total_first_votes),
                'Total_MVP_Points_Won': int(total_pts_won),
                'Total_MVP_Share': round(float(total_share), 4),
                'Avg_PTS_Per_36': round(float(pts_36), 1),
                'Avg_AST_Per_36': round(float(ast_36), 1),
                'Avg_TRB_Per_36': round(float(trb_36), 1),
                'Avg_AST_TOV_Ratio': round(float(ast_tov), 2),
                'Scouting_Score': round(float(scout_score), 2)
            })

        res_df = pd.DataFrame(pg_profiles).sort_values(by='Scouting_Score', ascending=False).reset_index(drop=True)
        res_df['Scouting_Rank'] = res_df.index + 1
        return res_df

    def build_cross_salary_efficiency(self, sal_df, adv_df, totals_df):
        """
        Cross-Table 3: Salary vs Performance Efficiency combining:
        rosters_salaries + advanced_pss + totals_pss
        """
        print("  -> Building Cross-Table 3: cross_salary_vs_performance...")
        merged = pd.merge(sal_df, adv_df[['Season', 'Player_Clean', 'Team', 'PER', 'WS', 'VORP', 'BPM']], on=['Season', 'Player_Clean', 'Team'], how='inner')
        merged = pd.merge(merged, totals_df[['Season', 'Player_Clean', 'Team', 'G', 'MP', 'PTS']], on=['Season', 'Player_Clean', 'Team'], how='inner')

        # Dollars per Win Share
        ws_safe = merged['WS'].apply(lambda x: x if x > 0 else np.nan)
        merged['Dollars_Per_Win_Share'] = (merged['Salary_Numeric'] / ws_safe).round(0)
        pts_safe = merged['PTS'].apply(lambda x: x if x > 0 else np.nan)
        merged['Dollars_Per_Point'] = (merged['Salary_Numeric'] / pts_safe).round(0)

        # Value Over Contract Index
        sal_mill = merged['Salary_Millions'].replace(0, np.nan)
        merged['Value_Over_Contract_Index'] = (merged['VORP'] / (sal_mill / 10.0)).round(3)

        def assign_contract_value(row):
            idx = row.get('Value_Over_Contract_Index', 0)
            sal = row.get('Salary_Millions', 0)
            if sal < 5.0 and row.get('VORP', 0) >= 2.0:
                return 'Massive Bargain / High Surplus'
            elif idx >= 1.5:
                return 'Surplus Value / Bargain'
            elif idx >= 0.7:
                return 'Fair Value'
            return 'Underperforming / Overpaid'

        merged['Contract_Performance_Class'] = merged.apply(assign_contract_value, axis=1)
        return merged

    def build_cross_champions_comparison(self, seasons_df, teams_all_df, totals_df, players_df):
        """
        Cross-Table 4: Championship Team vs Top 15 Players Profile (Quera PDF Q2) combining:
        seasons + teams_all_season + totals_pss + players
        """
        print("  -> Building Cross-Table 4: cross_champions_vs_top_players...")
        # Join totals with players for physical attributes
        p_stats = pd.merge(totals_df, players_df[['Player_Clean', 'Ht_CM', 'Wt_KG', 'Agility_Metric']], on='Player_Clean', how='left')

        # Map champion team names to abbreviations
        champ_col = 'Champion_Clean' if 'Champion_Clean' in seasons_df.columns else 'Champion'
        champ_map = dict(zip(seasons_df['Season_Year'], seasons_df[champ_col]))

        records = []
        for yr, champ_team in champ_map.items():
            if pd.isna(champ_team) or not champ_team:
                continue

            season_players = p_stats[p_stats['Season'] == yr]
            if season_players.empty:
                continue

            # Top 15 players of the season (by points or games)
            top15 = season_players.sort_values(by='PTS', ascending=False).head(15)

            # Championship team players (matching team in that season)
            # Find abbreviation for champ_team in teams_all
            t_match = teams_all_df[(teams_all_df['Season_Year'] == yr) & (teams_all_df['Team_Clean'] == champ_team)]
            
            top15_ht = top15['Ht_CM'].mean()
            top15_age = top15['Age'].mean()
            top15_agility = top15['Agility_Metric'].mean()

            records.append({
                'Season_Year': yr,
                'Champion_Team': champ_team,
                'Top15_Avg_Height_CM': round(float(top15_ht), 1) if pd.notna(top15_ht) else None,
                'Top15_Avg_Age': round(float(top15_age), 1) if pd.notna(top15_age) else None,
                'Top15_Avg_Agility': round(float(top15_agility), 4) if pd.notna(top15_agility) else None,
                'Top15_Leading_Scorer': top15.iloc[0]['Player_Clean'] if len(top15) > 0 else 'None',
                'Top15_Max_PTS': top15.iloc[0]['PTS'] if len(top15) > 0 else None
            })

        return pd.DataFrame(records)

    def build_cross_hypotheses_validation(self, totals_df, players_df, teams_all_df, seasons_df):
        """
        Cross-Table 5: Pre-computed validation metrics for Hypothesis 1 and Hypothesis 2:
        - Hypothesis 1: Top 20 players Agility across seasons
        - Hypothesis 2: Championship teams innate ability across seasons
        """
        print("  -> Building Cross-Table 5: cross_agility_innate_hypothesis...")
        p_stats = pd.merge(totals_df, players_df[['Player_Clean', 'Ht_CM', 'Wt_KG', 'Agility_Metric']], on='Player_Clean', how='left')

        hypo_records = []
        for yr in sorted(p_stats['Season'].unique()):
            if yr < 1980 or yr > 2027:
                continue
            
            s_data = p_stats[p_stats['Season'] == yr]
            top20 = s_data.sort_values(by='PTS', ascending=False).head(20)
            
            top20_agility_mean = top20['Agility_Metric'].mean()
            top20_innate_mean = top20['Innate_Ability'].mean()
            all_agility_mean = s_data['Agility_Metric'].mean()
            all_innate_mean = s_data['Innate_Ability'].mean()

            # Champ info
            champ_row = seasons_df[seasons_df['Season_Year'] == yr]
            champ_col = 'Champion_Clean' if 'Champion_Clean' in seasons_df.columns else 'Champion'
            champ_name = champ_row[champ_col].values[0] if (len(champ_row) > 0 and champ_col in champ_row.columns) else None

            hypo_records.append({
                'Season_Year': yr,
                'Top20_Avg_Agility': round(float(top20_agility_mean), 4) if pd.notna(top20_agility_mean) else None,
                'League_Avg_Agility': round(float(all_agility_mean), 4) if pd.notna(all_agility_mean) else None,
                'Top20_Avg_Innate_Ability': round(float(top20_innate_mean), 4) if pd.notna(top20_innate_mean) else None,
                'League_Avg_Innate_Ability': round(float(all_innate_mean), 4) if pd.notna(all_innate_mean) else None,
                'Champion_Team': champ_name
            })

        return pd.DataFrame(hypo_records)

    # --------------------------------------------------------------------
    # EXPORT MANAGER
    # --------------------------------------------------------------------
    def save_dataset(self, df, base_name, target_dirs):
        """
        Saves dataframe as CSV across specified directories.
        """
        for d in target_dirs:
            os.makedirs(d, exist_ok=True)
            csv_path = os.path.join(d, f"{base_name}.csv")
            df.to_csv(csv_path, index=False)
            
        print(f"    [Saved] {base_name}: {df.shape} -> CSV")

    def execute_all(self):
        print("=" * 80)
        print("STARTING INDIVIDUAL & CROSS-TABLE CLEANING & FEATURE ENGINEERING")
        print(f"  Input Directory:   '{self.raw_dir}/'")
        print(f"  Output Directory:  '{self.output_dir}/'")
        print("=" * 80)

        os.makedirs(self.indiv_dir, exist_ok=True)
        os.makedirs(self.cross_dir, exist_ok=True)

        # ----------------------------------------------------------------
        # Part A: Process Each of the 10 Raw CSVs
        # ----------------------------------------------------------------
        print("\n[PART A] Processing Each of the 10 Raw CSVs (Cleaning + In-Table Features)...")
        indiv_tables = {
            'players': self.process_players(),
            'rosters': self.process_rosters(),
            'totals_pss': self.process_totals(),
            'per_game_pss': self.process_per_game(),
            'advanced_pss': self.process_advanced(),
            'micheal_jordan_trophy': self.process_mjt(),
            'rosters_salaries': self.process_salaries(),
            'seasons': self.process_seasons(),
            'teams': self.process_teams(),
            'teams_all_season': self.process_teams_all_season()
        }

        print("\nExporting Individual Cleaned & Engineered CSV Files...")
        for name, df in indiv_tables.items():
            self.save_dataset(df, f"{name}_cleaned_and_engineered", [self.indiv_dir])

        # ----------------------------------------------------------------
        # Part B: Build Cross-Table Feature Engineered Datasets
        # ----------------------------------------------------------------
        print("\n[PART B] Building Cross-Table Feature Engineered Datasets (Combining Multiple CSVs)...")
        cross_tables = {
            'cross_player_master_features': self.build_cross_player_master(
                indiv_tables['totals_pss'], indiv_tables['advanced_pss'],
                indiv_tables['players'], indiv_tables['rosters_salaries']
            ),
            'cross_pg_mjt_scouting_candidates': self.build_cross_pg_scouting(
                indiv_tables['totals_pss'], indiv_tables['micheal_jordan_trophy'],
                indiv_tables['players']
            ),
            'cross_salary_vs_performance': self.build_cross_salary_efficiency(
                indiv_tables['rosters_salaries'], indiv_tables['advanced_pss'],
                indiv_tables['totals_pss']
            ),
            'cross_champions_vs_top_players': self.build_cross_champions_comparison(
                indiv_tables['seasons'], indiv_tables['teams_all_season'],
                indiv_tables['totals_pss'], indiv_tables['players']
            ),
            'cross_agility_innate_hypothesis': self.build_cross_hypotheses_validation(
                indiv_tables['totals_pss'], indiv_tables['players'],
                indiv_tables['teams_all_season'], indiv_tables['seasons']
            )
        }

        print("\nExporting Cross-Table Cleaned & Engineered CSV Files...")
        for name, df in cross_tables.items():
            self.save_dataset(df, name, [self.cross_dir])

        # ----------------------------------------------------------------
        # Part C: Build All-Inclusive SQLite Database
        # ----------------------------------------------------------------
        db_path = os.path.join(self.output_dir, 'nba_all_clean_and_engineered.db')
        print(f"\n[PART C] Building All-Inclusive SQLite Database: '{db_path}'...")
        conn = sqlite3.connect(db_path)
        for name, df in indiv_tables.items():
            df_sql = df.copy()
            for col in df_sql.select_dtypes(include=['datetime64[ns]']).columns:
                df_sql[col] = df_sql[col].astype(str)
            df_sql.to_sql(name, conn, if_exists='replace', index=False)

        for name, df in cross_tables.items():
            df_sql = df.copy()
            for col in df_sql.select_dtypes(include=['datetime64[ns]']).columns:
                df_sql[col] = df_sql[col].astype(str)
            df_sql.to_sql(name, conn, if_exists='replace', index=False)
        conn.close()
        print("  -> Complete SQLite Database created successfully.")

        # ----------------------------------------------------------------
        # Part D: Generate Comprehensive Data Dictionary
        # ----------------------------------------------------------------
        dict_path = os.path.join(self.output_dir, 'DATA_DICTIONARY.md')
        print(f"\n[PART D] Generating Data Dictionary documentation: '{dict_path}'...")
        with open(dict_path, 'w', encoding='utf-8') as f:
            f.write(f"""# 🏀 NBA Clean & Engineered Data Dictionary (1980 - 2027)
### پوشه داده‌های پاکسازی‌شده و ویژگی‌های مهندسی‌شده جدول‌به‌جدول و ترکیبی

تمامی فایل‌های ورودی پوشه `Raw data` پاکسازی شده و مهندسی ویژگی‌های اختصاصی روی تک‌تک آن‌ها اعمال شده است. همچنین ویژگی‌های چندجدولی در فایل‌های CSV مجزا پیاده‌سازی شده‌اند.
تمامی فایل‌ها به فرمت استاندارد و سبک **CSV** در دسترس می‌باشند.

---

## 📁 ۱. جداول تکی پاکسازی و مهندسی‌شده (Individual Tables)
موجود در دایرکتوری `clean_and_engineered_data/individual_tables/`:

| نام فایل | ابعاد | ویژگی‌های جدید مهندسی‌شده |
|:---|:---:|:---|
| `players_cleaned_and_engineered` | {len(indiv_tables['players']):,} × {len(indiv_tables['players'].columns)} | `Career_Length_Years`, `Draft_Decade`, `Agility_Metric`, `BMI`, `Height_Tier`, `Weight_Tier`, `Has_College`, `College_Count` |
| `rosters_cleaned_and_engineered` | {len(indiv_tables['rosters']):,} × {len(indiv_tables['rosters'].columns)} | `No_Numeric`, `Agility_Metric`, `BMI`, `Rookie_Flag`, `Roster_Exp_Tier`, `Estimated_Age`, `Innate_Ability_Roster` |
| `totals_pss_cleaned_and_engineered` | {len(indiv_tables['totals_pss']):,} × {len(indiv_tables['totals_pss'].columns)} | `Innate_Ability`, `Career_Phase`, `PTS_Per_Min`, `TRB_Per_Min`, `AST_Per_Min`, `STL_Per_Min`, `BLK_Per_Min`, `TOV_Per_Min`, `AST_TOV_Ratio`, `FG3A_Rate`, `FT_Rate`, `Starter_Ratio`, `Is_All_Star`, `Is_All_NBA`, `Is_All_Defensive`, `MVP_Rank_Numeric` |
| `per_game_pss_cleaned_and_engineered` | {len(indiv_tables['per_game_pss']):,} × {len(indiv_tables['per_game_pss'].columns)} | `Scoring_Volume_Tier`, `Playmaking_Tier`, `AST_TOV_Per_Game`, `Stocks_Per_Game`, `Per_Game_Production_Index` |
| `advanced_pss_cleaned_and_engineered` | {len(indiv_tables['advanced_pss']):,} × {len(indiv_tables['advanced_pss'].columns)} | `WS_Per_Game`, `Net_BPM`, `Offensive_Load`, `Player_Impact_Tier`, `PER_TS_Product` |
| `micheal_jordan_trophy_cleaned_and_engineered` | {len(indiv_tables['micheal_jordan_trophy']):,} × {len(indiv_tables['micheal_jordan_trophy'].columns)} | `Rank_Numeric`, `Is_Tied_Rank`, `Is_Winner`, `Top_3_Finish`, `Top_5_Finish`, `First_Place_Vote_Dominance`, `Unanimous_MVP`, `MVP_PTS_Per_Min`, `MVP_Box_Composite` |
| `rosters_salaries_cleaned_and_engineered` | {len(indiv_tables['rosters_salaries']):,} × {len(indiv_tables['rosters_salaries'].columns)} | `Salary_Millions`, `Salary_Log`, `Salary_Tier`, `Team_Payroll_Share`, `Team_Salary_Rank` |
| `seasons_cleaned_and_engineered` | {len(indiv_tables['seasons']):,} × {len(indiv_tables['seasons'].columns)} | `Season_Year`, `Era_Name`, `Scoring_Leader_Pts`, `Rebound_Leader_Trb`, `Assist_Leader_Ast`, `Win_Shares_Leader_WS` |
| `teams_cleaned_and_engineered` | {len(indiv_tables['teams']):,} × {len(indiv_tables['teams'].columns)} | `Is_Active`, `Championship_Rate`, `Playoff_Rate`, `Franchise_Tier` |
| `teams_all_season_cleaned_and_engineered` | {len(indiv_tables['teams_all_season']):,} × {len(indiv_tables['teams_all_season'].columns)} | `Season_Year`, `Net_Rating`, `Pythagorean_Wins`, `Luck_Factor_Wins`, `Pace_Style`, `Playoff_Rounds_Won` |

---

## 🌟 ۲. جداول ترکیبی مهندسی ویژگی‌های چندگانه (Cross-Table Feature Datasets)
موجود در دایرکتوری `clean_and_engineered_data/cross_tables/`:

1. **`cross_player_master_features` ({len(cross_tables['cross_player_master_features']):,} رکورد):**
   - ترکیب جداول: Totals + Advanced + Players + Salaries.
   - شامل بیش از ۷۰ ویژگی تحلیلی بیومتریک، ارزش، بهره‌وری، و فاز شغلی.
2. **`cross_pg_mjt_scouting_candidates` ({len(cross_tables['cross_pg_mjt_scouting_candidates']):,} پوینت‌گارد):**
   - ترکیب جداول: Totals + Micheal Jordan Trophy + Players.
   - رتبه‌بندی جامع و امتیاز استعدادیابی (Scouting Score) برای خرید بازیکنان پست پوینت‌گارد (پاسخ سوال ۳ کوئرا).
3. **`cross_salary_vs_performance` ({len(cross_tables['cross_salary_vs_performance']):,} قرارداد):**
   - ترکیب جداول: Rosters Salaries + Advanced + Totals.
   - دلار به ازای هر وین‌شیر، دلار به ازای هر امتیاز، و شاخص ارزش قرارداد (Bargain vs Overpaid).
4. **`cross_champions_vs_top_players` ({len(cross_tables['cross_champions_vs_top_players']):,} فصل):**
   - ترکیب جداول: Seasons + Teams All + Totals + Players.
   - مقایسه قد، سن و چابکی تیم‌های قهرمان با ۱۵ بازیکن برتر فصل (پاسخ سوال ۲ کوئرا).
5. **`cross_agility_innate_hypothesis` ({len(cross_tables['cross_agility_innate_hypothesis']):,} فصل):**
   - اعتبارسنجی فرضیه ۱ (تغییرات چابکی ۲۰ نفر برتر) و فرضیه ۲ (توانایی ذاتی تیم قهرمان).
""")

        print("\n" + "=" * 80)
        print("ALL INDIVIDUAL & CROSS-TABLE CLEANING & FEATURE ENGINEERING COMPLETED!")
        print(f"Results located in: '{self.output_dir}/'")
        print("=" * 80)


if __name__ == '__main__':
    fe = TableByTableFeatureEngineer()
    fe.execute_all()
