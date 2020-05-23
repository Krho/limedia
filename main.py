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

rootURL = 'https://galeries.limedia.fr'
csvFile = open('metadata.csv', 'wb')
errorsFile = open('errors.log', 'wb')
fields = [u'imageName', u'title', u'imageURL', u'author', u'date', u'technique', u'inventaire', u'dimensions',
 u'object_type', u'topic', u'category', u'institution', u'description', u'notes']
writer = csv.DictWriter(csvFile, fieldnames=fields, encoding='utf-8')
blackList = [u'/ark:/18128/dxvm8l0jlxf4hqs0/', u'/ark:/18128/dwpb3g26mmbdlgsk/', u'/ark:/31124/dlt9kgkmrvf7h0nf/', u'/ark:/18128/dbwv3060c97k8089/',
 u'/ark:/18128/dwtbg2mrsf8l2wd1/', u'/ark:/18128/dtk50r3l6prj61q9/', u"/ark:/18128/d65tz4vjprp1vrpv/"]

optionalFields = ['notes', 'dimensions']

def image_URL(soup):
    script = soup.findAll('script')[2].string
    pattern = re.compile("https:\/\/[\w|.|\/|-]+")
    imageUrl = pattern.findall(script)[0]
    return unicode(imageUrl)

def updateInstitution(metadata, institution):
    if(institution == u"bmi Epinal"):
        metadata['institution'] = u"Bibliothèque multimédia intercommunale d'Épinal"
        metadata['category'] = u"Collections of the Bibliothèque multimédia intercommunale d'Épinal"
    elif(institution == u"Bibliothèques de Nancy"):
        metadata['institution'] = u"Bibliothèque municipale de Nancy"
        metadata['category']= u"Collections of the Bibliothèque municipale de Nancy"
    elif(institution == u"Médiathèque intercommunale de Saint-Dié-des-Vosges"):
        metadata['institution'] = u"Médiathèque intercommunale de Saint-Dié-des-Vosges‎ "
        metadata['category']= u"Collections of the médiathèque intercommunale de Saint-Dié-des-Vosges‎ "
    elif(institution == u"Bibliothèques Médiathèques de Metz"):
        metadata['institution'] = u""
        metadata['category']= u"Collections of the Bibliothèques-Médiathèques de Metz"
    elif(institution == u"Musée de l'École de Nancy"):
        metadata['institution'] = u"Musée de l'École de Nancy"
        metadata['category']= u"Collections of the Musée de l'École de Nancy"
    elif(institution == u"Médiathèque Puzzle"):
        metadata['institution'] = u"Médiathèque Puzzle de Thionville"
        metadata['category']= u"Collections of the médiathèque Puzzle de Thionville"
    elif(institution == u"Archives municipales de Nancy"):
        metadata['institution'] = u"Archives municipales de Nancy"
        metadata['category']= u"Collections of the archives municipales de Nancy"
    return metadata

def retrieveTopics(source):
    topics = []
    for i in range((len(source.next_sibling.next_sibling.contents)-1)/4):
        topic = source.next_sibling.next_sibling.contents[4*i+1]
        topics.append(unicode(topic.contents[1].contents[0][26:].split("\n")[0]))
    return topics

def basicData(source):
    return unicode(source.next_sibling.next_sibling.contents[1].contents[0])

def linkedData(source):
    return unicode(source.next_sibling.next_sibling.contents[1].contents[1].contents[0])

def retrieveData(source, output):
    dataTitle = source.contents[0]
    if (u'Titre' in dataTitle):
        output["title"]=basicData(source)
    elif(u"Date" in dataTitle):
        output["date"]=basicData(source)
    elif(u"Auteur" in dataTitle):
        output['author']=linkedData(source)
    elif(u"Formats" in dataTitle):
        formats = basicData(source).split(";")
        output['technique']=unicode(formats[0])
        if (len(formats) > 1):
            output['dimensions']=unicode(formats[1][1:])
    elif(u"Source" in dataTitle):
        institution = basicData(source).split(',')
        updateInstitution(output, institution[0])
        output['inventaire']=unicode(institution[1][1:])
    elif(u"Description" in dataTitle):
        output['description']=basicData(source)
    elif(u"Typologies" in dataTitle):
         output['object_type']=basicData(source)
    elif(u"Technique" in dataTitle):
        output["title"] == linkedData(source)
    elif(u"Sujets" in dataTitle):
        output['topic'] = retrieveTopics(source)
    elif(u"Editeur" in dataTitle):
        output['notes']=linkedData(source)

