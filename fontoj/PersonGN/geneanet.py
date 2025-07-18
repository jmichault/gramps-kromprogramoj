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
"""
" gramplet Geneanet : fonctions pour accéder à geneanet en utilisant les API protobuf
"""

try:
  from google.protobuf.json_format import MessageToDict
  from google.protobuf.message import DecodeError
  from geneanet_pb import api_saisie_read_pb2, api_saisie_write_pb2, api_stats_pb2
except ImportError:
  pass

import sys
from os.path import exists
from urllib.error import HTTPError, URLError
from urllib.parse import unquote_to_bytes as unquote
from urllib.parse import quote, urlencode, urlparse, parse_qs
from urllib import request
import json
from datetime import datetime
import subprocess
# from https://stackoverflow.com/a/31174427
import functools

try:
  import certifi
  import ssl
  SslContext = ssl.create_default_context(cafile=certifi.where())
except ImportError:
  SslContext = None


try:
  from fake_useragent import UserAgent
  Headers = {"user-agent": UserAgent().firefox}
except ImportError:
  Headers = {
      "user-agent":
          "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"\
          " (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
  }
#from objbrowser import browse ;browse(locals())
#import pdb; pdb.set_trace()


def _rsetattr(obj, attr, val):
  pre, _, post = attr.rpartition('.')
  return setattr(_rgetattr(obj, pre) if pre else obj, post, val)


def _rgetattr(obj, attr, *args):
  def _getattr(obj, attr):
    return getattr(obj, attr, *args)
  return functools.reduce(_getattr, [obj] + attr.split('.'))


# ---


def url2id(parsed_url):
  """ crée un dict de la personne à partir de l'url """
  qs = parse_qs(parsed_url.query)
  personId = {'tree': parsed_url.path[1:].split('_')[0]}
  for field in ['i', 'n', 'p', 'oc']:
    if field in qs:
      if field in ['i', 'oc']:
        personId[field] = int(qs[field][0])
      else:
        personId[field] = qs[field][0]
  return personId


def id2url(persono):
  """ renvoie l'url geneanet pour la personne persono """
  if 'tree' in persono:
    return f"https://gw.geneanet.org/{persono['tree']}?{strId(persono)}"
  if 'person' in persono:
    persono = persono['person']
  if 'baseprefix' in persono:
    return f"https://gw.geneanet.org/{persono['baseprefix']}?{strId(persono)}"
  return 'https://gw.geneanet.org/'


def strId(persono):
  """ renvoie la portion d'url correspondant à la personne
  "  du type «p=prenom&n=nom&oc=occurence»
  """
  p = persono.get('p') or ''
  n = persono.get('n') or ''
  oc = persono.get('oc') or persono.get('occ') or ''
  if p != '':
    return urlencode({'p': p, 'n': n, 'oc': oc})
  if 'i' in persono:
    return urlencode({'i': persono['i']})
  if 'index' in persono:
    return urlencode({'i': persono['index']})
  return ''


