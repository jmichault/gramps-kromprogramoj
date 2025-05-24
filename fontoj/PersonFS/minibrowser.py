import gi
gi.require_version("Gtk", "3.0")		# GUI toolkit
try :
  gi.require_version("WebKit2", "4.1")	# Web content engine
except ValueError:
  gi.require_version("WebKit2", "4.0")	# Web content engine
from gi.repository import Gtk, WebKit2

class miniBrowser():

    def __init__(self, url=None,username=None,redirect=None,appKey=None) :
        self.code=''
        self.redirect = redirect
        if url is None :
          url = 'https://ident.familysearch.org/cis-web/oauth2/v3/authorization?response_type=code'
          if appKey is not None :
            url = url + '&client_id='+appKey
          if redirect is not None :
            url = url + '&redirect_uri='+redirect
          if username is not None :
            url = url + '&username=' + username
          #url = url + '&scope=openid profile country'
        # create window
        self.main_window = Gtk.Window(title = "My Browser")
        self.main_window.connect('destroy', Gtk.main_quit)	# connect the "destroy" trigger to Gtk.main_quit procedure
        self.main_window.set_default_size(800, 800)		# set window size

        # Create view for webpage
        self.web_view = WebKit2.WebView()				# initialize webview
        self.web_view.load_uri(url)
        self.web_view.connect('notify::title', self.change_title)	# trigger: title change
        self.web_view.connect('notify::uri', self.change_uri)	# trigger: webpage is loading
        self.scrolled_window = Gtk.ScrolledWindow()		# scrolling window widget
        self.scrolled_window.add(self.web_view)

        # Add everything and initialize
        self.vbox_container = Gtk.VBox()		# vertical box container
        self.vbox_container.pack_start(self.scrolled_window, True, True, 0)
        
        self.main_window.add(self.vbox_container)
        self.main_window.show_all()
        Gtk.main()

    def change_title(self, widget, frame):
        self.main_window.set_title(self.web_view.get_title())

    def change_uri(self, widget, frame):
        uri = self.web_view.get_uri()
        if uri is not None and uri[0:len(self.redirect)]==self.redirect :
          print("change_url:url="+uri)
          poscode=uri.find('code=')
          if poscode>0 :
            self.code= uri[poscode+5:]
            print("change_url:code="+self.code)
          self.main_window.close()

if __name__ == '__main__':
  x=miniBrowser( appKey = '3Z3L-Z4GK-J7ZS-YT3Z-Q4KY-YN66-ZX5K-176R' , redirect = 'https://www.familysearch.org/auth/familysearch/callback')
