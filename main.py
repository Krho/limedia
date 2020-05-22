# -*- coding: utf-8 -*-
import re
import os
import csv
import mwclient
import requests
import posixpath
import unicodecsv as csv
from bs4 import BeautifulSoup

import botconfig

csvFile = open('metadata.csv', 'wb')
fields = [u'imageName', u'title', u'imageURL', u'author', u'date', u'technique', u'inventaire', u'dimension', u'object_type', u'topic', u'category', u'institution', u'description']
writer = csv.DictWriter(csvFile, fieldnames=fields, encoding='utf-8')

def image_URL(soup):
    script = soup.findAll('script')[2].string
    pattern = re.compile("https:\/\/[\w|.|\/|-]+")
    imageUrl = pattern.findall(script)[0]
    return unicode(imageUrl)

def metadata(soup):
    metadata = {}
    data = soup.findAll(class_="viewer-block viewer-meta")[0]
    dataTitles = data.findAll("h3")
    metadata['title']=unicode(dataTitles[0].next_sibling.next_sibling.contents[1].contents[0])
    metadata['author']=unicode(dataTitles[1].next_sibling.next_sibling.contents[1].contents[1].contents[0])
    metadata['date']=unicode(dataTitles[2].next_sibling.next_sibling.contents[1].contents[0])
    formats = dataTitles[3].next_sibling.next_sibling.contents[1].contents[0].split(" ;")
    metadata['technique']=unicode(formats[0])
    metadata['dimension']=unicode(formats[1][1:])
    source = dataTitles[4].next_sibling.next_sibling.contents[1].contents[0].split(',')
    if(source[0] == u"bmi Epinal"):
        metadata['institution'] = u"Bibliothèque multimédia intercommunale d'Épinal"
        metadata['category'] = u"Collections of the Bibliothèque multimédia intercommunale d'Épinal"
    if(source[0] == u"Bibliothèques de Nancy"):
        metadata['institution'] = u"Bibliothèque municipale de Nancy"
        metadata['category']= u"Collections of the Bibliothèque municipale de Nancy"
    metadata['inventaire']=unicode(source[1][1:])
    metadata['description']=unicode(dataTitles[6].next_sibling.next_sibling.contents[1].contents[0])
    metadata['object_type']=unicode(dataTitles[7].next_sibling.next_sibling.contents[1].contents[0])
    metadata['topic']=[]
    for i in range((len(dataTitles[9].next_sibling.next_sibling.contents)-1)/4):
        topic = dataTitles[9].next_sibling.next_sibling.contents[4*i+1]
        metadata['topic'].append(unicode(topic.contents[1].contents[0][26:].split("\n")[0]))
    metadata['imageName'] = unicode(metadata['title'].replace("[","").replace("]","")+" "+metadata['inventaire'].replace("/","")+".jpg")
    metadata['imageURL'] = image_URL(soup)
    writer.writeheader()
    writer.writerow(metadata)
    return metadata

def upload(url, soup, metadata):
    imageRequest = requests.get(metadata['imageURL'])
    image = imageRequest.content
    # Save file
    open(metadata['imageName'], 'wb').write(imageRequest.content)
    # Upload to commons
    commons = mwclient.Site('commons.wikimedia.org')
    commons.login(username=botconfig.USER, password=botconfig.PASS)
    text = u"".join([
        u"== {{int:filedesc}}==\n",
        u"{{Artwork\n",
        u"|title=",metadata['title'],u"\n",
        u"|object_type",metadata['object_type'],u"\n",
        u"|source=",url,u"\n",
        u"|institution={{Institution:",metadata['institution'],"}}\n",
        u"|id=",metadata['inventaire'],u"\n",
        u"|date=",metadata['date'],u"\n",
        u"|technique=",metadata['technique'],u"\n",
        u"|dimensions=",metadata['dimension'],u"\n",
        u"|description={{fr|",metadata['description'],u"}}\n",
    #    u"|notes={{fr|",metadata["note"],u"}}\n",
        u"}}\n\n",
        u"=={{int:license-header}}==\n",
        "{{PD-old}}\n\n",
        u"[[Category:",metadata['category'],"]]\n",
        u"[[Category:Limédia galeries]]"]).encode('utf-8')
    print('Uploading '+metadata['imageName'])
    commons.upload(open(metadata['imageName'], 'rb'), u'File:{}'.format(metadata['imageName']), description=text, ignore=True)
    os.remove(metadata['imageName'])

def main():
    key = '31124/dlt9kgkmrvf7h0nf'
    url = 'https://galeries.limedia.fr/ark:/'+key
    r = requests.get(url, allow_redirects=True)
    soup = BeautifulSoup(r.content, features="lxml")
    data=metadata(soup)
    upload(url, soup, data)

main()