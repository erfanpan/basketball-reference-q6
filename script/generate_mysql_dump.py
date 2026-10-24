"""
generate_mysql_dump.py
======================
Generates:
1. CSV files for each normalized MySQL table in 'Data Base/tables_csv/'.
2. 'Data Base/load_data.sql': High-performance bulk data loading script using
   'LOAD DATA LOCAL INFILE' for each table.
3. 'Data Base/nba_db.sql': Complete standalone SQL dump with DDL and INSERT statements.
All covering historical NBA seasons from 1980 through 2027.
"""

import os
import re
import csv
import pandas as pd
import numpy as np


def clean_val(val, is_float=False):
    if pd.isna(val) or val is None or str(val).strip().lower() in ['nan', 'none', 'null', '']:
        return None
    try:
        if is_float:
            return round(float(val), 4)
        return int(float(val))
    except (ValueError, TypeError):
        return None


def clean_sql_str(val):
    if val is None or pd.isna(val) or str(val).strip().lower() in ['nan', 'none', 'null', '']:
        return "NULL"
    s = str(val).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"


def clean_sql_num(val, is_float=False):
    v = clean_val(val, is_float=is_float)
    if v is None:
        return "NULL"
    return str(v)


def build_mysql_dump(cleaned_data=None, data_dir='cleaned-data', output_dir='Data Base'):
    print("=" * 75)
    print("BUILDING MYSQL NORMALIZED TABLES & BULK LOAD SCRIPTS (1980 - 2027)")
    print("=" * 75)

    os.makedirs(output_dir, exist_ok=True)
    tables_csv_dir = os.path.join(output_dir, 'tables_csv')
    os.makedirs(tables_csv_dir, exist_ok=True)

    # 1. Load Cleaned Datasets
    if cleaned_data is None:
        print(f"Loading cleaned data from directory: {data_dir}...")
        totals_df = pd.read_csv(os.path.join(data_dir, 'totals_cleaned.csv'))
        advanced_df = pd.read_csv(os.path.join(data_dir, 'advanced_cleaned.csv'))
        players_df = pd.read_csv(os.path.join(data_dir, 'players_cleaned.csv'))
        teams_all_df = pd.read_csv(os.path.join(data_dir, 'teams_all_season_cleaned.csv'))
        seasons_df = pd.read_csv(os.path.join(data_dir, 'seasons_cleaned.csv'))
        mjt_df = pd.read_csv(os.path.join(data_dir, 'mjt_cleaned.csv'))
        salaries_df = pd.read_csv(os.path.join(data_dir, 'salaries_cleaned.csv'))
    else:
        totals_df = cleaned_data['totals']
        advanced_df = cleaned_data['advanced']
        players_df = cleaned_data['players']
        teams_all_df = cleaned_data['teams_all_season']
        seasons_df = cleaned_data['seasons']
        mjt_df = cleaned_data['mjt']
        salaries_df = cleaned_data['salaries']

    # Load existing player IDs and college IDs if backup exists for backwards compatibility
    existing_player_ids = {}
    existing_college_ids = {}
    backup_sql = os.path.join(output_dir, 'nba_db_2020_2026.sql')
    if os.path.exists(backup_sql):
        with open(backup_sql, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            p_m = re.findall(r'\((\d+),\'([^\']+)\'', content)
            for pid, pname in p_m:
                if int(pid) >= 21000 and pname not in existing_player_ids:
                    existing_player_ids[pname] = int(pid)
            c_m = re.findall(r'INSERT INTO `college`.*?VALUES (.*?);', content)
            if c_m:
                for cid, cname in re.findall(r'\((\d+),\'([^\']+)\'\)', c_m[0]):
                    existing_college_ids[cname] = int(cid)

    # 2. Teams Setup (40 franchises from 1980 to 2027)
    teams_map = {
        'ATL': (60, 'Atlanta Hawks'),
        'BOS': (61, 'Boston Celtics'),
        'BRK': (62, 'Brooklyn Nets'),
        'CHI': (63, 'Chicago Bulls'),
        'CHO': (64, 'Charlotte Hornets'),
        'CLE': (65, 'Cleveland Cavaliers'),
        'DAL': (66, 'Dallas Mavericks'),
        'DEN': (67, 'Denver Nuggets'),
        'DET': (68, 'Detroit Pistons'),
        'GSW': (69, 'Golden State Warriors'),
        'HOU': (70, 'Houston Rockets'),
        'IND': (71, 'Indiana Pacers'),
        'LAC': (72, 'Los Angeles Clippers'),
        'LAL': (73, 'Los Angeles Lakers'),
        'MEM': (74, 'Memphis Grizzlies'),
        'MIA': (75, 'Miami Heat'),
        'MIL': (76, 'Milwaukee Bucks'),
        'MIN': (77, 'Minnesota Timberwolves'),
        'NOP': (78, 'New Orleans Pelicans'),
        'NYK': (79, 'New York Knicks'),
        'OKC': (80, 'Oklahoma City Thunder'),
        'ORL': (81, 'Orlando Magic'),
        'PHI': (82, 'Philadelphia 76ers'),
        'PHO': (83, 'Phoenix Suns'),
        'POR': (84, 'Portland Trail Blazers'),
        'SAC': (85, 'Sacramento Kings'),
        'SAS': (86, 'San Antonio Spurs'),
        'TOR': (87, 'Toronto Raptors'),
        'UTA': (88, 'Utah Jazz'),
        'WAS': (89, 'Washington Wizards'),
        'SDC': (90, 'San Diego Clippers'),
        'KCK': (91, 'Kansas City Kings'),
        'WSB': (92, 'Washington Bullets'),
        'NJN': (93, 'New Jersey Nets'),
        'SEA': (94, 'Seattle SuperSonics'),
        'CHH': (95, 'Charlotte Hornets'),
        'VAN': (96, 'Vancouver Grizzlies'),
        'NOK': (97, 'New Orleans/Oklahoma City Hornets'),
        'NOH': (98, 'New Orleans Hornets'),
        'CHA': (99, 'Charlotte Bobcats'),
    }
    team_name_to_id = {v[1]: v[0] for v in teams_map.values()}
    team_name_to_id['NO/Ok. City Hornets'] = 97
    team_name_to_id['Kansas City-Omaha Kings'] = 91
    team_name_to_id['New Jersey Americans'] = 93
    team_name_to_id['New York Nets'] = 93
    team_name_to_id['San Diego Rockets'] = 70
    team_name_to_id['San Francisco Warriors'] = 69
    team_name_to_id['Philadelphia Warriors'] = 69

    # Table: team
    team_rows = []
    for abbr, (tid, tname) in sorted(teams_map.items(), key=lambda x: x[1][0]):
        team_rows.append({'team_id': tid, 'abbr': abbr, 'name': tname})

    # 3. Seasons Setup (1980 - 2027)
    season_rows = []
    for yr in range(1980, 2028):
        lbl = f"{yr-1}-{str(yr)[-2:]}"
        champ_row = seasons_df[seasons_df['Season'] == lbl]
        champ_name = champ_row['Champion'].values[0] if len(champ_row) > 0 and pd.notna(champ_row['Champion'].values[0]) else None
        champ_id = team_name_to_id.get(champ_name, None)
        season_rows.append({'season_year': yr, 'label': lbl, 'champion_team_id': champ_id})

    # 4. Colleges Setup
    all_colleges = set()
    for col_str in players_df['Colleges'].dropna():
        for c in str(col_str).split(','):
            c_clean = c.strip()
            if c_clean:
                all_colleges.add(c_clean)
    
    colleges_list = sorted(list(all_colleges))
    college_id_map = {}
    current_cid = 1
    for cname in colleges_list:
        if cname in existing_college_ids:
            college_id_map[cname] = existing_college_ids[cname]
        else:
            while current_cid in existing_college_ids.values():
                current_cid += 1
            college_id_map[cname] = current_cid
            current_cid += 1

    college_rows = [{'college_id': cid, 'name': cname} for cname, cid in sorted(college_id_map.items(), key=lambda x: x[1])]

    # 5. Players & Player-College Setup
    player_id_map = {}
    current_pid = 1
    player_rows = []
    player_college_rows = []
    seen_pc = set()

    for idx, row in players_df.iterrows():
        pname = row['Player_Clean']
        if pd.isna(pname) or not str(pname).strip():
            continue
        pname = str(pname).strip()
        
        if pname in existing_player_ids and pname not in player_id_map:
            pid = existing_player_ids[pname]
        elif pname in player_id_map:
            pid = current_pid
            current_pid += 1
        else:
            while current_pid in existing_player_ids.values():
                current_pid += 1
            pid = current_pid
            current_pid += 1
        
        player_id_map[pname] = pid
        
        bdate = str(row['Birth_Date_DT'])[:10] if pd.notna(row['Birth_Date_DT']) else None
        h_cm = clean_val(row['Ht_CM'], is_float=True)
        w_kg = clean_val(row['Wt_KG'], is_float=True)
        player_rows.append({'player_id': pid, 'name': pname, 'birth_date': bdate, 'height_cm': h_cm, 'weight_kg': w_kg})

        if pd.notna(row['Colleges']):
            for c in str(row['Colleges']).split(','):
                c_clean = c.strip()
                if c_clean in college_id_map:
                    cid = college_id_map[c_clean]
                    key = (pid, cid)
                    if key not in seen_pc:
                        seen_pc.add(key)
                        player_college_rows.append({'player_id': pid, 'college_id': cid})

    # 6. Team Season Setup
    team_season_rows = []
    seen_ts = set()
    for idx, row in teams_all_df.iterrows():
        try:
            s_lbl = str(row['Season']).strip()
            parts = s_lbl.split('-')
            if len(parts) == 2:
                century = parts[0][:2]
                yr_val = int(century + parts[1])
                if yr_val < 1950:
                    yr_val += 100
            else:
                continue
            
            if yr_val < 1980 or yr_val > 2027:
                continue

            t_clean = row['Team_Clean']
            if t_clean in team_name_to_id:
                tid = team_name_to_id[t_clean]
                key = (tid, yr_val)
                if key in seen_ts:
                    continue
                seen_ts.add(key)

                w = clean_val(row['W'])
                l = clean_val(row['L'])
                srs = clean_val(row['SRS'], is_float=True)
                pace = clean_val(row['Pace'], is_float=True)
                ortg = clean_val(row['ORtg'], is_float=True)
                drtg = clean_val(row['DRtg'], is_float=True)
                playoffs = str(row['Playoffs']).strip() if pd.notna(row['Playoffs']) else None
                team_season_rows.append({
                    'team_id': tid, 'season_year': yr_val, 'wins': w, 'losses': l,
                    'srs': srs, 'pace': pace, 'ortg': ortg, 'drtg': drtg, 'playoffs': playoffs
                })
        except Exception:
            continue

    # 7. Player Season, Awards, Totals & Advanced Stats Setup
    adv_indexed = {}
    for idx, row in advanced_df.iterrows():
        key = (int(row['Season']), str(row['Player_Clean']).strip(), str(row['Team']).strip())
        adv_indexed[key] = row

    sal_indexed = {}
    if 'Season' in salaries_df.columns and 'Player_Clean' in salaries_df.columns:
        for idx, row in salaries_df.iterrows():
            try:
                s_val = int(row['Season'])
                p_val = str(row['Player_Clean']).strip()
                sal_val = row['Salary_Numeric'] if 'Salary_Numeric' in row else row['Salary']
                sal_indexed[(s_val, p_val)] = sal_val
            except Exception:
                continue

    player_season_rows = []
    player_award_rows = []
    season_totals_rows = []
    season_adv_rows = []

    ps_id = 1
    seen_ps_keys = set()

    for idx, row in totals_df.iterrows():
        s_yr = int(row['Season'])
        if s_yr < 1980 or s_yr > 2027:
            continue
        
        pname = str(row['Player_Clean']).strip()
        if pname not in player_id_map:
            pid = current_pid
            current_pid += 1
            player_id_map[pname] = pid
            player_rows.append({'player_id': pid, 'name': pname, 'birth_date': None, 'height_cm': None, 'weight_kg': None})
        else:
            pid = player_id_map[pname]

        tm_str = str(row['Team']).strip()
        is_total = 1 if tm_str in ['2TM', '3TM', '4TM', '5TM', 'TOT'] else 0
        tid = teams_map[tm_str][0] if (tm_str in teams_map and not is_total) else None

        ps_uniq_key = (pid, s_yr, tid, is_total)
        if ps_uniq_key in seen_ps_keys:
            continue
        seen_ps_keys.add(ps_uniq_key)

        pos = str(row['Pos']).strip() if pd.notna(row['Pos']) else None
        exp = clean_val(row['Age'] - 20) if pd.notna(row['Age']) else None
        sal = clean_val(sal_indexed.get((s_yr, pname), None))

        player_season_rows.append({
            'player_season_id': ps_id, 'player_id': pid, 'team_id': tid,
            'season_year': s_yr, 'pos': pos, 'exp': exp, 'salary': sal, 'is_total': is_total
        })

        # Awards
        if pd.notna(row['Awards']) and str(row['Awards']).strip():
            for aw in str(row['Awards']).split(','):
                aw_clean = aw.strip()
                if aw_clean:
                    player_award_rows.append({'player_season_id': ps_id, 'award_code': aw_clean})

        # Totals
        season_totals_rows.append({
            'player_season_id': ps_id,
            'g': clean_val(row['G']), 'gs': clean_val(row['GS']), 'mp': clean_val(row['MP']),
            'fg': clean_val(row['FG']), 'fga': clean_val(row['FGA']),
            'fg3': clean_val(row['3P']), 'fg3a': clean_val(row['3PA']),
            'fg2': clean_val(row['2P']), 'fg2a': clean_val(row['2PA']),
            'ft': clean_val(row['FT']), 'fta': clean_val(row['FTA']),
            'orb': clean_val(row['ORB']), 'drb': clean_val(row['DRB']), 'trb': clean_val(row['TRB']),
            'ast': clean_val(row['AST']), 'stl': clean_val(row['STL']), 'blk': clean_val(row['BLK']),
            'tov': clean_val(row['TOV']), 'pf': clean_val(row['PF']), 'pts': clean_val(row['PTS']),
            'triple_doubles': clean_val(row.get('Trp-Dbl', 0)) or 0
        })

        # Advanced
        adv_row = adv_indexed.get((s_yr, pname, tm_str), None)
        if adv_row is not None:
            season_adv_rows.append({
                'player_season_id': ps_id,
                'per': clean_val(adv_row.get('PER'), is_float=True),
                'ts_pct': clean_val(adv_row.get('TS%'), is_float=True),
                'fg3a_rate': clean_val(adv_row.get('3PAr'), is_float=True),
                'ft_rate': clean_val(adv_row.get('FTr'), is_float=True),
                'orb_pct': clean_val(adv_row.get('ORB%'), is_float=True),
                'drb_pct': clean_val(adv_row.get('DRB%'), is_float=True),
                'trb_pct': clean_val(adv_row.get('TRB%'), is_float=True),
                'ast_pct': clean_val(adv_row.get('AST%'), is_float=True),
                'stl_pct': clean_val(adv_row.get('STL%'), is_float=True),
                'blk_pct': clean_val(adv_row.get('BLK%'), is_float=True),
                'tov_pct': clean_val(adv_row.get('TOV%'), is_float=True),
                'usg_pct': clean_val(adv_row.get('USG%'), is_float=True),
                'ows': clean_val(adv_row.get('OWS'), is_float=True),
                'dws': clean_val(adv_row.get('DWS'), is_float=True),
                'ws': clean_val(adv_row.get('WS'), is_float=True),
                'ws_per_48': clean_val(adv_row.get('WS/48'), is_float=True),
                'obpm': clean_val(adv_row.get('OBPM'), is_float=True),
                'dbpm': clean_val(adv_row.get('DBPM'), is_float=True),
                'bpm': clean_val(adv_row.get('BPM'), is_float=True),
                'vorp': clean_val(adv_row.get('VORP'), is_float=True)
            })
        else:
            season_adv_rows.append({
                'player_season_id': ps_id,
                'per': None, 'ts_pct': None, 'fg3a_rate': None, 'ft_rate': None,
                'orb_pct': None, 'drb_pct': None, 'trb_pct': None, 'ast_pct': None,
                'stl_pct': None, 'blk_pct': None, 'tov_pct': None, 'usg_pct': None,
                'ows': None, 'dws': None, 'ws': None, 'ws_per_48': None,
                'obpm': None, 'dbpm': None, 'bpm': None, 'vorp': None
            })

        ps_id += 1

    # 8. MVP Votes Setup
    mvp_rows = []
    seen_mvp = set()
    for idx, row in mjt_df.iterrows():
        try:
            s_yr = int(row['Season'])
            if s_yr < 1980 or s_yr > 2027:
                continue
            pname = str(row['Player_Clean']).strip()
            pid = player_id_map.get(pname, None)
            if pid is None:
                continue
            
            key = (s_yr, pid)
            if key in seen_mvp:
                continue
            seen_mvp.add(key)

            rk = clean_val(row.get('Rank_Numeric', row.get('Rank')))
            is_tied = 1 if 'T' in str(row.get('Rank', '')) else 0
            first_v = clean_val(row.get('First'))
            pts_won = clean_val(row.get('Pts Won'))
            pts_max = clean_val(row.get('Pts Max'))
            share = clean_val(row.get('Share'), is_float=True)

            mvp_rows.append({
                'season_year': s_yr, 'player_id': pid, 'rank_num': rk, 'is_tied': is_tied,
                'first_votes': first_v, 'pts_won': pts_won, 'pts_max': pts_max, 'share': share
            })
        except Exception:
            continue

    # Dict of all tables and columns
    tables_dict = {
        'college': (college_rows, ['college_id', 'name']),
        'team': (team_rows, ['team_id', 'abbr', 'name']),
        'season': (season_rows, ['season_year', 'label', 'champion_team_id']),
        'team_season': (team_season_rows, ['team_id', 'season_year', 'wins', 'losses', 'srs', 'pace', 'ortg', 'drtg', 'playoffs']),
        'player': (player_rows, ['player_id', 'name', 'birth_date', 'height_cm', 'weight_kg']),
        'player_college': (player_college_rows, ['player_id', 'college_id']),
        'player_season': (player_season_rows, ['player_season_id', 'player_id', 'team_id', 'season_year', 'pos', 'exp', 'salary', 'is_total']),
        'player_season_award': (player_award_rows, ['player_season_id', 'award_code']),
        'season_totals': (season_totals_rows, ['player_season_id', 'g', 'gs', 'mp', 'fg', 'fga', 'fg3', 'fg3a', 'fg2', 'fg2a', 'ft', 'fta', 'orb', 'drb', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf', 'pts', 'triple_doubles']),
        'season_advanced': (season_adv_rows, ['player_season_id', 'per', 'ts_pct', 'fg3a_rate', 'ft_rate', 'orb_pct', 'drb_pct', 'trb_pct', 'ast_pct', 'stl_pct', 'blk_pct', 'tov_pct', 'usg_pct', 'ows', 'dws', 'ws', 'ws_per_48', 'obpm', 'dbpm', 'bpm', 'vorp']),
        'mvp_vote': (mvp_rows, ['season_year', 'player_id', 'rank_num', 'is_tied', 'first_votes', 'pts_won', 'pts_max', 'share']),
    }

    # 9. Export CSV for Each Table
    print("\nExporting normalized table CSVs into: Data Base/tables_csv/ ...")
    for tbl_name, (rows, cols) in tables_dict.items():
        csv_file = os.path.join(tables_csv_dir, f"{tbl_name}.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
            writer.writerow(cols)
            for r in rows:
                row_vals = [r.get(c) if r.get(c) is not None else r'\N' for c in cols]
                writer.writerow(row_vals)
        print(f"  -> Exported {tbl_name:<20}: {len(rows):>6} rows -> {csv_file}")

    # 10. Generate 'Data Base/load_data.sql' with 'LOAD DATA LOCAL INFILE'
    load_sql_path = os.path.join(output_dir, 'load_data.sql')
    print(f"\nGenerating MySQL bulk loader script: {load_sql_path} ...")
    
    # Use forward slashes for MySQL LOAD DATA paths
    tables_csv_abs = os.path.abspath(tables_csv_dir).replace('\\', '/')

    with open(load_sql_path, 'w', encoding='utf-8') as f:
        f.write("""-- ====================================================================
-- MySQL Bulk Data Loader Script (LOAD DATA LOCAL INFILE)
-- Database: nba_db (1980 - 2027)
-- ====================================================================
-- Note: Ensure local_infile is enabled:
--   mysql --local-infile=1 -u root -p
-- ====================================================================

CREATE DATABASE IF NOT EXISTS `nba_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `nba_db`;

SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO';

-- --------------------------------------------------------------------
-- 1. DROP EXISTING TABLES IN REVERSE DEPENDENCY ORDER
-- --------------------------------------------------------------------
DROP TABLE IF EXISTS `player_season_award`;
DROP TABLE IF EXISTS `season_totals`;
DROP TABLE IF EXISTS `season_advanced`;
DROP TABLE IF EXISTS `mvp_vote`;
DROP TABLE IF EXISTS `player_season`;
DROP TABLE IF EXISTS `player_college`;
DROP TABLE IF EXISTS `team_season`;
DROP TABLE IF EXISTS `season`;
DROP TABLE IF EXISTS `player`;
DROP TABLE IF EXISTS `team`;
DROP TABLE IF EXISTS `college`;

-- --------------------------------------------------------------------
-- 2. CREATE TABLE SCHEMAS
-- --------------------------------------------------------------------

CREATE TABLE `college` (
  `college_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`college_id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `team` (
  `team_id` int NOT NULL AUTO_INCREMENT,
  `abbr` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`team_id`),
  UNIQUE KEY `abbr` (`abbr`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `season` (
  `season_year` int NOT NULL,
  `label` varchar(7) COLLATE utf8mb4_unicode_ci NOT NULL,
  `champion_team_id` int DEFAULT NULL,
  PRIMARY KEY (`season_year`),
  KEY `champion_team_id` (`champion_team_id`),
  CONSTRAINT `season_ibfk_1` FOREIGN KEY (`champion_team_id`) REFERENCES `team` (`team_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `team_season` (
  `team_id` int NOT NULL,
  `season_year` int NOT NULL,
  `wins` int DEFAULT NULL,
  `losses` int DEFAULT NULL,
  `srs` float DEFAULT NULL,
  `pace` float DEFAULT NULL,
  `ortg` float DEFAULT NULL,
  `drtg` float DEFAULT NULL,
  `playoffs` varchar(40) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`team_id`,`season_year`),
  KEY `season_year` (`season_year`),
  CONSTRAINT `team_season_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `team` (`team_id`),
  CONSTRAINT `team_season_ibfk_2` FOREIGN KEY (`season_year`) REFERENCES `season` (`season_year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `player` (
  `player_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `birth_date` date DEFAULT NULL,
  `height_cm` float DEFAULT NULL,
  `weight_kg` float DEFAULT NULL,
  PRIMARY KEY (`player_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `player_college` (
  `player_id` int NOT NULL,
  `college_id` int NOT NULL,
  PRIMARY KEY (`player_id`,`college_id`),
  KEY `college_id` (`college_id`),
  CONSTRAINT `player_college_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `player` (`player_id`),
  CONSTRAINT `player_college_ibfk_2` FOREIGN KEY (`college_id`) REFERENCES `college` (`college_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `player_season` (
  `player_season_id` int NOT NULL AUTO_INCREMENT,
  `player_id` int NOT NULL,
  `team_id` int DEFAULT NULL,
  `season_year` int NOT NULL,
  `pos` varchar(5) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp` int DEFAULT NULL,
  `salary` int DEFAULT NULL,
  `is_total` tinyint(1) NOT NULL,
  PRIMARY KEY (`player_season_id`),
  UNIQUE KEY `uq_player_season_team_total` (`player_id`,`season_year`,`team_id`,`is_total`),
  KEY `team_id` (`team_id`),
  KEY `season_year` (`season_year`),
  CONSTRAINT `player_season_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `player` (`player_id`),
  CONSTRAINT `player_season_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `team` (`team_id`),
  CONSTRAINT `player_season_ibfk_3` FOREIGN KEY (`season_year`) REFERENCES `season` (`season_year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `player_season_award` (
  `player_season_id` int NOT NULL,
  `award_code` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`player_season_id`,`award_code`),
  CONSTRAINT `player_season_award_ibfk_1` FOREIGN KEY (`player_season_id`) REFERENCES `player_season` (`player_season_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `season_totals` (
  `player_season_id` int NOT NULL,
  `g` int DEFAULT NULL,
  `gs` int DEFAULT NULL,
  `mp` int DEFAULT NULL,
  `fg` int DEFAULT NULL,
  `fga` int DEFAULT NULL,
  `fg3` int DEFAULT NULL,
  `fg3a` int DEFAULT NULL,
  `fg2` int DEFAULT NULL,
  `fg2a` int DEFAULT NULL,
  `ft` int DEFAULT NULL,
  `fta` int DEFAULT NULL,
  `orb` int DEFAULT NULL,
  `drb` int DEFAULT NULL,
  `trb` int DEFAULT NULL,
  `ast` int DEFAULT NULL,
  `stl` int DEFAULT NULL,
  `blk` int DEFAULT NULL,
  `tov` int DEFAULT NULL,
  `pf` int DEFAULT NULL,
  `pts` int DEFAULT NULL,
  `triple_doubles` int DEFAULT NULL,
  PRIMARY KEY (`player_season_id`),
  CONSTRAINT `season_totals_ibfk_1` FOREIGN KEY (`player_season_id`) REFERENCES `player_season` (`player_season_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `season_advanced` (
  `player_season_id` int NOT NULL,
  `per` float DEFAULT NULL,
  `ts_pct` float DEFAULT NULL,
  `fg3a_rate` float DEFAULT NULL,
  `ft_rate` float DEFAULT NULL,
  `orb_pct` float DEFAULT NULL,
  `drb_pct` float DEFAULT NULL,
  `trb_pct` float DEFAULT NULL,
  `ast_pct` float DEFAULT NULL,
  `stl_pct` float DEFAULT NULL,
  `blk_pct` float DEFAULT NULL,
  `tov_pct` float DEFAULT NULL,
  `usg_pct` float DEFAULT NULL,
  `ows` float DEFAULT NULL,
  `dws` float DEFAULT NULL,
  `ws` float DEFAULT NULL,
  `ws_per_48` float DEFAULT NULL,
  `obpm` float DEFAULT NULL,
  `dbpm` float DEFAULT NULL,
  `bpm` float DEFAULT NULL,
  `vorp` float DEFAULT NULL,
  PRIMARY KEY (`player_season_id`),
  CONSTRAINT `season_advanced_ibfk_1` FOREIGN KEY (`player_season_id`) REFERENCES `player_season` (`player_season_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `mvp_vote` (
  `season_year` int NOT NULL,
  `player_id` int NOT NULL,
  `rank_num` int DEFAULT NULL,
  `is_tied` tinyint(1) NOT NULL,
  `first_votes` int DEFAULT NULL,
  `pts_won` int DEFAULT NULL,
  `pts_max` int DEFAULT NULL,
  `share` float DEFAULT NULL,
  PRIMARY KEY (`season_year`,`player_id`),
  KEY `player_id` (`player_id`),
  CONSTRAINT `mvp_vote_ibfk_1` FOREIGN KEY (`season_year`) REFERENCES `season` (`season_year`),
  CONSTRAINT `mvp_vote_ibfk_2` FOREIGN KEY (`player_id`) REFERENCES `player` (`player_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------
-- 3. BULK LOAD DATA USING 'LOAD DATA LOCAL INFILE'
-- --------------------------------------------------------------------

-- Table: college
LOAD DATA LOCAL INFILE '""" + tables_csv_abs + """/college.csv'
INTO TABLE `college`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS
(`college_id`, `name`);

-- Table: team
LOAD DATA LOCAL INFILE '""" + tables_csv_abs + """/team.csv'
INTO TABLE `team`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS
(`team_id`, `abbr`, `name`);

-- Table: season
LOAD DATA LOCAL INFILE '""" + tables_csv_abs + """/season.csv'
INTO TABLE `season`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS
(`season_year`, `label`, @champ_id)
SET `champion_team_id` = NULLIF(NULLIF(@champ_id, ''), '\\\\N');

-- Table: team_season
LOAD DATA LOCAL INFILE '""" + tables_csv_abs + """/team_season.csv'
INTO TABLE `team_season`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS
(`team_id`, `season_year`, @w, @l, @srs, @pace, @ortg, @drtg, @playoffs)
SET
  `wins` = NULLIF(NULLIF(@w, ''), '\\\\N'),
  `losses` = NULLIF(NULLIF(@l, ''), '\\\\N'),
  `srs` = NULLIF(NULLIF(@srs, ''), '\\\\N'),
  `pace` = NULLIF(NULLIF(@pace, ''), '\\\\N'),
  `ortg` = NULLIF(NULLIF(@ortg, ''), '\\\\N'),
  `drtg` = NULLIF(NULLIF(@drtg, ''), '\\\\N'),
  `playoffs` = NULLIF(NULLIF(@playoffs, ''), '\\\\N');

-- Table: player
LOAD DATA LOCAL INFILE '""" + tables_csv_abs + """/player.csv'
INTO TABLE `player`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS
(`player_id`, `name`, @bdate, @h_cm, @w_kg)
SET
  `birth_date` = NULLIF(NULLIF(@bdate, ''), '\\\\N'),
  `height_cm` = NULLIF(NULLIF(@h_cm, ''), '\\\\N'),
  `weight_kg` = NULLIF(NULLIF(@w_kg, ''), '\\\\N');

-- Table: player_college
LOAD DATA LOCAL INFILE '""" + tables_csv_abs + """/player_college.csv'
INTO TABLE `player_college`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS
(`player_id`, `college_id`);

-- Table: player_season
LOAD DATA LOCAL INFILE '""" + tables_csv_abs + """/player_season.csv'
INTO TABLE `player_season`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS
(`player_season_id`, `player_id`, @tid, `season_year`, @pos, @exp, @sal, `is_total`)
SET
  `team_id` = NULLIF(NULLIF(@tid, ''), '\\\\N'),
  `pos` = NULLIF(NULLIF(@pos, ''), '\\\\N'),
  `exp` = NULLIF(NULLIF(@exp, ''), '\\\\N'),
  `salary` = NULLIF(NULLIF(@sal, ''), '\\\\N');

-- Table: player_season_award
LOAD DATA LOCAL INFILE '""" + tables_csv_abs + """/player_season_award.csv'
INTO TABLE `player_season_award`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS
(`player_season_id`, `award_code`);

-- Table: season_totals
LOAD DATA LOCAL INFILE '""" + tables_csv_abs + """/season_totals.csv'
INTO TABLE `season_totals`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS
(`player_season_id`, @g, @gs, @mp, @fg, @fga, @fg3, @fg3a, @fg2, @fg2a, @ft, @fta, @orb, @drb, @trb, @ast, @stl, @blk, @tov, @pf, @pts, @td)
SET
  `g` = NULLIF(NULLIF(@g, ''), '\\\\N'),
  `gs` = NULLIF(NULLIF(@gs, ''), '\\\\N'),
  `mp` = NULLIF(NULLIF(@mp, ''), '\\\\N'),
  `fg` = NULLIF(NULLIF(@fg, ''), '\\\\N'),
  `fga` = NULLIF(NULLIF(@fga, ''), '\\\\N'),
  `fg3` = NULLIF(NULLIF(@fg3, ''), '\\\\N'),
  `fg3a` = NULLIF(NULLIF(@fg3a, ''), '\\\\N'),
  `fg2` = NULLIF(NULLIF(@fg2, ''), '\\\\N'),
  `fg2a` = NULLIF(NULLIF(@fg2a, ''), '\\\\N'),
  `ft` = NULLIF(NULLIF(@ft, ''), '\\\\N'),
  `fta` = NULLIF(NULLIF(@fta, ''), '\\\\N'),
  `orb` = NULLIF(NULLIF(@orb, ''), '\\\\N'),
  `drb` = NULLIF(NULLIF(@drb, ''), '\\\\N'),
  `trb` = NULLIF(NULLIF(@trb, ''), '\\\\N'),
  `ast` = NULLIF(NULLIF(@ast, ''), '\\\\N'),
  `stl` = NULLIF(NULLIF(@stl, ''), '\\\\N'),
  `blk` = NULLIF(NULLIF(@blk, ''), '\\\\N'),
  `tov` = NULLIF(NULLIF(@tov, ''), '\\\\N'),
  `pf` = NULLIF(NULLIF(@pf, ''), '\\\\N'),
  `pts` = NULLIF(NULLIF(@pts, ''), '\\\\N'),
  `triple_doubles` = NULLIF(NULLIF(@td, ''), '\\\\N');

-- Table: season_advanced
LOAD DATA LOCAL INFILE '""" + tables_csv_abs + """/season_advanced.csv'
INTO TABLE `season_advanced`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS
(`player_season_id`, @per, @ts, @fg3a, @ftr, @orb, @drb, @trb, @ast, @stl, @blk, @tov, @usg, @ows, @dws, @ws, @ws48, @obpm, @dbpm, @bpm, @vorp)
SET
  `per` = NULLIF(NULLIF(@per, ''), '\\\\N'),
  `ts_pct` = NULLIF(NULLIF(@ts, ''), '\\\\N'),
  `fg3a_rate` = NULLIF(NULLIF(@fg3a, ''), '\\\\N'),
  `ft_rate` = NULLIF(NULLIF(@ftr, ''), '\\\\N'),
  `orb_pct` = NULLIF(NULLIF(@orb, ''), '\\\\N'),
  `drb_pct` = NULLIF(NULLIF(@drb, ''), '\\\\N'),
  `trb_pct` = NULLIF(NULLIF(@trb, ''), '\\\\N'),
  `ast_pct` = NULLIF(NULLIF(@ast, ''), '\\\\N'),
  `stl_pct` = NULLIF(NULLIF(@stl, ''), '\\\\N'),
  `blk_pct` = NULLIF(NULLIF(@blk, ''), '\\\\N'),
  `tov_pct` = NULLIF(NULLIF(@tov, ''), '\\\\N'),
  `usg_pct` = NULLIF(NULLIF(@usg, ''), '\\\\N'),
  `ows` = NULLIF(NULLIF(@ows, ''), '\\\\N'),
  `dws` = NULLIF(NULLIF(@dws, ''), '\\\\N'),
  `ws` = NULLIF(NULLIF(@ws, ''), '\\\\N'),
  `ws_per_48` = NULLIF(NULLIF(@ws48, ''), '\\\\N'),
  `obpm` = NULLIF(NULLIF(@obpm, ''), '\\\\N'),
  `dbpm` = NULLIF(NULLIF(@dbpm, ''), '\\\\N'),
  `bpm` = NULLIF(NULLIF(@bpm, ''), '\\\\N'),
  `vorp` = NULLIF(NULLIF(@vorp, ''), '\\\\N');

-- Table: mvp_vote
LOAD DATA LOCAL INFILE '""" + tables_csv_abs + """/mvp_vote.csv'
INTO TABLE `mvp_vote`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 ROWS
(`season_year`, `player_id`, @rk, `is_tied`, @fv, @pw, @pm, @sh)
SET
  `rank_num` = NULLIF(NULLIF(@rk, ''), '\\\\N'),
  `first_votes` = NULLIF(NULLIF(@fv, ''), '\\\\N'),
  `pts_won` = NULLIF(NULLIF(@pw, ''), '\\\\N'),
  `pts_max` = NULLIF(NULLIF(@pm, ''), '\\\\N'),
  `share` = NULLIF(NULLIF(@sh, ''), '\\\\N');

-- --------------------------------------------------------------------
-- 4. RESTORE ENVIRONMENT SETTINGS
-- --------------------------------------------------------------------
SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS = @OLD_UNIQUE_CHECKS;
SET SQL_MODE = @OLD_SQL_MODE;

SELECT 'NBA Database successfully bulk-loaded from CSV files!' AS Status;
""")

    print(f"[SUCCESS] Loader script written: {load_sql_path}")

    # 11. Also generate standalone 'Data Base/nba_db.sql' (INSERT-based dump for portable import)
    nba_db_dump = os.path.join(output_dir, 'nba_db.sql')
    print(f"Writing complete standalone MySQL dump to: {nba_db_dump}...")
    with open(nba_db_dump, 'w', encoding='utf-8') as f:
        f.write("""-- MySQL dump 10.13  Distrib 8.0.31, for Win64 (x86_64)
-- NBA Complete Relational Database (1980 - 2027)
-- Host: 127.0.0.1    Database: nba_db
-- ------------------------------------------------------
/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

CREATE DATABASE IF NOT EXISTS `nba_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `nba_db`;

""")
        # College
        f.write("DROP TABLE IF EXISTS `college`;\n")
        f.write("""CREATE TABLE `college` (
  `college_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`college_id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\nLOCK TABLES `college` WRITE;\n""")
        c_chunks = [f"({r['college_id']},'{r['name'].replace(chr(92), chr(92)+chr(92)).replace(chr(39), chr(92)+chr(39))}')" for r in college_rows]
        if c_chunks:
            f.write(f"INSERT INTO `college` (`college_id`, `name`) VALUES {','.join(c_chunks)};\n")
        f.write("UNLOCK TABLES;\n\n")

        # Team
        f.write("DROP TABLE IF EXISTS `team`;\n")
        f.write("""CREATE TABLE `team` (
  `team_id` int NOT NULL AUTO_INCREMENT,
  `abbr` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`team_id`),
  UNIQUE KEY `abbr` (`abbr`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\nLOCK TABLES `team` WRITE;\n""")
        t_chunks = [f"({r['team_id']},'{r['abbr']}','{r['name'].replace(chr(92), chr(92)+chr(92)).replace(chr(39), chr(92)+chr(39))}')" for r in team_rows]
        if t_chunks:
            f.write(f"INSERT INTO `team` (`team_id`, `abbr`, `name`) VALUES {','.join(t_chunks)};\n")
        f.write("UNLOCK TABLES;\n\n")

        # Season
        f.write("DROP TABLE IF EXISTS `season`;\n")
        f.write("""CREATE TABLE `season` (
  `season_year` int NOT NULL,
  `label` varchar(7) COLLATE utf8mb4_unicode_ci NOT NULL,
  `champion_team_id` int DEFAULT NULL,
  PRIMARY KEY (`season_year`),
  KEY `champion_team_id` (`champion_team_id`),
  CONSTRAINT `season_ibfk_1` FOREIGN KEY (`champion_team_id`) REFERENCES `team` (`team_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\nLOCK TABLES `season` WRITE;\n""")
        s_chunks = [f"({r['season_year']},'{r['label']}',{r['champion_team_id'] if r['champion_team_id'] is not None else 'NULL'})" for r in season_rows]
        if s_chunks:
            f.write(f"INSERT INTO `season` (`season_year`, `label`, `champion_team_id`) VALUES {','.join(s_chunks)};\n")
        f.write("UNLOCK TABLES;\n\n")

        # Team Season
        f.write("DROP TABLE IF EXISTS `team_season`;\n")
        f.write("""CREATE TABLE `team_season` (
  `team_id` int NOT NULL,
  `season_year` int NOT NULL,
  `wins` int DEFAULT NULL,
  `losses` int DEFAULT NULL,
  `srs` float DEFAULT NULL,
  `pace` float DEFAULT NULL,
  `ortg` float DEFAULT NULL,
  `drtg` float DEFAULT NULL,
  `playoffs` varchar(40) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`team_id`,`season_year`),
  KEY `season_year` (`season_year`),
  CONSTRAINT `team_season_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `team` (`team_id`),
  CONSTRAINT `team_season_ibfk_2` FOREIGN KEY (`season_year`) REFERENCES `season` (`season_year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\nLOCK TABLES `team_season` WRITE;\n""")
        ts_chunks = [f"({r['team_id']},{r['season_year']},{clean_sql_num(r['wins'])},{clean_sql_num(r['losses'])},{clean_sql_num(r['srs'], True)},{clean_sql_num(r['pace'], True)},{clean_sql_num(r['ortg'], True)},{clean_sql_num(r['drtg'], True)},{clean_sql_str(r['playoffs'])})" for r in team_season_rows]
        for i in range(0, len(ts_chunks), 1000):
            f.write(f"INSERT INTO `team_season` (`team_id`, `season_year`, `wins`, `losses`, `srs`, `pace`, `ortg`, `drtg`, `playoffs`) VALUES {','.join(ts_chunks[i:i+1000])};\n")
        f.write("UNLOCK TABLES;\n\n")

        # Player
        f.write("DROP TABLE IF EXISTS `player`;\n")
        f.write("""CREATE TABLE `player` (
  `player_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `birth_date` date DEFAULT NULL,
  `height_cm` float DEFAULT NULL,
  `weight_kg` float DEFAULT NULL,
  PRIMARY KEY (`player_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\nLOCK TABLES `player` WRITE;\n""")
        p_chunks = [f"({r['player_id']},{clean_sql_str(r['name'])},{clean_sql_str(r['birth_date'])},{clean_sql_num(r['height_cm'], True)},{clean_sql_num(r['weight_kg'], True)})" for r in player_rows]
        for i in range(0, len(p_chunks), 1000):
            f.write(f"INSERT INTO `player` (`player_id`, `name`, `birth_date`, `height_cm`, `weight_kg`) VALUES {','.join(p_chunks[i:i+1000])};\n")
        f.write("UNLOCK TABLES;\n\n")

        # Player College
        f.write("DROP TABLE IF EXISTS `player_college`;\n")
        f.write("""CREATE TABLE `player_college` (
  `player_id` int NOT NULL,
  `college_id` int NOT NULL,
  PRIMARY KEY (`player_id`,`college_id`),
  KEY `college_id` (`college_id`),
  CONSTRAINT `player_college_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `player` (`player_id`),
  CONSTRAINT `player_college_ibfk_2` FOREIGN KEY (`college_id`) REFERENCES `college` (`college_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\nLOCK TABLES `player_college` WRITE;\n""")
        pc_chunks = [f"({r['player_id']},{r['college_id']})" for r in player_college_rows]
        for i in range(0, len(pc_chunks), 1000):
            f.write(f"INSERT INTO `player_college` (`player_id`, `college_id`) VALUES {','.join(pc_chunks[i:i+1000])};\n")
        f.write("UNLOCK TABLES;\n\n")

        # Player Season
        f.write("DROP TABLE IF EXISTS `player_season`;\n")
        f.write("""CREATE TABLE `player_season` (
  `player_season_id` int NOT NULL AUTO_INCREMENT,
  `player_id` int NOT NULL,
  `team_id` int DEFAULT NULL,
  `season_year` int NOT NULL,
  `pos` varchar(5) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp` int DEFAULT NULL,
  `salary` int DEFAULT NULL,
  `is_total` tinyint(1) NOT NULL,
  PRIMARY KEY (`player_season_id`),
  UNIQUE KEY `uq_player_season_team_total` (`player_id`,`season_year`,`team_id`,`is_total`),
  KEY `team_id` (`team_id`),
  KEY `season_year` (`season_year`),
  CONSTRAINT `player_season_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `player` (`player_id`),
  CONSTRAINT `player_season_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `team` (`team_id`),
  CONSTRAINT `player_season_ibfk_3` FOREIGN KEY (`season_year`) REFERENCES `season` (`season_year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\nLOCK TABLES `player_season` WRITE;\n""")
        ps_chunks = [f"({r['player_season_id']},{r['player_id']},{clean_sql_num(r['team_id'])},{r['season_year']},{clean_sql_str(r['pos'])},{clean_sql_num(r['exp'])},{clean_sql_num(r['salary'])},{r['is_total']})" for r in player_season_rows]
        for i in range(0, len(ps_chunks), 1000):
            f.write(f"INSERT INTO `player_season` (`player_season_id`, `player_id`, `team_id`, `season_year`, `pos`, `exp`, `salary`, `is_total`) VALUES {','.join(ps_chunks[i:i+1000])};\n")
        f.write("UNLOCK TABLES;\n\n")

        # Player Season Award
        f.write("DROP TABLE IF EXISTS `player_season_award`;\n")
        f.write("""CREATE TABLE `player_season_award` (
  `player_season_id` int NOT NULL,
  `award_code` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`player_season_id`,`award_code`),
  CONSTRAINT `player_season_award_ibfk_1` FOREIGN KEY (`player_season_id`) REFERENCES `player_season` (`player_season_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\nLOCK TABLES `player_season_award` WRITE;\n""")
        pa_chunks = [f"({r['player_season_id']},{clean_sql_str(r['award_code'])})" for r in player_award_rows]
        for i in range(0, len(pa_chunks), 1000):
            f.write(f"INSERT INTO `player_season_award` (`player_season_id`, `award_code`) VALUES {','.join(pa_chunks[i:i+1000])};\n")
        f.write("UNLOCK TABLES;\n\n")

        # Season Totals
        f.write("DROP TABLE IF EXISTS `season_totals`;\n")
        f.write("""CREATE TABLE `season_totals` (
  `player_season_id` int NOT NULL,
  `g` int DEFAULT NULL,
  `gs` int DEFAULT NULL,
  `mp` int DEFAULT NULL,
  `fg` int DEFAULT NULL,
  `fga` int DEFAULT NULL,
  `fg3` int DEFAULT NULL,
  `fg3a` int DEFAULT NULL,
  `fg2` int DEFAULT NULL,
  `fg2a` int DEFAULT NULL,
  `ft` int DEFAULT NULL,
  `fta` int DEFAULT NULL,
  `orb` int DEFAULT NULL,
  `drb` int DEFAULT NULL,
  `trb` int DEFAULT NULL,
  `ast` int DEFAULT NULL,
  `stl` int DEFAULT NULL,
  `blk` int DEFAULT NULL,
  `tov` int DEFAULT NULL,
  `pf` int DEFAULT NULL,
  `pts` int DEFAULT NULL,
  `triple_doubles` int DEFAULT NULL,
  PRIMARY KEY (`player_season_id`),
  CONSTRAINT `season_totals_ibfk_1` FOREIGN KEY (`player_season_id`) REFERENCES `player_season` (`player_season_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\nLOCK TABLES `season_totals` WRITE;\n""")
        st_chunks = [f"({r['player_season_id']},{clean_sql_num(r['g'])},{clean_sql_num(r['gs'])},{clean_sql_num(r['mp'])},{clean_sql_num(r['fg'])},{clean_sql_num(r['fga'])},{clean_sql_num(r['fg3'])},{clean_sql_num(r['fg3a'])},{clean_sql_num(r['fg2'])},{clean_sql_num(r['fg2a'])},{clean_sql_num(r['ft'])},{clean_sql_num(r['fta'])},{clean_sql_num(r['orb'])},{clean_sql_num(r['drb'])},{clean_sql_num(r['trb'])},{clean_sql_num(r['ast'])},{clean_sql_num(r['stl'])},{clean_sql_num(r['blk'])},{clean_sql_num(r['tov'])},{clean_sql_num(r['pf'])},{clean_sql_num(r['pts'])},{clean_sql_num(r['triple_doubles'])})" for r in season_totals_rows]
        for i in range(0, len(st_chunks), 1000):
            f.write(f"INSERT INTO `season_totals` (`player_season_id`, `g`, `gs`, `mp`, `fg`, `fga`, `fg3`, `fg3a`, `fg2`, `fg2a`, `ft`, `fta`, `orb`, `drb`, `trb`, `ast`, `stl`, `blk`, `tov`, `pf`, `pts`, `triple_doubles`) VALUES {','.join(st_chunks[i:i+1000])};\n")
        f.write("UNLOCK TABLES;\n\n")

        # Season Advanced
        f.write("DROP TABLE IF EXISTS `season_advanced`;\n")
        f.write("""CREATE TABLE `season_advanced` (
  `player_season_id` int NOT NULL,
  `per` float DEFAULT NULL,
  `ts_pct` float DEFAULT NULL,
  `fg3a_rate` float DEFAULT NULL,
  `ft_rate` float DEFAULT NULL,
  `orb_pct` float DEFAULT NULL,
  `drb_pct` float DEFAULT NULL,
  `trb_pct` float DEFAULT NULL,
  `ast_pct` float DEFAULT NULL,
  `stl_pct` float DEFAULT NULL,
  `blk_pct` float DEFAULT NULL,
  `tov_pct` float DEFAULT NULL,
  `usg_pct` float DEFAULT NULL,
  `ows` float DEFAULT NULL,
  `dws` float DEFAULT NULL,
  `ws` float DEFAULT NULL,
  `ws_per_48` float DEFAULT NULL,
  `obpm` float DEFAULT NULL,
  `dbpm` float DEFAULT NULL,
  `bpm` float DEFAULT NULL,
  `vorp` float DEFAULT NULL,
  PRIMARY KEY (`player_season_id`),
  CONSTRAINT `season_advanced_ibfk_1` FOREIGN KEY (`player_season_id`) REFERENCES `player_season` (`player_season_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\nLOCK TABLES `season_advanced` WRITE;\n""")
        sa_chunks = [f"({r['player_season_id']},{clean_sql_num(r['per'], True)},{clean_sql_num(r['ts_pct'], True)},{clean_sql_num(r['fg3a_rate'], True)},{clean_sql_num(r['ft_rate'], True)},{clean_sql_num(r['orb_pct'], True)},{clean_sql_num(r['drb_pct'], True)},{clean_sql_num(r['trb_pct'], True)},{clean_sql_num(r['ast_pct'], True)},{clean_sql_num(r['stl_pct'], True)},{clean_sql_num(r['blk_pct'], True)},{clean_sql_num(r['tov_pct'], True)},{clean_sql_num(r['usg_pct'], True)},{clean_sql_num(r['ows'], True)},{clean_sql_num(r['dws'], True)},{clean_sql_num(r['ws'], True)},{clean_sql_num(r['ws_per_48'], True)},{clean_sql_num(r['obpm'], True)},{clean_sql_num(r['dbpm'], True)},{clean_sql_num(r['bpm'], True)},{clean_sql_num(r['vorp'], True)})" for r in season_adv_rows]
        for i in range(0, len(sa_chunks), 1000):
            f.write(f"INSERT INTO `season_advanced` (`player_season_id`, `per`, `ts_pct`, `fg3a_rate`, `ft_rate`, `orb_pct`, `drb_pct`, `trb_pct`, `ast_pct`, `stl_pct`, `blk_pct`, `tov_pct`, `usg_pct`, `ows`, `dws`, `ws`, `ws_per_48`, `obpm`, `dbpm`, `bpm`, `vorp`) VALUES {','.join(sa_chunks[i:i+1000])};\n")
        f.write("UNLOCK TABLES;\n\n")

        # MVP Vote
        f.write("DROP TABLE IF EXISTS `mvp_vote`;\n")
        f.write("""CREATE TABLE `mvp_vote` (
  `season_year` int NOT NULL,
  `player_id` int NOT NULL,
  `rank_num` int DEFAULT NULL,
  `is_tied` tinyint(1) NOT NULL,
  `first_votes` int DEFAULT NULL,
  `pts_won` int DEFAULT NULL,
  `pts_max` int DEFAULT NULL,
  `share` float DEFAULT NULL,
  PRIMARY KEY (`season_year`,`player_id`),
  KEY `player_id` (`player_id`),
  CONSTRAINT `mvp_vote_ibfk_1` FOREIGN KEY (`season_year`) REFERENCES `season` (`season_year`),
  CONSTRAINT `mvp_vote_ibfk_2` FOREIGN KEY (`player_id`) REFERENCES `player` (`player_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\nLOCK TABLES `mvp_vote` WRITE;\n""")
        mvp_chunks = [f"({r['season_year']},{r['player_id']},{clean_sql_num(r['rank_num'])},{r['is_tied']},{clean_sql_num(r['first_votes'])},{clean_sql_num(r['pts_won'])},{clean_sql_num(r['pts_max'])},{clean_sql_num(r['share'], True)})" for r in mvp_rows]
        for i in range(0, len(mvp_chunks), 1000):
            f.write(f"INSERT INTO `mvp_vote` (`season_year`, `player_id`, `rank_num`, `is_tied`, `first_votes`, `pts_won`, `pts_max`, `share`) VALUES {','.join(mvp_chunks[i:i+1000])};\n")
        f.write("UNLOCK TABLES;\n\n")

        # Footer
        f.write("""/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;
/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
-- Dump completed
""")

    print(f"[SUCCESS] Complete standalone dump written: {nba_db_dump} ({os.path.getsize(nba_db_dump)/1024/1024:.2f} MB)")
    print("[SUCCESS] All MySQL files (CSV tables, LOAD DATA script, SQL dump) ready.")


if __name__ == '__main__':
    build_mysql_dump()
