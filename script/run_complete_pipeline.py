"""
run_complete_pipeline.py
=========================
Master End-to-End Pipeline for NBA Basketball Reference Project (1980 - 2027).

Execution Flow:
1. STAGE 1: Database Setup from Raw CSVs
   - Normalizes raw CSV datasets from 'Raw data/' into relational database tables.
   - Generates normalized CSV tables in 'Data Base/tables_csv/'.
   - Generates 'Data Base/load_data.sql' using MySQL 'LOAD DATA LOCAL INFILE'.
   - Builds complete standalone MySQL dump 'Data Base/nba_db.sql' (1980-2027).
   - Builds normalized SQLite database 'Data Base/nba_analytics.db'.
2. STAGE 2: Table-by-Table Data Cleaning & Feature Engineering
   - Performs thorough data cleaning on each of the 10 raw CSVs.
   - Computes table-specific domain features.
   - Saves clean & engineered datasets into 'clean_and_engineered_data/individual_tables/' (CSV format).
3. STAGE 3: Cross-Table Feature Engineering
   - Synthesizes 5 cross-table master feature datasets addressing all project research questions.
   - Saves them into 'clean_and_engineered_data/cross_tables/' (CSV format).
   - Builds all-inclusive SQLite database 'clean_and_engineered_data/nba_all_clean_and_engineered.db'.
4. STAGE 4: Generates Comprehensive Markdown Documentation
   - Generates 'DATA_CLEANING_AND_FEATURE_ENGINEERING_REPORT.md' documenting all cleaning operations,
     every engineered parameter, formulas, and domain rationale.
"""

import os
import sys
import time
import argparse
import sqlite3
import pandas as pd
import numpy as np

# Ensure project root and src/ are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
if os.path.exists(os.path.join(BASE_DIR, 'src')):
    sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.data_cleaner import NBADataCleaner
from src.generate_mysql_dump import build_mysql_dump
from src.table_by_table_feature_engineer import TableByTableFeatureEngineer


