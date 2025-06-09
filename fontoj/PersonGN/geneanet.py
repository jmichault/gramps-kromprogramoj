#!/usr/bin/env python
# coding: utf-8
#
# Gramplet - PersonGN (interfaco por GeneaNet)
#
# Kopirajto © 2025 Jean Michault
# Licenco «GPL-3.0-or-later»
#
# Ĉi tiu programo estas libera programaro; vi povas redistribui ĝin kaj/aŭ modifi
# ĝi laŭ la kondiĉoj de la Ĝenerala Publika Permesilo de GNU kiel eldonita de
# la Free Software Foundation; ĉu versio 3 de la Licenco, aŭ
# (laŭ via elekto) ajna posta versio.
#
# Ĉi tiu programo estas distribuata kun la espero, ke ĝi estos utila,
# sed SEN AJN GARANTIO; sen eĉ la implicita garantio de
# KOMERCEBLECO aŭ TAĜECO POR APARTA CELO. Vidu la
# GNU Ĝenerala Publika Permesilo por pliaj detaloj.
#
# Vi devus esti ricevinta kopion de la Ĝenerala Publika Permesilo de GNU
# kune kun ĉi tiu programo; se ne, skribu al 
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#


try :
  from google.protobuf.json_format import MessageToJson, MessageToDict
  from google.protobuf.message import DecodeError
  from geneanet_pb import api_saisie_read_pb2, api_saisie_write_pb2, api_app_pb2, api_stats_pb2
except :
  pass

from urllib.error import HTTPError, URLError
from urllib.parse import unquote_plus, unquote_to_bytes as unquote
from urllib.parse import quote, urlencode, urlparse, parse_qs
from urllib import request

from html import unescape as htmlunescape

import json
from time import sleep
import struct
from zipfile import ZipFile
from datetime import datetime

# from https://stackoverflow.com/a/31174427
import functools

#from objbrowser import browse ;browse(locals())
#import pdb; pdb.set_trace()

def rsetattr(obj, attr, val):
  pre, _, post = attr.rpartition('.')
  return setattr(rgetattr(obj, pre) if pre else obj, post, val)

def rgetattr(obj, attr, *args):
  def _getattr(obj, attr):
    return getattr(obj, attr, *args)
  return functools.reduce(_getattr, [obj] + attr.split('.'))

# ---

def url2id(parsed_url):
  qs = parse_qs(parsed_url.query)
  person_id = {'tree': parsed_url.path[1:].split('_')[0]}
  for field in ['i', 'n', 'p', 'oc']:
    if field in qs:
      if field in ['i', 'oc']:
        person_id[field] = int(qs[field][0])
      else:
        person_id[field] = qs[field][0]
  return person_id

def id2url(persono):
  if 'tree' in persono :
    return 'https://gw.geneanet.org/%s?%s' % (persono['tree'] , strId(persono) )
  elif 'baseprefix' in persono :
    return 'https://gw.geneanet.org/'+persono['baseprefix']+'?'+strId(persono)
  elif 'person' in persono :
    return 'https://gw.geneanet.org/'+persono['person'].get('baseprefix')+'?'+strId(persono['person'])
  return 'https://gw.geneanet.org/'

def strId(persono):
  p = persono.get('p') or ''
  n = persono.get('n') or ''
  oc =persono.get('oc') or persono.get('occ') or ''
  if p != '' :
    return urlencode({'p': p, 'n': n,'oc': oc })
  elif 'i' in persono:
    return urlencode({'i': persono['i']})
  elif 'index' in persono:
    return urlencode({'i': persono['index']})
  else:
    return ''

