from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class Waiting(webapp.RequestHandler):
    def get(self):
        downloadUrl = '/download?' + self.request.query_string
        self.response.out.write(
        '''<html><head><title>Download of Google Docs Backup Demo</title></head><body>
        <h3>Please wait, your download from <a href="http://arendvr.com/2009/03/21/google-docs-back/">Google Docs Backup Demo</a> will start shortly . . .</h3>
        <iframe style="display:none;" src="%s"></iframe>
        </body></html>''' % downloadUrl
        )

application = webapp.WSGIApplication([('/wait', Waiting)], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()