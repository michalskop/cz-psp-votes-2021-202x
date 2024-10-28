"""MPs confusing votings for one year."""

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

year = 2024

current_hlasovani = 2021
first_vote_event = 77302

# download fresh data
url = "https://www.psp.cz/eknih/cdrom/opendata/hl-" + str(current_hlasovani) + "ps.zip"
r = requests.get(url, verify=True)
if r.ok:
  z = zipfile.ZipFile(io.BytesIO(r.content))
  z.extractall(path + source_path)

# zpochybnění
# note: mode: "Typ zpochybnění: 0 - žádost o opakování hlasování - v tomto případě se o této žádosti neprodleně hlasuje a teprve je-li tato žádost přijata, je hlasování opakováno; 1 - pouze sdělení pro stenozáznam, není požadováno opakování hlasování.""
confused = []
try: 
    # check = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "z.unl", sep="|", encoding="cp1250")
    # header = ['vote_event_id', 'turn', 'mode', 'id_h2', 'id_h3', 'dummy']
    check = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "x.unl", sep="|", encoding="cp1250")
    header = ['vote_event_id', 'mp_id', 'mode', 'dummy']
    check.columns = header
    confused = check[check['vote_event_id'] >= first_vote_event]
except:
    pass

# read vote events
vote_events = pd.read_csv(path + source_path + "hl" + str(current_hlasovani) + "s.unl", sep="|", encoding="cp1250")
header = ['vote_event_id', 'org_id', 'sitting', 'vote_event_number', 'bod', 'date', 'time', 'yes', 'no', 'abstain', 'not_voting', 'voted', 'quorum', 'vote_event_type', 'result', 'name', 'short_name', 'dummy']
vote_events.columns = header
vote_events['date'] = vote_events['date'].apply(lambda x: datetime.datetime.strptime(x, "%d.%m.%Y").strftime("%Y-%m-%d"))

# filter by year
mask = vote_events['date'].str.startswith(str(year))
confused = confused[confused['vote_event_id'].isin(vote_events[mask]['vote_event_id'])]

# counts
pt = pd.pivot_table(confused, index=['mp_id'], columns=['mode'], values=['vote_event_id'], fill_value=0, aggfunc=len).reset_index()

pt.columns = ['id', 'repeted', 'unrepeted']

pt['all'] = pt['repeted'] + pt['unrepeted']

# read mps from previously prepared file
mps = pd.read_csv(path + data_path + "mps.csv")

ptx = pt.merge(mps, on=['id'])

ptx.sort_values(by=['repeted', 'all', 'last_group_abbreviation'], ascending=[False, False, True], inplace=True)

ptx['name'] = ptx['given_name'] + " " + ptx['family_name']

out = ptx.loc[:, ['repeted', 'unrepeted', 'all', 'name', 'last_group_abbreviation']]
out.columns = ['Hlasování se opakovalo', 'Jen oznámeno pro záznam', 'Celkem', 'Poslanec/kyně', 'Klub']

out.to_csv(path + data_path + "confused.v1." + str(year) + ".csv", index=False)