"""Calculates rebelity and govity."""

# TODO: govity

import numpy as np
import pandas as pd

# path
path = "./v2/"
data_path = "data/"
views_path = "views/"

current_hlasovani = 2021
gov_since = '2021-12-17'

# read data
mps = pd.read_csv(path + views_path + "mps.csv")
votes = pd.read_csv(path + data_path + "votes.csv")
vote_events = pd.read_csv(path + data_path + "vote_events.csv")

# check 1: zmatečná hlasování
invalid1 = list(vote_events[vote_events['invalid']]['vote_event_id'].unique())

# check 2: zpochybnění
# note: we can use ...x or ...z, currently ...z is not available
# note: mode: "Typ zpochybnění: 0 - žádost o opakování hlasování - v tomto případě se o této žádosti neprodleně hlasuje a teprve je-li tato žádost přijata, je hlasování opakováno; 1 - pouze sdělení pro stenozáznam, není požadováno opakování hlasování.""
invalid2 = []

invalid = invalid1 + invalid2

# valid votes (not zpochynění)
valid_votes = votes[~votes['vote_event_id'].isin(invalid)]

# add vote_values (active)
valid_votes['vote_value'] = pd.NA
valid_votes['vote_value_active'] = pd.NA
valid_votes['present'] = 0
valid_votes.loc[valid_votes['option'].isin(['yes']), ['vote_value','vote_value_active']] = 1
valid_votes.loc[valid_votes['option'].isin(['no', 'abstain']), ['vote_value']] = -1
valid_votes.loc[valid_votes['option'].isin(['no']), ['vote_value_active']] = -1
valid_votes.loc[valid_votes['option'].isin(['absent', 'before oath']), ['vote_value']] = 0
valid_votes.loc[valid_votes['option'].isin(['abstain', 'absent', 'before oath']), ['vote_value_active']] = 0
valid_votes.loc[valid_votes['option'].isin(['yes', 'no', 'abstain']), ['present']] = 1

# add group vote and merge back
pt = pd.pivot_table(valid_votes, index=['vote_event_id', 'group_id'], values=['vote_value'], aggfunc='sum').reset_index()
pt['group_way'] = np.sign(pt['vote_value'])
pt['group_way_abs'] = np.abs(np.sign(pt['vote_value']))

valid_votes = valid_votes.merge(pt.loc[:, ['vote_event_id', 'group_id', 'group_way', 'group_way_abs']], on=['vote_event_id', 'group_id'])

# add gov vote and merge back
# ptg = pd.pivot_table(valid_votes, index=['vote_event_id', 'in_gov'], values=['vote_value'], dropna=False, fill_value=0, aggfunc=np.sum).reset_index()
# ptgf = ptg[ptg['in_gov']]
# ptgf['gov_way'] = np.sign(ptgf['vote_value'])
# ptgf['gov_way_abs'] = np.abs(np.sign(ptgf['vote_value']))

# valid_votes = valid_votes.merge(ptgf.loc[:, ['vote_event_id', 'gov_way', 'gov_way_abs']], on='vote_event_id')

# rebeling
# actively voting against their group
valid_votes['rebeling'] = 0
valid_votes.loc[valid_votes['vote_value_active'] * valid_votes['group_way'] == -1, ['rebeling']] = 1

rt = pd.pivot_table(valid_votes, index=['mp_id'], values=['rebeling', 'group_way_abs'], aggfunc='sum')
rt['rebelity'] = rt['rebeling'] / rt['group_way_abs']

# voting against government
# valid_votes['against_gov'] = 0
# valid_votes['possibly_against_gov'] = 0
# valid_votes.loc[valid_votes['vote_value_active'] * valid_votes['gov_way'] == -1, ['against_gov']] = 1
# valid_votes.loc[(valid_votes['present'] == 1) & (valid_votes['gov_way_abs'] == 1), ['possibly_against_gov']] = 1

# gt = pd.pivot_table(valid_votes, index=['mp_id'], values=['against_gov', 'possibly_against_gov'], aggfunc=np.sum)
# gt['govity'] = 1 - gt['against_gov'] / gt['possibly_against_gov']

# join with MPs rebelity
rebelity = mps[mps['current']].merge(rt, on=['mp_id'])

rebelity.sort_values(by=['last_group_abbreviation', 'rebelity'], ascending=[True, False], inplace=True)

# output v.1
rebelity['photo_url'] = "https://www.psp.cz/eknih/cdrom/" + str(current_hlasovani) + "ps/eknih/" + str(current_hlasovani) + "ps/poslanci/i" + rebelity["mp_id"].astype(str) + ".jpg" 
rebelity['name'] = rebelity['given_name'] + " " + rebelity['family_name']

rebelity['rebelity'] = rebelity['rebelity'].astype(float)
rebelity['rebel'] = round(10000 * rebelity['rebelity']) / 100

rebelity.rename(columns={'group_way_abs': 'possible'}, inplace=True)

output = rebelity.loc[:, ['mp_id', 'name', 'rebeling', 'possible', 'rebel', 'last_group_abbreviation', 'region_name_cs', 'photo_url']]

output.to_csv(path + views_path + "rebelity.v1.csv", index=False)

# # join with MPs govity
# govity = mps[mps['in_parliament']].merge(gt, on=['mp_id'])

# govity.sort_values(by=['last_group_abbreviation', 'govity'], ascending=[True, False], inplace=True)

# # output v.1
# govity['photo_url'] = "https://www.psp.cz/eknih/cdrom/" + str(current_hlasovani) + "ps/eknih/" + str(current_hlasovani) + "ps/poslanci/i" + govity["id"].astype(str) + ".jpg" 
# govity['name'] = govity['given_name'] + " " + govity['family_name']

# govity['gover'] = round(1000 * govity['govity']) / 10

# govity.rename(columns={'possibly_against_gov': 'possible'}, inplace=True)
# govity['with_gov'] = govity['possible'] - govity['against_gov']

# output2 = govity.loc[:, ['id', 'name', 'with_gov', 'possible', 'gover', 'last_group_abbreviation', 'region_name_cs', 'photo_url']]

# output2.to_csv(path + data_path + "govity.v1.csv", index=False)


