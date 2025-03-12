# essai de minibrowser utilisant webui2
# actuellement ne marche pas

from webui import webui
import time

class miniBrowser():

  def __init__(self, *args, **kwargs):
    self.code=''
    if len(args) >= 1:
      self.url=args[0]
    else :
      appKey = 'a02j000000KTRjpAAH'
      redirect = 'https://misbach.github.io/fs-auth/index_raw.html'
      self.url = 'https://ident.familysearch.org/cis-web/oauth2/v3/authorization?response_type=code&scope=openid%20profile%20email%20qualifies_for_affiliate_account%20country&client_id='+appKey+'&redirect_uri='+redirect
    print("url = "+self.url)
    # create window
    self.main_window = webui.window()
    webui.set_timeout(3)
    self.main_window.set_public(True)
    self.main_window.set_size(800, 800)		# set window size
    self.main_window.bind('Exit',self.exit)
    bind_id = self.main_window.bind("",self.change)
    print(f"Function bound with ID: {bind_id}")

    #self.main_window.show(self.url)
    self.main_window.show('<html><head><meta http-equiv="refresh" content="0; url='+self.url+'" /></head><body></body></html>')
    time.sleep(1.0)
    bind_id = self.main_window.bind("",self.change)
    print(f"Function bound with ID: {bind_id}")
    webui.set_timeout(20)
    webui.wait()

  def exit( e:webui.event ):
    print("exit")
    webui.exit()

  def change(e:webui.event ):
    print("change:"+e.event_type)

  def change_uri(self, widget, frame):
    uri = self.web_view.get_uri()
    print("change_uri:"+uri);
    if uri[0:10]=='https://mi':
      poscode=uri.find('code=')
      if poscode>0 :
        self.code= uri[poscode+5:]
        print("change_url:code="+self.code)
      self.main_window.close()

if __name__ == '__main__':
  x=miniBrowser()
