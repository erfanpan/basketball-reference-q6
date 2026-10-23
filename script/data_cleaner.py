"""
data_cleaner.py
================
OOP-based Data Cleaning Module for NBA Basketball Reference Datasets.
Comprehensive handling of Mojibake artifacts, League Average summary rows,
multi-team trade aggregate stints, physical units parsing, and type conversions.
"""

import os
import re
import numpy as np
import pandas as pd


class NBADataCleaner:
    """
    Dedicated Data Cleaning Pipeline for NBA Basketball-Reference datasets.
    """

    def __init__(self, data_dir="."):
        self.data_dir = data_dir

    @staticmethod
    def fix_mojibake(text):
        """
        Fix Latin-1 / UTF-8 Mojibake artifacts (e.g., 'Luka DonÄ\x8diÄ\x87' -> 'Luka Dončić').
        """
        if not isinstance(text, str):
            return text
        try:
            return text.encode('latin1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text

    @classmethod
    def clean_player_name(cls, name):
        """
        Normalize player names: fix encoding, strip Hall of Fame asterisks, and strip whitespace.
        """
        if not isinstance(name, str):
            return name
        name_fixed = cls.fix_mojibake(name)
        return name_fixed.replace('*', '').strip()

    @staticmethod
    def parse_height(ht_str):
        """
        Parse height formatted as 'feet-inches' (e.g. '6-8') into total inches and centimeters.
        Returns a tuple: (height_inches, height_cm).
        """
        if not isinstance(ht_str, str) or '-' not in ht_str:
            return np.nan, np.nan
        try:
            parts = ht_str.strip().split('-')
            feet = int(parts[0])
            inches = int(parts[1])
            total_inches = feet * 12 + inches
            height_cm = round(total_inches * 2.54, 2)
            return total_inches, height_cm
        except (ValueError, IndexError):
            return np.nan, np.nan

    @staticmethod
    def parse_weight_to_kg(wt_lbs):
        """
        Convert weight from pounds (lbs) to kilograms (kg).
        """
        if pd.isna(wt_lbs):
            return np.nan
        try:
            return round(float(wt_lbs) * 0.45359237, 2)
        except ValueError:
            return np.nan

    @staticmethod
    def parse_experience(exp_val):
        """
        Convert NBA experience to numeric integer. 'R' (Rookie) maps to 0.
        """
        if pd.isna(exp_val):
            return np.nan
        val_str = str(exp_val).strip()
        if val_str.upper() == 'R':
            return 0
        try:
            return int(float(val_str))
        except ValueError:
            return np.nan

    @staticmethod
    def parse_salary(salary_str):
        """
        Convert formatted currency string (e.g. '$25,102,511') to numeric float.
        """
        if pd.isna(salary_str):
            return np.nan
        cleaned = re.sub(r'[^\d.]', '', str(salary_str))
        try:
            return float(cleaned)
        except ValueError:
            return np.nan

    def clean_players(self, path=None):
        """
        Clean players.csv:
        - Normalize names
        - Parse height (inches & cm)
        - Parse weight (lbs & kg)
        - Parse birth date to datetime
        """
        path = path or os.path.join(self.data_dir, 'players.csv')
        df = pd.read_csv(path)
        
        df['Player_Clean'] = df['Player'].apply(self.clean_player_name)
        heights = df['Ht'].apply(self.parse_height)
        df['Ht_Inches'] = [h[0] for h in heights]
        df['Ht_CM'] = [h[1] for h in heights]
        df['Wt_LBS'] = pd.to_numeric(df['Wt'], errors='coerce')
        df['Wt_KG'] = df['Wt_LBS'].apply(self.parse_weight_to_kg)
        df['Birth_Date_DT'] = pd.to_datetime(df['Birth Date'], errors='coerce')
        df['Colleges'] = df['Colleges'].fillna('None')
        
        return df

    def clean_rosters(self, path=None):
        """
        Clean rosters.csv:
        - Normalize names
        - Parse height & weight
        - Convert 'R' to 0 in experience
        - Parse birth date
        """
        path = path or os.path.join(self.data_dir, 'rosters.csv')
        df = pd.read_csv(path)
        
        df['Player_Clean'] = df['Player'].apply(self.clean_player_name)
        heights = df['Ht'].apply(self.parse_height)
        df['Ht_Inches'] = [h[0] for h in heights]
        df['Ht_CM'] = [h[1] for h in heights]
        df['Wt_LBS'] = pd.to_numeric(df['Wt'], errors='coerce')
        df['Wt_KG'] = df['Wt_LBS'].apply(self.parse_weight_to_kg)
        df['Exp_Numeric'] = df['Exp'].apply(self.parse_experience)
        df['Birth_Date_DT'] = pd.to_datetime(df['Birth Date'], errors='coerce')
        df['College'] = df['College'].fillna('None')
        
        return df

    def clean_player_season_stats(self, filename):
        """
        Clean totals_pss.csv, per_game_pss.csv, or advanced_pss.csv:
        - Remove 'League Average' aggregate summary rows
        - Normalize names
        - Flag multi-team traded player rows (e.g. '2TM', '3TM')
        - Fill 0/0 percentage NaNs where attempts were 0
        """
        path = os.path.join(self.data_dir, filename)
        df = pd.read_csv(path)
        
        # Remove League Average
        df = df[df['Player'] != 'League Average'].copy()
        df = df[df['Rk'].notnull()].copy()
        
        df['Player_Clean'] = df['Player'].apply(self.clean_player_name)
        df['Rk'] = df['Rk'].astype(int)
        df['Season'] = df['Season'].astype(int)
        
        # Flag trade aggregate stint (2TM, 3TM, 4TM)
        df['Is_Multi_Team_Aggregate'] = df['Team'].str.contains(r'^\d+TM$', na=False)
        
        # Percentage columns: fill with 0.0 where appropriate
        pct_cols = [c for c in df.columns if '%' in c or c in ['3PAr', 'FTr']]
        for col in pct_cols:
            df[col] = df[col].fillna(0.0)
            
        return df

    def clean_mjt(self, path=None):
        """
        Clean micheal_jordan_trophy.csv:
        - Normalize names
        - Convert numeric types
        """
        path = path or os.path.join(self.data_dir, 'micheal_jordan_trophy.csv')
        df = pd.read_csv(path)
        
        df['Player_Clean'] = df['Player'].apply(self.clean_player_name)
        df['Rank_Numeric'] = pd.to_numeric(df['Rank'].astype(str).str.replace('T', '', regex=False), errors='coerce')
        df['Season'] = df['Season'].astype(int)
        
        return df

    def clean_salaries(self, path=None):
        """
        Clean rosters_salaries.csv:
        - Rename 'Unnamed: 3' to 'Player'
        - Normalize names
        - Parse salary into float
        """
        path = path or os.path.join(self.data_dir, 'rosters_salaries.csv')
        df = pd.read_csv(path)
        
        if 'Unnamed: 3' in df.columns:
            df.rename(columns={'Unnamed: 3': 'Player'}, inplace=True)
            
        df = df[df['Player'].notnull()].copy()
        df['Player_Clean'] = df['Player'].apply(self.clean_player_name)
        df['Salary_Numeric'] = df['Salary'].apply(self.parse_salary)
        
        return df

    def clean_seasons(self, path=None):
        """
        Clean seasons.csv:
        - Filter out header repetitions and non-season rows
        - Extract clean player names and values for awards and league leaders
        """
        path = path or os.path.join(self.data_dir, 'seasons.csv')
        df = pd.read_csv(path)
        
        # Keep valid seasons (format: YYYY-YY or similar)
        df = df[df['Season'].notnull()].copy()
        df = df[df['Season'].str.match(r'^\d{4}-\d{2}$', na=False)].copy()
        
        # Clean MVP and leader columns
        for col in ['MVP', 'Rookie of the Year', 'Points', 'Rebounds', 'Assists', 'Win Shares']:
            if col in df.columns:
                df[f'{col}_Clean'] = df[col].apply(self.clean_player_name)
                
        return df

    def clean_teams(self, path=None):
        """
        Clean teams.csv
        """
        path = path or os.path.join(self.data_dir, 'teams.csv')
        df = pd.read_csv(path)
        return df

    def clean_teams_all_season(self, path=None):
        """
        Clean teams_all_season.csv:
        - Drop 100% null divider columns (Unnamed: 8, Unnamed: 15)
        - Clean playoff asterisks from Team name
        """
        path = path or os.path.join(self.data_dir, 'teams_all_season.csv')
        df = pd.read_csv(path)
        
        # Drop empty columns
        drop_cols = [c for c in ['Unnamed: 8', 'Unnamed: 15'] if c in df.columns]
        if drop_cols:
            df.drop(columns=drop_cols, inplace=True)
            
        df['Team_Clean'] = df['Team'].str.replace('*', '', regex=False).str.strip()
        df['Made_Playoffs'] = df['Team'].str.contains(r'\*$', na=False)
        return df
