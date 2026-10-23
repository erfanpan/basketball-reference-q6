"""
feature_engineer.py
====================
OOP-based Feature Engineering Module for NBA Basketball Reference Datasets.
Constructs biometric agility indicators, innate ability scores, BMI, efficiency rates,
decision-making ratios, career phase categories, position flags, and economic value measures.
"""

import numpy as np
import pandas as pd


class NBAFeatureEngineer:
    """
    Constructs and transforms advanced domain features for NBA players,
    supporting statistical modeling and scouting evaluations.
    """

    def __init__(self, data_dict):
        """
        data_dict contains cleaned dataframes:
        {'players', 'rosters', 'totals', 'per_game', 'advanced', 'mjt', 'salaries', 'seasons'}
        """
        self.data = data_dict
        self._build_player_master_map()

    def _build_player_master_map(self):
        """
        Build an aggregated player reference table for Height, Weight, and Experience.
        """
        p_df = self.data['players'].dropna(subset=['Ht_CM', 'Wt_KG'])
        p_map = p_df.drop_duplicates(subset=['Player_Clean']).set_index('Player_Clean')
        
        r_df = self.data['rosters'].dropna(subset=['Ht_CM', 'Wt_KG'])
        r_map = r_df.drop_duplicates(subset=['Player_Clean']).set_index('Player_Clean')
        
        self.ht_cm_map = p_map['Ht_CM'].combine_first(r_map['Ht_CM']).to_dict()
        self.wt_kg_map = p_map['Wt_KG'].combine_first(r_map['Wt_KG']).to_dict()
        self.ht_in_map = p_map['Ht_Inches'].combine_first(r_map['Ht_Inches']).to_dict()
        self.wt_lbs_map = p_map['Wt_LBS'].combine_first(r_map['Wt_LBS']).to_dict()
        
        # Build season-specific experience mapping
        r_exp = self.data['rosters'].dropna(subset=['Exp_Numeric'])
        self.exp_season_map = r_exp.set_index(['Player_Clean', 'Season'])['Exp_Numeric'].to_dict()

    def get_player_exp(self, player_name, season):
        """
        Get player experience for a specific season.
        """
        if (player_name, season) in self.exp_season_map:
            return self.exp_season_map[(player_name, season)]
        # Fallback to any season roster record
        sub = self.data['rosters'][self.data['rosters']['Player_Clean'] == player_name]
        if len(sub) > 0 and sub['Exp_Numeric'].notnull().any():
            valid_row = sub.dropna(subset=['Exp_Numeric']).iloc[0]
            base_exp = valid_row['Exp_Numeric']
            base_s = valid_row['Season']
            return max(0, int(base_exp + (season - base_s)))
        return np.nan

    def compute_agility(self, df):
        """
        Feature 1: Player Agility (Height / Weight).
        Calculates metric (cm/kg) and imperial (in/lbs) ratios.
        Also calculates Body Mass Index (BMI).
        """
        df = df.copy()
        if 'Ht_CM' not in df.columns or df['Ht_CM'].isnull().all():
            df['Ht_CM'] = df['Player_Clean'].map(self.ht_cm_map)
        if 'Wt_KG' not in df.columns or df['Wt_KG'].isnull().all():
            df['Wt_KG'] = df['Player_Clean'].map(self.wt_kg_map)
        if 'Ht_Inches' not in df.columns or df['Ht_Inches'].isnull().all():
            df['Ht_Inches'] = df['Player_Clean'].map(self.ht_in_map)
        if 'Wt_LBS' not in df.columns or df['Wt_LBS'].isnull().all():
            df['Wt_LBS'] = df['Player_Clean'].map(self.wt_lbs_map)

        # Agility Ratio = Height / Weight
        df['Agility_Metric'] = df['Ht_CM'] / df['Wt_KG']
        df['Agility_Imperial'] = df['Ht_Inches'] / df['Wt_LBS']
        
        # BMI = Wt (kg) / (Ht (m))^2
        df['BMI'] = df['Wt_KG'] / ((df['Ht_CM'] / 100.0) ** 2)
        return df

    def compute_innate_ability(self, df):
        """
        Feature 2: Innate Ability (Exp / Age).
        Calculates the ratio of experience to biological age.
        """
        df = df.copy()
        if 'Exp_Numeric' not in df.columns or df['Exp_Numeric'].isnull().all():
            df['Exp_Numeric'] = df.apply(lambda r: self.get_player_exp(r['Player_Clean'], r['Season']), axis=1)

        df['Innate_Ability'] = df['Exp_Numeric'] / df['Age']
        
        # Categorize career phase
        def categorize_phase(exp):
            if pd.isna(exp):
                return 'Unknown'
            if exp <= 1:
                return 'Rookie/Sophomore'
            elif exp <= 4:
                return 'Developing'
            elif exp <= 10:
                return 'Peak Prime'
            else:
                return 'Veteran Core'
                
        df['Career_Phase'] = df['Exp_Numeric'].apply(categorize_phase)
        return df

    def compute_efficiency_and_scouting_metrics(self, df_totals, df_advanced):
        """
        Merges totals and advanced stats to calculate:
        - Points per minute
        - Assist to turnover ratio
        - Win shares per game
        - True shooting efficiency
        """
        # Deduplicate to keep season totals (2TM / single team)
        def deduplicate_season(df, sort_col):
            df_sorted = df.sort_values(by=[sort_col, 'G'], ascending=False)
            return df_sorted.drop_duplicates(subset=['Player_Clean', 'Season']).copy()

        tot_clean = deduplicate_season(df_totals, 'PTS')
        adv_clean = deduplicate_season(df_advanced, 'WS')

        merged = pd.merge(
            tot_clean,
            adv_clean[['Player_Clean', 'Season', 'PER', 'TS%', 'USG%', 'OWS', 'DWS', 'WS', 'WS/48', 'BPM', 'VORP']],
            on=['Player_Clean', 'Season'],
            how='inner'
        )

        merged = self.compute_agility(merged)
        merged = self.compute_innate_ability(merged)

        # Efficiency features
        merged['PTS_Per_Min'] = np.where(merged['MP'] > 0, merged['PTS'] / merged['MP'], 0.0)
        merged['AST_TOV_Ratio'] = np.where(merged['TOV'] > 0, merged['AST'] / merged['TOV'], merged['AST'])
        merged['WS_Per_Game'] = np.where(merged['G'] > 0, merged['WS'] / merged['G'], 0.0)
        
        # Position indicators
        merged['Is_PG'] = merged['Pos'].str.contains('PG', na=False)
        merged['Is_Wing'] = merged['Pos'].str.contains('SG|SF', na=False)
        merged['Is_Big'] = merged['Pos'].str.contains('PF|C', na=False)

        return merged

    def compute_mjt_scouting_profile(self, min_season=1980, max_season=2026):
        """
        Constructs scouting profiles for players appearing in the
        Michael Jordan Trophy (MVP) voting list from min_season to max_season.
        """
        mjt = self.data['mjt']
        mjt_filtered = mjt[mjt['Season'].between(min_season, max_season)].copy()
        
        summary = mjt_filtered.groupby('Player_Clean').agg(
            MJT_Appearances=('Season', 'count'),
            Seasons_List=('Season', lambda s: sorted(list(s))),
            Total_Share=('Share', 'sum'),
            Total_First_Votes=('First', 'sum'),
            Avg_PTS=('PTS', 'mean'),
            Avg_AST=('AST', 'mean'),
            Avg_TRB=('TRB', 'mean'),
            Avg_WS=('WS', 'mean'),
            Avg_WS48=('WS/48', 'mean'),
            Avg_Age=('Age', 'mean')
        ).reset_index()

        summary = self.compute_agility(summary)

        totals = self.data['totals']
        pg_players = set(totals[totals['Pos'].str.contains('PG', na=False)]['Player_Clean'].unique())
        summary['Is_PG'] = summary['Player_Clean'].isin(pg_players)

        summary.sort_values(by=['MJT_Appearances', 'Total_Share'], ascending=False, inplace=True)
        return summary
