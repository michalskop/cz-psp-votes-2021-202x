"""Scrape vote events from the Czech Parliament website and save them to a CSV file."""

import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

path = './v2/'

parliament_id = 173  # Constant for 2021-2025

def get_last_vote_event_id():
  # Read the vote_events CSV and get the maximum vote_event_id
  try:
    df = pd.read_csv(path + 'data/vote_events.csv')
    return df['vote_event_id'].max()
  except FileNotFoundError:
    return 0

GROUP_ABBREVIATIONS = {
  'Nezařaz': 1720,
  'Piráti': 1535,
  'STAN': 1536,
  'ANO': 1537,
  'ODS': 1538,
  'KDU-ČSL': 1539,
  'SPD': 1540,
  'TOP09': 1541
}

# Czech month names mapping (including declension forms used in dates)
CZECH_MONTHS = {
  'ledna': 1,
  'února': 2,
  'března': 3,
  'dubna': 4,
  'května': 5,
  'června': 6,
  'července': 7,
  'srpna': 8,
  'září': 9,
  'října': 10,
  'listopadu': 11,
  'prosince': 12
}

def parse_czech_date(date_str):
  try:
    # Split the date string into components
    day, month_name, year = date_str.strip().split()
    # Remove dot from day
    day = day.replace('.', '')
    # Convert month name to number
    month = CZECH_MONTHS[month_name.lower()]
    # Create date string in standard format
    standard_date = f"{year}-{month:02d}-{int(day):02d}"
    return standard_date
  except Exception as e:
    print(f"Error parsing date '{date_str}': {e}")
    return None

def parse_title_element(title_element):
  try:
    # Get text before <br> tag
    pre_br_text = ''
    for content in title_element.contents:
      if content.name == 'br':
        break
      pre_br_text += str(content)
    
    # Split the pre <br> text by commas
    parts = [p.strip() for p in pre_br_text.split(',')]
    
    # First part contains: "112. schůze, "
    sitting_number = int(parts[0].split('.')[0])
    
    # Second part contains vote number (inside <a> tag)
    vote_link = title_element.find('a')
    if vote_link:
      vote_text = vote_link.text if vote_link else ""
    else:
      vote_text = parts[1]
    vote_number = int(vote_text.split('.')[0])
    
    # Third and fourth parts contain date and time: "10. září 2024" "14:06:00"
    datetime_text = ', '.join(parts[2:]).strip()
    
    # Split date and time
    date_part = ' '.join(datetime_text.split()[:3]).strip(',')  # "10. září 2024"
    time_part = datetime_text.split()[-1]  # "14:06:00"
    
    # Parse date
    day = int(date_part.split('.')[0])
    month = CZECH_MONTHS[date_part.split()[1].lower()]
    year = int(date_part.split()[-1])
    date = f"{year}-{month:02d}-{day:02d}"
    
    # Get name (after <br>)
    br = title_element.find('br')
    name = br.next_sibling.strip() if br and br.next_sibling else ""
    
    return {
      'sitting': sitting_number,
      'vote_event_number': vote_number,
      'date': date,
      'time': time_part[0:5],  # Only HH:MM
      'name': name
    }
    
  except Exception as e:
    print(f"Error parsing title element: {e}")
    return None

def parse_votes(soup, date):
  votes = []
  
  # Find all sections with party votes
  party_sections = soup.find_all('h2', class_='section-title center')
  
  for section in party_sections[1:]:
    # Get party name
    party_name = section.find('span').text.strip()
    # Remove the vote counts in parentheses
    party_name = party_name.split('(')[0].strip()
    
    # Find the following list of votes
    vote_list = section.find_next('ul', class_='results')
    if not vote_list:
      continue
      
    # Process each vote
    for vote in vote_list.find_all('li'):
      # break
      try:
        # Get MP link which contains the ID
        mp_link = vote.find('a')
        voter_id = int(mp_link['href'].split('id=')[1].split('&')[0])
        
        # Get vote option
        vote_flag = vote.find('span', class_='flag')
        option = None
        if 'yes' in vote_flag['class']:
          option = 'yes'
        elif 'no' in vote_flag['class']:
          option = 'no'
        elif 'refrained' in vote_flag['class']:
          option = 'abstain'
        elif 'not-logged-in' in vote_flag['class']:
          option = 'absent'
        elif 'excused' in vote_flag['class']:
          option = 'absent'
          
        # group id
        group_id = GROUP_ABBREVIATIONS.get(party_name)
        
        if option in ['yes', 'no', 'abstain', 'absent']:
          votes.append({
            'mp_id': voter_id,
            'option': option,
            'date': date,
            'group_id': group_id,
            'group_abbreviation': party_name
          })
          
      except Exception as e:
        print(f"Error parsing individual vote: {e}")
        continue
        
  return votes

