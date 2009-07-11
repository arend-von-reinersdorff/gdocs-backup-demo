import StringIO
import zipfile
import unicodedata
import string
import re

import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.api import users

import gdata.docs.service
import gdata.alt.appengine


# Fetches the first 10 documents from Google Docs and returns them in a .zip file
# fetching more documents eventually runs into a google apps timeout
class Fetcher(webapp.RequestHandler):
    NO_FETCHED = 10

    def __init__(self):
        self.names         = set()
        self.folders       = {}
        self.folder_names   = {}
  
    def get(self):

      # Initialize a client to talk to Google Data API services.
      client = gdata.docs.service.DocsService()
      gdata.alt.appengine.run_on_appengine(client)

      sessionToken = None
      # Find the AuthSub token and upgrade it to a session token.
      authToken = gdata.auth.extract_auth_sub_token_from_url(self.request.uri)
      if authToken:
          # Upgrade the single-use AuthSub token to a multi-use session token.
          sessionToken = client.upgrade_to_session_token(authToken)
          client.current_token = sessionToken
          self.fetchFeed(client)
      else:
          nextUrl = 'http://avrei.appspot.com/wait'
          urls = ('http://docs.google.com/feeds/','http://spreadsheets.google.com/feeds/')
          authSubUrl = client.GenerateAuthSubURL(nextUrl, urls, secure=False, session=True)
          self.response.out.write('<div id="request"><h4><a href="%s">Request a token</h4></a></div>' % authSubUrl)
        

    def fetchFeed(self, client):
        feed = client.QueryDocumentListFeed('http://docs.google.com/feeds/documents/private/full?showfolders=true')
      
        for entry in feed.entry:
            entry.kind = get_kind(entry)
            entry.id_str = get_id(entry)
            if entry.kind == 'folder':
                self.folders[entry.id_str] = entry

        f = StringIO.StringIO()
        zFile = zipfile.ZipFile(f, "w")

        getterUrls = {
            'document'     : 'http://docs.google.com/feeds/download/documents/Export?docID=%s&exportFormat=doc',
            'spreadsheet'  : 'http://spreadsheets.google.com/feeds/download/spreadsheets/Export?key=%s&fmcmd=4',
            'presentation' : 'http://docs.google.com/feeds/download/presentations/Export?docID=%s&exportFormat=ppt'
        }

        filesAdded = 0;
        for entry in feed.entry:
            if entry.kind in getterUrls:
                filesAdded += 1
                try:
                    url = getterUrls.get(entry.kind) % entry.id_str
                    content = client.Get(url, converter = (lambda x: x))
                    filename = self.get_name(entry)
                    zFile.writestr(filename, content)
                except:
                    pass
            if filesAdded >= Fetcher.NO_FETCHED:
                break

        zFile.close()
        self.output_file(f)
        f.close()


    def get_name(self, entry):
        #check for already processed folder
        folderName = self.folder_names.get(entry.id_str)
        if folderName:
            return folderName

        #reduce to ascii
        uniName = unicode(entry.title.text, 'utf-8')
        uniName = unicodedata.normalize('NFKD', uniName)
        asciiName = uniName.encode('ascii', 'ignore')

        #reduce to whitelisted characters
        validChars = ' !#$&\'()+,-.;=@[]^_`{}~%s%s' % (string.ascii_letters, string.digits)
        safeName = ''
        for c in asciiName:
            if c in validChars:
                safeName += c

        #add extension for files
        extension = ''
        extensions = {
            'document'     : 'doc',
            'spreadsheet'  : 'xls',
            'presentation' : 'ppt'
        }
        if entry.kind in extensions:
            extension = '.' + extensions.get(entry.kind)
        else:
            #must not end in space or dot
            safeName = re.sub('[\. ]+$', '', safeName)
            #handle empty name
            if safeName == '':
                safeName = entry.kind

        #get parent name
        parentFolderId = get_first_parent_folder_id(entry)
        if parentFolderId:
            safeName = self.get_name(self.folders.get(parentFolderId)) + '/' + safeName

        #check for double name
        uniqueName = safeName + extension
        counter = 1
        while uniqueName in self.names:
            uniqueName = safeName + '(' + str(counter) + ')' + extension
            counter += 1
        self.names.add(uniqueName)

        self.folder_names[entry.id_str] = uniqueName
        return uniqueName

    def output_file(self, file):
        self.response.headers['Content-Type'] = 'application/zip'
        self.response.headers['Content-Disposition'] = 'attachment; filename="Google_docs_backup.zip"'

        file.seek(0)
        while True:
            buf=file.read(2048)
            if buf=="":
                break
            self.response.out.write(buf)


def get_kind(entry):
    for category in entry.category:
        if category.scheme == 'http://schemas.google.com/g/2005#kind':
            return category.label
    return None


def get_first_parent_folder_id(entry):
    for link in entry.link:
        if link.rel == 'http://schemas.google.com/docs/2007#parent':
            return link.href.split('%3A')[1]
    return None


def get_id(entry):
    return entry.id.text.split('%3A')[1]
        

def main():
    application = webapp.WSGIApplication([('/download', Fetcher),], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()