def metadata(soup):
    metadata = {}
    data = soup.findAll(class_="viewer-block viewer-meta")[0]
    for source in data.findAll("h3"):
        retrieveData(source, metadata)
    metadata['imageName'] = unicode(metadata['title'][:100].replace("[","").replace("]","").replace("/","sur")+" "+metadata['inventaire'].replace("/","")+".jpg")
    metadata['imageURL'] = image_URL(soup)
    writer.writeheader()
    writer.writerow(metadata)
    return metadata

def outputLines(metadata, url):
    lines = [
        u"== {{int:filedesc}}==\n",
        u"{{Artwork\n",
        u"|title=",metadata['title'],u"\n",
        u"|object_type=",metadata['object_type'],u"\n",
        u"|source=",url,u"\n",
        u"|institution={{Institution:",metadata['institution'],"}}\n",
        u"|id=",metadata['inventaire'],u"\n",
        u"|date=",metadata['date'],u"\n",
        u"|technique=",metadata['technique'],u"\n",
        u"|description={{fr|",metadata['description'],u"}}\n"]
    for key in optionalFields:
        if (key in metadata):
            lines.append(u"|"+key+"={{fr|"+metadata[key]+u"}}\n")
        else:
            metadata[key]="no value"
    lines.extend([u"}}\n\n",
        u"=={{int:license-header}}==\n",
        u"{{PD-old}}\n\n",
        u"[[Category:",metadata['category'],"]]\n",
        u"[[Category:Jeanne d'Arc]]\n",
        u"[[Category:Limédia galeries]]"])
    return lines

def upload(url, soup, metadata):
    imageRequest = requests.get(metadata['imageURL'])
    image = imageRequest.content
    # Save file
    open(metadata['imageName'], 'wb').write(imageRequest.content)
    # Upload to commons
    commons = mwclient.Site('commons.wikimedia.org')
    commons.login(username=botconfig.USER, password=botconfig.PASS)
    lines = outputLines(metadata, url)
    text = u"".join(lines).encode('utf-8')
    print('Uploading '+metadata['imageName'])
    try:
        commons.upload(open(metadata['imageName'], 'rb'), u'File:{}'.format(metadata['imageName']), description=text, ignore=True)
    except Exception as error:
        errorsFile.write(u"".join(["\n",metadata['imageName']," - ",url]).encode('utf-8'))
        print(type(error))
    os.remove(metadata['imageName'])

def documentsFromSubject(subject):
    subjectURL = 'https://galeries.limedia.fr/recherche/?subjects='+subject
    pageURL = subjectURL+'&page='
    r = requests.get(subjectURL, allow_redirects=True)
    pageSoup = BeautifulSoup(r.content, features="lxml")
    nb_pages = int(pageSoup.find_all("li", "num-page")[2].contents[0].contents[0])
    for i in range(nb_pages-3):
        url = pageURL+str(i+3)
        print(url)
        pageRequest = requests.get(url, allow_redirects=True)
        soup = BeautifulSoup(pageRequest.content, features="lxml")
        documentLinks = soup.findAll("a", "titre")
        for documentLink in documentLinks:
            key = documentLink['href']
            if key not in blackList:
                documentURL = rootURL+key
                documentRequest = requests.get(documentURL, allow_redirects=True)
                documentSoup = BeautifulSoup(documentRequest.content, features="lxml")
                data = metadata(documentSoup)
                upload(documentURL, documentSoup, data)

def main():
    subject = 'Jeanne%20d%27Arc%20(sainte%20;%201412-1431)'
    documentsFromSubject(subject)

main()