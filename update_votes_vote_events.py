"""Update votes and vote_events tables."""

# Note: depends on mps.csv from create_mp_list.py
# https://www.psp.cz/sqw/hp.sqw?k=1302

import datetime
import io
import numpy as np
import pandas as pd

import requests
import zipfile

# path
path = "./"
source_path = "source/"
data_path = "data/"

current_hlasovani = 2021
current_term = 'PSP9'

# download fresh data
url = "http://www.psp.cz/eknih/cdrom/opendata/hl-" + str(current_hlasovani) + "ps.zip"
r = requests.get(url, verify=True)
if r.ok:
  z = zipfile.ZipFile(io.BytesIO(r.content))
  z.extractall(path + source_path)

url = "https://www.psp.cz/eknih/cdrom/opendata/poslanci.zip"
r = requests.get(url, verify=True)
if r.ok:
  z = zipfile.ZipFile(io.BytesIO(r.content))
  z.extractall(path + source_path)

# read data
mps = pd.read_csv(path + data_path + "mps.csv")

votes = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "h1.unl", sep="|", encoding="cp1250", header=None)
header = ["mp_id", "vote_event_id", "vote", "dummy"]
votes.columns = header
del votes["dummy"]

vote_events = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "s.unl", sep="|", encoding="cp1250", header=None)
header = ['vote_event_id', 'org_id', 'sitting', 'vote_event_number', 'bod', 'date', 'time', 'yes', 'no', 'abstain', 'not_voting', 'voted', 'quorum', 'vote_event_type', 'result', 'name', 'short_name', 'dummy']
vote_events.columns = header
vote_events['date'] = vote_events['date'].apply(lambda x: datetime.datetime.strptime(x, "%d.%m.%Y").strftime("%Y-%m-%d"))
del vote_events["dummy"]

# check 1: zmatečná hlasování
invalid1 = []
try: 
  check = pd.read_csv(path + source_path + "zmatecne.unl", sep="|", encoding="cp1250")
  header = ['vote_event_id', 'dummy']
  check.columns = header
  invalid1 = list(check['vote_event_id'].unique())
except:
  pass

vote_events["invalid"] = False
vote_events["invalid"] = vote_events["vote_event_id"].isin(invalid1)

# check 2: zpochybnění
# note: we count also these to attendances
# note: mode: "Typ zpochybnění: 0 - žádost o opakování hlasování - v tomto případě se o této žádosti neprodleně hlasuje a teprve je-li tato žádost přijata, je hlasování opakováno; 1 - pouze sdělení pro stenozáznam, není požadováno opakování hlasování.""
invalid2 = []
try: 
  check = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "z.unl", sep="|", encoding="cp1250")
  header = ['vote_event_id', 'turn', 'mode', 'id_h2', 'id_h3', 'dummy']
  check.columns = header
  invalid2 = check[check['mode'] == 0]['vote_event_id'].unique()
except:
  pass

vote_events["repeted"] = False
vote_events["repeted"] = vote_events["vote_event_id"].isin(invalid1)

# ADD INFO ABOUT MPS
# read organy
organy = pd.read_csv(path + source_path + "organy.unl", sep='|', encoding='cp1250', header=None)
header = ['org_id', 'sup_org_id', 'type_org_id', 'org_abbreviation', 'org_name_cs', 'org_name_en', 'org_since', 'org_until', 'priority', 'members_base', 'dummy']
organy.columns = header
organy['org_since'] = organy['org_since'].apply(lambda x: datetime.datetime.strptime(x, '%d.%m.%Y').strftime('%Y-%m-%d'))
organy['org_until'] = organy['org_until'].apply(lambda x: datetime.datetime.strptime(x, '%d.%m.%Y').strftime('%Y-%m-%d') if x is not np.nan else np.nan)

# read typ_organu
typ_organu = pd.read_csv(path + source_path + "typ_organu.unl", sep='|', encoding='cp1250', header=None)
header = ['type_org_id', 'type_sup_org_id', 'type_org_name_cs', 'type_org_name_en', 'general_type_org_id', 'priority', 'dummy']
typ_organu.columns = header
parlament_id = typ_organu[typ_organu['type_org_name_cs'] == 'Parlament']['type_org_id'].values[0]

# read zarazeni
zarazeni = pd.read_csv(path + source_path + "zarazeni.unl", sep='|', encoding='cp1250', header=None)
header = ['id', 'of_id', 'of_status', 'since', 'until', 'm_since', 'm_until', 'dummy']
zarazeni.columns = header
zarazeni['since'] = zarazeni['since'].apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d %H').strftime('%Y-%m-%d'))
zarazeni['until'] = zarazeni['until'].apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d %H').strftime('%Y-%m-%d') if x is not np.nan else np.nan)

# read funkce
funkce = pd.read_csv(path + source_path + "funkce.unl", sep='|', encoding='cp1250', header=None)
header = ['funkce_id', 'org_id', 'type_org_id', 'name', 'priority', 'dummy']
funkce.columns = header

# JOINS
term_id = organy[organy['org_abbreviation'] == current_term]['org_id'].values[0]

group_type = typ_organu[typ_organu['type_org_name_cs'] == 'Klub']['type_org_id'].values[0]

groups = organy[(organy['type_org_id'] == group_type) & (organy['sup_org_id'] == term_id)]

group_ids = groups['org_id'].unique()

# merge vote_events
votes = votes.merge(vote_events.loc[:, ['vote_event_id', 'date']], how='left', on='vote_event_id')

# merge mps
votes = votes.merge(mps.loc[:, ['id', 'mp_id', 'family_name', 'given_name']], how='left', on='mp_id', suffixes=('', '_mp'))

# add group info
merged_df = pd.merge(votes, zarazeni[zarazeni['of_id'].isin(group_ids)], on="id", how="left")

filtered_df = merged_df[(merged_df['date'] > merged_df['since']) & (pd.isna(merged_df['until']) | (merged_df['date'] <= merged_df['until']))]

m_df = votes.merge(filtered_df.loc[:, ["mp_id", "vote_event_id", "id"]], on=["mp_id", "vote_event_id"], how="left", suffixes=('', '_filtered'))

not_in_filtered_df = m_df[m_df['id_filtered'].isna()]

full_df = pd.concat([filtered_df, not_in_filtered_df]).sort_values(by=['vote_event_id', 'id'])
full_df = full_df.merge(organy.loc[:, ['org_id', 'org_abbreviation']], how='left', left_on='of_id', right_on='org_id')

# final votes table
votes_df = full_df.loc[:, ['id', 'vote_event_id', 'vote', 'date', 'of_id', 'org_abbreviation']].rename(columns={'org_abbreviation': 'group_abbreviation', 'of_id': 'group_id', 'id': 'voter_id', 'vote': 'option'})

# replace options to standard
mapping = {'A': 'yes', 'N': 'no', 'B': 'no', 'C': 'abstain', 'F': 'not voting', '@': 'absent', 'M': 'excused', 'W': 'before oath', 'K': 'abstain'}

# Recode the column using the mapping
votes_df['option'] = votes_df['option'].replace(mapping)

# save data
votes_df.to_csv(path + "data/votes.csv", index=False)
vote_events.to_csv(path + "data/vote_events.csv", index=False)
