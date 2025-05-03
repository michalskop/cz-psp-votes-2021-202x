"""Create list of all MPs."""

# data standard: https://www.popoloproject.com/specs/person.html

import datetime
import numpy as np
import pandas as pd

import io
import requests
import zipfile

path = './v2/'
source_path = "source/"
views_path = "views/"

# current term is PSP9
current_term = 'PSP9'
historical = False
# current_term = 'PSP1'
# historical = True

region_type_name = 'Volební kraj - 2002'

# download fresh data
url = "https://www.psp.cz/eknih/cdrom/opendata/poslanci.zip"
r = requests.get(url, verify=True)
if r.ok:
  z = zipfile.ZipFile(io.BytesIO(r.content))
  z.extractall(path + source_path)


# read osoby, transform to standard format
osoby = pd.read_csv(path + source_path + "osoby.unl", sep="|", encoding="cp1250", header=None)
header = ['mp_id', 'title_pre', 'family_name', 'given_name', 'title_post', 'birth_date', 'gender', 'updated_on', 'death_date', 'dummy']
osoby.columns = header
osoby['birth_date'] = osoby['birth_date'].apply(lambda x: datetime.datetime.strptime(x, '%d.%m.%Y').strftime('%Y-%m-%d'))
osoby['death_date'] = osoby['death_date'].apply(lambda x: datetime.datetime.strptime(x, '%d.%m.%Y').strftime('%Y-%m-%d') if x is not np.nan else np.nan)

# read poslanec
poslanec = pd.read_csv(path + source_path + "poslanec.unl", sep='|', encoding='cp1250', header=None)
header = ['id', 'mp_id', 'region_id', 'list_id', 'org_id', 'web', 'street', 'municipality', 'postcode', 'email','phone', 'fax', 'psp_phone', 'facebook', 'photo', 'dummy']
poslanec.columns = header

# read organy
# correct split rows
def fix_split_rows(file_path):
  # Read the entire file
  with open(file_path, 'r', encoding='cp1250') as file:
    content = file.read()
  
  # Fix the split rows by replacing newline followed by pipe
  fixed_content = content.replace('\n|', '')
  
  # Create StringIO object with fixed content
  import io
  fixed_data = io.StringIO(fixed_content)
  
  # Read with pandas
  df = pd.read_csv(fixed_data, 
                   sep='|', 
                   encoding='cp1250',
                   header=None)
  return df

organy = fix_split_rows(path + source_path + "organy.unl")
header = ['org_id', 'sup_org_id', 'type_org_id', 'org_abbreviation', 'org_name_cs', 'org_name_en', 'org_since', 'org_until', 'priority', 'members_base', 'dummy']
organy.columns = header
# note: some dates are not in the correct format
def parse_date(date_str):
  for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
    try:
      return pd.to_datetime(date_str, format=fmt)
    except ValueError:
      continue
  return pd.NaT

organy["org_since"] = organy["org_since"].apply(parse_date)
organy["org_until"] = organy["org_until"].apply(parse_date)

# read typ_organu
typ_organu = pd.read_csv(path + source_path + "typ_organu.unl", sep='|', encoding='cp1250', header=None)
header = ['type_org_id', 'type_sup_org_id', 'type_org_name_cs', 'type_org_name_en', 'general_type_org_id', 'priority', 'dummy']
typ_organu.columns = header
parlament_id = typ_organu[typ_organu['type_org_name_cs'] == 'Parlament']['type_org_id'].values[0]

# read zarazeni
zarazeni = pd.read_csv(path + source_path + "zarazeni.unl", sep='|', encoding='cp1250', header=None)
header = ['mp_id', 'of_id', 'of_status', 'since', 'until', 'm_since', 'm_until', 'dummy']
zarazeni.columns = header
zarazeni['since'] = zarazeni['since'].apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d %H').strftime('%Y-%m-%d'))
zarazeni['until'] = zarazeni['until'].apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d %H').strftime('%Y-%m-%d') if x is not np.nan else np.nan)

# read funkce
funkce = pd.read_csv(path + source_path + "funkce.unl", sep='|', encoding='cp1250', header=None)
header = ['function_id', 'organ_id', 'function_type_id', 'function_name_cs', 'priority', 'dummy']
funkce.columns = header

