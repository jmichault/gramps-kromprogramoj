import gi
gi.require_version("Gtk", "3.0")		# GUI toolkit
gi.require_version("WebKit2", "4.0")	# Web content engine
from gi.repository import Gtk, WebKit2

class miniBrowser():

    def __init__(self, *args, **kwargs):
        self.code=''
        # create window
        self.main_window = Gtk.Window(title = "My Browser")
        self.main_window.connect('destroy', Gtk.main_quit)	# connect the "destroy" trigger to Gtk.main_quit procedure
        self.main_window.set_default_size(800, 800)		# set window size

        # Create view for webpage
        self.web_view = WebKit2.WebView()				# initialize webview
        if len(args) >= 1:
          self.web_view.load_uri(args[0])	# default homepage
        else :
          self.web_view.load_uri('https://google.com')	# default homepage
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
        print("change_title:"+self.web_view.get_title())
        self.main_window.set_title(self.web_view.get_title())

    def change_uri(self, widget, frame):
        uri = self.web_view.get_uri()
        print("change_uri:"+uri);
        if uri[0:10]=='https://mi':
          poscode=uri.find('code=')
          if poscode>0 :
            self.code= uri[poscode+5:]
            print("change_url:code="+self.code)
          self.main_window.close()

