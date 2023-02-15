# Analyses of votes in Lower Chamber in Czech Parliament 2021-202x

## Articles
https://www.seznamzpravy.cz/clanek/fakta-poslanecka-snemovna-hlasovani-dochazka-poslancu-219329

## Former articles
### Presence
https://www.seznamzpravy.cz/clanek/fakta-jak-poslanci-v-dobe-omezeni-dochazeji-do-snemovny-143664

### WPCA
https://www.seznamzpravy.cz/clanek/kdo-s-kym-hlasoval-ve-snemovne-aneb-stranicka-disciplina-nebo-jine-ambice-176641

## Manual update
```bash
# cd to project directory
git pull
conda activate base # possibly activate base environment
pip3 install -r requirements.txt
python3 create_mp_list.py
python3 attendance.py
python3 rebelity.py
python3 confused.py
git add -A
timestamp=$(date +%FT%T%Z)
git commit -m "Manual update ${timestamp}"
```
