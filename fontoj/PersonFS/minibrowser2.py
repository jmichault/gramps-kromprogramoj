import webview

class miniBrowser:

  def __init__(self, *args, **kwargs):
    if len(args) >= 1:
      self.url=args[0]
    else :
      appKey = 'a02j000000KTRjpAAH'
      redirect = 'https://misbach.github.io/fs-auth/index_raw.html'
      self.url = 'https://ident.familysearch.org/cis-web/oauth2/v3/authorization?response_type=code&scope=openid%20profile%20email%20qualifies_for_affiliate_account country&client_id='+appKey+'&redirect_uri='+redirect
    self.code=''
    # create window
    #self.main_window = webview.create_window('miniBrowser',self.url, min_size=(600, 450))
    self.main_window = webview.create_window('miniBrowser',html='<html><head><meta http-equiv="refresh" content="0; url='+self.url+'" /></head><body></body></html>')
    self.main_window.events.loaded += self.on_loaded
    webview.start()


  def on_loaded(self):
    uri = self.main_window.get_current_url()
    if uri is None :
      return
    print("change_uri:"+str(uri));
    if uri[0:10]=='https://mi':
      poscode=uri.find('code=')
      if poscode>0 :
        self.code= uri[poscode+5:]
        print("change_url:code="+self.code)
      self.main_window.destroy()

if __name__ == '__main__':
  x=miniBrowser()
