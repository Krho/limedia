# -*- coding: utf-8 -*-
import re
import os
import mwclient
import requests
import posixpath
from bs4 import BeautifulSoup

import botconfig

def metadata(soup):
    metadata = {}
    data = soup.findAll(class_="viewer-block viewer-meta")[0].find_all("span")
    metadata['title'] = unicode(data[0].contents[0])
    metadata['date'] = unicode(data[1].contents[0])
    metadata['editeur'] = unicode(data[2].find_all("a")[0].contents[0])
    source = data[5].contents[0].split(',')
    metadata['inventaire'] = unicode(source[1][1:])
    metadata['description'] = unicode(data[7].contents[0])
    if(source[0] == "bmi Epinal"):
        metadata['institution'] = u"Bibliothèque multimédia intercommunale d'Épinal"
        metadata['category'] = u"Collections of the Bibliothèque multimédia intercommunale d'Épinal"
    return metadata

def upload(url, soup, metadata):
    # Find and download image
    script = unicode(soup.findAll('script')[2].string)
    pattern = re.compile("https:\/\/[\w|.|\/]+")
    imageUrl = pattern.findall(script)[0]
    imageRequest = requests.get(imageUrl)
    imageName = metadata['title'].replace("[","").replace("]","")+" "+metadata['inventaire'].replace("/","")+".jpg"
    image = imageRequest.content
    # Save file
    open(imageName, 'wb').write(imageRequest.content)
    # Upload to commons
    commons = mwclient.Site('commons.wikimedia.org')
    commons.login(username=botconfig.USER, password=botconfig.PASS)
    text = u"".join([
        u"== {{int:filedesc}}==\n",
        u"{{Artwork",
        u"|title=",metadata['title'],
        u"|source=",url,
        u"|institution={{Institution:",metadata['institution']+"}}",
        u"|id=",metadata['inventaire'],
        u"|date=",metadata['date'],
        u"|description={{fr|",metadata['description'],u"}}",
        u"}}\n",
        u"=={{int:license-header}}==\n",
        "{{PD-old}}",
        u"[[Category:",metadata['category'],"]]",
        u"[[Category:Limédia galeries]]"]).encode('utf-8')
    print('Upload '+imageName)
    commons.upload(open(imageName, 'rb'), u'File:{}'.format(imageName), description=text, ignore=True)
    os.remove(imageName)

def main():
    key = 'dbwv3060c97k8089/'
    url = 'https://galeries.limedia.fr/ark:/18128/'+key
    r = requests.get(url, allow_redirects=True)
    soup = BeautifulSoup(r.content, features="lxml")
    data=metadata(soup)
    upload(url, soup, data)

main()