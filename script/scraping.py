from bs4 import BeautifulSoup,Comment
import requests_cache
import time
import re
import pandas as pd
from urllib.parse import urljoin

base_url = 'https://www.basketball-reference.com/'
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
session = requests_cache.CachedSession("my_cache")
years = range(1980,2028)


def scraper(url,table_id):
    rows=[]
    url = url
    response = session.get(url,headers=headers)
    print(url, response.status_code, "cache" if response.from_cache else "live")
    soup = BeautifulSoup(response.text,'html.parser')
    table = soup.find("table", {"id": table_id})
    if not response.from_cache:
        time.sleep(4) 
    if table is None:
        for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
            if f'id="{table_id}"' in c:
                table = BeautifulSoup(c, 'html.parser').find("table", {"id": table_id})
                break
    if table is None:
        return None
    header = [head.get_text(strip=True) for head in table.find('thead').find_all('tr')[-1].find_all('th')]
    for row in table.find('tbody').find_all("tr"):
        if 'thead' in (row.get("class") or []):
            continue
        rows.append([cell.get_text(strip=True) for cell in row.find_all(['th','td'])])
    df = pd.DataFrame(rows,columns=header)
    return df 

def team_link(base_url,table_id=None):
    url=urljoin(base_url,'teams/')
    response = session.get(url,headers=headers)
    soup = BeautifulSoup(response.text,'html.parser')
    attrs = {"id": table_id} if table_id else {}
    tables = soup.find_all("table", attrs=attrs)
    links=[]
    for table in tables:
        for a in table.find_all("a", href=True):
            links.append(a["href"])
    return links

    
def players(base_url):
    alpha ='abcdefghijklmnopqrstuvwxyz'
    all_alpha=[]

    for i in alpha:
        df=scraper(urljoin(base_url, f"players/{i}/"),table_id='players')
        if df is not None:
            all_alpha.append(df)

    pd.concat(all_alpha,ignore_index=True).to_csv("players.csv", index=False, encoding="utf-8-sig")


def micheal_jordan_trophy(base_url):
    total_year=[]

    for year in years:
        df=scraper(urljoin(base_url,f'awards/awards_{year}.html'),table_id='mvp')
        if df is not None:
            df.insert(0,'Season', year)
            total_year.append(df)

    pd.concat(total_year,ignore_index=True).to_csv("micheal_jordan_trophy.csv", index=False, encoding="utf-8-sig")


def player_stats_season(base_url):
    html_pages = {
    'totals': 'totals_stats',
    'per_game': 'per_game_stats',
    'advanced': 'advanced',
}
   

    for page, table_id in html_pages.items():
        total_year=[]
        for year in years:
            df = scraper(url = urljoin(base_url,f'leagues/NBA_{year}_{page}.html'),table_id=table_id)
            if df is not None:
                df.insert(0,'Season', year)
                total_year.append(df)

        pd.concat(total_year,ignore_index=True).to_csv(f'{page}_pss.csv',index=False,encoding="utf-8-sig")

def teams(base_url):
    tabels={'teams_active':'active', 'teams_defunct':'defunct'}
    all_tabels=[]
    url = urljoin(base_url,'teams/')
    response = session.get(url,headers=headers)
    print(url, response.status_code, "cache" if response.from_cache else "live")
    soup = BeautifulSoup(response.text,'html.parser')
    for table_id , status in tabels.items():
        rows=[]
        code=[]
        table = soup.find("table", {"id": table_id})
        if not response.from_cache:
            time.sleep(3) 
        if table is None:
            for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
                if f'id="{table_id}"' in c:
                    table = BeautifulSoup(c, 'html.parser').find("table", {"id": table_id})
                    break
        if table is None:
            continue
        header = [head.get_text(strip=True) for head in table.find('thead').find_all('tr')[-1].find_all('th')]
        for row in table.find('tbody').find_all("tr"):
            if 'thead' in (row.get("class") or []):
                continue
            a = row.find('a', href=True)
            if a is None:
                a = row.find_previous('a', href=True)  
            if a is None:
                continue
            rows.append([cell.get_text(strip=True) for cell in row.find_all(['th', 'td'])])
            code.append(a['href'].split('/')[2])
        df = pd.DataFrame(rows,columns=header)
        df.insert(0,'Status',status)
        df.insert(1,'Team',code)
        all_tabels.append(df)
    if all_tabels:
        pd.concat(all_tabels,ignore_index=True).to_csv('teams.csv',index=False,encoding="utf-8-sig")
       


def seasons(base_url):
    rows=[]
    url = urljoin(base_url,'leagues/')
    response = session.get(url,headers=headers)
    print(url, response.status_code, "cache" if response.from_cache else "live")
    soup = BeautifulSoup(response.text,'html.parser')
    table = soup.find("table", {"id": 'stats'})
    if table:
        for row in table.find_all("tr"):
            rows.append([cell.get_text(strip=True) for cell in row.find_all(['th','td'])])
    df = pd.DataFrame(rows,columns=rows[1]) 
    df.to_csv('seasons.csv',index=False,encoding='utf-8-sig')   

def roster(base_url):

    links=team_link(base_url,'teams_active')
    all_years=[]
    for link_team in links: 
        for year in years:
            df = scraper(urljoin(base_url,f'{link_team}{year}.html'),"roster")
            if df is not None:
                df.insert(0,'Season',year)
                df.insert(1,'Team',link_team.split('/')[2])
                all_years.append(df)
    pd.concat(all_years,ignore_index=True).to_csv('rosters.csv',index=False,encoding="utf-8-sig")


def salaries(base_url):
    links=team_link(base_url,'teams_active')
    all_years=[]
    for link_team in links: 
        for year in years:
            df = scraper(urljoin(base_url,f'{link_team}{year}.html'),"salaries2")
            if df is not None:
                df.insert(0,'Season',year)
                df.insert(1,'Team',link_team.split('/')[2])
                all_years.append(df)
    pd.concat(all_years,ignore_index=True).to_csv('rosters_salaries.csv',index=False,encoding="utf-8-sig")
    

def teams_all_season(base_url):
    links=team_link(base_url)
    all_team=[]
    for link_team in links: 
            df = scraper(urljoin(base_url,f'{link_team}'),link_team.split('/')[2])
            if df is not None:
                all_team.append(df)
    pd.concat(all_team,ignore_index=True).to_csv('teams_all_season.csv',index=False,encoding="utf-8-sig")




# teams_all_season(base_url)
#salaries(base_url)   
# roster(base_url)
# players(base_url)
# micheal_jordan_trophy(base_url)
# player_stats_season(base_url)
# teams(base_url)
# seasons(base_url)