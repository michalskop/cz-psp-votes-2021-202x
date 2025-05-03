"""Voting attendance."""

import pandas as pd

# path
path = "./v2/"
data_path = "data/"
views_path = "views/"

current_hlasovani = 2021

# read data
mps = pd.read_csv(path + views_path + "mps.csv")
votes = pd.read_csv(path + data_path + "votes.csv")
vote_events = pd.read_csv(path + data_path + "vote_events.csv")

# check 1: zmatečná hlasování
invalid1 = list(vote_events[vote_events['invalid']]['vote_event_id'].unique())

# check 2: zpochybnění
# note: we count also these to attendances
# note: mode: "Typ zpochybnění: 0 - žádost o opakování hlasování - v tomto případě se o této žádosti neprodleně hlasuje a teprve je-li tato žádost přijata, je hlasování opakováno; 1 - pouze sdělení pro stenozáznam, není požadováno opakování hlasování.""
invalid2 = []
# try: 
#     check = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "z.unl", sep="|", encoding="cp1250")
#     header = ['vote_event_id', 'turn', 'mode', 'id_h2', 'id_h3', 'dummy']
#     check.columns = header
#     invalid2 = check[check['mode'] == 0]['vote_event_id'].unique()
# except:
#     pass

invalid = invalid1 + invalid2

# valid votes (not zmatečná)
valid_votes = votes[~votes['vote_event_id'].isin(invalid)]

# overall attendance
attendance = pd.pivot_table(valid_votes, index=['mp_id'], columns=['option'], values=['vote_event_id'], aggfunc='count', fill_value=0)

attendance['attendance'] = attendance['vote_event_id']['yes'] + attendance['vote_event_id']['no'] + attendance['vote_event_id']['abstain']
attendance['possible'] = attendance['vote_event_id']['yes'] + attendance['vote_event_id']['no'] + attendance['vote_event_id']['abstain'] + attendance['vote_event_id']['absent']
attendance['rate'] = attendance['attendance'] / attendance['possible']

attendance.columns = attendance.columns.get_level_values(0) + '_' +  attendance.columns.get_level_values(1)
attendance.columns = [c.strip('_') for c in attendance.columns]

# merge with mps
attendance = attendance.reset_index()
attendance = attendance.merge(mps, on='mp_id')

# only current mps
attendance = attendance[attendance['current']]

# photo + name
attendance['photo_url'] = "https://www.psp.cz/eknih/cdrom/" + str(current_hlasovani) + "ps/eknih/" + str(current_hlasovani) + "ps/poslanci/i" + attendance["mp_id"].astype(str) + ".jpg" 
attendance['name'] = attendance['given_name'] + " " + attendance['family_name']

# output v.1
output = attendance.loc[:, ['mp_id', 'name', 'attendance', 'possible', 'rate', 'last_group_abbreviation', 'region_name_cs', 'photo_url']]

output['účast'] = (output['rate'] * 100).round(0).astype(int)
del output['rate']

# output.rename(columns={'last_group_abbreviation': 'klub'}, inplace=True)

output.sort_values(by=['last_group_abbreviation'], inplace=True)

output.to_csv(path + views_path + "attendance.v1.csv", index=False)
