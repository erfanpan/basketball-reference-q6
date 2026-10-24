-- ====================================================================
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
LOAD DATA LOCAL INFILE 'E:/Pycharm Project/quera/basketball reference/basketball-reference-q6/Data Base/tables_csv/college.csv'
INTO TABLE `college`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(`college_id`, `name`);

-- Table: team
LOAD DATA LOCAL INFILE 'E:/Pycharm Project/quera/basketball reference/basketball-reference-q6/Data Base/tables_csv/team.csv'
INTO TABLE `team`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(`team_id`, `abbr`, `name`);

-- Table: season
LOAD DATA LOCAL INFILE 'E:/Pycharm Project/quera/basketball reference/basketball-reference-q6/Data Base/tables_csv/season.csv'
INTO TABLE `season`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(`season_year`, `label`, @champ_id)
SET `champion_team_id` = NULLIF(NULLIF(@champ_id, ''), '\\N');

-- Table: team_season
LOAD DATA LOCAL INFILE 'E:/Pycharm Project/quera/basketball reference/basketball-reference-q6/Data Base/tables_csv/team_season.csv'
INTO TABLE `team_season`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(`team_id`, `season_year`, @w, @l, @srs, @pace, @ortg, @drtg, @playoffs)
SET
  `wins` = NULLIF(NULLIF(@w, ''), '\\N'),
  `losses` = NULLIF(NULLIF(@l, ''), '\\N'),
  `srs` = NULLIF(NULLIF(@srs, ''), '\\N'),
  `pace` = NULLIF(NULLIF(@pace, ''), '\\N'),
  `ortg` = NULLIF(NULLIF(@ortg, ''), '\\N'),
  `drtg` = NULLIF(NULLIF(@drtg, ''), '\\N'),
  `playoffs` = NULLIF(NULLIF(@playoffs, ''), '\\N');

-- Table: player
LOAD DATA LOCAL INFILE 'E:/Pycharm Project/quera/basketball reference/basketball-reference-q6/Data Base/tables_csv/player.csv'
INTO TABLE `player`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(`player_id`, `name`, @bdate, @h_cm, @w_kg)
SET
  `birth_date` = NULLIF(NULLIF(@bdate, ''), '\\N'),
  `height_cm` = NULLIF(NULLIF(@h_cm, ''), '\\N'),
  `weight_kg` = NULLIF(NULLIF(@w_kg, ''), '\\N');

-- Table: player_college
LOAD DATA LOCAL INFILE 'E:/Pycharm Project/quera/basketball reference/basketball-reference-q6/Data Base/tables_csv/player_college.csv'
INTO TABLE `player_college`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(`player_id`, `college_id`);

-- Table: player_season
LOAD DATA LOCAL INFILE 'E:/Pycharm Project/quera/basketball reference/basketball-reference-q6/Data Base/tables_csv/player_season.csv'
INTO TABLE `player_season`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(`player_season_id`, `player_id`, @tid, `season_year`, @pos, @exp, @sal, `is_total`)
SET
  `team_id` = NULLIF(NULLIF(@tid, ''), '\\N'),
  `pos` = NULLIF(NULLIF(@pos, ''), '\\N'),
  `exp` = NULLIF(NULLIF(@exp, ''), '\\N'),
  `salary` = NULLIF(NULLIF(@sal, ''), '\\N');

-- Table: player_season_award
LOAD DATA LOCAL INFILE 'E:/Pycharm Project/quera/basketball reference/basketball-reference-q6/Data Base/tables_csv/player_season_award.csv'
INTO TABLE `player_season_award`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(`player_season_id`, `award_code`);

