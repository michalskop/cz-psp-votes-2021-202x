"""Calculates rebelity and govity."""

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

current_term = 'PSP9'
current_hlasovani = 2021
gov_since = '2021-12-17'

# download fresh data
url = "http://www.psp.cz/eknih/cdrom/opendata/hl-" + str(current_hlasovani) + "ps.zip"
r = requests.get(url)
if r.ok:
  z = zipfile.ZipFile(io.BytesIO(r.content))
  z.extractall(path + source_path)

url = "https://www.psp.cz/eknih/cdrom/opendata/poslanci.zip"
r = requests.get(url)
if r.ok:
  z = zipfile.ZipFile(io.BytesIO(r.content))
  z.extractall(path + source_path)

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

# read hlasovani
votes = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "h1.unl", sep='|', encoding='cp1250', header=None)
header = ["mp_id", "vote_event_id", "vote", "dummy"]
votes.columns = header
del votes["dummy"]

# read vote events
vote_events = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "s.unl", sep="|", encoding="cp1250")
header = ['vote_event_id', 'org_id', 'sitting', 'vote_event_number', 'bod', 'date', 'time', 'yes', 'no', 'abstain', 'not_voting', 'voted', 'quorum', 'vote_event_type', 'result', 'name', 'short_name', 'dummy']
vote_events.columns = header
vote_events['date'] = vote_events['date'].apply(lambda x: datetime.datetime.strptime(x, "%d.%m.%Y").strftime("%Y-%m-%d"))

# check 1: zmatečná hlasování
invalid1 = []
try: 
    check = pd.read_csv(path + source_path + "zmatecne.unl", sep="|", encoding="cp1250")
    header = ['vote_event_id', 'dummy']
    check.columns = header
    invalid1 = list(check['vote_event_id'].unique())
except:
    pass

# check 2: zpochybnění
# note: we can use ...x or ...z, currently ...z is not available
# note: mode: "Typ zpochybnění: 0 - žádost o opakování hlasování - v tomto případě se o této žádosti neprodleně hlasuje a teprve je-li tato žádost přijata, je hlasování opakováno; 1 - pouze sdělení pro stenozáznam, není požadováno opakování hlasování.""
invalid2 = []
try: 
    # check = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "z.unl", sep="|", encoding="cp1250")
    # header = ['vote_event_id', 'turn', 'mode', 'id_h2', 'id_h3', 'dummy']
    check = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "x.unl", sep="|", encoding="cp1250")
    header = ['vote_event_id', 'mp_id', 'mode', 'dummy']
    check.columns = header
    invalid2 = list(check[check['mode'] == 0]['vote_event_id'].unique())
except:
    pass

invalid = invalid1 + invalid2

# valid votes (not zpochynění)
valid_votes = votes[~votes['vote_event_id'].isin(invalid)]

# read mps from previously prepared file
mps = pd.read_csv(path + data_path + "mps.csv")

# add org_id
current_parliament_id = organy[(organy['type_org_id'] == parlament_id) & (organy['org_abbreviation'] == current_term)]['org_id'].iloc[0]

valid_votes['org_id'] = pd.NA
valid_votes['in_gov'] = False
valid_votes = valid_votes.merge(vote_events.loc[:, ['vote_event_id', 'date']], on='vote_event_id')

for index, row in mps.iterrows():
  mp = row

  t = zarazeni[zarazeni['id'] == mp['id']].merge(organy, left_on='of_id', right_on='org_id').merge(typ_organu, on='type_org_id')
  membership = t[(t['type_org_name_cs'] == 'Klub') & (t['sup_org_id'] == current_parliament_id)]
  membershipgov = t[(t['type_org_name_cs'] == 'Vláda')]

  for i, mm in membership.iterrows():
    valid_votes.loc[(valid_votes['date'] >= mm['since']) & ((valid_votes['date'] <= mm['until']) | (mm['until'] in ['nan', np.nan])) & (valid_votes['mp_id'] == mp['mp_id']), ['org_id']] = mm['org_id']

  for ii, mm in membershipgov.iterrows():
    valid_votes.loc[(valid_votes['date'] >= mm['since']) & (valid_votes['date'] >= gov_since) & ((valid_votes['date'] <= mm['until']) | (mm['until'] in ['nan', np.nan])) & (valid_votes['mp_id'] == mp['mp_id']), ['in_gov']] = True

