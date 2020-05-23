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

errorsFile = open('errors.log', 'wb')

optionalFields = ['notes', 'dimensions']

fields = [u'imageName', u'title', u'imageURL', u'author', u'date', u'technique', u'inventaire', u'dimensions',
 u'object_type', u'topic', u'category', u'institution', u'description', u'notes']
csvFileName = 'metadata.csv'
blackList = [row['imageURL'] for row in csv.DictReader(open(csvFileName, 'rb'))]
csvFile = open(csvFileName, 'wb')
writer = csv.DictWriter(csvFile, fieldnames=fields, encoding='utf-8')

categoryRoot = u"Limédia galeries - "
limediaCategory = u"[[Category:Limédia galeries]]"

commons = mwclient.Site('commons.wikimedia.org')
commons.login(username=botconfig.USER, password=botconfig.PASS)
    

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
        u"[[Category:",metadata['category'],"]]\n"])
    lines.extend(categories(metadata['topic']))
    return lines

def categories(topics):
    categories = [limediaCategory]
    for topic in topics:
        categoryName = categoryRoot+topic
        categoryPage = commons.pages["Category:"+categoryName]
        if len(categoryPage.text()) == 0:
            print(categoryPage.name)
            categoryPage.save(limediaCategory, summary="#LimediaGallery creating temporary category")
            categories.append(u"[[Category:"+categoryName+u"]]\n")
    return categories


def upload(url, soup, metadata):
    if (u"manuscrit" not in metadata['object_type']):
        print('Uploading '+metadata['imageName'])
        imageRequest = requests.get(metadata['imageURL'])
        image = imageRequest.content
        # Save file
        open(metadata['imageName'], 'wb').write(imageRequest.content)
        # Upload to commons
        lines = outputLines(metadata, url)
        text = u"".join(lines).encode('utf-8')
        try:
            commons.upload(open(metadata['imageName'], 'rb'), u'File:{}'.format(metadata['imageName']), description=text, ignore=True)
        except Exception as error:
            errorsFile.write(u"".join(["\n",metadata['imageName']," - ",url]).encode('utf-8'))
            print(type(error))
        os.remove(metadata['imageName'])

def uploadDocuments(search_param):
    pageURL = 'https://galeries.limedia.fr/recherche/?'+search_param+'&page='
    r = requests.get(pageURL, allow_redirects=True)
    pageSoup = BeautifulSoup(r.content, features="lxml")
    num_page = pageSoup.find_all("li", "num-page")
    nb_pages = int(num_page[2].contents[0].contents[0]) if len(num_page) > 0 else 1
    for i in range(nb_pages):
        url = pageURL+str(i+1)
        print(url)
        pageRequest = requests.get(url, allow_redirects=True)
        soup = BeautifulSoup(pageRequest.content, features="lxml")
        documentLinks = soup.findAll("a", "titre")
        for documentLink in documentLinks:
            documentURL = rootURL+documentLink['href']
            documentRequest = requests.get(documentURL, allow_redirects=True)
            documentSoup = BeautifulSoup(documentRequest.content, features="lxml")
            data = metadata(documentSoup)
            #if data['imageURL'] not in blackList:
            upload(documentURL, documentSoup, data)

def main():
    prefixes = [u"subjects=", u"filter_location="]
    # subject = 'Jeanne%20d%27Arc%20(sainte%20;%201412-1431)'
    location = u"ludres (meurthe-et-moselle)"
    search_param = prefixes[1]+location
    uploadDocuments(search_param)

main()