class Api:
  def __init__(self):
    self.user = False
    self.rights = {}
    try :
      import certifi
      import ssl
      ssl_context = ssl.create_default_context(cafile=certifi.where())
    except :
      ssl_context = None
    try :
      from fake_useragent import UserAgent
      self.headers = {"user-agent": UserAgent().firefox }
    except:
      self.headers = {"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36" }
    self.headers.update ( {"content-Type": "application/json;charset=UTF-8"} )
    self.headers.update ( {"DNT": "1"})
    cookie_processor = request.HTTPCookieProcessor()
    https_processor = request.HTTPSHandler(context=ssl_context)
    self.opener = request.build_opener(cookie_processor,https_processor)


  def urlopen(self, url, data=None, json_data=False, headers=None):
    if headers is None :
      headers=self.headers
    if isinstance(data, str):
      data = data.encode('ascii')
    req = request.Request(url,data=data,headers=headers)
    #response = request.urlopen(req, timeout=10)
    status_code = 403
    out=b''
    try:
      response = self.opener.open(req, timeout=10)
      status_code = response.status
      out=response.read()
    except HTTPError as e:
      print('Error code: ', e.code)
    except URLError as e:
      print('Reason: ', e.reason)
    if status_code == 403 or b'Sign up for free' in out:
      del self.opener
      self.opener = request.build_opener(request.HTTPCookieProcessor())
      req = request.Request(url,data=data,headers=headers)
      try :
        response = self.opener.open(req, timeout=10)
        status_code = response.status
        out=response.read()
      except HTTPError as e:
        print(' Error code: ', e.code)
      except URLError as e:
        print(' Reason: ', e.reason)
      if b'Sign up for free' in out:
        print("************ Sign up for free in response *************")
    if status_code != 403 :
      return out
    #print(out.decode('utf-8'))
    c = 1
    while b',cUPMDTk:' in out:
      tmp = out.decode('utf-8').split(',cUPMDTk: ')[1]
      tmp = tmp.split(tmp[0], 2)
      o = urlparse(url)
      url2 = o.scheme+'://'+o.netloc+tmp[1].replace('\\', '')
      print('  Retrying', c, url2)
      req = request.Request(url2,data=data,headers=headers)
      response = request.urlopen(req, timeout=10)
      out=response.read()
      status_code = response.status
      c += 1
      if c > 20:
        break
    return out

  def login(self, user, passwd):
    # Web login
    #csrf_token = self.opener.open('https://www.geneanet.org/connexion/').text.split('name="_csrf_token" value="')[1].split('"', 1)[0]
    #self.opener.open('https://www.geneanet.org/connexion/login_check', urlencode([('_username', user), ('_password', passwd), ('_remember_me', 1), ('_csrf_token', csrf_token)]).encode('utf-8'))
    # Geneanet Android app login (works only with username and not e-mail)
    #check = int(self.urlopen('https://www.geneanet.org/connexion/verify.php?ctype=id', data={'login': user, 'password': passwd, 'persistent': 1}))
    headers = self.headers
    #headers.append("DNT: 1")
    check = int(self.urlopen('https://www.geneanet.org/connexion/verify.php?ctype=id',
            #data={'login': user, 'password': passwd, 'persistent': 1},
            data='{"login": "'+ user+'", "password": "'+ passwd+ '", "persistent": 1}',
            headers=headers))
    if check > 0:
      self.user = user
    return check > 0

  def accountInfos(self, tree=''):
    return json.loads(self.urlopen('https://www.geneanet.org/app/arbre/?action=accountInfos&st='+tree).decode('utf-8'))

  def logged(self):
    headers = self.headers
    #headers.append("DNT: 1")
    return bool(self.urlopen('https://www.geneanet.org/app/arbre/?action=logged',headers=headers))

  def getTreeTitle(self, tree, lang="en", addprovider = True):
    page = self.urlopen('https://gw.geneanet.org/'+tree+'?lang='+lang).decode('utf-8')
    title = htmlunescape(page.split('class="svg-icon-home-white svg-icon-s-small" title="')[1].split('">', 1)[1].split('<', 1)[0].strip()) + ' ('+tree+')'
    if addprovider:
      title = 'Geneanet - ' + title
    return title

  """
  def checkRights(self, tree):
    url_w = 'https://gw.geneanet.org/'+tree+'_w'
    url_f = 'https://gw.geneanet.org/'+tree+'_f'
    if self.session.head(url_w, allow_redirects=True).url == url_w:
      return 'w'
    elif self.session.head(url_f, allow_redirects=True).url == url_f:
      return 'f'
    else:
      return ''
  """

  def checkRights(self, tree):
    if not self.user:
      return ''
    if tree in self.rights:
      return self.rights[tree]
    else:
      info = self.accountInfos(tree)
      if info['canEdit'] == 1:
        rights = 'w' # wizard
      elif info['tree'] == 1:
        rights = 'f' # friend
      else:
        rights = ''
      self.rights[tree] = rights
      return rights

  def arbre_api(self, req, params, req_msg = False, res_msg = False, mode = False, lang = 'en'):
    actions = {
      'person': ('read', 'IndexPerson', 'Person'), # index
      'graph_v2': ('read', 'GraphTreeParams', 'GraphTree'), # NbAsc, NbDesc, Index
      'edit_person': ('write', 'IndexPerson', 'Person'),
      'edit_person_ok': ('write', 'Person', 'ModificationStatus'),
      'edit_family_request': ('write', 'IndexPerson', 'EditFamilyRequest'),
      'edit_family': ('write', 'IndexPersonAndFamily', 'EditFamily'), # indexperson, indexfamily
      'edit_family_ok': ('write', 'EditFamilyOk', 'ModificationStatus'),
      'add_family': ('write', 'IndexPersonAndFamily', 'AddFamily'),
      'add_family_ok': ('write', 'AddFamilyOk', 'ModificationStatus'),
      'add_child': ('write', 'AddChildRequest', 'AddChild'), # index, sex, IndexFamily
      'add_child_ok': ('write', 'AddChildOk', 'ModificationStatus'),
      'add_sibling': ('write', 'AddSiblingRequest', 'AddSibling'), # index, sex
      'add_sibling_ok': ('write', 'AddSiblingOk', 'ModificationStatus'),
      'add_parents': ('write', 'IndexPersonAndFamily', 'AddParents'),
      'add_parents_ok': ('write', 'AddParentsOk', 'ModificationStatus'),
      'autocomplete': ('write', 'AutoComplete', 'AutoCompleteResult'),
      'person_search_list': ('write', 'PersonSearchListParams', 'PersonSearchList'), # lastname, firstname, limit
      'person_search_info': ('write', 'IndexPerson', 'PersonSearchInfo'),
      'translate_keywords': ('write', False, 'Config'),
      'del_family': ('write', 'IndexPersonAndFamily', 'ModificationStatus'),
      'del_person': ('write', 'IndexPerson', 'ModificationStatus'),
      'stats': ('stats', 'StatsParams', 'Stats'),
    }
    if req in actions:
      if not mode:
        mode = actions[req][0]
      if not req_msg:
        req_msg = actions[req][1]
      if not res_msg:
        res_msg = actions[req][2]
    if req_msg:
      if mode == 'read':
        message = getattr(api_saisie_read_pb2, req_msg)
      elif mode == 'stats':
        message = getattr(api_stats_pb2, req_msg)
      elif mode == 'write' or not mode:
        message = getattr(api_saisie_write_pb2, req_msg)
      else:
        return {'error': 'unknown api'}
      data = message()
    tree = params['tree']
    del(params['tree'])
    if params:
      for e in params:
        rsetattr(data, e, params[e])
    access = self.checkRights(tree)
    url = 'https://gw.geneanet.org/setup/api/?arbre='+req+'&sourcename='+tree+'&lang='+lang+'&type='
    if req_msg:
      resp = self.urlopen(url, '{"data": "'+quote(data.SerializeToString())+'"}')
    else:
      resp = self.urlopen(url)
    if(resp):
      if mode == 'read':
        message = getattr(api_saisie_read_pb2, res_msg)
      elif mode == 'write':
        message = getattr(api_saisie_write_pb2, res_msg)
      elif mode == 'stats':
        message = getattr(api_stats_pb2, res_msg)
      response = message()
      try:
        response.ParseFromString(resp.decode('utf-8').encode('raw_unicode_escape'))
      except DecodeError:
        response.ParseFromString(resp)
      #try:
      #  response.ParseFromString(resp.encode('raw_unicode_escape'))
      #except DecodeError:
      #  response.ParseFromString(resp)
      #import pdb; pdb.set_trace()
      return MessageToDict(response)
    return {'error': 'no response'}

  def getPerson(self, person_id):
    if 'tree' in person_id:
      tree = person_id['tree']
    elif self.user:
      tree = self.user
    else:
      return {'error': 'missing tree'}
    media = False
    if 'i' in person_id:
      person_id['i'] = int(person_id['i'])
    if 'n' in person_id and 'p' in person_id:
      params = {'tree': tree,
            'identifier_person.p': person_id['p'],
            'identifier_person.n': person_id['n'],
            'nb_asc': 1,
            'nb_desc': 1}
      if 'oc' in person_id:
        params['identifier_person.oc'] = person_id['oc']
      else:
        params['identifier_person.oc'] = 0
      person_graph = self.arbre_api('graph_v2', params)
      if person_graph:
        person_id['i'] = person_graph['nodesAsc'][0]['person']['index']
      elif 'i' in person_id:
        person_graph = self.arbre_api('graph_v2', {'tree': tree, 'identifier_person.index': person_id['i'], 'nb_asc': 1, 'nb_desc': 1})
        if person_graph:
          person_id['p'] = person_graph['nodesAsc'][0]['person']['p']
          person_id['n'] = person_graph['nodesAsc'][0]['person']['n']
          person_id['oc'] = person_graph['nodesAsc'][0]['person']['occ']
        else:
          return {'error': 'could not find that person'}
      else:
        return {'error': 'could not find that person'}
      media = self.listMedia(person_id)
    elif 'i' in person_id:
      media, person_id = self.listMedia(person_id, return_person_id = True)
    else:
      return {'error': 'missing person identifier'}

    person = self.arbre_api('person', {'tree': tree, 'index': person_id['i']})
    person_return = {'provider': 'geneanet', 'user': self.user, 'person_id': person_id, 'person': person, 'media': media, 'checked': datetime.now()}
    modified = self.getLastModified(person_id)
    if modified:
      person_return['modified'] = modified
    else:
      person_return['retrieved'] = person_return['checked']
    if self.checkRights(tree) == 'w':
      families = []
      fam = False
      edit_person = None
      if 'families' in person:
        for fam in person['families']:
          family = self.arbre_api('edit_family', {'tree': tree, 'index_person': person_id['i'], 'index_family': fam['index']})
          if not 'family' in family :
            continue
          families.append(family['family'])
          for p in ('father', 'mother'):
            if families[-1][p]['index'] == person_id['i']:
              edit_person = families[-1][p]
            families[-1][p] = families[-1][p]['index']
          if 'children' in families[-1]:
            for e in range(len(families[-1]['children'])):
              families[-1]['children'][e] = families[-1]['children'][e]['index']
      if edit_person is None :
        edit_person = self.arbre_api('edit_person', {'tree': tree, 'index': person_id['i']})
      person_return['person_edit'] = edit_person
      person_return['families'] = families
    return person_return

  def listMedia(self, person_id, lang='en', return_person_id = False):
    url = 'https://gw.geneanet.org/'+person_id['tree']+'?i='+str(person_id['i'])+'&lang='+lang+'&type=tree&ajax=1'
    #print(url)
    page = self.urlopen(url).decode('utf-8')
    #print(page)
    pgsplit = page.split('"gntGeneweb":{"media":')
    if len(pgsplit) <2:
      #import pdb; pdb.set_trace()
      print(" list media error")
      return None
    media, person = pgsplit[1].split(',"settings":{')[0].split(',"person":')
    media = json.loads(media)
    if return_person_id:
      person = json.loads(person)
      person_id['p'] = person['p']
      person_id['n'] = person['n']
      person_id['oc'] = person['oc']
      return [media, person_id]
    else:
      return media

  def getMedia(self, m):
    #print(m['type']) # media_autre|media_etatcivil|media_portrait|monument|registre|acte|memlieux_resident
    if m['type'] == 'monument':
      a = self.urlopen('https://www.geneanet.org/cimetieres/images/depots/'+str(m['id'])).decode('utf-8')
      for b in a:
        urlretrieve('https://www.geneanet.org/public/img/cimetieres/pictures/'+b['path']+'/normal.jpg', t[0]+'/media/'+b['path'].rsplit('/', 1)[1]+'.jpg')
    elif m['type'] == 'blason':
      urlretrieve('https:'+m['src'].replace('/medium.', '/normal.'), t[0]+'/media/blason.'+str(m['id'])+'.jpg')
    elif m['type'] == 'registre':
      l = m['link'].split('/registres/view/')[1].split('?')[0].split('/')
      a = self.urlopen('https://www.geneanet.org/registres/api/images/'+l[0]+'?min_page=0&max_page=9999').decode('utf-8')
      if len(l) > 1:
        b = a[int(l[1])-1]
      else:
        b = a[0]
      cmd = ['python3', 'dezoomify.py', '-b', 'https://www.geneanet.org'+b['image_base_url'], t[0]+'/media/'+str(m['id'])+'.'+str(m['part_id'])+'.jpg']
      subprocess.call(cmd)
    elif m['type'] == 'acte':
      a = self.urlopen(m['link']).decode('utf-8')
      if 'pagination' in a:
        z = a.split('data-img-url="')[1].split('"', 1)[0]
        cmd = ['python3', 'dezoomify.py', '-b', 'https://www.geneanet.org'+unquote(z).decode('UTF-8'), t[0]+'/media/'+str(m['id'])+'.1.jpg']
        subprocess.call(cmd)
        numpages = int(a.split('<div class="pagination-documents" ')[1].split('</div>', 1)[0].split('href="')[-1].split('"', 1)[0].split('?p=')[1])
        for p in range(1, numpages):
          z = self.session.get(m['link']+'?p='+str(p+1)).text.split('data-img-url="')[1].split('"', 1)[0]
          cmd = ['python3', 'dezoomify.py', '-b', 'https://www.geneanet.org'+unquote(z).decode('UTF-8'), t[0]+'/media/'+str(m['id'])+'.'+str(p+1)+'.jpg']
          subprocess.call(cmd)
      else:
        z = a.split('data-img-url="')[1].split('"', 1)[0]
        cmd = ['python3', 'dezoomify.py', '-b', 'https://www.geneanet.org'+unquote(z).decode('UTF-8'), t[0]+'/media/'+str(m['id'])+'.jpg']
        subprocess.call(cmd)
    elif m['type'] == 'bibliotheque':
      print('https:'+m['link'])
      doc_url = urlparse(self.session.head('https:'+m['link'], allow_redirects=True).url)
      q = parse_qs(doc_url.query)
      print(m)
      print(doc_url)
      print(q)
    elif m['type'] == 'memlieux_resident':
      pass
    elif m['type'] == 'vuesdhier':
      urlretrieve('https:'+m['src'], t[0]+'/media/'+str(m['id'])+'.jpg')
    else:
      try:
        uri = t[0]+'/media/'+str(m['id'])+'.json'
        if not exists(uri):
          deposit = g.getDeposit(m['id'])
          with open(uri, 'w') as f:
            json.dump(deposit, f, indent=2)
          for p in deposit['views']:
            uri = t[0]+'/media/'+str(p['id'])+'.'+p['files']['normal'].rsplit('?', 1)[0].rsplit('.', 1)[1]
            urlretrieve('https://gw.geneanet.org'+p['files']['normal'], uri)
            refs = g.getDepositRef(m['id'], p['id'])
            if refs != []:
              with open(t[0]+'/media/'+str(m['id'])+'.references.json', 'w') as f:
                json.dump(refs, f, indent=2)
            links = g.getDepositLinks(m['id'], p['id'])
            if links != []:
              with open(t[0]+'/media/'+str(m['id'])+'.links.json', 'w') as f:
                json.dump(links, f, indent=2)
      except:
        print(sys.exc_info()[0], 'Deposit: https://www.geneanet.org/media/api/deposits/'+str(m['id'])+' ')

  def getDeposit(self, depositId):
    return self.urlopen('https://www.geneanet.org/media/api/deposits/'+str(depositId)).decode('utf-8')

  def getDepositRef(self, depositId, viewId):
    return self.urlopen('https://www.geneanet.org/media/api/deposits/'+str(depositId)+'/views/'+str(viewId)+'/references').decode('utf-8')

  def getDepositLinks(self, depositId, viewId):
    return self.urlopen('https://www.geneanet.org/media/api/deposits/'+str(depositId)+'/views/'+str(viewId)+'/links').decode('utf-8')

  def getMonumentImages(self, mediaId):
    return self.urlopen('https://www.geneanet.org/cimetieres/images/depots/'+str(mediaId)).decode('utf-8')

  def getRegistreImages(self, registreId):
    return self.urlopen('https://www.geneanet.org/registres/api/images/'+registreId+'?min_page=0&max_page=9999').decode('utf-8')

  def getRegistreRef(self, url):
    if url.startswith('//'):
      url = 'https:' + url
    print(url)
    page = self.urlopen(url).decode('utf-8')
    ref = []
    for r in page.split('<div class="popup-link hoverable')[1:]:
      r = r.split('"\n            ', 1)[1]
      r = r.split('</a>')[0]
      tmp = r.split('>')[0]
      if tmp:
        tmp = tmp.split('data-')[1:]
        area = {}
        for t in tmp:
          t = t.split('=')
          area[t[0].strip()] = t[1].strip().strip('"')
      else:
        area = None
      tmp = {'person': url2id(urlparse(htmlunescape(r.split('<a href="')[1].split('"', 1)[0])))}
      note = r.split('<div class="notes">')[1].split('<p>', 1)[1].rsplit('</div>', 1)[0].rsplit('</p>', 1)[0]
      if area:
        tmp['area'] = area
      if note:
        tmp['note'] = note
      ref.append(tmp)
    return ref

  def getFullDeposit(self, tree):
    return self.urlopen('https://www.geneanet.org/media/api/deposits?filters[basename]='+tree+'&page=1&per_page=20').decode('utf-8')

  def getPersonDeposit(self, tree, p):
    return self.urlopen('https://www.geneanet.org/media/api/deposits?filters[basename]='+tree+'&filters[i][0][ref_gw]='+p).decode('utf-8')

  def getHints(self, tree, p):
    data = {"sourcename":tree,"individus":[p]}
    return self.urlopen("https://gw.geneanet.org/match/api/indices", data, True).decode('utf-8')

  def getLastModified(self, person_id):
    if 'oc' not in person_id:
      person_id['oc'] = 0
    url = 'https://gw.geneanet.org/'+person_id['tree']+'?lang=en&m=HIST_DIFF&t=SUM&f='+(person_id['p']+'.'+str(person_id['oc'])+'.'+person_id['n']).replace(' ', '_')+'&ajax=1'
    #print(url)
    revisions_page = self.urlopen(url).decode('utf-8')
    #print(revisions_page)
    if '<td id="date_0"  v="' in revisions_page:
      return datetime.fromisoformat(revisions_page.split('<td id="date_0"  v="')[1].split('">', 1)[0])
    else:
      return False

  def getHistory(self, tree, limit = 0, media = False, wiz = False):
    # TODO: media history
    nb=200
    if limit < nb:
      nb = limit
    media_str = ''
    if media:
      media_str = '&action=medias'
    wiz_str = ''
    if wiz:
      wiz_str = '&wiz='+wiz
    hist = []
    page = 1
    pos_str = ''
    while True:
      #print(page)
      table, trail = self.urlopen('https://gw.geneanet.org/'+tree+'?lang=en&m=HIST&k='+str(nb)+media_str+wiz_str+pos_str+'&ajax=1').decode('utf-8').split("</table>")
      pos = trail.split('name="pos" value="')[1].split('">', 1)[0]
      table = table.split('<tr>\n<th>')[1].split('" >\n<td>\n')
      header = table.pop(0).split('<th>')
      for x in range(len(header)):
        header[x] = header[x].split('</th>')[0]
      for x in range(len(table)):
        mod = table[x].split('</td>\n</tr>')[0].split('</td>\n<td>')
        if header[0] == "History":
          mod.pop(0)
        #mod[0] = dateparser.parse(mod[0])
        mod[0] = datetime.fromisoformat(mod[0])
        ids = mod[1].strip()
        if '<a href' in ids:
          url, name  = ids.split('<a href="')[1].split('</a>')[0].split('">')
          tmp = parse_qs(urlparse(url).query)
          
          mod[1] = [name, {k:tmp[k][0] for k in ['p', 'n', 'oc'] if k in tmp}]
        else:
          mod[1] = [ids]
        mod[2] = mod[2].split('">')[1].split('</a>')[0]
        hist.append(mod)
      page += 1
      if pos == '0' or (isinstance(limit, int) and limit > 0 and page > limit) or (isinstance(limit, datetime) and mod[0] < limit):
        break
      pos_str = '&pos='+pos
    #print(len(hist))
    return hist

  def getAvailableTrees(self):
    trees = []
    info = self.accountInfos()
    trees.append(info['login'])
    for tree in info['otherTrees']:
      trees.append(tree[0])
    return trees

  def dlTree(self, tree):
    return self.urlopen('https://www.geneanet.org/app/arbre/index.php?action=import', {'st': tree}).decode('utf-8')

  def getPlaceCoord(self,placename):
    coords = json.loads(self.urlopen('https://www.geneanet.org/geo/api/coordinates', '{"place": "'+placename+'"}').decode('utf-8'))
    if coords:
      return coords[placename]

