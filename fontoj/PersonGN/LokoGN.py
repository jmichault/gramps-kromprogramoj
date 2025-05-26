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


import json
import socket

from urllib import request
from fake_useragent import UserAgent
from gramps.gen.display.place import displayer as _pd
from gramps.gen.config import config
from gramps.gen.lib import Place, PlaceName, PlaceType, Url, UrlType

vorteco = 0

def geneanetCoord(placename):
  data = '{"place": "%s"}' % placename
  headers = {"user-agent": UserAgent().firefox }
  headers.update ( {"content-Type": "application/json;charset=UTF-8"} )
  headers.update ( {"DNT": "1"})
  req=request.Request('https://www.geneanet.org/geo/api/coordinates', data=data.encode('ascii'),headers=headers)
  res = request.urlopen(req)
  coords = json.loads(res.read().decode('utf-8'))
  if coords:
    return coords[placename]

def osmGetUrl(osm_url, osm_datoj=None):
  print( "osmGetUrl %s" % osm_url )
  try:
    with request.urlopen(osm_url,data=osm_datoj, timeout=10) as response:
      data = response.read()
      rezultoj=json.loads(data)
  except request.URLError as err:
    try:
      txt = err.read().decode('utf-8')
      print("eraro pridemandante osm: %s" % txt)
    except:
      txt = ''
    return None
  except socket.timeout:
    return None
  if not rezultoj or len(rezultoj)==0 :
      return None
  return rezultoj

def osmSearch(nomo):
  """ find matching places in the osmnames, if possible """
  osm_url = ('https://nominatim.openstreetmap.org/search?format=jsonv2&q='+request.quote(nomo))
  return osmGetUrl(osm_url)

