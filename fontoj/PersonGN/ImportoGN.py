#
# Gramplet - GN (interfaco por GeneaNet)
#
# Kopirajto © 2022 Jean Michault
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
GeneaNet Gramplet.
"""

#-------------------------------------------------------------------------

from gramps.gen.lib import Citation, Date, Event, EventRef, EventRoleType, EventType, Name, NameType, Note, NoteType
from gramps.gen.lib import  Person, Place, PlaceName, PlaceRef, PlaceType , RepoRef, Repository, RepositoryType, Source, SourceMediaType, SrcAttribute, Url , UrlType
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.datehandler import parser
from gramps.plugins.tool.changenames import ChangeNames

from gramps.gen.datehandler import LANG_TO_PARSER
parserEn = LANG_TO_PARSER['en']()

from urllib.parse import unquote
from html import unescape

from gn_constants import GN_GRAMPS_FAKTOJ
  
#from objbrowser import browse ;browse(locals())
#import pdb; pdb.set_trace()
import PersonGN
import LokoGN
from geneanet import id2url
from NoteGN import convert_to_styled

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

def aldNomo(db, txn, grPerson, extNomo, extANomo) :
  nomo = Name()
  nomo.set_type(NameType(NameType.BIRTH))
  nomo.set_first_name(extANomo)
  s = nomo.get_primary_surname()
  s.set_surname(extNomo)
  grPerson.set_primary_name(nomo)


def aldNomoj( db, txn, extPersono, grPerson) :
  extNomo = ChangeNames.name_cap(None, extPersono['person'].get('lastname'))
  extANomo = extPersono['person'].get('firstname')
  aldNomo(db, txn, grPerson, extNomo, extANomo)

def get_place_from_titolo(db, titolo, parento = None) -> Place:
  
  db.dbapi.execute(
            f"SELECT {db.serializer.data_field} FROM place WHERE title = ?",
            [titolo.strip(" ,")],
        )   
  while True :
    row = db.dbapi.fetchone()
    if row:
      datoj = db.serializer.string_to_data(row[0])
      if not parento :
        return datoj
      rl = datoj.get('placeref_list')
      if parento.handle in rl :
         return datoj
    else :
      return None
  return None

def kreiLokoDeOsm(db, txn, osmDatoj, parento=None) :
  nomo = osmDatoj['tags'].get('name')
  osm_tipo = osmDatoj.get('type')
  osm_id = osmDatoj.get('id')
  url = Url()
  url.set_path('https://www.openstreetmap.org/%s/%s' % (osm_tipo , osm_id))
  url.set_description('openstreetmap %s %s' % (osm_tipo , osm_id))
  url.set_type(UrlType('openstreetmap'))
  place = Place()
  place.add_url(url)
  place_name = PlaceName()
  place_name.set_value( nomo.strip() )
  place.set_name(place_name)
  place.set_title(nomo.strip())
  al = osmDatoj['tags'].get('admin_level')
  pl = osmDatoj['tags'].get('place')
  refI = osmDatoj['tags'].get('ref:INSEE')
  place.gramps_id = 'Osm_%s_%s' % (osm_tipo,osm_id)
  if refI : # France !
    match al :
     case '3' : # France métropolitaine, polynésie, …
      place.place_type = PlaceType(PlaceType.STATE)
     case '4' : # Régions : Aquitaine, Nouvelle-Aquitaine, …
      place.place_type = PlaceType(PlaceType.REGION)
      place.gramps_id = 'FrCogReg%s' % refI
     #case 5 : # Circonscription départementale
     case '6' : # Départements
      place.place_type = PlaceType(PlaceType.DEPARTMENT)
      place.gramps_id = 'FrCogDep%s' % refI
     #case 7 : # Arrondissements
     case '8' : # communes
      place.place_type = PlaceType(PlaceType.MUNICIPALITY)
      place.gramps_id = 'FrCogCom%s' % refI
     #case 9 : # Arrondissements municipaux (à Paris, Lyon, Marseille ), ou communes associées, ou communes déléguées
     case '10' : # quartier
      place.place_type = PlaceType(PlaceType.BOROUGH)
  if not place.place_type or place.place_type.value == PlaceType.UNKNOWN : # autres pays, on se cale sur les USA
    match al :
     case '2' :
      place.place_type = PlaceType(PlaceType.COUNTRY)
      code = osmDatoj['tags'].get("ISO3166-1:alpha3")
      if code : place.gramps_id = code
     #case 3 : # grandes régions, semi-officielles
     case '4' :
      place.place_type = PlaceType(PlaceType.STATE)
     case '5' : 
      place.place_type = PlaceType(PlaceType.REGION)
     case '6' : # State counties and "county equivalents," Territorial municipalities
      place.place_type = PlaceType(PlaceType.COUNTY)
     # case 7 : # Civil townships (in about one-third of states)
     case '8' : # state Municipalities: cities, towns and villages; infrequently, hamlets
      place.place_type = PlaceType(PlaceType.MUNICIPALITY)
     #case 9 : # Wards (rare)
     #case 10 : Neighborhoods (infrequent), homeowner associations (infrequent)
  if not place.place_type :
    match pl :
     case 'hamlet' :
      place.place_type = PlaceType(PlaceType.HAMLET)
  if place.place_type.value == PlaceType.UNKNOWN :
    print("  lieu osm(%s/%s) , type à traiter : admin_level=%s place=%s" % (osm_tipo,osm_id,al,pl))
  if parento :
    placeref = PlaceRef()
    placeref.set_reference_handle(parento.handle)
    place.set_placeref_list([placeref])
  db.add_place(place, txn)
  db.commit_place(place, txn)
  return place

def akiriOsmLoko(db, txn, osmDatoj, parento=None) :
  # on va chercher un lieu :
  #  1. avec le même gramps ID
  #  2. avec gramps_ID == osm_ID
  #  3. sinon : avec le même nom et un lien internet de type «openstreetmap» correspondant
  #  4. sinon et si le parent est renseigné : même parent avec même lien internet
  #  finalement : si le c'est un pays ou si le parent est renseigné : on crée le lieu
  nomo = osmDatoj['tags'].get('name')
  print("akiriOsmLoko : %s" % nomo)
  loko = db.get_place_from_gramps_id(osmDatoj.get('gramps_id'))
  if loko :
    return loko
  loko = db.get_place_from_gramps_id(osmDatoj.get('osm_id'))
  if loko :
    return loko
  osm_tipo = osmDatoj.get('type')
  osm_id = osmDatoj.get('id')
  url = 'https://www.openstreetmap.org/%s/%s' % (osm_tipo , osm_id)
  db.dbapi.execute(
            f"SELECT {db.serializer.data_field} FROM place WHERE title = ?",
            [nomo.strip()],
        )
  while True:
    row = db.dbapi.fetchone()
    if row is None :
      break
    loko = db.serializer.string_to_data(row[0])
    urlj = loko.get('urls')
    if urlj is None :
      continue
    for u in urlj :
      if u.get('path') == url :
         return loko
  if parento :
    #import pdb; pdb.set_trace()
    for rl in parento.get_placeref_list() :
      loko = db.get_place_from_handle(rl.ref)
      for curl in loko.urls :
        if curl.path == url :
           return loko
  if parento or ( int(osmDatoj['tags'].get('admin_level')) <=2 ) :
    return kreiLokoDeOsm(db, txn, osmDatoj, parento)
      
  return None

def akiriLoko(db, txn, nomo) :
  print("akiriLoko : %s" % nomo)
  if nomo is None or nomo.strip()=='' :
    return None
  # si on a déjà un lieu avec ce nom, on le prend :
  loko = get_place_from_titolo(db,nomo)
  if loko:
    return loko
  # le format de lieu recommandé par geneanet est :
  #    «[Lieu-dit, paroisse, abréviation] - Commune, code ville (INSEE ou postal - facultatif), Sous-région (Département), Région (facultatif), Pays»
  #   on va donc couper le nom selon les virgules, et éventuellement le premier élément selon le '-'
  partoj = nomo.split(',')
  lieudit = kodo = None
  if partoj[0].find(' - ') >= 0 :  # on a un lieu-dit
    x = partoj[0].split(' - ')
    lieudit=x[0].strip(" []")
    partoj[0]=x[1].strip()
  for x in partoj :
    if x.strip().isdecimal() :
      kodo = int(x.strip())
      partoj.remove(x)
  print("partoj = %s" % partoj)
  # on tente de trouver le lieu sur openstreetmap :
  osmLokoj = LokoGN.osmSearch(nomo)
  print("résultat osm = %s" %osmLokoj)
  if osmLokoj is None or len(osmLokoj) == 0 :  # osm n'a rien trouvé : on tente de trouver la commune
    komunumo = ''.join(partoj)
    osmLokoj = LokoGN.osmSearch(komunumo)
  else : # lieu complet trouvé sur osm, on n'a plus besoin du lieu-dit
    lieudit = None
  if osmLokoj is None or len(osmLokoj) == 0 :  # Perdu, osm n'a rien trouvé : on crée le lieu tel que
    place = Place()
    place_name = PlaceName()
    place_name.set_value( nomo.strip() )
    place.set_name(place_name)
    place.set_title(nomo)
    db.add_place(place, txn)
    db.commit_place(place, txn)
    return place
  antNomo = nomo.split(',')[0].strip()
  osmLoko = LokoGN.osmParse(osmLokoj[0])
  print("résultat détaillé osm = %s" %osmLoko.osmDatoj)
  print("  gramps_id=%s" % osmLoko.gramps_id)
  #print("    parents = %s" % osmLoko.parentoj)

  loko = db.get_place_from_gramps_id(osmLoko.gramps_id)
  if loko :
    return loko

  # on cherche les parents, on les crée si nécessaire
  parento = None
  osmParentoj = osmLoko.parentoj.copy()
  while (len(osmParentoj)) :
    osmParento = osmParentoj.pop()
    parento = akiriOsmLoko(db, txn, osmParento, parento)
  # on cherche ou crée le lieu trouvé par osm :
  loko = akiriOsmLoko(db, txn, osmLoko.osmDatoj , parento)
  if lieudit is None :
    return loko
  # si le lieu à chercher est un lieu-dit enfant du lieu trouvé dans osm, il faut aller plus loin
  parento = loko
  loko = get_place_from_titolo(db,lieudit,parento)
  if loko :
    return loko
  place = Place()
  place_name = PlaceName()
  place_name.set_value( nomo.strip() )
  place.set_name(place_name)
  place.set_title(nomo)
  placeref = PlaceRef()
  placeref.set_reference_handle(parento.handle)
  place.set_placeref_list([placeref])
  db.add_place(place, txn)
  db.commit_place(place, txn)
  return place

def htmlAlStyled(teksto) :
  teksto = teksto.replace('<p>','')
  teksto = teksto.replace('</p>','')
  teksto = teksto.replace('<br>\n','\n')
  return(convert_to_styled(teksto))

def aldFaktoj( db, txn, extPersono, grPerson) :
  faktoj = extPersono['person'].get('events')
  if faktoj is None or len(faktoj) == 0 :
    return
  for f in faktoj.get('elements') :
    if f.get('type') == "EFAM_MARRIAGE" :
      continue
    event = Event()
    evtType = GN_GRAMPS_FAKTOJ.get(unquote(f.get('type')))
    if not evtType:
      evtType = unquote(f.get('name'))
    print("ajout évènement %s" % evtType)
    event.set_type( evtType )
    dato = f.get('dateLong')
    if dato :
      grDato = parserEn.parse(dato)
      if grDato :
        event.set_date_object( grDato )
    db.add_event(event, txn)
    db.commit_event(event, txn)
    loko = unescape(f.get('place') or '')
    if loko :
      grLoko = akiriLoko(db, txn, loko)
      event.set_place_handle(grLoko.handle)
      db.commit_event(event, txn)
    noto = f.get('note')
    if noto :
      print("   note evt :%s" % noto)
      grNoto = Note()
      grNoto.set_type(NoteType(_('note geneanet %s') % extPersono['person'].get('baseprefix')))
      st = htmlAlStyled(noto)
      grNoto.set_styledtext(st)
      db.add_note(grNoto, txn)
      db.commit_note(grNoto, txn)
      event.add_note(grNoto.handle)
      db.commit_event(event, txn)
    src = f.get('src')
    if src :
      print("   src evt :%s" % src)
      citation = Citation()
      citation.set_confidence_level(Citation.CONF_LOW)
      attr = SrcAttribute()
      attr.set_type(_("Internet Address"))
      url = id2url(extPersono)
      attr.set_value(url)
      citation.add_attribute(attr)
      s = extPersono.get('grFonto')
      if s :
        citation.set_reference_handle(s.get_handle())
      db.add_citation(citation,txn)
      db.commit_citation(citation,txn)
      n = Note()
      n.set_type(NoteType(NoteType.CITATION))
      st = htmlAlStyled(src)
      n.set_styledtext(st)
      db.add_note(n, txn)
      db.commit_note(n, txn)
      citation.add_note(n.handle)
      db.commit_citation(citation,txn)
      event.add_citation(citation.get_handle())
    er = EventRef()
    er.set_role(EventRoleType.PRIMARY)
    er.set_reference_handle(event.get_handle())
    db.commit_event(event, txn)
    grPerson.add_event_ref(er)
    if event.type == EventType.BIRTH :
      grPerson.set_birth_ref(er)
    elif event.type == EventType.DEATH :
      grPerson.set_death_ref(er)
    db.commit_person(grPerson, txn)

def aldPersono(db, txn, extPersono) :
  grPerson = Person()
  aldNomoj( db, txn, extPersono, grPerson)
  s = extPersono['person'].get('sex')
  if s == 'MALE' :
    grPerson.set_gender(Person.MALE) 
  elif s == 'FEMALE' :
    grPerson.set_gender(Person.FEMALE)
  else :
    grPerson.set_gender(Person.UNKNOWN)
  db.add_person(grPerson,txn)
  db.commit_person(grPerson, txn)
  # récupération ou création du dépôt geneanet :
  db.dbapi.execute("select handle from repository where name=?",['geneanet'])
  datumoj = db.dbapi.fetchone()
  if datumoj and datumoj[0] :
    rh = datumoj[0]
  else :
    r = Repository()
    r.set_name('geneanet')
    rtype = RepositoryType()
    rtype.set((RepositoryType.WEBSITE))
    r.set_type(rtype)
    url = Url()
    url.path = 'https://www.geneanet.org/'
    url.set_type(UrlType.WEB_HOME)
    r.add_url(url)
    db.add_repository(r, txn)
    db.commit_repository(r,txn)
    rh = r.handle
  # récupération ou création de la source geneanet/arbre
  db.dbapi.execute("select handle from source where gramps_id=?",['geneanet_%s' % extPersono['person'].get('baseprefix')])
  datumoj = db.dbapi.fetchone()
  s = None
  while datumoj and datumoj[0] :
    s = db.get_source_from_handle(datumoj[0])
    break
    #datumoj = db.dbapi.fetchone()
  if not s :
    s = Source()
    s.gramps_id = 'geneanet_%s' % extPersono['person'].get('baseprefix')
    s.set_title(_('arbre geneanet %s') % extPersono['person'].get('baseprefix'))
    attr = SrcAttribute()
    attr.set_type(_('Internet Address'))
    attr.set_value('https://gw.geneanet.org/%s' % extPersono['person'].get('baseprefix'))
    s.add_attribute(attr)
    if rh :
      rr = RepoRef()
      rr.ref = rh
      rr.set_media_type( SourceMediaType.ELECTRONIC)
      s.add_repo_reference(rr)
    db.add_source(s,txn)
    db.commit_source(s,txn)
  # on met de coté la source pour la suite :
  extPersono['grFonto'] = s
  # création d'une citation
  citation = Citation()
  citation.set_confidence_level(Citation.CONF_LOW)
  attr = SrcAttribute()
  attr.set_type(_("Internet Address"))
  url = id2url(extPersono)
  attr.set_value(url)
  citation.add_attribute(attr)
  citation.set_reference_handle(s.get_handle())
  db.add_citation(citation,txn)
  db.commit_citation(citation,txn)
  src = extPersono.get('src')
  if src :
    n = Note()
    n.set_type(NoteType(NoteType.CITATION))
    st = htmlAlStyled(src)
    n.set_styledtext(st)
    db.add_note(n, txn)
    db.commit_note(n, txn)
    citation.add_note(n.handle)
  db.commit_citation(citation,txn)
  grPerson.add_citation(citation.get_handle())
  # ajout des évènements :
  aldFaktoj( db, txn, extPersono, grPerson)
  return grPerson

