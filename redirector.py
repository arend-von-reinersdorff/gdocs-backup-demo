from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class Redirector(webapp.RequestHandler):
    def get(self):
        self.redirect('http://arendvr.com/2009/03/21/google-docs-back/')

application = webapp.WSGIApplication([('/', Redirector)], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
