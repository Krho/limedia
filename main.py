# -*- coding: utf-8 -*-
import re
import os
import logging
import mwclient
import requests
import posixpath
from bs4 import BeautifulSoup

import botconfig

LOG =  logging.getLogger(name=__name__)

key = '18128/dxvm8l0jlxf4hqs0/'
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
# Find and download image
script = unicode(soup.findAll('script')[2].string)
pattern = re.compile("https:\/\/[\w|.|\/]+")
imageUrl = pattern.findall(script)[0]
imageRequest = requests.get(imageUrl)
imageName = title.replace("[","").replace("]","")+" "+inventaire.replace("/","")+".jpg"
image = imageRequest.content
# Save file
open(imageName, 'wb').write(imageRequest.content)
# Upload to commons
commons = mwclient.Site('commons.wikimedia.org')
commons.login(username=botconfig.USER, password=botconfig.PASS)
text = u"\n".join([
    u"== {{int:filedesc}}==",
    u"{{Artwork",
    u"|title=",title,
    u"|source=",url,
    u"|institution={{Institution:Bibliothèque multimédia intercommunale d'Épinal}}",
    u"|id="+inventaire,
    u"|date="+date,
    u"|description={{fr|",description,u"}}",
    u"}}",
    u"=={{int:license-header}}==",
    "{{PD-old}}",
    u"[[Category:Collections of the Bibliothèque multimédia intercommunale d'Épinal]]",
    u"[[Category:Limédia galeries]]"]).encode('utf-8')
print('Upload '+imageName)
commons.upload(open(imageName, 'rb'), u'File:{}'.format(imageName), description=text, ignore=True)
os.remove(imageName)
print("Done !")

# <img crossorigin="anonymous" src="https://rgw.atolcd.com/swift/v1/sillon_container_prod/entrepot/B881606401_cp_000005509_h.jpg?t=1590069678110" id="viewer-image-cache">