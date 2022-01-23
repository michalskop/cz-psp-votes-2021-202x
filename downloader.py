"""Download and extract data for analyses."""

import io
import requests
import zipfile

# path
path = "./"
data_path = "source/"


# url = "http://www.psp.cz/eknih/cdrom/opendata/hl-2021ps.zip"
# r = requests.get(url)
# if r.ok:
#     z = zipfile.ZipFile(io.BytesIO(r.content))
#     z.extractall(path + data_path)

url = "http://www.psp.cz/eknih/cdrom/opendata/poslanci.zip"
r = requests.get(url)
if r.ok:
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(path + data_path)

# url = "https://api.napistejim.cz/data_all.json"
# r = requests.get(url)
# if r.ok:
#     with open(path + data_path + "people.json", "w") as fout:
#         json.dump(r.json(), fout)
