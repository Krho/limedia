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

optionalFields = [u'notes', u'dimensions', u'description', u'inventaire', u'object_type']

fields = [u'imageName', u'title', u'imageURL', u'author', u'date', u'technique', u'inventaire', u'dimensions',
 u'object_type', u'topic', u'category', u'institution', u'description', u'notes', u'source', u'technique']
csvFileName = 'metadata.csv'
blackList = [row['imageURL'] for row in csv.DictReader(open(csvFileName, 'rb'))]
csvFile = open(csvFileName, 'a')
writer = csv.DictWriter(csvFile, fieldnames=fields, encoding='utf-8')

categoryRoot = u"Limédia galeries - "
limediaCategory = u"[[Category:Limédia galeries]]"

commons = mwclient.Site('commons.wikimedia.org')
commons.login(username=botconfig.USER, password=botconfig.PASS)
    

def updateInstitution(metadata, institution):
    if('bmi' in institution):
        metadata['institution'] = u"Bibliothèque multimédia intercommunale d'Épinal"
        metadata['category'] = u"Collections of the Bibliothèque multimédia intercommunale d'Épinal"
    elif(institution == u"Bibliothèques de Nancy"):
        metadata['institution'] = u"Bibliothèque municipale de Nancy"
        metadata['category']= u"Collections of the Bibliothèque municipale de Nancy"
    elif(institution == u"Médiathèque intercommunale de Saint-Dié-des-Vosges"):
        metadata['institution'] = u"Médiathèque intercommunale de Saint-Dié-des-Vosges‎ "
        metadata['category']= u"Collections of the médiathèque intercommunale de Saint-Dié-des-Vosges‎ "
    elif(u"Metz" in institution):
        metadata['institution'] = u"Bibliothèques Médiathèques de Metz"
        metadata['category']= u"Collections of the Bibliothèques-Médiathèques de Metz"
    elif(u"Musée" in institution):
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
    contents = source.next_sibling.next_sibling.contents
    for i in range((len(contents)+2)/4):
        topic = contents[4*i+1]
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
        if (len(institution) > 1):
            output['inventaire']=unicode(institution[1][1:])
    elif(u"Description" in dataTitle):
        output['description']=basicData(source)
    elif(u"Typologies" in dataTitle):
         output['object_type']=basicData(source)
    elif(u"Technique" in dataTitle):
        output["title"] == linkedData(source)
    elif(u"Sujet" in dataTitle):
        output['topic'] = retrieveTopics(source)
    elif(u"Editeur" in dataTitle):
        output['notes']=linkedData(source)

def image_URL(soup):
    script = soup.findAll('script')[2].string
    pattern = re.compile("https:\/\/[\w|.|\/|-]+")
    imageUrl = pattern.findall(script)[0]
    return unicode(imageUrl)

def sanitize(name):
    return name.replace("[","").replace("]","").replace("/","sur").replace("/","")

def imageName(metadata):
    name = metadata['title'][:100]+" "+metadata['inventaire'] if 'inventaire' in metadata else metadata['title'][:100]
    name = sanitize(name)
    return unicode(name+".jpg")

def metadata(soup):
    metadata = {}
    s = soup.findAll(class_="viewer-block viewer-meta")
    if (len(s) > 0): # Else it's a map, not a file
        data = s[0]
        for source in data.findAll("h3"):
            retrieveData(source, metadata)
        metadata['imageName'] = imageName(metadata)
        metadata['imageURL'] = image_URL(soup)
    return metadata

def outputLines(metadata, url, additionnalCategories):
    lines = [
        u"== {{int:filedesc}}==\n",
        u"{{Artwork\n",
        u"|title=",metadata['title'],u"\n",
        u"|source=",url,u"\n",
        u"|institution={{Institution:",metadata['institution'],"}}\n",
        u"|date=",metadata['date'],u"\n"
        ]
    for key in optionalFields:
        if (key in metadata):
            if u"inventaire" in key:
                lines.append(u"|id="+metadata['inventaire']+u"\n")
            else:
                lines.append(u"|"+key+"={{fr|"+metadata[key]+u"}}\n")
        else:
            metadata[key]="no value"
    lines.extend([u"}}\n\n",
        u"=={{int:license-header}}==\n",
        u"{{PD-old}}\n\n",
        u"[[Category:",metadata['category'],"]]\n"])
    lines.extend(categories(metadata['topic']))
    lines.extend(additionnalCategories)
    for additionalCategory in additionnalCategories:
        categoryPage = commons.pages[sanitize(additionalCategory)]
        if len(categoryPage.text()) == 0:
            print(categoryPage.name)
            categoryPage.save(limediaCategory, summary="#LimediaGallery creating temporary category")
    return lines

def categories(topics):
    categories = [limediaCategory]
    for topic in topics:
        categoryName = sanitize(categoryRoot+topic)
        categoryPage = commons.pages["Category:"+categoryName]
        if len(categoryPage.text()) == 0:
            print(categoryPage.name)
            categoryPage.save(limediaCategory, summary="#LimediaGallery creating temporary category")
            categories.append(u"[[Category:"+categoryName+u"]]\n")
    return categories


def upload(url, soup, metadata, categories):
    fileName = u'File:{}'.format(metadata['imageName'])
    if (len(commons.pages[fileName].text())>0):
        print(fileName+" already exists")
    elif('object_type' in metadata and "monography" in metadata["object_type"]):
        print("Unsupported data type : monography")
    else:
        print('Uploading '+metadata['imageName'])
        imageRequest = requests.get(metadata['imageURL'])
        image = imageRequest.content
        # Save file
        open(metadata['imageName'], 'wb').write(imageRequest.content)
        # Upload to commons
        lines = outputLines(metadata, url, categories)
        text = u"".join(lines).encode('utf-8')
        try:
            commons.upload(open(metadata['imageName'], 'rb'), fileName, description=text, ignore=True)
        except Exception as error:
            errorsFile.write(u"".join(["\n",metadata['imageName']," - ",url]).encode('utf-8'))
            print(error)
        os.remove(metadata['imageName'])

def uploadDocument(documentURL, categories):
    documentRequest = requests.get(documentURL, allow_redirects=True)
    documentSoup = BeautifulSoup(documentRequest.content, features="lxml")
    print(documentURL)
    data = metadata(documentSoup)
    if (len(data.keys()) > 0): #else it is not a file
        data['source']=documentURL
        writer.writerow(data)
        upload(documentURL, documentSoup, data, categories)

def uploadDocuments(search_param, categories):
    pageURL = 'https://galeries.limedia.fr/recherche/?hide=article&'+search_param+'&page='
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
            uploadDocument(rootURL+documentLink['href'], categories)

def main():
    prefixes = [u"subjects", u"filter_location", u"author"]
    subjects = [u'Art nouveau']
    for subject in subjects:
        search_param = prefixes[0]+u"="+subject
        categories=[u"[[Category:"+categoryRoot+subject+u"]]\n"]
        uploadDocuments(search_param, categories)

main()