def parse_pb_base_idx(f):
  data = []
  while True:
    b = f.read(4)
    if b:
      data.append(struct.unpack('>L',b)[0])
    else:
      break
  return data

def parse_pb_base_info(f):
  info = {}
  info['realNbPersons'], info['nbFamilies'] = struct.unpack('>LL',f.read(8))
  has_sosa, sosa = struct.unpack('<LL',f.read(8))
  if has_sosa:
    info['sosa'] = sosa
  string_size = struct.unpack('>b',f.read(1))[0]
  info['retrieved'] = datetime.fromtimestamp(int(f.read(string_size).decode('utf-8')))
  return info

def parse_pb_base_person(f, offset=-1):
  if offset >= 0:
    f.seek(offset+4)
    record_size = struct.unpack('>L',f.read(4))[0]
    record = f.read(record_size)
    person = api_app_pb2.Person()
    person.ParseFromString(record)
    return MessageToDict(person)
  else:
    datasize = struct.unpack('>L',f.read(4))[0]
    data = []
    while f.tell() < datasize+4:
      record_size = struct.unpack('>L',f.read(4))[0]
      record = f.read(record_size)
      person = api_app_pb2.Person()
      person.ParseFromString(record)
      data.append(MessageToDict(person))
    return data

def parse_pb_base_family(f, offset=-1):
  if offset >= 0:
    f.seek(offset+4)
    record_size = struct.unpack('>L',f.read(4))[0]
    record = f.read(record_size)
    family = api_app_pb2.Family()
    family.ParseFromString(record)
    return MessageToDict(family)
  else:
    datasize = struct.unpack('>L',f.read(4))[0]
    data = []
    while f.tell() < datasize+4:
      record_size = struct.unpack('>L',f.read(4))[0]
      record = f.read(record_size)
      family = api_app_pb2.Family()
      family.ParseFromString(record)
      data.append(MessageToDict(family))
    return data