# JOINS
term_id = organy[organy['org_abbreviation'] == current_term]['org_id'].values[0]
term_since = organy[organy['org_id'] == term_id]['org_since'].values[0]
term_since = pd.to_datetime(term_since).strftime('%Y-%m-%d')
data = poslanec[poslanec['org_id'] == term_id].merge(osoby, on='mp_id')
current_parl = zarazeni[(zarazeni['of_id'] == term_id) & (zarazeni['of_status'] == 0)]
data = data.merge(current_parl, on='mp_id')
# region
region_type = typ_organu[typ_organu['type_org_name_cs'] == region_type_name]['type_org_id'].values[0]
organy_region = organy[organy['type_org_id'] == region_type].loc[:, ['org_id', 'org_name_cs', 'org_name_en']].rename(columns={'org_name_cs': 'region_name_cs', 'org_name_en': 'region_name_en', 'org_id': 'region_id'})
data = data.merge(organy_region, on='region_id')
# list
data = data.merge(organy.loc[:, ['org_id', 'org_abbreviation', 'org_name_cs', 'org_name_en']].rename(columns={'org_abbreviation': 'list_abbreviation', 'org_name_cs': 'list_name_cs', 'org_name_en': 'list_name_en', 'org_id': 'list_id'}), on='list_id')
# groups
group_type = typ_organu[typ_organu['type_org_name_cs'] == 'Klub']['type_org_id'].values[0]
organy_group = organy[organy['type_org_id'] == group_type].loc[:, ['org_id', 'org_name_cs', 'org_name_en', 'org_abbreviation']].rename(columns={'org_name_cs': 'group_name_cs', 'org_name_en': 'group_name_en', 'org_id': 'group_id', 'org_abbreviation': 'group_abbreviation'})
# add nezařazení
organy[organy['org_name_cs'] == 'Nezařazení']

group_memberships = zarazeni[(zarazeni['of_id'].isin(organy_group['group_id'])) & (zarazeni['of_status'] == 0) & (zarazeni['since'] > term_since)]
# current groups
current_group_memberships = group_memberships[group_memberships['until'].isnull()].loc[:, ['mp_id', 'of_id', 'since', 'until']].rename(columns={'of_id': 'group_id', 'since': 'group_since', 'until': 'group_until'})
data = data.merge(current_group_memberships, on='mp_id', how='left')
# last groups for former mps
open_memberships = group_memberships[group_memberships['until'].isnull()]
open_mps_ids = open_memberships['mp_id'].unique()
former_mps = group_memberships[group_memberships['until'].notnull() & ~group_memberships['mp_id'].isin(open_mps_ids)]

last_group_memberships = former_mps.loc[:, ['mp_id', 'of_id', 'since', 'until']].rename(columns={'of_id': 'group_id', 'since': 'group_since', 'until': 'group_until'})
last_group_memberships['group_until_day'] = pd.to_datetime(last_group_memberships['group_until'], format='%Y-%m-%d')
last_group_memberships = last_group_memberships.loc[last_group_memberships.groupby('mp_id')['group_until_day'].idxmax()]
data = data.merge(last_group_memberships, on='mp_id', how='left')

# merge groups
data['group_id'] = (data['group_id_x'].replace(np.nan, 0) + data['group_id_y'].replace(np.nan, 0)).astype(int)
data['last_group_since'] = (data['group_since_x'].replace(np.nan, '') + data['group_since_y'].replace(np.nan, ''))
data['last_group_until'] = data['group_until_y']
# add group details
data = data.merge(organy_group, on='group_id', how='left')
data.rename(columns={'group_name_cs': 'last_group_name_cs', 'group_name_en': 'last_group_name_en', 'group_abbreviation': 'last_group_abbreviation', 'group_id': 'last_group_id'}, inplace=True)

# currently in parliament
data['current'] = data['last_group_until'].isnull()

# full term
data['full_term'] = (data['since'] == term_since) & data['current']

# clear spaces
c2c = data.columns[data.dtypes == 'object'].tolist()
for c in c2c:
  data[c] = data[c].apply(lambda x: x.strip() if type(x) == str else x)

# rename id to psp_id
data.rename(columns={'id': 'psp_id'}, inplace=True)

# filter
columns = ['psp_id', 'mp_id', 'family_name', 'given_name', 'title_pre', 'title_post', 'birth_date', 'death_date', 'gender', 'region_id', 'region_name_cs', 'region_name_en', 'list_id', 'list_abbreviation', 'list_name_cs', 'list_name_en', 'last_group_id', 'last_group_abbreviation','last_group_name_cs', 'last_group_name_en',  'last_group_since', 'last_group_until', 'since', 'until', 'current', 'full_term', 'web', 'street', 'municipality', 'postcode', 'email', 'phone', 'fax', 'psp_phone', 'facebook']

# save
if historical:
  data.loc[:, columns].to_csv(path + views_path + f'mps_{current_term}.csv', index=False)
else:
  data.loc[:, columns].to_csv(path + views_path + 'mps.csv', index=False)
  data.loc[:, columns].to_json(path + views_path + 'mps.json', orient='records', force_ascii=False, indent=2)



