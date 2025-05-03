"""Get vote events and votes."""

# Note: there are missing data in the official records for votes, last date: 2024-07-12, last vote_event_id: 83598
# Note 2: depends on mps.csv from create_mp_list.py

from datetime import datetime
import numpy as np
import pandas as pd

import re
from requests_html import HTMLSession

path = './v2/'
source_path = "source/"
views_path = "views/"

current_hlasovani = 2021
first_vote_event = 77302
group_id = 173

# get existing data if available
try:
  vote_events = pd.read_csv(path + views_path + "vote_events.csv")
  votes = pd.read_csv(path + views_path + "votes.csv")
except:
  vote_events = pd.DataFrame()
  votes = pd.DataFrame()

mps = pd.read_csv(path + views_path + "mps.csv")

# repeat the process for each vote event
next = True
next_vote_event = first_vote_event

def parse_czech_date(date_str):
  # Remove non-breaking spaces and normalize regular spaces
  date_str = date_str.replace('\xa0', ' ').strip()
  
  # Czech month names mapping
  czech_months = {
    'ledna': '1',
    'února': '2',
    'března': '3',
    'dubna': '4',
    'května': '5',
    'června': '6',
    'července': '7',
    'srpna': '8',
    'září': '9',
    'října': '10',
    'listopadu': '11',
    'prosince': '12'
  }
  
  # Extract day, month, and year using regex
  match = re.match(r'(\d+)\.\s*(\w+)\s*(\d{4})', date_str)
  if not match:
    raise ValueError(f"Cannot parse date string: {date_str}")
    
  day, month_name, year = match.groups()
  month = czech_months.get(month_name.lower())
  if not month:
    raise ValueError(f"Unknown month name: {month_name}")
    
  return datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d')

def parse_vote_events(html, vote_event_id):
  # Extract date and time
  title = html.find('h1.page-title-x', first=True).text
  date_match = re.search(r'(\d+\.\s*\w+\s*\d{4}),\s*(\d+:\d+)', title)
  date_str = date_match.group(1)
  time_str = date_match.group(2)
  
  # Parse the Czech date
  date_obj = parse_czech_date(date_str)
  
  # Extract vote counts
  summary = html.find('div.summary', first=True)
  counts = summary.find('p.counts', first=True).text
  total_present = int(re.search(r'Přítomno:\s*(\d+)', counts).group(1))
  quorum = int(re.search(r'Je třeba:\s*(\d+)', counts).group(1))
  
  # Extract voting results
  results = summary.find('table', first=True).text
  yes_votes = int(re.search(r'Ano:\s*(\d+)', results).group(1))
  no_votes = int(re.search(r'Ne:\s*(\d+)', results).group(1))
  abstain_votes = int(re.search(r'Zdržel se:\s*(\d+)', results).group(1))
  excused_votes = int(re.search(r'Omluven:\s*(\d+)', results).group(1))
  not_logged_in = int(re.search(r'Nepřihlášen:\s*(\d+)', results).group(1))
  
  # Extract result
  result_text = summary.find('h2.section-title', first=True).text.strip()
  result = 'pass' if 'PŘIJAT' in result_text else 'fail'

  # Extract sitting number and vote event number
  
  vote_events_data = {
    'vote_event_id': [vote_event_id],
    'org_id': [group_id],
    'sitting': [1],
    'vote_event_number': [1],
    'date': [date_obj.strftime('%Y-%m-%d')],
    'time': [time_str],
    'start_date': [date_obj.strftime('%Y-%m-%d') + 'T' + time_str + ':00'],
    'yes': [yes_votes],
    'no': [no_votes],
    'abstain': [abstain_votes],
    'not_voting': [not_logged_in + excused_votes],
    'voted': [total_present],
    'quorum': [quorum],
    'vote_event_type': ['N'],  # Normal voting
    'result': [result],
    'name': [title.split('\n')[-1]],
    'short_name': [''],
    'invalid': [False],
    'repeated': [False]
  }
  
  return pd.DataFrame(vote_events_data)

def parse_votes(html, vote_id=77302):
  votes_data = []
  date = datetime.now().strftime('%Y-%m-%d')
  
  # Find all party sections excluding the summary table
  party_sections = [section for section in html.find('h2.section-title') 
                   if 'Tabulkovy vypis' not in section.text]
  
  for party_section in party_sections:
    party_name = re.search(r'(\w+)\s*\(', party_section.text)
    if not party_name:
      continue
      
    party_abbrev = party_name.group(1)
    
    # Find the list of MPs after this header
    mp_list = html.find(f'h2:contains("{party_abbrev}") + ul.results', first=True)
    if not mp_list:
      continue
      
    for mp in mp_list.find('li'):
      vote_flag = mp.find('span.flag', first=True)
      if not vote_flag:
        continue
        
      vote_classes = vote_flag.attrs.get('class', [])
      vote_type = next((c for c in vote_classes if c != 'flag'), '')
      
      option = {
        'yes': 'yes',
        'no': 'no',
        'refrained': 'abstain',
        'not-logged-in': 'not voting',
        'excused': 'absent'
      }.get(vote_type, 'not voting')
      
      mp_link = mp.find('a', first=True)
      if mp_link:
        mp_id = re.search(r'id=(\d+)', mp_link.attrs['href'])
        if mp_id:
          votes_data.append({
            'vote_event_id': vote_id,
            'mp_id': int(mp_id.group(1)),
            'option': option,
            'group_abbreviation': party_abbrev,
            'date': date
          })
  
  return pd.DataFrame(votes_data)

def main():
  vote_event_id = 77302
  
  # Read the HTML 
  url = 'https://www.psp.cz/sqw/hlasy.sqw?g=' + str(vote_event_id)
  session = HTMLSession()
  response = session.get(url)
  response.raise_for_status()
  
  # Force CP-1250 encoding
  response.encoding = 'cp1250'
  
  # Create HTML object with correct encoding
  html = response.html
  html.html = response.text
  
  # Generate the DataFrames
  vote_events_df = parse_vote_events(html, )
  votes_df = parse_votes(html)
  
  # Save to CSV files
  vote_events_df.to_csv('vote_events.csv', index=False)
  votes_df.to_csv('votes.csv', index=False)
  
  print("Files generated successfully!")
  
  # Close the session
  session.close()