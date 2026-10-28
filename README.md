# 🏀 NBA Basketball Reference: End-to-End Analytics Pipeline

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Database](https://img.shields.io/badge/RDBMS-MySQL%20%7C%20SQLite-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0%2B-150458.svg?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Plotly](https://img.shields.io/badge/Plotly-Interactive_Viz-3F4F75.svg?logo=plotly&logoColor=white)](https://plotly.com/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-K--Means-F7931E.svg?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Status](https://img.shields.io/badge/Project_Status-Completed-success.svg)]()

> **پروژه نهایی بوت‌کمپ تحلیل داده کوئرا (تابستان ۱۴۰۵)**  
> تحلیل آماری، وب‌اسکرپینگ، پایگاه‌داده رابطه‌ای و تست فرض داده‌های لیگ NBA مرجع Basketball-Reference (فصول ۱۹۸۰ تا ۲۰۲۷).

---

## 📌 معرفی کلی پروژه (Project Overview)

این پروژه یک پیاده‌سازی گام‌به‌گام از کل چرخه حیات داده (**Full Data Lifecycle**) است که شامل مراحل زیر می‌باشد:
1. **فاز اول (Web Scraping):** خزش ساختاریافته داده‌های تاریخی مسابقات بسکتبال NBA از مرجع [Basketball-Reference](https://www.basketball-reference.com).
2. **فاز دوم (Database Design & Normalization):** طراحی پایگاه داده رابطه‌ای نرمال (3NF) با ۱۱ جدول مجزا در MySQL و SQLite به همراه اسکریپت بارگذاری سریع `LOAD DATA LOCAL INFILE`.
3. **پالایش و مهندسی ویژگی‌ها (Data Cleaning & Feature Engineering):** اصلاح خطاهای انکودینگ (Mojibake)، استانداردسازی متریک، تفکیک بازیکنان معامله‌شده (`Is_Multi_Team_Aggregate`) و ساخت شاخص‌های چابکی، توانایی ذاتی و BMI.
4. **فاز سوم - بخش اول (Descriptive Statistics):** تحلیل توزیع قد نامزدهای مایکل جردن (MVP)، بررسی قد و تجربه تیم‌های قهرمان، و استعدادیابی پست Point Guard.
5. **فاز سوم - بخش دوم (Hypothesis Testing):** آزمون‌های فرض آماری ناپارامتریک شاپیرو-ویلک، ویلکاکسون و من-ویتنی.
6. **بخش‌های امتیازی (Bonus Section):** خوشه‌بندی عملکرد بازیکنان با الگوریتم K-Means و آزمون فرض آماری مقایسه دستمزد در خوشه‌ها.

---

## 🏗 ساختار دایرکتوری مخزن (Repository Architecture)

```text
basketball-reference-q6/
│
├── NBA_Merged_Master_Pipeline.ipynb             # نوت‌بوک اصلی و یکپارچه شامل کل فازها از صفر تا صد
├── NBA_Databases.ipynb                          # نوت‌بوک اختصاصی مدیریت دیتابیس‌ها و کوئری‌های SQL
│
├── scraping.py                                  # اسکریپت وب‌اسکرپینگ با BeautifulSoup و requests_cache
│
├── Data Base/                                   # معماری پایگاه‌داده رابطه‌ای
│   ├── tables_csv/                              # ۱۱ جدول تفکیک‌شده و نرمال (CSV)
│   ├── load_data.sql                            # بارگذاری فوق‌سریع MySQL با LOAD DATA LOCAL INFILE
│   ├── nba_db.sql                               # دامپ کامل و مستقل MySQL (فصول ۱۹۸۰ تا ۲۰۲۷)
│   ├── nba_analytics.db                         # پایگاه داده رابطه‌ای سبک SQLite
│   └── nba_analytics.sql                        # دامپ SQL پایگاه داده رابطه‌ای
│
├── clean_and_engineered_data/                   # خروجی نهایی داده‌های تمیز و ویژگی‌های جدید
│   ├── individual_tables/                       # ۱۰ جدول تکی پاکسازی و مهندسی‌شده (CSV)
│   ├── cross_tables/                            # ۵ جدول تحلیلی ترکیبی چندجدولی (CSV)
│   ├── nba_all_clean_and_engineered.db          # پایگاه داده تجمیعی تمام ۱۵ جدول (SQLite)
│   └── nba_all_clean_and_engineered.sql         # دامپ کامل SQL پایگاه تحلیلی (۴۴.۷ مگابایت)
│
├── Raw data/                                    # داده‌های خام استخراج شده از وب (۱۰ فایل CSV)
│
├── script/                                      # اسکریپت‌ها و ماژول‌های پروژه (OOP & Pipeline)
│   ├── NBA.ipynb
│   ├── clean_and_feature_engineer.py
│   ├── data_cleaner.py
│   ├── feature_engineer.py
│   ├── generate_mysql_dump.py
│   ├── run_clean_data_pipeline.py
│   ├── run_complete_pipeline.py
│   ├── scraping.py
│   └── table_by_table_feature_engineer.py
│
|---Hypothesis Testing                           #تست فرض
|
├── requirements.txt                             # لیست پکیج‌ها و پیش‌نیازهای پروژه
|
└── README.md                                    # مستندات معرفی پروژه
```

---

## ⚙️ نوت‌بوک‌های تحلیلی اصلی (Notebooks Guide)

### ۱. نوت‌بوک مستر: [`NBA_Merged_Master_Pipeline.ipynb`](NBA_Merged_Master_Pipeline.ipynb)
نوت‌بوک اصلی پروژه که به صورت کاملاً ساختاریافته به زبان انگلیسی فازها را پوشش می‌دهد:
* **Phase 1: Data Acquisition (Web Scraping):** توابع استخراج داده‌های بیومتریک، روستر، آمار فصلی و جوایز.
* **Phase 2: Database Design & Relational Schema:** مدل‌های ۱۱ گانه SQLAlchemy ORM در سطح ۳NF و فرآیند ETL.
* **Data Cleaning & Feature Engineering:** فرمول‌های شاخص چابکی (قد به وزن)، توانایی ذاتی (تجربه به سن)، شاخص BMI و نسبت پاس به ترن‌اور.
* **Phase 3 - Part 1: Descriptive Statistics:**
  - سوال ۱: مقایسه قد نامزدهای تروفی مایکل جردن در برابر ۵۰ اسکورر برتر لیگ (فصول ۲۰۲۰ تا ۲۰۲۴).
  - سوال ۲: توزیع قد و تجربه تیم‌های قهرمان (دنور ۲۰۲۳ و بوستون ۲۰۲۴) در برابر ۱۵ بازیکن برتر با باکس‌پلات تعاملی.
  - سوال ۳: استعدادیابی پست Point Guard و ارائه ۳ پیشنهاد برتر (دانچیچ، کری و گیلجس-الکساندر/پاول).
* **Phase 3 - Part 2: Hypothesis Testing:**
  - فرضیه اول: تست افزایش چابکی ۲۰ بازیکن برتر با شاپیرو-ویلک و ویلکاکسون/من-ویتنی ($p > 0.05 \implies$ عدم رد فرض صفر).
  - فرضیه دوم: بررسی توانایی ذاتی قهرمانان با من-ویتنی ($p > 0.05 \implies$ عدم رد فرض صفر).
* **Bonus Section:** خوشه‌بندی بازیکنان با K-Means و ارزیابی تفاوت دستمزد در خوشه‌ها.

### ۲. نوت‌بوک پایگاه‌داده: [`NBA_Databases.ipynb`](NBA_Databases.ipynb)
* مدیریت و ثبت رجیستری تمامی فایل‌های SQL (`load_data.sql`, `nba_db.sql`, `nba_analytics.sql`, `nba_all_clean_and_engineered.sql`).
* اجرای کوئری‌های تحلیلی چندجدولی با `JOIN` جهت استخراج مستقیم داده‌ها از جداول پایگاه داده.

---

## 🔬 یافته‌های کلیدی آماری (Key Analytical Findings)

1. **توزیع قد نامزدهای MVP در برابر ۵۰ اسکورر برتر:**
   - نامزدهای مایکل جردن با میانگین قد حدود ۲۰۱ سانتی‌متر به طور معناداری بلندقامت‌تر از میانگین عمومی اسکوررهای لیگ (حدود ۱۹۷ سانتی‌متر) هستند؛ این امر نشان‌دهنده تغییر ماهیت MVP مدرن به سمت «یونیکورن‌ها» و فورواردهای بازیساز همه‌کاره (نظیر یوکیچ، یانیس و امبید) است.
2. **قد و سابقه تیم‌های قهرمان:**
   - قهرمانان دو فصل اخیر (دنور ناگتس و بوستون سلتیکس) تعادل سنی و تجربه‌ای بالایی در رختکن دارند (میانگین سابقه ۶ تا ۷ سال) که ناشی از عمق بالای نیمکت است، برخلاف گروه ۱۵ اسکورر برتر که تمرکزشان بر عملکرد انفرادی فوق‌العاده است.
3. **استعدادیابی و اولویت خرید پست Point Guard:**
   - **اولویت اول:** Luka Dončić (۵ بار حضور متوالی در لیست MJT، سهم رأی 0.968 و امتیاز ۳۰+)
   - **اولویت دوم:** Stephen Curry (۳ بار حضور در لیست، پرتاب‌های تاریخ‌ساز و فضا سازی عالی)
   - **اولویت سوم:** Shai Gilgeous-Alexander / Chris Paul (بهره‌وری فوق‌العاده هجومی و نسبت پاس گل به ترن‌اور عالی)
4. **نتایج آزمون‌های فرضیه:**
   - فرضیه اول (چابکی ۲۰ بازیکن برتر): مقدار $p$-value برابر با ۰.۴۸ بود و فرض صفر رد نشد؛ ستاره‌های لیگ همچنان توازن عضلانی و قد متناسبی حفظ کرده‌اند.
   - فرضیه دوم (توانایی ذاتی قهرمانان): مقدار $p$-value برابر با ۰.۳۶ بود و فرض صفر رد نشد؛ قهرمانی مستلزم بلوغ فکری و تیمی در فاز اوج سنی است.

---

## 🚀 راهنمای نصب و اجرا (Quick Start)

### ۱. کلون کردن مخزن و نصب پیش‌نیازها:
```bash
git clone https://github.com/erfanpan/basketball-reference-q6.git
cd basketball-reference-q6
pip install -r requirements.txt
```

### ۲. بارگذاری سریع پایگاه داده در MySQL:
```bash
mysql --local-infile=1 -u root -p < "Data Base/load_data.sql"
```

### ۳. اجرای نوت‌بوک‌ها در ژوپیتر:
```bash
jupyter notebook NBA_Merged_Master_Pipeline.ipynb
```
(یا جهت بازبینی پایگاه‌داده‌ها و کوئری‌های SQL: `jupyter notebook NBA_Databases.ipynb`)

---

## 🛠 ابزارها و تکنولوژی‌ها (Tech Stack)

* **زبان و ابزار تحلیل:** Python 3.10+, Jupyter Notebook
* **وب‌اسکرپینگ:** BeautifulSoup4, Requests-Cache
* **پایگاه داده و رابطه‌ها:** MySQL 8.0, SQLite3, SQLAlchemy ORM (3NF)
* **پالایش و مهندسی داده:** Pandas, NumPy
* **آمار استنباطی و آزمون‌های فرض:** SciPy (Shapiro-Wilk, Mann-Whitney U, Wilcoxon)
* **یادگیری ماشین (بخش امتیازی):** Scikit-Learn (K-Means, StandardScaler, Silhouette)
* **مصورسازی:** Plotly Express, Plotly Graph Objects, Seaborn, Matplotlib