def osmParse(json_datoj):
  """ get data for place and parse out g_name dom structure into the
  NewPlace structure """
  osm_tipo = json_datoj['osm_type']
  osm_id = json_datoj['osm_id']
  newplace = NewPlace(json_datoj['display_name'])
  newplace.osmid = 'Osm_%s_%s' % (osm_tipo,osm_id)
  newplace.gramps_id = 'Osm_%s_%s' % (osm_tipo,osm_id)
  newplace.lat = json_datoj['lat']
  newplace.long = json_datoj['lon']
  new_place = PlaceName()
  new_place.set_value(json_datoj['name'])
  new_place.set_language("")
  # make sure we have the topname in the names list and default to
  # primary
  newplace.add_name(new_place)
  newplace.name = new_place
  # obtenir plus d'informations :
  osm_url = ('https://overpass-api.de/api/interpreter')
  if osm_tipo == 'relation' :
    osm_datoj= 'data='+request.quote('[out:json][timeout:25];rel('+str(osm_id)+');out center tags;')
  elif osm_tipo == 'way' :
    osm_datoj= 'data='+request.quote('[out:json][timeout:25];way('+str(osm_id)+');out center tags;')
  elif osm_tipo == 'node' :
    osm_datoj= 'data='+request.quote('[out:json][timeout:25];node('+str(osm_id)+');out center tags;')
  res = osmGetUrl(osm_url,bytes(osm_datoj,'utf-8'))
  newplace.code = ''
  rezultoj = None
  allowed_languages = [ 'fr' , 'en' ]
  fmt = config.get('preferences.place-format')
  placef = _pd.get_formats()[fmt]
  lang = placef.language
  if len(lang) != 2:
    lang = lang[:2]
  if lang not in allowed_languages:
    allowed_languages.append(lang)
  if res and len(res) :
    rezultoj=res.get("elements")
    for lingvo in allowed_languages :
      ling_nomo = rezultoj[0]["tags"].get("name:"+lingvo)
      if ling_nomo :
        new_place = PlaceName()
        new_place.set_language(lingvo)
        new_place.set_value(ling_nomo)
        newplace.add_name(new_place)
    admin_level = rezultoj[0]["tags"].get("admin_level")
    code = rezultoj[0]["tags"].get("ref:INSEE")
    if code :
      match admin_level :
        case "8" :
          newplace.gramps_id = 'FrCogCom'+str(code)
        case "6" :
          newplace.gramps_id = 'FrCogDep'+str(code)
        case "4" :
          newplace.gramps_id = 'FrCogReg'+str(code)
    else :
      code = rezultoj[0]["tags"].get("postal_code")
    if admin_level == "2" :
      code = rezultoj[0]["tags"].get("ISO3166-1:alpha3")
      if code : newplace.gramps_id = code
    newplace.code = code
  if rezultoj :
    newplace.osmDatoj=rezultoj[0]
    admin_level = int( rezultoj[0]["tags"].get("admin_level") or "9")
    res = None
    # obtenir tous les parents administratifs :
    # 'is_in(46.6121074,0.5541073)->.a;relation["admin_level"~"8|7|6|5|4|3|2"](pivot.a);out tags center;'
    while admin_level>1 :
      osm_datoj= '[timeout:10][out:json];is_in('+str(newplace.lat)+','+str(newplace.long)+')->.a;relation["admin_level"~"8|6|4|2"](pivot.a);out tags center;'
      #if json_datoj['display_name'].endswith('France') :
      #  # en France, on saute les arrondissements (niveau 7), les circonscriptions départementales(5) et la France Métropolitaine (niveau 3) :
      #  if admin_level==8 or admin_level==6 or admin_level == 4 :
      #    admin_level = admin_level - 1
      #osm_datoj= '[timeout:10][out:json];is_in('+str(newplace.lat)+','+str(newplace.long)+')->.a;relation["admin_level"="'+str(admin_level-1)+'"](pivot.a);out tags center;'
      osm_url = ('https://overpass-api.de/api/interpreter')
      if vorteco>0 : print("requête overpass %s" % osm_datoj)
      res = osmGetUrl(osm_url,bytes(osm_datoj,'utf-8'))
      if not res or not len(res) :
        continue
      if res and len(res) and not res.get("elements") :
        admin_level = admin_level - 1
        res = None
        continue;
      rezultoj=res.get("elements")
      if vorteco>0 : print("   parent=%s" % rezultoj)
      print("   parent=%s" % rezultoj)
      return None
      if len(rezultoj)==0 :
        admin_level = admin_level - 1
        res = None
        continue;
      
      osm_id = 'Osm_'+ rezultoj[0]["type"] +"_"+ str(rezultoj[0]["id"])
      if admin_level == 2 :
        code = rezultoj[0]["tags"].get("ISO3166-1:alpha3")
        if code : osm_id = code
      gramps_id = osm_id
      if json_datoj['display_name'].endswith('France') :
        code = rezultoj[0]["tags"].get("ref:INSEE")
        if code and admin_level == 8 :
          gramps_id  = 'FrCogCom'+str(code)
        elif code and admin_level == 6 :
          gramps_id = 'FrCogDep'+str(code)
        elif code and admin_level == 4 :
          gramps_id = 'FrCogReg'+str(code)
      rezultoj[0]["osm_id"] = osm_id
      rezultoj[0]["gramps_id"] = gramps_id
      newplace.parentoj.append(rezultoj[0])
      admin_level = admin_level -1
  # autre option : obtenir les parents directs :
  # '[timeout:10][out:json]; rel(7377); rel(br); out tags center;
  return newplace

class NewPlace():
  """ structure to store data about a found place"""
  def __init__(self, title):
      self.title = title
      self.osmDatoj = None
      self.gramps_id = ''
      self.lat = ''
      self.long = ''
      self.code = ''
      self.names = []  # all names, including alternate, acts like a set
      self.name = PlaceName()
      self.links = []
      self.osmid = ''
      self.parentoj = []   # list of parents in hierarchical order

  def add_name(self, name):
      """ Add a name to names list without repeats """
      if ',' in name.value:
          name.value = name.value.split(',')[0]
          return
      if name not in self.names:
          self.names.append(name)

  def add_names(self, names):
      """ Add names to names list without repeats """
      for name in names:
          self.add_name(name)

if __name__ == '__main__':
  res = osmSearch('9ème arrondissement, Paris, Paris, Île-de-France, France')
  print(res)