class Api:
  """ classe d'interface geneanet """
  def __init__(self):
    self.user = False
    self.rights = {}
    Headers.update({"content-Type": "application/json;charset=UTF-8"})
    Headers.update({"DNT": "1"})
    cookieProcessor = request.HTTPCookieProcessor()
    httpsProcessor = request.HTTPSHandler(context=SslContext)
    self.opener = request.build_opener(cookieProcessor, httpsProcessor)

  def urlopen(self, url, data=None, headers=None):
    """ chargement d'une url """
    headers = headers or Headers
    if isinstance(data, str):
      data = data.encode('ascii')
    req = request.Request(url, data=data, headers=headers)
    statusCode = 403
    out = b''
    try:
      response = self.opener.open(req, timeout=10)
      statusCode = response.status
      out = response.read()
    except HTTPError as e:
      print('HTTPError loading %s code: %s ', (url, e.code))
    except (URLError,UnicodeEncodeError) as e:
      print(f'{e.__class__.__name__} loading {url} reason: {e.reason}')
    if statusCode == 403 or b'Sign up for free' in out:
      del self.opener
      self.opener = request.build_opener(request.HTTPCookieProcessor())
      req = request.Request(url, data=data, headers=headers)
      try:
        response = self.opener.open(req, timeout=10)
        statusCode = response.status
        out = response.read()
      except HTTPError as e:
        print('HTTPError loading %s code: %s ', (url, e.code))
      except URLError as e:
        print('URLError loading %s reason: %s ', (url, e.reason))
      except UnicodeEncodeError as e:
        print('UnicodeError loading %s reason: %s ', (url, e.reason))
      if b'Sign up for free' in out:
        print("************ Sign up for free in response *************")
    if statusCode != 403:
      return out
    c = 1
    while b',cUPMDTk:' in out:
      tmp = out.decode('utf-8').split(',cUPMDTk: ')[1]
      tmp = tmp.split(tmp[0], 2)
      o = urlparse(url)
      url2 = o.scheme + '://' + o.netloc + tmp[1].replace('\\', '')
      print('  Retrying', c, url2)
      req = request.Request(url2, data=data, headers=headers)
      with request.urlopen(req, timeout=10) as response:
        out = response.read()
        statusCode = response.status
      c += 1
      if c > 20:
        break
    return out

  def login(self, user, passwd):
    """ login geneanet """
    check = int(
        self.urlopen(
            'https://www.geneanet.org/connexion/verify.php?ctype=id',
            data='{"login": "' + user + '", "password": "' + passwd + '", "persistent": 1}',
            headers=Headers))
    if check > 0:
      self.user = user
    return check > 0

  def _account_infos(self, tree=''):
    return json.loads(
        self.urlopen('https://www.geneanet.org/app/arbre/?action=accountInfos&st=' +
                     tree).decode('utf-8'))

  def logged(self):
    """ renvoie l'état de connexion """
    return bool(self.urlopen('https://www.geneanet.org/app/arbre/?action=logged', headers=Headers))

  def check_rights(self, tree):
    """ renvoie les droits de l'utilisateur connecté sur l'arbre tree """
    if not self.user:
      return ''
    if tree in self.rights:
      return self.rights[tree]
    info = self._account_infos(tree)
    if info['canEdit'] == 1:
      rights = 'w'  # wizard
    elif info['tree'] == 1:
      rights = 'f'  # friend
    else:
      rights = ''
    self.rights[tree] = rights
    return rights

  def _arbre_api(self, req, params, opts=None):
    """ appel de l'api protobuf
        opts : dict pouvant contenir reqMsg,resMsg ou mode
    """
    actions = {
        'person': ('read', 'IndexPerson', 'Person'),  # index
        'graph_v2': ('read', 'GraphTreeParams', 'GraphTree'),  # NbAsc, NbDesc, Index
        'edit_person': ('write', 'IndexPerson', 'Person'),
        'edit_person_ok': ('write', 'Person', 'ModificationStatus'),
        'edit_family_request': ('write', 'IndexPerson', 'EditFamilyRequest'),
        'edit_family': ('write', 'IndexPersonAndFamily', 'EditFamily'),  # indexperson, indexfamily
        'edit_family_ok': ('write', 'EditFamilyOk', 'ModificationStatus'),
        'add_family': ('write', 'IndexPersonAndFamily', 'AddFamily'),
        'add_family_ok': ('write', 'AddFamilyOk', 'ModificationStatus'),
        'add_child': ('write', 'AddChildRequest', 'AddChild'),  # index, sex, IndexFamily
        'add_child_ok': ('write', 'AddChildOk', 'ModificationStatus'),
        'add_sibling': ('write', 'AddSiblingRequest', 'AddSibling'),  # index, sex
        'add_sibling_ok': ('write', 'AddSiblingOk', 'ModificationStatus'),
        'add_parents': ('write', 'IndexPersonAndFamily', 'AddParents'),
        'add_parents_ok': ('write', 'AddParentsOk', 'ModificationStatus'),
        'autocomplete': ('write', 'AutoComplete', 'AutoCompleteResult'),
        'person_search_list':
            ('write', 'PersonSearchListParams', 'PersonSearchList'),  # lastname, firstname, limit
        'person_search_info': ('write', 'IndexPerson', 'PersonSearchInfo'),
        'translate_keywords': ('write', False, 'Config'),
        'del_family': ('write', 'IndexPersonAndFamily', 'ModificationStatus'),
        'del_person': ('write', 'IndexPerson', 'ModificationStatus'),
        'stats': ('stats', 'StatsParams', 'Stats'),
    }
    if not req in actions:
      return {'error': 'unknown action'}
    if opts is None:
      opts={}
    mode = opts.get('mode') or actions[req][0]
    reqMsg = opts.get('reqMsg') or actions[req][1]
    resMsg = opts.get('resMsg') or actions[req][2]
    data = None
    if reqMsg:
      match mode:
        case 'read':
          message = getattr(api_saisie_read_pb2, reqMsg)
        case 'stats':
          message = getattr(api_stats_pb2, reqMsg)
        case 'write':
          message = getattr(api_saisie_write_pb2, reqMsg)
        case _:
          return {'error': 'unknown api'}
      data = message()
    tree = params['tree']
    del params['tree']
    if params:
      for e in params:
        _rsetattr(data, e, params[e])
    url = f"https://gw.geneanet.org/setup/api/?arbre={req}&sourcename={tree}&lang=en&type="
    if reqMsg:
      resp = self.urlopen(url, '{"data": "' + quote(data.SerializeToString()) + '"}')
    else:
      resp = self.urlopen(url)
    if not resp:
      return {'error': 'no response'}
    if mode == 'read':
      message = getattr(api_saisie_read_pb2, resMsg)
    elif mode == 'write':
      message = getattr(api_saisie_write_pb2, resMsg)
    elif mode == 'stats':
      message = getattr(api_stats_pb2, resMsg)
    response = message()
    try:
      response.ParseFromString(resp.decode('utf-8').encode('raw_unicode_escape'))
    except DecodeError:
      response.ParseFromString(resp)
    return MessageToDict(response)

  def _get_graph(self, tree, person_id):
    media = False
    if 'n' in person_id and 'p' in person_id:
      params = {
          'tree': tree,
          'identifier_person.p': person_id['p'],
          'identifier_person.n': person_id['n'],
          'nb_asc': 1,
          'nb_desc': 1
      }
      params['identifier_person.oc'] = person_id.get('oc') or 0
      personGraph = self._arbre_api('graph_v2', params)
      if personGraph:
        person_id['i'] = personGraph['nodesAsc'][0]['person']['index']
      elif 'i' in person_id:
        personGraph = self._arbre_api('graph_v2', {
            'tree': tree,
            'identifier_person.index': person_id['i'],
            'nb_asc': 1,
            'nb_desc': 1
        })
        if not personGraph:
          return {'error': 'could not find that person'}
        person_id['p'] = personGraph['nodesAsc'][0]['person']['p']
        person_id['n'] = personGraph['nodesAsc'][0]['person']['n']
        person_id['oc'] = personGraph['nodesAsc'][0]['person']['occ']
      else:
        return {'error': 'could not find that person'},None
      media = self.list_media(person_id)
    elif 'i' in person_id:
      person_id['i'] = int(person_id['i'])
      media, person_id = self.list_media(person_id, return_person_id=True)
    else:
      return {'error': 'missing person identifier'},None
    return ( media, person_id)

  def get_person(self, person_id):
    """ renvoie le json de la personne """
    tree = person_id.get('tree') or self.user
    if not tree:
      return {'error': 'missing tree'}
    (media,person_id) = self._get_graph(tree,person_id)
    if not person_id:
      return media

    person = self._arbre_api('person', {'tree': tree, 'index': person_id['i']})
    personReturn = {
        'provider': 'geneanet',
        'user': self.user,
        'person_id': person_id,
        'person': person,
        'media': media,
        'checked': datetime.now()
    }
    modified = self.get_last_modified(person_id)
    if modified:
      personReturn['modified'] = modified
    else:
      personReturn['retrieved'] = personReturn['checked']
    if self.check_rights(tree) == 'w':
      families = []
      fam = False
      editPerson = None
      for fam in person.get('families') or []:
        family = self._arbre_api('edit_family', {
            'tree': tree,
            'index_person': person_id['i'],
            'index_family': fam['index']
        })
        if not 'family' in family:
          continue
        families.append(family['family'])
        for p in ('father', 'mother'):
          if families[-1][p]['index'] == person_id['i']:
            editPerson = families[-1][p]
          families[-1][p] = families[-1][p]['index']
        if 'children' in families[-1]:
          for e in range(len(families[-1]['children'])):
            families[-1]['children'][e] = families[-1]['children'][e]['index']
      editPerson = (editPerson
                   or self._arbre_api('edit_person', {'tree': tree, 'index': person_id['i']}))
      personReturn['person_edit'] = editPerson
      personReturn['families'] = families
    return personReturn

  def list_media(self, person_id, lang='en', return_person_id=False):
    """ liste les media de la personne """
    url = 'https://gw.geneanet.org/' + person_id['tree'] + '?' + strId(person_id) \
         + '&lang=' + lang + '&type=tree&ajax=1'
    #print(url)
    page = self.urlopen(url).decode('utf-8')
    #print(page)
    pgsplit = page.split('"gntGeneweb":{"media":')
    if len(pgsplit) < 2:
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
    return media

  def _get_registre(self, m, rep):
    l = m['link'].split('/registres/view/')[1].split('?')[0].split('/')
    a = self.urlopen('https://www.geneanet.org/registres/api/images/' + l[0] +
                       '?min_page=0&max_page=9999').decode('utf-8')
    if len(l) > 1:
      b = a[int(l[1]) - 1]
    else:
      b = a[0]
    cmd = [
          'python3', 'dezoomify.py', '-b', 'https://www.geneanet.org' + b['image_base_url'],
          rep + '/media/' + str(m['id']) + '.' + str(m['part_id']) + '.jpg'
      ]
    subprocess.call(cmd)

  def _get_acte(self, m, rep):
    """ récupère les actes """
    a = self.urlopen(m['link']).decode('utf-8')
    if 'pagination' in a:
      b = a.split('data-img-url="')[1].split('"', 1)[0]
      cmd = [
          'python3', 'dezoomify.py', '-b',
          'https://www.geneanet.org' + unquote(b).decode('UTF-8'),
          rep + '/media/' + str(m['id']) + '.1.jpg'
      ]
      subprocess.call(cmd)
      numpages = int(
          a.split('<div class="pagination-documents" ')[1].split('</div>',
                                                                 1)[0].split('href="')[-1].split(
                                                                     '"', 1)[0].split('?p=')[1])
      for p in range(1, numpages):
        b = self.urlopen(m['link'] + '?p=' +
                             str(p + 1)).text.split('data-img-url="')[1].split('"', 1)[0]
        cmd = [
            'python3', 'dezoomify.py', '-b',
            'https://www.geneanet.org' + unquote(b).decode('UTF-8'),
            rep + '/media/' + str(m['id']) + '.' + str(p + 1) + '.jpg'
        ]
        subprocess.call(cmd)
    else:
      b = a.split('data-img-url="')[1].split('"', 1)[0]
      cmd = [
          'python3', 'dezoomify.py', '-b',
          'https://www.geneanet.org' + unquote(b).decode('UTF-8'),
          rep + '/media/' + str(m['id']) + '.jpg'
      ]
      subprocess.call(cmd)

  def get_media(self, m, rep):
    """ charge les media de l'arbre
    "   m = dict des media (id, type, link)
    "   rep = dossier de base, dans lequel on a le sous-dossier media
    """
    match m['type']:
      case 'monument':
        a = self.urlopen('https://www.geneanet.org/cimetieres/images/depots/' +
                       str(m['id'])).decode('utf-8')
        for b in a:
          request.urlretrieve(
            'https://www.geneanet.org/public/img/cimetieres/pictures/' + b['path'] + '/normal.jpg',
            rep + '/media/' + b['path'].rsplit('/', 1)[1] + '.jpg')
      case 'blason':
        request.urlretrieve('https:' + m['src'].replace('/medium.', '/normal.'),
                  rep + '/media/blason.' + str(m['id']) + '.jpg')
      case 'registre':
        self._get_registre( m, rep)
      case 'acte':
        self._get_acte( m, rep)
      case 'bibliotheque':
        print('https:' + m['link'])
        a = request.Request('https:' + m['link'] , method = 'HEAD')
        docUrl = self.opener.open(a, timeout=10)
        #docUrl = urlparse(self.session.head('https:' + m['link'], allow_redirects=True).url)
        b = parse_qs(docUrl.query)
        print(m)
        print(docUrl)
        print(b)
      case 'memlieux_resident':
        pass
      case 'vuesdhier':
        request.urlretrieve('https:' + m['src'], rep + '/media/' + str(m['id']) + '.jpg')
      case _:
        try:
          uri = rep + '/media/' + str(m['id']) + '.json'
          if not exists(uri):
            deposit = self.get_deposit(m['id'])
            with open(uri, 'w', encoding="utf-8") as f:
              json.dump(deposit, f, indent=2)
            for p in deposit['views']:
              uri = rep + '/media/' + str(p['id']) + '.' + p['files']['normal'].rsplit(
                '?', 1)[0].rsplit('.', 1)[1]
              request.urlretrieve('https://gw.geneanet.org' + p['files']['normal'], uri)
              refs = self.get_deposit_ref(m['id'], p['id'])
              if refs != []:
                with open( f"{rep}/media/{str(m['id'])}.references.json"
                         , 'w', encoding="utf-8") as f:
                  json.dump(refs, f, indent=2)
              links = self.get_deposit_links(m['id'], p['id'])
              if links != []:
                with open(f"{rep}/media/{str(m['id'])}.links.json", 'w', encoding="utf-8") as f:
                  json.dump(links, f, indent=2)
        except (ValueError,TypeError,FileNotFoundError,IOError):
          print(sys.exc_info()[0],
              'Deposit: https://www.geneanet.org/media/api/deposits/' + str(m['id']) + ' ')

  def get_deposit(self, deposit_id):
    """ récupère le json du document """
    return self.urlopen('https://www.geneanet.org/media/api/deposits/' +
                        str(deposit_id)).decode('utf-8')

  def get_deposit_ref(self, deposit_id, view_id):
    """ renvoie les références du document """
    return self.urlopen('https://www.geneanet.org/media/api/deposits/' + str(deposit_id) +
                        '/views/' + str(view_id) + '/references').decode('utf-8')

  def get_deposit_links(self, deposit_id, view_id):
    """ renvoie les liens du document """
    return self.urlopen('https://www.geneanet.org/media/api/deposits/' + str(deposit_id) +
                        '/views/' + str(view_id) + '/links').decode('utf-8')

  def get_monument_images(self, media_id):
    """ renvoie les images d'un cimetière genenanet """
    return self.urlopen('https://www.geneanet.org/cimetieres/images/depots/' +
                        str(media_id)).decode('utf-8')

  def get_registre_images(self, registre_id):
    """ renvoie les images d'un registre genenanet """
    return self.urlopen('https://www.geneanet.org/registres/api/images/' + registre_id +
                        '?min_page=0&max_page=9999').decode('utf-8')

  def get_full_deposit(self, tree):
    """ renvoie les documents de l'arbre """
    return self.urlopen('https://www.geneanet.org/media/api/deposits?filters[basename]=' + tree +
                        '&page=1&per_page=20').decode('utf-8')

  def get_person_deposit(self, tree, p):
    """ renvoie les documents liés à la personne """
    return self.urlopen('https://www.geneanet.org/media/api/deposits?filters[basename]=' + tree +
                        '&filters[i][0][ref_gw]=' + p).decode('utf-8')

  def get_hints(self, tree, p):
    """ renvoie les indices de recherche """
    data = {"sourcename": tree, "individus": [p]}
    return self.urlopen("https://gw.geneanet.org/match/api/indices", data, True).decode('utf-8')

  def get_last_modified(self, person_id):
    """ renvoie la date de dernière modification (nécessite premium ?)"""
    if 'oc' not in person_id:
      person_id['oc'] = 0
    url = 'https://gw.geneanet.org/' + person_id['tree'] + '?lang=en&m=HIST_DIFF&t=SUM&f=&' + strId(
        person_id).replace(' ', '_') + '&ajax=1'
    revisionsPage = self.urlopen(url).decode('utf-8')
    if '<td id="date_0"  v="' in revisionsPage:
      return datetime.fromisoformat(
          revisionsPage.split('<td id="date_0"  v="')[1].split('">', 1)[0])
    return False

  def get_available_trees(self):
    """ renvoie la liste des arbres auxquels l'utilisateur a accès (nécessite d'être connecté) """
    trees = []
    info = self._account_infos()
    trees.append(info['login'])
    for tree in info['otherTrees']:
      trees.append(tree[0])
    return trees

  def dl_tree(self, tree):
    """ importe l'arbre complet de l'utilisateur (fichier zip) """
    return self.urlopen('https://www.geneanet.org/app/arbre/index.php?action=import', {
        'st': tree
    }).decode('utf-8')

  def get_place_coord(self, placename):
    """ renvoie les coordonnées du lieu placename par interrogation de geneanet """
    coords = json.loads(
        self.urlopen('https://www.geneanet.org/geo/api/coordinates',
                     '{"place": "' + placename + '"}').decode('utf-8'))
    if coords:
      return coords[placename]
    return None


if __name__ == '__main__':
  g = Api()
  libaros = {'n': 'libaros', 'p': 'pierre', 'tree': 'jmt'}
  js = g.get_person(libaros)
  print(json.dumps(js, indent=2, default=str))
