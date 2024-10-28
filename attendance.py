"""Voting attendance."""

# Note: depends on mps.csv from create_mp_list.py
# https://www.psp.cz/sqw/hp.sqw?k=1302

import datetime
import io
# from itertools import count
# import numpy as np
import pandas as pd

import requests
import zipfile

# path
path = "./"
source_path = "source/"
data_path = "data/"

current_hlasovani = 2021

# download fresh data
url = "https://www.psp.cz/eknih/cdrom/opendata/hl-" + str(current_hlasovani) + "ps.zip"
r = requests.get(url, verify=True)
if r.ok:
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(path + source_path)

# read data
mps = pd.read_csv(path + data_path + "mps.csv")

votes = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "h1.unl", sep="|", encoding="cp1250", header=None)
header = ["psp_id", "mp_id", "vote_event_id", "vote", "dummy"]
votes.columns = header

vote_events = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "s.unl", sep="|", encoding="cp1250", header=None)
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
attendance = pd.pivot_table(valid_votes, index=['mp_id'], columns=['vote'], values=['vote_event_id'], aggfunc='count', fill_value=0)

attendance['attendance'] = attendance['vote_event_id']['A'] + attendance['vote_event_id']['B'] + attendance['vote_event_id']['K']
attendance['possible'] = attendance['vote_event_id']['A'] + attendance['vote_event_id']['B'] + attendance['vote_event_id']['K'] + attendance['vote_event_id']['@']
attendance['rate'] = attendance['attendance'] / attendance['possible']

attendance.columns = attendance.columns.get_level_values(0) + '_' +  attendance.columns.get_level_values(1)
attendance.columns = [c.strip('_') for c in attendance.columns]

# merge with mps
attendance = attendance.reset_index()
attendance = attendance.merge(mps, on='mp_id')

# only current mps
attendance = attendance[attendance['in_parliament']]

# photo + name
attendance['photo_url'] = "https://www.psp.cz/eknih/cdrom/" + str(current_hlasovani) + "ps/eknih/" + str(current_hlasovani) + "ps/poslanci/i" + attendance["id"].astype(str) + ".jpg" 
attendance['name'] = attendance['given_name'] + " " + attendance['family_name']

# output v.1
output = attendance.loc[:, ['id', 'name', 'attendance', 'possible', 'rate', 'last_group_abbreviation', 'region_name_cs', 'photo_url']]

output['účast'] = (output['rate'] * 100).round(0).astype(int)
del output['rate']

# output.rename(columns={'last_group_abbreviation': 'klub'}, inplace=True)

output.sort_values(by=['last_group_abbreviation'], inplace=True)

output.to_csv(path + data_path + "attendance.v1.csv", index=False)