def parse_vote_page(html_content):
  # Decode content with correct encoding
  html_text = html_content.decode('windows-1250')
  soup = BeautifulSoup(html_text, 'html.parser')
  
  # Extract basic information
  try:
    invalid_status = soup.find('p', class_='status invalid')
    is_invalid = bool(invalid_status and 'zmatečné' in invalid_status.text)
    
    # Get the title which contains date and time
    title_element = soup.find('h1', class_='page-title-x')
    parsed_data = parse_title_element(title_element)
    
    # Get voting results
    summary = soup.find('div', class_='summary')
    
    # Get quorum
    quorum_text = summary.find('p', class_='counts').text
    quorum = int(quorum_text.split('Je třeba: ')[1].strip())
    voted = int(quorum_text.split('|')[0].split('Přítomno: ')[1].split(',')[0].strip())
    
    # Get voting counts
    results = {}
    for td in summary.find('table').find_all('td'):
      text = td.text.strip()
      if 'Ano:' in text:
        results['yes'] = int(td.find('strong').text)
      elif 'Ne:' in text:
        results['no'] = int(td.find('strong').text)
      elif 'Zdržel se:' in text:
        results['abstain'] = int(td.find('strong').text)
      elif 'Nepřihlášen:' in text:
        not_voting = int(td.find('strong').text)
      elif 'Omluven:' in text:
        excused = int(td.find('strong').text)
    results['not_voting'] = not_voting + excused
    
    # Get result text
    result = soup.find('h2', class_='section-title center').find('span').text.strip()
    result = 'A' if 'NÁVRH BYL PŘIJAT' in result else 'R'
    
    # Return parsed data
    date = parsed_data['date']
    time = parsed_data['time']
    name = parsed_data['name']
    sitting = parsed_data['sitting']
    vote_event_number = parsed_data['vote_event_number']
    return {
      'vote_event': {
        'date': date,
        'time': time,
        'name': name,
        'sitting': sitting,
        'vote_event_number': vote_event_number,
        'yes': results['yes'],
        'no': results['no'],
        'abstain': results['abstain'],
        'not_voting': results['not_voting'],
        'voted': voted,
        'quorum': quorum,
        'result': result,
        'invalid': is_invalid,
        'repeted': None  # TODO - probably the same as invalid + wrong name in original
      },
      'votes': parse_votes(soup, date)
    }
    
  except Exception as e:
    print(f"Error parsing page: {e}")
    return None

def main():
  # Get the last vote event ID
  last_id = get_last_vote_event_id()
  next_id = last_id + 1
  
  # stop if counter = 10
  counter = 0
  
  while counter < 10:
    # Try to download the next vote
    url = f"https://www.psp.cz/sqw/hlasy.sqw?g={next_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
      
      # if the html contains text 'Hlasovani nebylo nalezeno.' add counter
      if 'Hlasovani nebylo nalezeno.' in response.content.decode('windows-1250'):
        counter += 1
        print("Not found {next_id}. Counter {counter}")
        continue
      
      vote_data = parse_vote_page(response.content)
      
      if vote_data:
        vote_event_data = vote_data['vote_event']
        # Calculate type of vote event
        # It is not always possible to determine the type of vote event from the values
        if vote_event_data['quorum'] < 101:
          vote_event_data['vote_event_type'] = 'N'
        else:
          vote_event_data['vote_event_type'] = None # we don't know the type
        # Create new row for vote_events.csv
        vote_event = {
          'vote_event_id': next_id,
          'org_id': parliament_id,
          'sitting': None,  # Would need additional parsing
          'vote_event_number': None,  # Would need additional parsing
          'bod': None,  # Would need additional parsing
          'short_name': None,
          **vote_event_data
        }
        print(vote_event)
        
        # # Append to CSV
        # save in correct order:
        # vote_event_id,org_id,sitting,vote_event_number,bod,date,time,yes,no,abstain,not_voting,voted,quorum,vote_event_type,result,name,short_name,invalid,repeted
        try:
          columns = [
            'vote_event_id', 'org_id', 'sitting', 'vote_event_number', 'bod', 
            'date', 'time', 'yes', 'no', 'abstain', 'not_voting', 'voted', 
            'quorum', 'vote_event_type', 'result', 'name', 'short_name', 
            'invalid', 'repeted'
          ]
          df = pd.DataFrame([vote_event])
          df = df[columns]
          df.to_csv(path + 'data/vote_events.csv', mode='a', header=False, index=False)
          print(f"Successfully scraped vote event {next_id}")
        except Exception as e:
          print(f"Error saving vote event: {e}")
      
        # save votes
        try:
          columns = [
            'voter_id', 'vote_event_id', 'option', 'date', 
            'group_id', 'group_abbreviation'
          ]
          votes_data = vote_data['votes']
          df = pd.DataFrame(votes_data)
          df['vote_event_id'] = next_id
          df = df[columns]
          df.to_csv(path + 'data/votes.csv', mode='a', header=False, index=False)
          print(f"Successfully saved {len(votes_data)} votes")
        except Exception as e:
          print(f"Error saving votes: {e}")
        
        counter = 0
        next_id += 1
      
      
    else:
      print(f"Failed to download page for vote event {next_id}, counter {counter}")
      counter += 1

if __name__ == "__main__":
  main()