"""
run_data_pipeline.py
=====================
Pipeline for Data Cleaning and Feature Engineering (NBA Basketball Reference).
Executes end-to-end data cleansing, feature construction, relational SQLite DB export,
and exploratory visualizations of engineered metrics.
"""

import os
import json
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from src.data_cleaner import NBADataCleaner
from src.feature_engineer import NBAFeatureEngineer


def run_pipeline():
    print("=" * 75)
    print("STARTING DATA CLEANING & FEATURE ENGINEERING PIPELINE")
    print("=" * 75)

    os.makedirs('data/cleaned', exist_ok=True)
    os.makedirs('figures', exist_ok=True)

    # 1. DATA CLEANING
    print("\n[Step 1/4] Executing Data Cleaning on Raw Datasets...")
    cleaner = NBADataCleaner(data_dir=".")

    cleaned_data = {
        'players': cleaner.clean_players('players.csv'),
        'rosters': cleaner.clean_rosters('rosters.csv'),
        'totals': cleaner.clean_player_season_stats('totals_pss.csv'),
        'per_game': cleaner.clean_player_season_stats('per_game_pss.csv'),
        'advanced': cleaner.clean_player_season_stats('advanced_pss.csv'),
        'mjt': cleaner.clean_mjt('micheal_jordan_trophy.csv'),
        'salaries': cleaner.clean_salaries('rosters_salaries.csv'),
        'seasons': cleaner.clean_seasons('seasons.csv'),
        'teams': cleaner.clean_teams('teams.csv'),
        'teams_all_season': cleaner.clean_teams_all_season('teams_all_season.csv')
    }

    # Export cleaned CSVs
    for name, df in cleaned_data.items():
        out_csv = os.path.join('data/cleaned', f'{name}_cleaned.csv')
        df.to_csv(out_csv, index=False)
        print(f"  -> Cleaned {name:<16}: {str(df.shape):<14} saved to {out_csv}")

    # 2. SQLITE RELATIONAL DATABASE
    print("\n[Step 2/4] Building Normalized Relational SQLite Database...")
    db_path = os.path.join('data/cleaned', 'nba_analytics.db')
    conn = sqlite3.connect(db_path)
    for name, df in cleaned_data.items():
        df_sql = df.copy()
        for col in df_sql.select_dtypes(include=['datetime64[ns]']).columns:
            df_sql[col] = df_sql[col].astype(str)
        df_sql.to_sql(name, conn, if_exists='replace', index=False)
    conn.close()
    print(f"  -> SQLite Database successfully generated at: {db_path}")

    # 3. FEATURE ENGINEERING
    print("\n[Step 3/4] Constructing Domain Features...")
    fe = NBAFeatureEngineer(cleaned_data)
    master_df = fe.compute_efficiency_and_scouting_metrics(cleaned_data['totals'], cleaned_data['advanced'])
    master_path = os.path.join('data/cleaned', 'player_master_features.csv')
    master_df.to_csv(master_path, index=False)
    print(f"  -> Master feature dataset: {master_df.shape} saved to {master_path}")

    # Point Guard Scouting Profiles
    pg_profile = fe.compute_mjt_scouting_profile(1980, 2026)
    pg_candidates = pg_profile[pg_profile['Is_PG']].copy()
    pg_path = os.path.join('data/cleaned', 'pg_mjt_candidates.csv')
    pg_candidates.to_csv(pg_path, index=False)
    print(f"  -> Point guard scouting profiles: {pg_candidates.shape} saved to {pg_path}")

    # Update SQLite with feature tables
    conn = sqlite3.connect(db_path)
    master_df.to_sql('player_master_features', conn, if_exists='replace', index=False)
    
    pg_sql = pg_candidates.copy()
    if 'Seasons_List' in pg_sql.columns:
        pg_sql['Seasons_List'] = pg_sql['Seasons_List'].apply(lambda x: ', '.join(map(str, x)) if isinstance(x, list) else str(x))
    pg_sql.to_sql('pg_mjt_candidates', conn, if_exists='replace', index=False)
    conn.close()
    print("  -> Feature tables stored into SQLite Database.")

    # 4. EXPLORATORY VISUALIZATIONS OF ENGINEERED FEATURES
    print("\n[Step 4/4] Rendering Feature Visualizations...")
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

    # Figure 1: Distributions of Agility, Innate Ability, BMI, PPM
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    sns.histplot(master_df['Agility_Metric'].dropna(), kde=True, color='#1f77b4', ax=axes[0, 0], bins=30)
    axes[0, 0].axvline(master_df['Agility_Metric'].mean(), color='red', linestyle='--', label=f"Mean = {master_df['Agility_Metric'].mean():.2f}")
    axes[0, 0].set_title("Distribution: Agility Metric (Ht cm / Wt kg)", fontweight='bold')
    axes[0, 0].set_xlabel("Agility (cm / kg)")
    axes[0, 0].legend()

    sns.histplot(master_df['Innate_Ability'].dropna(), kde=True, color='#ff7f0e', ax=axes[0, 1], bins=30)
    axes[0, 1].axvline(master_df['Innate_Ability'].mean(), color='darkred', linestyle='--', label=f"Mean = {master_df['Innate_Ability'].mean():.2f}")
    axes[0, 1].set_title("Distribution: Innate Ability Ratio (Exp / Age)", fontweight='bold')
    axes[0, 1].set_xlabel("Innate Ability (Exp / Age)")
    axes[0, 1].legend()

    pos_order = ['PG', 'SG', 'SF', 'PF', 'C']
    sub_pos = master_df[master_df['Pos'].isin(pos_order)]
    sns.boxplot(x='Pos', y='Agility_Metric', data=sub_pos, order=pos_order, palette='Blues_r', ax=axes[1, 0])
    axes[1, 0].set_title("Agility Metric by Primary Position", fontweight='bold')
    axes[1, 0].set_xlabel("Position")
    axes[1, 0].set_ylabel("Agility (cm / kg)")

    phase_order = ['Rookie/Sophomore', 'Developing', 'Peak Prime', 'Veteran Core']
    sub_phase = master_df[(master_df['Career_Phase'].isin(phase_order)) & (master_df['MP'] > 300)]
    sns.boxplot(x='Career_Phase', y='AST_TOV_Ratio', data=sub_phase, order=phase_order, palette='mako', ax=axes[1, 1])
    axes[1, 1].set_title("Assist-to-Turnover Ratio across Career Phases (MP > 300)", fontweight='bold')
    axes[1, 1].set_xlabel("Career Phase")
    axes[1, 1].set_ylabel("AST / TOV Ratio")
    axes[1, 1].set_ylim(0, 5)

    plt.suptitle("Feature Engineering: Distributions & Domain Metric Profiles", fontweight='bold', fontsize=15, y=1.02)
    plt.tight_layout()
    f1_path = os.path.join('figures', 'feature_engineering_distributions.png')
    plt.savefig(f1_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  -> Generated: {f1_path}")

    # Figure 2: Physical scatter: Height vs Weight with Agility Color Map
    fig, ax = plt.subplots(figsize=(10, 6))
    sc = ax.scatter(master_df['Ht_CM'], master_df['Wt_KG'], c=master_df['Agility_Metric'], cmap='viridis', alpha=0.6, edgecolors='none', s=25)
    plt.colorbar(sc, label="Agility Metric (cm / kg)")
    ax.set_title("Biometric Profile: Height (cm) vs Weight (kg) Colored by Agility Ratio", fontweight='bold')
    ax.set_xlabel("Height (cm)")
    ax.set_ylabel("Weight (kg)")
    plt.tight_layout()
    f2_path = os.path.join('figures', 'biometric_height_weight_agility.png')
    plt.savefig(f2_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  -> Generated: {f2_path}")

    print("\n" + "=" * 75)
    print("DATA CLEANING & FEATURE ENGINEERING PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    run_pipeline()