def parse_pb_base_notes(f, offset=False):
  if offset:
    f.seek(offset)
    length = struct.unpack('>L', f.read(4))[0]
    return f.read(length).decode('utf-8')
  else:
    zero = struct.unpack('>L',f.read(4))[0]
    data = []
    while True:
      b = f.read(4)
      if len(b):
        length = struct.unpack('>L', b)[0]
        data.append(f.read(length).decode('utf-8'))
      else:
        break
    return data

def parse_pb_base_zip(filename):
  data = {}
  with ZipFile(filename) as pb_base:
    with pb_base.open('pb_base_info.dat') as myfile:
      data['info'] = parse_pb_base_info(myfile)

    with pb_base.open('pb_base_person.dat') as myfile:
      data['people'] = parse_pb_base_person(myfile)

    with pb_base.open('pb_base_person_note.inx') as myfile:
      idx = parse_pb_base_idx(myfile)
    with pb_base.open('pb_base_person_note.dat') as myfile:
      for i in range(len(idx)):
        if idx[i]:
          data['people'][i]['notes'] = parse_pb_base_notes(myfile, idx[i])

    with pb_base.open('pb_base_family.dat') as myfile:
      data['families'] = parse_pb_base_family(myfile)

    with pb_base.open('pb_base_family_note.inx') as myfile:
      idx = parse_pb_base_idx(myfile)
    with pb_base.open('pb_base_family_note.dat') as myfile:
      for i in range(len(idx)):
        if idx[i]:
          data['families'][i]['comment'] = parse_pb_base_notes(myfile, idx[i])
  return data

if __name__ == '__main__':
  g = Api()
  js = g.getPerson({'n': 'libaros', 'p': 'pierre', 'tree': 'jmt'})
  print(json.dumps(js, indent=2, default = str))
