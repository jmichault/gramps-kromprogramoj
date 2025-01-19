""" modulo reakirante la aŭtentikigkodon kun undetected_chromedriver """

import json
import time
import undetected_chromedriver as uc
#from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def getcode(username,password) :
  """ getcode reakirante la aŭtentikigkodon kun undetected_chromedriver """
  try :
    driver = uc.Chrome(headless=False,use_subprocess=False)
  except Exception:
    return ""
  url = 'https://ident.familysearch.org/cis-web/oauth2/v3/authorization'
  url += '?response_type=code'
  url += '&scope=openid profile email qualifies_for_affiliate_account country'
  url += '&client_id=' + 'a02j000000KTRjpAAH'
  url += '&redirect_uri=' + 'https://misbach.github.io/fs-auth/index_raw.html'
  url += '&username='+username
  driver.get(url)
  #time.sleep(0.5)
  elem = WebDriverWait(driver, 10).until(
          EC.presence_of_element_located((By.ID, "password"))
      )
  #time.sleep(1.1)
  elem.send_keys(password)
  #time.sleep(0.5)
  elem.send_keys(Keys.RETURN)
  elem = WebDriverWait(driver, 10).until(
          EC.presence_of_element_located((By.ID, "jwt"))
      )
  get_url = driver.current_url
  print("The current url is:"+str(get_url))
  time.sleep(0.5)
  jwt = driver.find_element(By.ID,'jwt')
  token = None
  try :
    tekstoj = json.loads(jwt.text)
    token = tekstoj['sessionId']
  except Exception:
    print("token pas trouvé.")
  driver.quit()
  return token