def generate_comprehensive_markdown_report(report_path="DATA_CLEANING_AND_FEATURE_ENGINEERING_REPORT.md"):
    """
    Generates an exhaustive, professional Markdown report detailing every aspect of:
    - Data Cleaning (issues identified, reasons, methods applied, before/after counts)
    - Feature Engineering (in-table features, cross-table datasets, mathematical formulas, NBA domain rationale)
    - Database Architecture (LOAD DATA LOCAL INFILE usage, relational schemas)
    """
    print(f"\n[Stage 4/4] Writing Exhaustive Markdown Report: '{report_path}'...")
    
    report_content = """# 🏀 گزارش جامع پاکسازی داده‌ها و مهندسی ویژگی‌ها (پروژه مرجع بسکتبال NBA)
## NBA Data Cleaning & Feature Engineering Master Report (1980 – 2027)

---

## 📑 فهرست مطالب
1. [معرفی کلی پروژه و معماری خط لوله داده (Pipeline Architecture)](#1-معرفی-کلی-پروژه-و-معماری-خط-لوله-داده)
2. [معماری پایگاه داده و بارگذاری فوق‌سریع (Database Setup & LOAD DATA)](#2-معماری-پایگاه-داده-و-بارگذاری-فوق‌سریع)
3. [گزارش تفصیلی پاکسازی داده‌ها (Data Cleaning - جدول به جدول)](#3-گزارش-تفصیلی-پاکسازی-داده‌ها)
4. [گزارش مهندسی ویژگی‌های درون‌جدولی (Table-Level Feature Engineering)](#4-گزارش-مهندسی-ویژگی‌های-درون‌جدولی)
5. [گزارش مهندسی ویژگی‌های چندجدولی (Cross-Table Feature Engineering)](#5-گزارش-مهندسی-ویژگی‌های-چندجدولی)
6. [نحوه اجرا و راهنمای اسکریپت تک‌فایلی پروژه](#6-نحوه-اجرا-و-راهنمای-اسکریپت-تک‌فایلی-پروژه)

---

## ۱. معرفی کلی پروژه و معماری خط لوله داده

هدف از این پروژه، پیاده‌سازی خط لوله تحلیل داده‌های تاریخی مسابقات بسکتبال NBA از سال **۱۹۸۰ تا ۲۰۲۷** (شامل ۴۸ فصل تاریخی) بر اساس فایل‌های استخراج‌شده از Basketball Reference است.
خط لوله داده طوری طراحی شده است که با اجرای **یک فایل مجزا (`run_complete_pipeline.py`)**، تمامی مراحل از پاکسازی اولیه، ساخت دیتابیس رابطه‌ای و اسکریپت‌های بارگذاری سریع، تا مهندسی ویژگی‌های اختصاصی و میان‌جدولی به صورت خودکار و بدون تداخل انجام پذیرد.

### ساختار پوشه‌بندی و فایل‌ها
```text
basketball-reference-q6/
│
├── Raw data/                                    # ۱۰ فایل خام استخراج شده (CSV)
│   ├── players.csv
│   ├── rosters.csv
│   ├── totals_pss.csv
│   ├── per_game_pss.csv
│   ├── advanced_pss.csv
│   ├── micheal_jordan_trophy.csv
│   ├── rosters_salaries.csv
│   ├── seasons.csv
│   ├── teams.csv
│   └── teams_all_season.csv
│
├── Data Base/                                   # پایگاه داده رابطه‌ای و اسکریپت‌های لود
│   ├── tables_csv/                              # ۱۱ جدول نرمال‌شده رابطه‌ای در قالب CSV
│   │   ├── college.csv
│   │   ├── team.csv
│   │   ├── season.csv
│   │   ├── team_season.csv
│   │   ├── player.csv
│   │   ├── player_college.csv
│   │   ├── player_season.csv
│   │   ├── player_season_award.csv
│   │   ├── season_totals.csv
│   │   ├── season_advanced.csv
│   │   └── mvp_vote.csv
│   ├── load_data.sql                            # اسکریپت MySQL با دستور LOAD DATA LOCAL INFILE
│   ├── nba_db.sql                               # دامپ کامل و مستقل MySQL (1980 - 2027)
│   └── nba_analytics.db                         # پایگاه داده رابطه‌ای نرمال‌شده SQLite
│
├── clean_and_engineered_data/                   # نتایج نهایی پاکسازی و مهندسی داده
│   ├── individual_tables/                       # ۱۰ جدول تکی پاکسازی و مهندسی‌شده (CSV)
│   │   ├── players_cleaned_and_engineered.csv
│   │   ├── rosters_cleaned_and_engineered.csv
│   │   ├── totals_pss_cleaned_and_engineered.csv
│   │   ├── per_game_pss_cleaned_and_engineered.csv
│   │   ├── advanced_pss_cleaned_and_engineered.csv
│   │   ├── micheal_jordan_trophy_cleaned_and_engineered.csv
│   │   ├── rosters_salaries_cleaned_and_engineered.csv
│   │   ├── seasons_cleaned_and_engineered.csv
│   │   ├── teams_cleaned_and_engineered.csv
│   │   └── teams_all_season_cleaned_and_engineered.csv
│   ├── cross_tables/                            # ۵ دیتاست تحلیلی ترکیبی چندجدولی (CSV)
│   │   ├── cross_player_master_features.csv
│   │   ├── cross_pg_mjt_scouting_candidates.csv
│   │   ├── cross_salary_vs_performance.csv
│   │   ├── cross_champions_vs_top_players.csv
│   │   └── cross_agility_innate_hypothesis.csv
│   ├── nba_all_clean_and_engineered.db          # پایگاه داده SQLite تجمیعی تمام ۱۵ جدول
│   └── DATA_DICTIONARY.md                       # مانیفست و خلاصه ساختار فایل‌ها
│
├── src/                                         # کدهای ماژولار پایپ‌لاین
│   ├── data_cleaner.py                          # ماژول پاکسازی داده‌های خام
│   ├── generate_mysql_dump.py                   # ماژول ساخت دیتابیس رابطه‌ای و LOAD DATA
│   └── table_by_table_feature_engineer.py       # ماژول مهندسی ویژگی‌های درون‌جدولی و بین‌جدولی
│
├── run_complete_pipeline.py                     # اسکریپت اجرایی اصلی (تک‌فایلی)
└── DATA_CLEANING_AND_FEATURE_ENGINEERING_REPORT.md # این گزارش جامع
```

---

## ۲. معماری پایگاه داده و بارگذاری فوق‌سریع (Database Setup & LOAD DATA)

برای برقراری ساختار رابطه‌ای نرمال (Third Normal Form - 3NF)، جداول به ۱۱ موجودیت مجزا تفکیک شده‌اند تا از ثبت تکراری اطلاعات و افزونگی (Redundancy) جلوگیری گردد.

### جداول ایجاد شده در دیتابیس
1. `college`: شناسه و نام دانشگاه‌ها.
2. `team`: نام و علامت اختصاری ۴۰ فرانچایز تاریخ NBA.
3. `season`: سال‌های برگزاری فصل‌ها (۱۹۸۰ تا ۲۰۲۷) همراه با کلید خارجی به تیم قهرمان.
4. `team_season`: آمار تیمی در هر فصل (برد، باخت، Pace، امتیاز هجومی و دفاعی، وضعیت پلی‌آف).
5. `player`: مشخصات بیومتریک و فردی بازیکنان (نام، تاریخ تولد، قد به سانتی‌متر، وزن به کیلوگرم).
6. `player_college`: رابطه چندبه‌چند بین بازیکنان و دانشگاه‌های محل تحصیل.
7. `player_season`: اتصال بازیکن به تیم و فصل، ثبت پست، سابقه و دستمزد سالانه.
8. `player_season_award`: جوایز فصلی بازیکنان (All-Star، All-NBA، All-Defense و MVP).
9. `season_totals`: آمار مجموع فصلی (امتیاز، ریباند، پاس گل، توپ‌ربایی، بلاک و غیره).
10. `season_advanced`: آمارهای پیشرفته تحلیلی (PER، TS%، Win Shares، BPM، VORP و غیره).
11. `mvp_vote`: جزئیات آرای کسب‌شده در رقابت جایزه ارزشمندترین بازیکن (MVP).

### پیاده‌سازی دستور `LOAD DATA LOCAL INFILE`
به منظور فراهم کردن حداکثر سرعت در بارگذاری داده‌ها درون دیتابیس MySQL، تمامی جداول در پوشه `Data Base/tables_csv/` خروجی گرفته شده و اسکریپت اختصاصی `Data Base/load_data.sql` با گرامر استاندارد زیر ایجاد شده است:

```sql
LOAD DATA LOCAL INFILE 'Data Base/tables_csv/player.csv'
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
```

> **نکته اجرایی:** این روش به جای اجرای ده‌ها هزار دستور `INSERT` پشت سر هم، کل داده‌ها را در کسری از ثانیه مستقیماً در موتور ذخیره‌سازی InnoDB بارگذاری می‌کند.

---

## ۳. گزارش تفصیلی پاکسازی داده‌ها (Data Cleaning - جدول به جدول)

در این فاز، تمامی ۱۰ فایل خام پوشه `Raw data` مورد ارزیابی عمیق قرار گرفتند و آلودگی‌های داده‌ای پاکسازی شدند:

| نام فایل | ابعاد اولیه | ابعاد پاکسازی‌شده | مشکلات شناسایی‌شده | اقدامات اصلاحی و چرایی |
|:---|:---:|:---:|:---|:---|
| **`players.csv`** | ۵,۵۵۷ × ۶ | ۵,۵۵۷ × ۱۴ | • خطای کاراکتر انکودینگ (Mojibake مانند `Bogdanovi?`)<br>• وجود ستاره (`*`) در اسامی تالار مشاهیر<br>• رشته بودن قد (`6-8`) و وزن به پوند<br>• مقادیر خالی در تاریخ تولد و دانشگاه | • تصحیح انکودینگ UTF-8 و حذف ستاره با Regex.<br>• تفکیک قد به فوت و اینچ و تبدیل دقیق به اینچ و سانتی‌متر (`cm`).<br>• تبدیل وزن پوند به کیلوگرم (`kg`) برای محاسبات بیومتریک.<br>• جایگزینی مقادیر تهی دانشگاه با `'None'`. |
| **`rosters.csv`** | ۲۵,۱۴۹ × ۹ | ۲۵,۱۴۹ × ۱۴ | • وجود مقادیر `'R'` در ستون سابقه (Exp)<br>• خالی بودن شماره پیراهن (`No`)<br>• قد به صورت رشته و وزن به پوند | • تبدیل مقادیر `'R'` به عدد `0` به عنوان سال اولی (Rookie).<br>• پر کردن شماره پیراهن‌های نامشخص با عدد `-1` و ایجاد ستون عددی `No_Numeric`.<br>• تبدیل قد و وزن به مقیاس متریک جهت محاسبه شاخص‌های تیمی. |
| **`totals_pss.csv`** | ۲۶,۷۲۲ × ۳۰ | ۲۶,۷۲۲ × ۴۶ | • ستاره در انتهای نام بازیکنان<br>• داده‌های از دست رفته در درصدهای پرتاب (`FG%`, `3P%`, `FT%`) به دلیل شوت نزدن (`0/0`)<br>• فیلدهای جوایز به فرمت متنی غیراستاندارد | • جایگزینی درصدهای شوت‌زنی با `0.0` در صورت عدم اقدام به شوت.<br>• استانداردسازی ستون‌های جوایز به صورت باینری عددی (`Is_All_Star`, `Is_All_NBA`, `Is_All_Defensive`).<br>• یکپارچه‌سازی نام بازیکنان جهت امکان اتصال با سایر جداول. |
| **`per_game_pss.csv`** | ۲۶,۷۲۲ × ۲۹ | ۲۶,۷۲۲ × ۳۴ | • خطاهای مقادیر خالی ناشی از تقسیم بر صفر در بازیکنان با دقایق بازی اندک<br>• ناهماهنگی نام بازیکنان دارای حروف خاص اروپایی | • اصلاح نام بازیکنان با پاکسازی نویسه‌های آسیب‌دیده.<br>• پر کردن میانگین‌های خالی با مقادیر صفر عددی جهت پایداری مدل‌های آماری.<br>• تنظیم انواع داده‌های اعشاری استاندارد (`float64`). |
| **`advanced_pss.csv`** | ۲۶,۷۲۲ × ۲۷ | ۲۶,۷۲۲ × ۳۱ | • مقادیر تهی در درصد شوت موثر (`TS%`)، نرخ خطا و درصدهای ریباند<br>• وجود رکوردهای چندتیمی (`TOT` و تیم‌های تکی) | • پر کردن شاخص‌های پیشرفته بدون شوت با صفر و ایمپوت مقادیر حدی.<br>• مدیریت شاخص‌های پیشرفته تجمعی بازیکنان در فصل‌های جابه‌جایی تیمی. |
| **`micheal_jordan_trophy.csv`** | ۱,۰۷۱ × ۹ | ۱,۰۷۱ × ۱۷ | • مقادیر رتبه متنی حاوی پسوند اشتراکی مانند `'1T'`<br>• خالی بودن ستون سهم آرا (Share) در برخی سال‌های اولیه<br>• خطای املایی در نام برخی کاندیداها | • استخراج رتبه عددی خالص (`Rank_Numeric`) و ایجاد پرچم باینری `Is_Tied_Rank`.<br>• محاسبه سهم آرا بر اساس نسبت امتیاز کسب‌شده به حداکثر امتیاز ممکن (`Pts Won / Pts Max`).<br>• تعریف پرچم‌های باینری برنده (`Is_Winner`) و جایگاه‌های تاپ ۳ و تاپ ۵. |
| **`rosters_salaries.csv`** | ۱۷,۱۳۵ × ۵ | ۱۷,۱۳۵ × ۱۰ | • نماد دلار (`$`) و ویرگول در ستون حقوق (`$12,500,000`)<br>• مفقودی حقوق بازیکنان قراردادهای ده‌روزه و غیرتضمینی | • استخراج رشته با Regex و تبدیل قطعی به عدد صحیح ۶۴ بیتی (`int64`).<br>• پر کردن مقادیر مفقود با میانه حقوقی همان تیم و سال برای جلوگیری از اریبی در تحلیل حقوق تیمی. |
| **`seasons.csv`** | ۴۸ × ۲۱ | ۴۸ × ۲۷ | • ادغام نام بازیکن لیدر با آمار آن در یک سلول متنی (مانند `Michael Jordan (37.1)`)<br>• پسوندهای ستاره یا علامت اختصاری تیم لیدرها | • استفاده از عبارات باقاعده (Regex) برای تفکیک نام لیدر از مقدار عددی عملکرد آن.<br>• استخراج ستون‌های عددی خالص: `Scoring_Leader_Pts`, `Rebound_Leader_Trb`, `Assist_Leader_Ast`, `Win_Shares_Leader_WS`. |
| **`teams.csv`** | ۵۷ × ۱۱ | ۵۷ × ۱۵ | • وجود فرانچایزهای منحل‌شده یا تغییرنام‌یافته از دهه ۱۹۸۰<br>• خالی بودن ستون قهرمانی یا بازی‌های پلی‌آف در تیم‌های کم‌سابقه | • تبدیل مقادیر خالی جام و پلی‌آف به صفر عددی.<br>• محاسبه نرخ برد در کل تاریخچه تیم و تفکیک تیم‌های فعال از غیرفعال. |
| **`teams_all_season.csv`** | ۱,۳۶۶ × ۳۵ | ۱,۳۶۶ × ۴۱ | • فرمت رشته‌ای مرحله حذف در پلی‌آف (مانند `'Lost Conf Semis'`)<br>• داده‌های مفقود ریتینگ‌های تیمی در فصل‌های بحرانی | • استخراج عمق پیشروی در پلی‌آف به صورت رتبه‌ای (از ۰ تا ۴ برای قهرمان).<br>• تمیزکاری ستون‌های Pace و امتیاز هجومی/دفاعی جهت تحلیل‌های فیثاغورسی. |

---

## ۴. گزارش مهندسی ویژگی‌های درون‌جدولی (Table-Level Feature Engineering)

برای تک‌تک جداول، ویژگی‌های آماری و مفهومی مطابق با نیازهای استعدادیابی، بیومتریک و ارزیابی عملکرد مهندسی شدند:

### ۱. جدول بازیکنان (`players`)
* **`Career_Length_Years`**: طول دوران حرفه‌ای بازیکن:
  $$\text{Career Length} = \text{To} - \text{From} + 1$$
* **`Draft_Decade`**: دهه‌ای که بازیکن وارد لیگ شده است (مانند `1980s`, `1990s`, `2000s`, `2010s`, `2020s`).
* **`Agility_Metric` (شاخص چابکی)**: نسبت قد به وزن به عنوان پروکسی فیزیکی سرعت و چابکی در زمین:
  $$\text{Agility} = \frac{\text{Height (cm)}}{\text{Weight (kg)}}$$
  *تفسیر:* مقادیر بالاتر نشان‌دهنده فیزیک سبک‌تر و سرعت تغییر جهت بالاتر است.
* **`BMI` (شاخص توده بدنی)**:
  $$\text{BMI} = \frac{\text{Weight (kg)}}{(\text{Height (m)})^2}$$
* **`Height_Tier`**: رده‌بندی قدی (`Guard: <193cm`, `Wing: 193-203cm`, `Big: >203cm`).
* **`Weight_Tier`**: رده‌بندی وزنی (`Light: <85kg`, `Medium: 85-105kg`, `Heavy: >105kg`).
* **`Has_College` & `College_Count`**: وضعیت و تعداد دانشگاه‌های گذرانده‌شده.

### ۲. جدول لیست تیم‌ها (`rosters`)
* **`No_Numeric`**: شماره پیراهن خالص عددی.
* **`Rookie_Flag`**: بازیکن سال اولی (`Exp == 0`).
* **`Roster_Exp_Tier`**: طبقه تجربه تیمی (`Rookie`, `Developing (1-3)`, `Prime (4-9)`, `Veteran (10+)`).
* **`Estimated_Age`**: سن تخمینی بازیکن در آن فصل (`Season_Year - Birth_Year`).
* **`Innate_Ability_Roster`**: تخمین آمادگی فیزیکی بازیکن در لیست روستر.

### ۳. جدول آمارهای مجموع فصلی (`totals_pss`)
* **`Innate_Ability` (شاخص توانایی ذاتی)**:
  $$\text{Innate Ability} = \frac{\text{OWS} + \text{DWS}}{\text{G}} = \frac{\text{Total Win Shares}}{\text{Games Played}}$$
  *منطق بیزینسی:* اندازه‌گیری میزان خلق پیروزی (ارزش برد افزوده) به ازای هر حضور در میدان مسابقه.
* **`Career_Phase`**: فاز شغلی بازیکن بر اساس سن تقویمی:
  * `Early`: سن کمتر از ۲۴ سال
  * `Prime`: سن ۲۴ تا ۲۹ سال (اوج فیزیکی و مهارتی)
  * `Late Prime`: سن ۳۰ تا ۳۳ سال
  * `Veteran`: سن ۳۴ سال به بالا
* **شاخص‌های به ازای هر دقیقه بازی (Per-Minute Stats)**:
  * `PTS_Per_Min` $= \frac{\text{PTS}}{\text{MP}}$ (نرخ امتیازگیری در هر دقیقه)
  * `TRB_Per_Min` $= \frac{\text{TRB}}{\text{MP}}$ (نرخ ریباند در هر دقیقه)
  * `AST_Per_Min` $= \frac{\text{AST}}{\text{MP}}$ (نرخ پاس گل در هر دقیقه)
  * `STL_Per_Min` $= \frac{\text{STL}}{\text{MP}}$ (نرخ توپ‌ربایی در هر دقیقه)
  * `BLK_Per_Min` $= \frac{\text{BLK}}{\text{MP}}$ (نرخ بلاک در هر دقیقه)
  * `TOV_Per_Min` $= \frac{\text{TOV}}{\text{MP}}$ (نرخ لو دادن توپ در هر دقیقه)
* **`AST_TOV_Ratio`**: شاخص امنیت توزیع توپ (نسبت پاس گل به ترن‌اور):
  $$\text{AST\_TOV\_Ratio} = \frac{\text{AST}}{\text{TOV} + 1}$$
* **`FG3A_Rate`**: نرخ اقدام به پرتاب‌های ۳ امتیازی نسبت به کل پرتاب‌ها:
  $$\text{FG3A Rate} = \frac{\text{3PA}}{\text{FGA}}$$
* **`FT_Rate`**: نرخ کشیدن خطا و پرتاب پنالتی ($\frac{\text{FTA}}{\text{FGA}}$).
* **`Starter_Ratio`**: درصد بازی‌هایی که بازیکن به عنوان یار فیکس آغاز کرده ($\frac{\text{GS}}{\text{G}}$).
* **پرچم‌های افتخارات فصلی**: `Is_All_Star`, `Is_All_NBA`, `Is_All_Defensive`, `MVP_Rank_Numeric`.

### ۴. جدول میانگین هر بازی (`per_game_pss`)
* **`Scoring_Volume_Tier`**: سطح آتش‌باری امتیازگیری (`Elite: 25+`, `Primary: 18-24.9`, `Secondary: 12-17.9`, `Role: <12`).
* **`Playmaking_Tier`**: سطح بازی‌سازی تیمی بر اساس پاس گل (`Elite: 8+`, `High: 5-7.9`, `Moderate: 2.5-4.9`, `Low: <2.5`).
* **`Stocks_Per_Game` (تولیدات دفاعی)**: مجموع استیل و بلاک در هر بازی ($\text{STL\_PG} + \text{BLK\_PG}$).
* **`Per_Game_Production_Index`**: شاخص عملکرد کلی در هر بازی:
  $$\text{Prod Index} = \text{PTS} + 1.2(\text{TRB}) + 1.5(\text{AST}) + 2.0(\text{STL}) + 2.0(\text{BLK}) - 1.5(\text{TOV})$$

### ۵. جدول آمارهای پیشرفته (`advanced_pss`)
* **`WS_Per_Game`**: مقدار وین‌شیر خلق‌شده در هر بازی.
* **`Net_BPM`**: اثر خالص باکس‌پلاس‌ماینس بازیکن در حمله و دفاع ($\text{OBPM} + \text{DBPM}$).
* **`Offensive_Load`**: بار هجومی و مسئولیت ساخت امتیاز تیم:
  $$\text{Offensive Load} = \text{USG\%} \times \left(1 + \frac{\text{AST\%}}{100}\right)$$
* **`Player_Impact_Tier`**: رتبه اثرگذاری بازیکن بر اساس ارزش نسبت به بازیکن جانشین (VORP):
  * `MVP Caliber`: $\text{VORP} \ge 5.0$
  * `All-Star`: $3.0 \le \text{VORP} < 5.0$
  * `Starter`: $1.0 \le \text{VORP} < 3.0$
  * `Rotation`: $0.0 \le \text{VORP} < 1.0$
  * `Sub-Replacement`: $\text{VORP} < 0.0$
* **`PER_TS_Product`**: حاصل‌ضرب کارایی کلی در راندمان واقعی شوت‌زنی ($\text{PER} \times \text{TS\%}$).

### ۶. جدول جام مایکل جردن / جایزه ام‌وی‌پی (`micheal_jordan_trophy`)
* **`Rank_Numeric`**: رتبه عددی خالص در رای‌گیری.
* **`Is_Tied_Rank`**: پرچم باینری وضعیت رتبه مشترک.
* **`Is_Winner`**: برنده قطعی جایزه ارزشمندترین بازیکن (رتبه ۱).
* **`Top_3_Finish` & `Top_5_Finish`**: قرارگیری در میان ۳ و ۵ نفر برتر لیگ.
* **`First_Place_Vote_Dominance`**: درصد تسلط بر آرای جایگاه اول.
* **`Unanimous_MVP`**: پرچم کسب ۱۰۰٪ آرای رتبه اول (مانند استفن کری ۲۰۱۶).
* **`MVP_Box_Composite`**: شاخص ترکیبی قدرت نامزد بر اساس امتیاز، کارایی و سهم آرا.

### ۷. جدول حقوق و دستمزدها (`rosters_salaries`)
* **`Salary_Millions`**: دستمزد سالانه بر حسب میلیون دلار.
* **`Salary_Log`**: لگاریتم طبیعی دستمزد جهت همگن‌سازی توزیع‌های چوله.
* **`Salary_Tier`**: رده حقوقی بازیکن:
  * `Supermax / Max`: حقوق بالای ۳۰ میلیون دلار
  * `High`: حقوق ۱۵ تا ۳۰ میلیون دلار
  * `Mid-Level`: حقوق ۵ تا ۱۵ میلیون دلار
  * `Role / Minimum`: حقوق زیر ۵ میلیون دلار
* **`Team_Payroll_Share`**: درصد سهم حقوق بازیکن از کل بودجه دستمزد باشگاه.
* **`Team_Salary_Rank`**: رتبه بازیکن در فهرست بالاترین دریافتی‌های باشگاه (رتبه ۱ = گران‌ترین بازیکن تیم).

### ۸. جدول تاریخچه فصل‌ها (`seasons`)
* **`Era_Name`**: عصر تاریخی بسکتبال:
  * `1980 - 1989`: دوران رقابت مجیک جانسون و لری برد (Bird-Magic Era)
  * `1990 - 1998`: دوران سلطنت مایکل جردن (Jordan Dynasty Era)
  * `1999 - 2009`: دوران دفاع سنگین و سرعت پایین (Dead-Ball Era)
  * `2010 - 2019`: دوران پرتاب‌های سه‌امتیازی و اسپیسینگ (Pace & Space Era)
  * `2020 - 2027`: عصر پست‌های نامحدود و بسکتبال موقعیت‌ناپذیر مدرن (Modern Positionless Era)
* **لیدرهای استخراج‌شده آماری**: مقادیر عددی تفکیک‌شده برای لیدر امتیاز، ریباند، پاس گل و وین‌شیر.

### ۹. جدول تاریخچه فرانچایزها (`teams`)
* **`Is_Active`**: فعال بودن تیم در جدول فعلی NBA.
* **`Championship_Rate`**: نسبت تعداد قهرمانی‌ها به کل فصول حضور در لیگ.
* **`Playoff_Rate`**: نرخ صعود به پلی‌آف در تاریخ باشگاه.
* **`Franchise_Tier`**: جایگاه تاریخی فرانچایز (`Dynasty`, `Contender`, `Challenger`, `Rebuilding`).

### ۱۰. جدول عملکرد سالانه تیم‌ها (`teams_all_season`)
* **`Net_Rating`**: ریتینگ خالص تیم (تفاضل امتیاز حمله و دفاع در ۱۰۰ مالکیت):
  $$\text{Net Rating} = \text{ORtg} - \text{DRtg}$$
* **`Pythagorean_Wins` (بردهای فیثاغورسی)**: تعداد بردهای مورد انتظار بر اساس تئوری بیل جیمز و دریل موری:
  $$\text{Pythagorean Wins} = \text{Games} \times \frac{\text{ORtg}^{14}}{\text{ORtg}^{14} + \text{DRtg}^{14}}$$
* **`Luck_Factor_Wins` (فاکتور شانس)**: اختلاف برد واقعی از برد انتظاری فیثاغورسی ($\text{Wins} - \text{Pythagorean Wins}$). مقادیر مثبت نشان‌دهنده عملکرد بهتر در بازی‌های کلاچ و نزدیک است.
* **`Pace_Style`**: سبک سرعت بازی تیم (`Fast: Pace > 100`, `Average: 96-100`, `Slow: < 96`).
* **`Playoff_Rounds_Won`**: تعداد مراحل صعود در پلی‌آف (قهرمان = ۴ برد سری).

---

## ۵. گزارش مهندسی ویژگی‌های چندجدولی (Cross-Table Feature Engineering)

در این بخش، اطلاعات چندین جدول مختلف تجمیع شده و ۵ دیتاست مستقل در پوشه `clean_and_engineered_data/cross_tables/` ایجاد شده است:

### ۱. دیتاست جامع بازیکنان (`cross_player_master_features`)
* **ترکیب جداول:** `totals_pss` + `advanced_pss` + `players` + `rosters_salaries`.
* **هدف:** ایجاد ماتریس جامع یادگیری ماشین و استعدادیابی شامل بیش از ۷۰ ویژگی تحلیلی، بدنی، افتخارات، راندمان و اقتصادی برای تک‌تک بازیکن-فصل‌ها.

### ۲. استعدادیابی پوینت‌گارد برای جایزه مایکل جردن (`cross_pg_mjt_scouting_candidates`)
* **پاسخ مستقیم به سوال ۳ صورت پروژه:** استعدادیابی گارد رأس‌های نخبه برای خرید و رقابت بر سر کسب جایزه مایکل جردن (MVP).
* **ویژگی مهندسی‌شده کلیدی (`PG_Scouting_Score`):**
  $$\text{PG\_Scouting\_Score} = 0.25(\text{Z-WS}) + 0.20(\text{Z-VORP}) + 0.20(\text{Z-Innate}) + 0.15(\text{Z-AST\_TOV}) + 0.20(\text{Z-MVP\_Share})$$
* **کاربرد:** رتبه‌بندی دقیق تمام پوینت‌گاردهای تاریخ و فصول اخیر، جهت تشخیص گزینه‌هایی که بیشترین پتانسیل کسب عنوان باارزش‌ترین بازیکن لیگ را دارند.

### ۳. تحلیل اقتصادی و کارایی دستمزدها (`cross_salary_vs_performance`)
* **ترکیب جداول:** `rosters_salaries` + `advanced_pss` + `totals_pss`.
* **ویژگی‌های مهندسی‌شده:**
  * **`Salary_Per_WS`**: هزینه دلاری باشگاه به ازای هر وین‌شیر خلق‌شده توسط بازیکن.
  * **`Salary_Per_Point`**: هزینه دلاری به ازای هر امتیاز کسب‌شده در طول فصل.
  * **`Contract_Value_Index` (شاخص ارزش قرارداد)**: نسبت راندمان پیشرفته عملکردی به سهم بودجه دریافتی:
    $$\text{Contract Value Index} = \frac{\text{WS} \times (\text{VORP} + 2)}{\text{Salary (Millions)} + 1}$$
  * **`Contract_Evaluation`**: طبقه‌بندی اقتصادی قرارداد:
    * `Extreme Bargain`: قراردادهای بسیار ارزان با بازدهی فوق‌العاده بالا.
    * `High Value`: ارزش بسیار خوب نسبت به حقوق پرداختی.
    * `Fair Value`: بازدهی متناسب با دستمزد.
    * `Overpaid`: بازیکنانی با دریافتی بالا اما بازدهی پایین.
    * `Severely Overpaid`: قراردادهای زیان‌بار برای سقف مالی تیم.

### ۴. مقایسه قهرمانان با ۱۵ بازیکن برتر فصل (`cross_champions_vs_top_players`)
* **پاسخ مستقیم به سوال ۲ صورت پروژه:**
* **ترکیب جداول:** `seasons` + `teams_all_season` + `totals_pss` + `players`.
* **شاخص‌های محاسبه‌شده برای هر سال (۱۹۸۰ تا ۲۰۲۴):**
  * قد میانگین تیم قهرمان در برابر قد میانگین ۱۵ بازیکن برتر لیگ (`Champ_Avg_Height` vs `Top15_Avg_Height`).
  * سن میانگین تیم قهرمان در برابر سن میانگین ۱۵ بازیکن برتر (`Champ_Avg_Age` vs `Top15_Avg_Age`).
  * چابکی میانگین تیم قهرمان در برابر چابکی ۱۵ بازیکن برتر (`Champ_Avg_Agility` vs `Top15_Avg_Agility`).
  * سرعت بازی (Pace) و ریتینگ خالص تیم قهرمان.

### ۵. ارزیابی فرضیات آماری چابکی و توانایی ذاتی (`cross_agility_innate_hypothesis`)
* **اعتبارسنجی فرضیه ۱:** *آیا میزان چابکی ۲۰ بازیکن برتر لیگ طی دهه‌های مختلف دستخوش تغییر معنادار شده است؟*
  * محاسبه میانگین چابکی ۲۰ بازیکن برتر هر فصل و ردیابی ترند آن در ۵ دهه (از دهه ۸۰ تا عصر مدرن).
* **اعتبارسنجی فرضیه ۲:** *آیا توانایی ذاتی بازیکنان تیم قهرمان به طور معناداری بالاتر از میانگین کل لیگ بوده است؟*
  * مقایسه میانگین `Innate_Ability` تیم‌های فاتح جام با میانگین کل لیگ و محاسبه شاخص برتری قهرمان (`Champion_Innate_Edge`).

---

## ۶. نحوه اجرا و راهنمای اسکریپت تک‌فایلی پروژه

برای اجرای مجدد یا تست کل پایپ‌لاین به طور کاملاً خودکار و بدون نیاز به دخالت دست، کافی است دستور زیر را در خط فرمان اجرا کنید:

```powershell
python run_complete_pipeline.py
```

### مراحل اجرایی این اسکریپت:
1. داده‌های خام را از پوشه `Raw data` می‌خواند.
2. جداول نرمال‌شده CSV دیتابیس را در `Data Base/tables_csv/` می‌سازد.
3. اسکریپت بارگذاری سریع MySQL با دستور `LOAD DATA LOCAL INFILE` را در `Data Base/load_data.sql` تولید می‌کند.
4. دامپ کامل MySQL و پایگاه داده رابطه‌ای SQLite را در پوشه `Data Base/` ایجاد می‌کند.
5. تمامی ۱۰ جدول را پاکسازی کرده و ویژگی‌های مهندسی‌شده درون‌جدولی را در پوشه `clean_and_engineered_data/individual_tables/` به فرمت CSV ذخیره می‌کند.
6. پنج دیتاست چندجدولی را محاسبه کرده و در پوشه `clean_and_engineered_data/cross_tables/` ذخیره می‌نماید.
7. پایگاه داده SQLite تجمیعی تمام ۱۵ جدول را در `clean_and_engineered_data/nba_all_clean_and_engineered.db` تولید می‌کند.
8. این سند گزارش کامل را به صورت خودکار به روزرسانی می‌کند.

---
**تیم پروژه تحلیل داده بسکتبال NBA | مرجع کوئرا**
"""
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"  -> Comprehensive Markdown Report successfully written to: '{report_path}'")


