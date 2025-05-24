""" modulo reakirante la aŭtentikigkodon kun undetected_chromedriver """

import json
import time
import undetected_chromedriver as uc
#from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

appKey = 'a02j000000KTRjpAAH'
redirect = 'https://misbach.github.io/fs-auth/index_raw.html'

def getcode(username,password) :
  """ getcode reakirante la aŭtentikigkodon kun undetected_chromedriver """
  try :
    driver = uc.Chrome()
  except Exception:
    print("échec de chargement de chrome")
    return ""
  print("essai cx avec selenium")
  url = 'https://ident.familysearch.org/cis-web/oauth2/v3/authorization?response_type=code'
  url = url + '&client_id='+appKey
  url = url + '&redirect_uri='+redirect
  if username is not None :
    url = url + '&username=' + username
  driver.get(url)
  driver.implicitly_wait(10)
  elem = driver.find_element(By.ID,"password")

  timeout = 30
  if password is not None and password != '' :
    elem.send_keys(password)
    elem.send_keys(Keys.RETURN)
    timeout = 3
  try :
    elem = WebDriverWait(driver, timeout).until(
          EC.presence_of_element_located((By.ID, "jwt"))
      )
  except Exception as e:
    print(f"exception : {e}")
    driver.quit()
    return None
  if elem.text == '' :
    driver.get('https://ident.familysearch.org/cis-web/oauth2/v3/authorization?response_type=code&scope=openid%20profile%20email%20qualifies_for_affiliate_account%20country&client_id=a02j000000KTRjpAAH&redirect_uri=https://misbach.github.io/fs-auth/index_raw.html')
  try :
    jwt = WebDriverWait(driver, timeout).until(
          EC.visibility_of_element_located((By.ID, "jwt"))
      )
  except Exception as e:
    print(f"exception : {e}")
    driver.quit()
    return None

  token = None
  try :
    tekstoj = json.loads(jwt.text)
    token = tekstoj['sessionId']
  except Exception:
    print("token pas trouvé.")
  driver.quit()
  return token

if __name__ == '__main__':
  token = getcode('xxx','')
  print("token="+str(token))
