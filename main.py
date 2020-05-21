import re
import requests
from bs4 import BeautifulSoup

key = '18128/dtk50r3l6prj61q9/'
url = 'https://galeries.limedia.fr/ark:/'+key
r = requests.get(url, allow_redirects=True)
soup = BeautifulSoup(r.content, features="lxml")
# Find metadata
data = soup.findAll(class_="viewer-block viewer-meta")[0].find_all("span")
title = unicode(data[0].contents[0])
date = unicode(data[1].contents[0])
editeur = unicode(data[2].find_all("a")[0].contents[0])
source = data[5].contents[0].split(',')
institution = source[0]
inventaire = source[1][1:]
description = unicode(data[7].contents[0])
print(description)
# Find and download image
script = unicode(soup.findAll('script')[2].string)
pattern = re.compile("https:\/\/[\w|.|\/]+")
imageUrl = pattern.findall(script)[0]
imageRequest = requests.get(imageUrl)
imageName = title+".jpg"
print(imageName)
#open(imageName, 'wb').write(imageRequest.content)

# <img crossorigin="anonymous" src="https://rgw.atolcd.com/swift/v1/sillon_container_prod/entrepot/B881606401_cp_000005509_h.jpg?t=1590069678110" id="viewer-image-cache">