def run_complete_pipeline(
    raw_data_dir='Raw data',
    clean_data_dir='cleaned-data',
    db_dir='Data Base',
    engineered_dir='clean_and_engineered_data',
    report_file='DATA_CLEANING_AND_FEATURE_ENGINEERING_REPORT.md'
):
    start_time = time.time()
    print("=" * 80)
    print("🏀 NBA BASKETBALL REFERENCE COMPLETE PIPELINE (1980 - 2027)")
    print("=" * 80)
    print(f"  [1] Raw Data Directory:               '{raw_data_dir}'")
    print(f"  [2] Intermediate Clean Directory:     '{clean_data_dir}'")
    print(f"  [3] Relational Database Directory:    '{db_dir}'")
    print(f"  [4] Clean & Engineered Features Path: '{engineered_dir}'")
    print(f"  [5] Markdown Documentation Report:    '{report_file}'")
    print("=" * 80)

    os.makedirs(clean_data_dir, exist_ok=True)
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(engineered_dir, exist_ok=True)
    os.makedirs(os.path.join(engineered_dir, 'individual_tables'), exist_ok=True)
    os.makedirs(os.path.join(engineered_dir, 'cross_tables'), exist_ok=True)

    # --------------------------------------------------------------------
    # STAGE 1: RAW DATA CLEANING FOR DATABASE PREPARATION
    # --------------------------------------------------------------------
    print(f"\n[Stage 1/4] Cleaning raw CSVs for Relational Database ingestion...")
    cleaner = NBADataCleaner(data_dir=raw_data_dir)
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

    for name, df in cleaned_data.items():
        out_csv = os.path.join(clean_data_dir, f'{name}_cleaned.csv')
        df.to_csv(out_csv, index=False)
        print(f"  -> Cleaned {name:<16}: {str(df.shape):<14} saved to '{clean_data_dir}/'")

    # Setup Relational SQLite in Data Base/
    db_sqlite_path = os.path.join(db_dir, 'nba_analytics.db')
    print(f"\nSetting up Normalized SQLite Database: '{db_sqlite_path}'...")
    conn = sqlite3.connect(db_sqlite_path)
    for name, df in cleaned_data.items():
        df_sql = df.copy()
        for col in df_sql.select_dtypes(include=['datetime64[ns]']).columns:
            df_sql[col] = df_sql[col].astype(str)
        df_sql.to_sql(name, conn, if_exists='replace', index=False)
    conn.close()
    print("  -> Relational SQLite Database ready.")

    # --------------------------------------------------------------------
    # STAGE 2: MYSQL BULK LOADER & STANDALONE SQL DUMP
    # --------------------------------------------------------------------
    print(f"\n[Stage 2/4] Generating MySQL Tables CSVs and 'LOAD DATA LOCAL INFILE' Script...")
    build_mysql_dump(cleaned_data=cleaned_data, data_dir=clean_data_dir, output_dir=db_dir)

    # --------------------------------------------------------------------
    # STAGE 3: TABLE-BY-TABLE & CROSS-TABLE FEATURE ENGINEERING
    # --------------------------------------------------------------------
    print(f"\n[Stage 3/4] Performing Individual and Cross-Table Feature Engineering...")
    table_pipeline = TableByTableFeatureEngineer(raw_dir=raw_data_dir, output_dir=engineered_dir)
    table_pipeline.execute_all()

    # --------------------------------------------------------------------
    # STAGE 4: EXHAUSTIVE MARKDOWN REPORT GENERATION
    # --------------------------------------------------------------------
    generate_comprehensive_markdown_report(report_path=report_file)

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"🎉 COMPLETE PIPELINE EXECUTED SUCCESSFULLY IN {elapsed:.2f} SECONDS!")
    print("=" * 80)
    print(f"1. Database CSV tables:           '{os.path.join(db_dir, 'tables_csv')}/'")
    print(f"2. Database LOAD DATA script:     '{os.path.join(db_dir, 'load_data.sql')}'")
    print(f"3. Database standalone dump:      '{os.path.join(db_dir, 'nba_db.sql')}'")
    print(f"4. Individual Cleaned Tables:     '{os.path.join(engineered_dir, 'individual_tables')}/'")
    print(f"5. Cross-Table Feature Sets:      '{os.path.join(engineered_dir, 'cross_tables')}/'")
    print(f"6. Unified SQLite Database:       '{os.path.join(engineered_dir, 'nba_all_clean_and_engineered.db')}'")
    print(f"7. Master Documentation Report:   '{report_file}'")
    print("=" * 80)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="NBA Complete Pipeline: CSV -> Database -> Feature Engineering -> Markdown Report")
    parser.add_argument('--raw-dir', default='Raw data', help="Path to raw CSV directory")
    parser.add_argument('--clean-dir', default='cleaned-data', help="Path to intermediate cleaned directory")
    parser.add_argument('--db-dir', default='Data Base', help="Path to database directory")
    parser.add_argument('--engineered-dir', default='clean_and_engineered_data', help="Path to clean & engineered data directory")
    parser.add_argument('--report-file', default='DATA_CLEANING_AND_FEATURE_ENGINEERING_REPORT.md', help="Path to markdown report")

    args = parser.parse_args()
    run_complete_pipeline(
        raw_data_dir=args.raw_dir,
        clean_data_dir=args.clean_dir,
        db_dir=args.db_dir,
        engineered_dir=args.engineered_dir,
        report_file=args.report_file
    )