# add vote_values (active)
valid_votes['vote_value'] = pd.NA
valid_votes['vote_value_active'] = pd.NA
valid_votes['present'] = 0
valid_votes.loc[valid_votes['vote'].isin(['A']), ['vote_value','vote_value_active']] = 1
valid_votes.loc[valid_votes['vote'].isin(['B', 'N', 'K', 'C', 'F']), ['vote_value']] = -1
valid_votes.loc[valid_votes['vote'].isin(['B', 'N']), ['vote_value_active']] = -1
valid_votes.loc[valid_votes['vote'].isin(['@', 'W', 'M']), ['vote_value']] = 0
valid_votes.loc[valid_votes['vote'].isin(['@', 'W', 'M', 'K', 'F', 'C']), ['vote_value_active']] = 0
valid_votes.loc[valid_votes['vote'].isin(['A', 'N', 'K']), ['present']] = 1

# add group vote and merge back
pt = pd.pivot_table(valid_votes, index=['vote_event_id', 'org_id'], values=['vote_value'], aggfunc=np.sum).reset_index()
pt['group_way'] = np.sign(pt['vote_value'])
pt['group_way_abs'] = np.abs(np.sign(pt['vote_value']))

valid_votes = valid_votes.merge(pt.loc[:, ['vote_event_id', 'org_id', 'group_way', 'group_way_abs']], on=['vote_event_id', 'org_id'])

# add gov vote and merge back
ptg = pd.pivot_table(valid_votes, index=['vote_event_id', 'in_gov'], values=['vote_value'], dropna=False, fill_value=0, aggfunc=np.sum).reset_index()
ptgf = ptg[ptg['in_gov']]
ptgf['gov_way'] = np.sign(ptgf['vote_value'])
ptgf['gov_way_abs'] = np.abs(np.sign(ptgf['vote_value']))

valid_votes = valid_votes.merge(ptgf.loc[:, ['vote_event_id', 'gov_way', 'gov_way_abs']], on='vote_event_id')

# rebeling
# actively voting against their group
valid_votes['rebeling'] = 0
valid_votes.loc[valid_votes['vote_value_active'] * valid_votes['group_way'] == -1, ['rebeling']] = 1

rt = pd.pivot_table(valid_votes, index=['mp_id'], values=['rebeling', 'group_way_abs'], aggfunc=np.sum)
rt['rebelity'] = rt['rebeling'] / rt['group_way_abs']

# voting against government
valid_votes['against_gov'] = 0
valid_votes['possibly_against_gov'] = 0
valid_votes.loc[valid_votes['vote_value_active'] * valid_votes['gov_way'] == -1, ['against_gov']] = 1
valid_votes.loc[(valid_votes['present'] == 1) & (valid_votes['gov_way_abs'] == 1), ['possibly_against_gov']] = 1

gt = pd.pivot_table(valid_votes, index=['mp_id'], values=['against_gov', 'possibly_against_gov'], aggfunc=np.sum)
gt['govity'] = 1 - gt['against_gov'] / gt['possibly_against_gov']

# join with MPs rebelity
rebelity = mps[mps['in_parliament']].merge(rt, on=['mp_id'])

rebelity.sort_values(by=['last_group_abbreviation', 'rebelity'], ascending=[True, False], inplace=True)

# output v.1
rebelity['photo_url'] = "https://www.psp.cz/eknih/cdrom/" + str(current_hlasovani) + "ps/eknih/" + str(current_hlasovani) + "ps/poslanci/i" + rebelity["id"].astype(str) + ".jpg" 
rebelity['name'] = rebelity['given_name'] + " " + rebelity['family_name']

rebelity['rebel'] = round(10000 * rebelity['rebelity']) / 100

rebelity.rename(columns={'group_way_abs': 'possible'}, inplace=True)

output = rebelity.loc[:, ['id', 'name', 'rebeling', 'possible', 'rebel', 'last_group_abbreviation', 'region_name_cs', 'photo_url']]

output.to_csv(path + data_path + "rebelity.v1.csv", index=False)

# join with MPs govity
govity = mps[mps['in_parliament']].merge(gt, on=['mp_id'])

govity.sort_values(by=['last_group_abbreviation', 'govity'], ascending=[True, False], inplace=True)

# output v.1
govity['photo_url'] = "https://www.psp.cz/eknih/cdrom/" + str(current_hlasovani) + "ps/eknih/" + str(current_hlasovani) + "ps/poslanci/i" + govity["id"].astype(str) + ".jpg" 
govity['name'] = govity['given_name'] + " " + govity['family_name']

govity['gover'] = round(1000 * govity['govity']) / 10

govity.rename(columns={'possibly_against_gov': 'possible'}, inplace=True)
govity['with_gov'] = govity['possible'] - govity['against_gov']

output2 = govity.loc[:, ['id', 'name', 'with_gov', 'possible', 'gover', 'last_group_abbreviation', 'region_name_cs', 'photo_url']]

output2.to_csv(path + data_path + "govity.v1.csv", index=False)