-- Table: season_totals
LOAD DATA LOCAL INFILE 'E:/Pycharm Project/quera/basketball reference/basketball-reference-q6/Data Base/tables_csv/season_totals.csv'
INTO TABLE `season_totals`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(`player_season_id`, @g, @gs, @mp, @fg, @fga, @fg3, @fg3a, @fg2, @fg2a, @ft, @fta, @orb, @drb, @trb, @ast, @stl, @blk, @tov, @pf, @pts, @td)
SET
  `g` = NULLIF(NULLIF(@g, ''), '\\N'),
  `gs` = NULLIF(NULLIF(@gs, ''), '\\N'),
  `mp` = NULLIF(NULLIF(@mp, ''), '\\N'),
  `fg` = NULLIF(NULLIF(@fg, ''), '\\N'),
  `fga` = NULLIF(NULLIF(@fga, ''), '\\N'),
  `fg3` = NULLIF(NULLIF(@fg3, ''), '\\N'),
  `fg3a` = NULLIF(NULLIF(@fg3a, ''), '\\N'),
  `fg2` = NULLIF(NULLIF(@fg2, ''), '\\N'),
  `fg2a` = NULLIF(NULLIF(@fg2a, ''), '\\N'),
  `ft` = NULLIF(NULLIF(@ft, ''), '\\N'),
  `fta` = NULLIF(NULLIF(@fta, ''), '\\N'),
  `orb` = NULLIF(NULLIF(@orb, ''), '\\N'),
  `drb` = NULLIF(NULLIF(@drb, ''), '\\N'),
  `trb` = NULLIF(NULLIF(@trb, ''), '\\N'),
  `ast` = NULLIF(NULLIF(@ast, ''), '\\N'),
  `stl` = NULLIF(NULLIF(@stl, ''), '\\N'),
  `blk` = NULLIF(NULLIF(@blk, ''), '\\N'),
  `tov` = NULLIF(NULLIF(@tov, ''), '\\N'),
  `pf` = NULLIF(NULLIF(@pf, ''), '\\N'),
  `pts` = NULLIF(NULLIF(@pts, ''), '\\N'),
  `triple_doubles` = NULLIF(NULLIF(@td, ''), '\\N');

-- Table: season_advanced
LOAD DATA LOCAL INFILE 'E:/Pycharm Project/quera/basketball reference/basketball-reference-q6/Data Base/tables_csv/season_advanced.csv'
INTO TABLE `season_advanced`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(`player_season_id`, @per, @ts, @fg3a, @ftr, @orb, @drb, @trb, @ast, @stl, @blk, @tov, @usg, @ows, @dws, @ws, @ws48, @obpm, @dbpm, @bpm, @vorp)
SET
  `per` = NULLIF(NULLIF(@per, ''), '\\N'),
  `ts_pct` = NULLIF(NULLIF(@ts, ''), '\\N'),
  `fg3a_rate` = NULLIF(NULLIF(@fg3a, ''), '\\N'),
  `ft_rate` = NULLIF(NULLIF(@ftr, ''), '\\N'),
  `orb_pct` = NULLIF(NULLIF(@orb, ''), '\\N'),
  `drb_pct` = NULLIF(NULLIF(@drb, ''), '\\N'),
  `trb_pct` = NULLIF(NULLIF(@trb, ''), '\\N'),
  `ast_pct` = NULLIF(NULLIF(@ast, ''), '\\N'),
  `stl_pct` = NULLIF(NULLIF(@stl, ''), '\\N'),
  `blk_pct` = NULLIF(NULLIF(@blk, ''), '\\N'),
  `tov_pct` = NULLIF(NULLIF(@tov, ''), '\\N'),
  `usg_pct` = NULLIF(NULLIF(@usg, ''), '\\N'),
  `ows` = NULLIF(NULLIF(@ows, ''), '\\N'),
  `dws` = NULLIF(NULLIF(@dws, ''), '\\N'),
  `ws` = NULLIF(NULLIF(@ws, ''), '\\N'),
  `ws_per_48` = NULLIF(NULLIF(@ws48, ''), '\\N'),
  `obpm` = NULLIF(NULLIF(@obpm, ''), '\\N'),
  `dbpm` = NULLIF(NULLIF(@dbpm, ''), '\\N'),
  `bpm` = NULLIF(NULLIF(@bpm, ''), '\\N'),
  `vorp` = NULLIF(NULLIF(@vorp, ''), '\\N');

-- Table: mvp_vote
LOAD DATA LOCAL INFILE 'E:/Pycharm Project/quera/basketball reference/basketball-reference-q6/Data Base/tables_csv/mvp_vote.csv'
INTO TABLE `mvp_vote`
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(`season_year`, `player_id`, @rk, `is_tied`, @fv, @pw, @pm, @sh)
SET
  `rank_num` = NULLIF(NULLIF(@rk, ''), '\\N'),
  `first_votes` = NULLIF(NULLIF(@fv, ''), '\\N'),
  `pts_won` = NULLIF(NULLIF(@pw, ''), '\\N'),
  `pts_max` = NULLIF(NULLIF(@pm, ''), '\\N'),
  `share` = NULLIF(NULLIF(@sh, ''), '\\N');

-- --------------------------------------------------------------------
-- 4. RESTORE ENVIRONMENT SETTINGS
-- --------------------------------------------------------------------
SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS = @OLD_UNIQUE_CHECKS;
SET SQL_MODE = @OLD_SQL_MODE;

SELECT 'NBA Database successfully bulk-loaded from CSV files!' AS Status;
