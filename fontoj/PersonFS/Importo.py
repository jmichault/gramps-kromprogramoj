#
# interfaco por familysearch
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
" «FamilySearch» importo.
"""
import json
from urllib.parse import unquote


from gi.repository import Gtk

from gramps.gen.db import DbTxn
from gramps.gen.config import config
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.lib import Attribute, ChildRef, Citation, Date, Event, EventRef, EventType, EventRoleType, Family, Media, Name, NameType, Note, NoteType
from gramps.gen.lib import Person, Place, PlaceName, PlaceRef, PlaceType, RepoRef, Repository, RepositoryType, Source, SourceMediaType, SrcAttribute, StyledText, StyledTextTag, StyledTextTagType, Url, UrlType
from gramps.gen.plug.menu import StringOption, PersonOption, BooleanOption, NumberOption, FilterOption, MediaOption
from gramps.gui.dialog import WarningDialog, QuestionDialog2
from gramps.gui.plug import MenuToolOptions, PluginWindows
from gramps.gui.utils import ProgressMeter


import fs_db
import PersonFS
import utila
from fs_constants import GEDCOMX_GRAMPS_FAKTOJ, GEDCOMX_GRAMPS_LOKOJ
import tree
import komparo
from utila import fsdato_al_gr, get_fsftid

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


# gedcomx_v1 biblioteko. Instalu kun `pip install --user --upgrade --break-system-packages gedcomx_v1`
import instdep
instdep.instDep('gedcomx_v1','1.0.24')
import gedcomx_v1


# tutmondaj variabloj
vorteco = 0

#from objbrowser import browse ;browse(locals())
#import pdb; pdb.set_trace()

def kreiLoko(db, txn, fsPlace, parent):
  place = Place()
  url = Url()
  url.path = 'https://api.familysearch.org/platform/places/description/'+fsPlace.id
  url.type = UrlType('FamilySearch')
  url2 = Url()
  url2.path = fsPlace.links['place'].href.removesuffix('?flag=fsh')
  url2.type = UrlType('FamilySearch')
  tp = Place()
  tp.add_url(url)
  tp.add_url(url2)
  place._merge_url_list(tp)
  nomo = fsPlace.display.name
  place_name = PlaceName()
  place_name.set_value( nomo )
  place.set_name(place_name)
  place.set_title(nomo)
  place_type = None
  place.lat = str(fsPlace.latitude)
  place.long = str(fsPlace.longitude)
  if hasattr(fsPlace, 'type'):
    tipo = GEDCOMX_GRAMPS_LOKOJ.get(fsPlace.type)
    if tipo :
      place_type = PlaceType(tipo)
  if not place_type :
    if not parent:
      place_type = PlaceType(1)
    else:
      if parent.place_type == PlaceType(1):
        place_type = PlaceType(9)
      elif parent.place_type == PlaceType(9):
        place_type = PlaceType(10)
      elif parent.place_type == PlaceType(10):
        place_type = PlaceType(14)
      elif parent.place_type == PlaceType(14):
        place_type = PlaceType(20)
  if parent:
    placeref = PlaceRef()
    placeref.ref = parent.handle
    place.add_placeref(placeref)
  place.set_type(place_type)
  db.add_place(place, txn)
  db.commit_place(place, txn)
  fsPlace._handle = place.handle
  if utila.fs_gr_lokoj :
    utila.fs_gr_lokoj[url.path] = place.handle
    utila.fs_gr_lokoj[url2.path] = place.handle
  return place



def aldLoko(db, txn, pl):
  if not hasattr(pl,'_handle') :
    pl._handle = None
  if pl._handle :
    try:
      grLoko = db.get_place_from_handle(pl._handle)
      return grLoko
    except:
      pass
  # sercxi por loko 
  grLoko = akiriLokoPerId(db, pl)
  if grLoko:
    pl._handle = grLoko.handle
    return grLoko
  if not pl.id : return None
  print("aldLoko:"+pl.id)
  mendo = '/platform/places/description/'+pl.id
  r = tree._FsSeanco.get_url( mendo ,{"Accept": "application/json,*/*"})
  if r and r.status_code == 200 :
    try:
      datumoj = r.json()
    except Exception as e:
      print("WARNING: corrupted file from %s, error: %s" % (mendo, e))
      print(r.content)
      return None
  else:
    if r :
      print("WARNING: Status code: %s" % r.status_code)
    return None
  if not 'places' in datumoj : return
  t = gedcomx_v1.Gedcomx()
  gedcomx_v1.maljsonigi(t,datumoj)
  fsPlaceId = datumoj['places'][0]['id']
  # FARINDAĴO : charger le lien place, et récupérer toutes les descriptions
  fsPlace = gedcomx_v1.PlaceDescription._indekso.get(fsPlaceId)
  if fsPlace.jurisdiction :
    fsParentId = fsPlace.jurisdiction.resourceId
    fsParent = gedcomx_v1.PlaceDescription._indekso.get(fsParentId)
    grParent = aldLoko( db, txn, fsParent)
  else:
    grParent = None
  if fsPlaceId != pl.id :
    # lieux fusionnés !
    grLoko2 = akiriLokoPerId(db, fsPlace)
    if not grLoko2:
      grLoko2 = aldLoko(db, txn, fsPlace)
    url = Url()
    url.path = 'https://api.familysearch.org/platform/places/description/'+pl.id
    url.type = UrlType('FamilySearch')
    url2 = Url()
    url2.path = fsPlace.links['place'].href.removesuffix('?flag=fsh')
    url2.type = UrlType('FamilySearch')
    tp = Place()
    tp.add_url(url)
    tp.add_url(url2)
    grLoko2._merge_url_list(tp)
    if utila.fs_gr_lokoj :
      utila.fs_gr_lokoj[url.path] = grLoko2.handle
      utila.fs_gr_lokoj[url2.path] = grLoko2.handle
    db.commit_place(grLoko2, txn)
    return grLoko2

  return kreiLoko(db, txn, fsPlace, grParent)
  

def akiriLokoPerId(db, fsLoko):
  #print ("sercxi loko:"+str(fsLoko.id))
  if not fsLoko.id and fsLoko.description and fsLoko.description[:1]=='#' :
     fsLoko.id=fsLoko.description[1:]
  if not fsLoko.id:
    return None
  s_url = 'https://api.familysearch.org/platform/places/description/'+fsLoko.id
  if hasattr(fsLoko,'links') and fsLoko.links and fsLoko.links.get('place') :
    s_url2 = fsLoko.links['place'].href.removesuffix('?flag=fsh')
  else :
    s_url2 = None
  if utila.fs_gr_lokoj :
    place_handle=utila.fs_gr_lokoj.get(s_url)
    if not place_handle :
      place_handle=utila.fs_gr_lokoj.get(s_url2)
    if place_handle :
      try :
        return db.get_place_from_handle(place_handle)
      except:
        pass
    else :
      return None
    
  # krei fs_gr_lokoj
  if not utila.fs_gr_lokoj :
    print(_('Konstrui FSID listo por lokoj'))
    utila.fs_gr_lokoj = dict()
    #print ("sercxi url:"+s_url)
    for handle in db.get_place_handles():
      place = db.get_place_from_handle(handle)
      for url in place.urls :
        if str(url.type) == 'FamilySearch' :
          utila.fs_gr_lokoj[url.path] = handle
  # sercxi por loko kun cî «id»
  place_handle=utila.fs_gr_lokoj.get(s_url)
  if place_handle :
    return db.get_place_from_handle(place_handle)
  return None

def aldNoto(db, txn, fsNoto,EkzNotoj):
  # sercxi ekzistantan
  for nh in EkzNotoj:
    n = db.get_note_from_handle(nh)
    titolo = _(n.type.xml_str())
    if titolo == fsNoto.subject:
      for t in n.text.get_tags():
        if t.name == StyledTextTagType.LINK :
          fsNotoId = t.value
          if titolo == fsNoto.subject and fsNotoId=="_fsftid="+fsNoto.id :
            return n
  grNoto = Note()
  grNoto.set_format(Note.FORMATTED)
  grNoto.set_type(NoteType(fsNoto.subject))
  if fsNoto.id :
    # on met un tag de type lien sur le premier caractère pour mémoriser l'ID FamilySearch :
    tags = [  StyledTextTag(StyledTextTagType.LINK,"_fsftid="+ fsNoto.id,[(0, 1)])]
    # on ajoute un caractère invisible en début de texte :
    grNoto.set_styledtext(StyledText("\ufeff"+(fsNoto.text or ''), tags))
  db.add_note(grNoto, txn)
  db.commit_note(grNoto, txn)
  return grNoto
  
def updFakto(db, txn, fsFakto, grFakto):
  if fsFakto.place :
    if not hasattr(fsFakto.place,'normalized') :
      #from objbrowser import browse ;browse(locals())
      print("lieu pas normalisé : "+fsFakto.place.original)
      plantage()
    grLoko = akiriLokoPerId(db, fsFakto.place)
    if grLoko:
      grLokoHandle = grLoko.handle
    else :
      aldLoko( db, txn, fsFakto.place)
      grLokoHandle = fsFakto.place._handle
    grFakto.set_place_handle( grLokoHandle )
  fsFaktoPriskribo = fsFakto.value or ''
  fsFaktoDato = fsFakto.date or ''
  grDato = fsdato_al_gr(fsFakto.date)
  if grDato :
    grFakto.set_date_object( grDato )
  grFakto.set_description(fsFaktoPriskribo)
  db.commit_event(grFakto, txn)

def aldFakto(db, txn, fsFakto, obj):
  evtType = GEDCOMX_GRAMPS_FAKTOJ.get(unquote(fsFakto.type))
  if not evtType:
    if fsFakto.type[:6] == 'data:,':
      evtType = unquote(fsFakto.type[6:])
    else:
      evtType = fsFakto.type
  grLokoHandle = None
  if fsFakto.place :
    if not hasattr(fsFakto.place,'normalized') :
      #from objbrowser import browse ;browse(locals())
      print("lieu par normalisé : "+fsFakto.place.original)
      plantage()
    grLoko = akiriLokoPerId(db, fsFakto.place)
    if grLoko:
      grLokoHandle = grLoko.handle
    else :
      grLoko = aldLoko( db, txn, fsFakto.place)
      if grLoko :
        grLokoHandle = grLoko.handle
      
  fsFaktoPriskribo = fsFakto.value or ''
  fsFaktoDato = fsFakto.date or ''
  grDato = fsdato_al_gr(fsFakto.date)

  # serĉi ekzistanta per FSFTID
  for fakto in obj.event_ref_list :
    e = db.get_event_from_handle(fakto.ref)
    attr = get_fsftid(e)
    if attr == fsFakto.id :
      return e

  # serĉi ekzistanta per (tipo kaj dato) aux (tipo kaj …)
  for fakto in obj.event_ref_list :
    e = db.get_event_from_handle(fakto.ref)
    grTipo = int(e.type) or e.type
    if ( grTipo == evtType ) :
      if ( e.get_date_object() == grDato 
           and ( e.get_place_handle() == grLokoHandle or (not e.get_place_handle() and not grLokoHandle))
           and ( e.description == fsFaktoPriskribo or (not e.description and not fsFaktoPriskribo))
         ):
        return e
      elif ( ( e.get_date_object().is_empty() and not grDato)
           and ( e.get_place_handle() == grLokoHandle or (not e.get_place_handle() and not grLokoHandle))
           and ( e.description == fsFaktoPriskribo or (not e.description and not fsFaktoPriskribo))
         ) :
        return e
  event = Event()
  event.set_type( evtType )
  if grLokoHandle:
    event.set_place_handle( grLokoHandle )
  if grDato :
    event.set_date_object( grDato )
  event.set_description(fsFaktoPriskribo)
  if fsFakto.id :
    attr = Attribute()
    attr.set_type('_FSFTID')
    attr.set_value(fsFakto.id)
    event.add_attribute(attr)
  # noto
  for fsNoto in fsFakto.notes:
    noto = aldNoto(db, txn, fsNoto,event.note_list)
    event.add_note(noto.handle)
  db.add_event(event, txn)
  db.commit_event(event, txn)
  return event

def aldNomo(db, txn, fsNomo, grPerson):
  nomo = Name()
  if fsNomo.type == 'http://gedcomx.org/MarriedName' :
    nomo.set_type(NameType(NameType.MARRIED))
  elif fsNomo.type == 'http://gedcomx.org/AlsoKnownAs' :
    nomo.set_type(NameType(NameType.AKA))
  elif fsNomo.type == 'http://gedcomx.org/BirthName' :
    nomo.set_type(NameType(NameType.BIRTH))
  #elif fsNomo.type == 'http://gedcomx.org/NickName' :
  #elif fsNomo.type == 'http://gedcomx.org/AdoptiveName' :
  #elif fsNomo.type == 'http://gedcomx.org/FormalName' :
  #elif fsNomo.type == 'http://gedcomx.org/ReligiousName' :
  else :
    # FARINDAĴO : administri moknomojn ĝuste
    nomo.set_type(NameType(NameType.CUSTOM))
  nomo.set_first_name(fsNomo.akGiven())
  s = nomo.get_primary_surname()
  s.set_surname(fsNomo.akSurname())
  for fsNoto in fsNomo.notes :
    noto = aldNoto(db, txn, fsNoto,nomo.note_list)
    nomo.add_note(noto.handle)
  if fsNomo.preferred :
    grPerson.set_primary_name(nomo)
  else:
    grPerson.add_alternate_name(nomo)

def aldNomoj(db, txn, fsPersono, grPerson):
  for fsNomo in fsPersono.names :
    aldNomo(db, txn, fsNomo, grPerson)

def akFontDatoj(fsTree):
  # récupère les dates des sources, qui sont absentes des API
  for sd in fsTree.sourceDescriptions :
    if sd.id[:2] == 'SD' : # pas une vraie sourceDescription
      continue
    if hasattr(sd,'_date'):
      continue
    sd._date = None
    sd._collectionUri = None
    sd._collection = None
    
    r = tree._FsSeanco.get_url("https://www.familysearch.org/service/tree/links/source/%s" % sd.id,{"Accept": "application/json"})
    if r and r.text :
      datumoj = r.json()
      #print("akFonto : res="+str(datumoj))
      e = datumoj.get('event')
      if e:
        strFormal = e.get('eventDate')
        d= gedcomx_v1.Date()
        d.original=strFormal
        d.formal = gedcomx_v1.dateformal.DateFormal(strFormal)
        sd._date = d
      sd._collectionUri = datumoj.get('fsCollectionUri')
      if sd._collectionUri :
        sd._collection = sd._collectionUri.removeprefix('https://www.familysearch.org/platform/records/collections/')
      t = datumoj.get('title')
      if t :
        if len(sd.titles) :
          next(iter(sd.titles)).value = t
        else :
          fsTitolo = gedcomx_v1.TextValue()
          fsTitolo.value = t
          sd.titles.add(fsTitolo)
      u = datumoj.get('uri')
      if u :
        sd.about = u.get('uri')
      n = datumoj.get('notes')
      if len(sd.notes) :
        next(iter(sd.notes)).text = n
      else :
        fsNoto = gedcomx_v1.Note()
        fsNoto.text = n
        sd.notes.add(fsNoto)

#def aldFonto(db, txn, fsFonto, obj, EkzCit):
def aldFonto(db, txn, sdId, obj, EkzCit):
    # akiri SourceDescription
    sourceDescription = gedcomx_v1.SourceDescription._indekso.get(sdId)
    if not sourceDescription : return
    mFonto = MezaFonto()
    mFonto.deFS(sourceDescription,None)
    citation = mFonto.alGramps(db, txn, obj)
    
    return citation

class MezaFonto:
  # destinée à servir d'intermédiaire entre les classes gramps et gedcomx pour une citation gramps et une source FS
  # pour faciliter la comparaison
  # et pour faciliter la lecture du code
  #
  # attributs :
  # id = sourceDescription.id
  # deponejo = titre du dépôt gramps
  # sTitolo = titre de la source gramps
  # cTitolo = titre FS (--> première ligne note de type citation)
  # posizio = Vue/Page
  # konfido = niveau de confiance
  # url = URL
  # dato = date gedcomx.DateFormal
  # noto = note FS
  # kolekto = N° de collection FS
  # kolektoUrl = URL de la collection
  #filmo = N° de film FS
  #
  # méthodes :
  # def deFS(self, fsSD, fsSR): de FS vers MezaFonto
  # def alFS(self, fsSD, fsSR): de MezaFonto vers FS
  # def deGramps(self, db, citation): de gramps vers MezaFonto
  # def alGramps(self, db, txn, citation): de MezaFonto vers gramps
  #
  def deFS(self, fsSD, fsSR):
    self.id = fsSD.id
    self.deponejo = 'FamilySearch'
    self.sTitolo = 'FamilySearch'
    self.cTitolo = None
    self.posizio = None
    self.konfido = None
    self.url = fsSD.about
    self.dato = None
    self.noto = '\n'
    if hasattr(fsSD,'_collection') :
      self.kolekto = fsSD._collection
    else :
      self.kolekto = None
    if self.kolekto is not None :
      self.kolektoUrl = 'https://www.familysearch.org/search/collection/'+self.kolekto
    else:
      self.kolektoUrl = None
    if len(fsSD.titles):
      self.cTitolo = next(iter(fsSD.titles)).value
    FSCitation = None
    if len(fsSD.citations):
      FSCitation = next(iter(fsSD.citations)).value
    if fsSD.resourceType != 'FSREADONLY' and fsSD.resourceType != 'LEGACY' and fsSD.resourceType != 'DEFAULT' and fsSD.resourceType != 'IGI' :
      print(" Type de ressource inconnu !!! : "+str(fsSD.resourceType))
    if fsSD.resourceType == 'LEGACY':
      self.sTitolo='Legacy NFS Sources'
    #if fsSD.resourceType == 'FSREADONLY':
    if fsSD.resourceType != 'DEFAULT':
      self.deponejo = 'FamilySearch'
      if FSCitation :
        linioj = FSCitation.split("\"") 
        if len(linioj) >=3 :
          self.sTitolo = linioj[1]
          self.noto = self.noto + '\n'.join(linioj[2:])
    if len(fsSD.notes) :
      self.noto = next(iter(fsSD.notes)).text or ''
    if FSCitation and fsSD.resourceType == 'DEFAULT':
      linioj = FSCitation.split("\n") 
      for linio in linioj :
        if linio.startswith(_('Repository')):
          self.deponejo = linio.removeprefix(_('Repository')+" :").strip()
        elif linio.startswith(_('Source:')):
          self.sTitolo = linio.removeprefix(_('Source:')).strip()
        elif linio.startswith(_('Volume/Page:')):
          self.posizio = linio.removeprefix(_('Volume/Page:')).strip()
        elif linio.startswith(_('Confidence:')):
          self.konfido = linio.removeprefix(_('Confidence:')).strip()
      # FARINDAĴO : si rien de trouvé et langue de la source != langue en cours, ré-essayer avec la langue de la source
      # si pas trouvé de titre de source, on prend la première ligne
      if not self.sTitolo and  len(linioj) >=1 :
        self.sTitolo = linioj[0]
    if hasattr(fsSD,'_date') and fsSD._date:
      self.dato = fsSD._date

  def alFS(self, fsSD, fsSR):
    # fsSD est une gedcomx_v1.SourceDescription
    # fsSR est une gedcomx_v1.SourceReference
    fsSR.id = self.id
    fsSR.description = "https://api.familysearch.org/platform/sources/descriptions/"+self.id
    fsSD.id = self.id
    fsSD.titles.add(self.cTitolo)
    fsNoto = gedcomx_v1.Note()
    fsNoto.text = self.noto
    fsSD.notes.add(fsNoto)
    # about sera l'Adresse Internet
    fsSD.about = self.url
    # la référence sera : titre dépôt + titre source + volume/page + confiance --> référence
    referenco = _('Volume/Page:') +" "+ self.posizio
    if self.sTitolo :
      referenco = _('Source:') + " " + self.sTitolo + '\n' + referenco
      if self.deponejo :
        referenco = _('Repository')+" : " + self.deponejo + '\n' + referenco
    referenco = referenco + '\n' + _('Confidence:') +" " + self.konfido
    fsCitation = gedcomx_v1.SourceCitation
    fsCitation.value = referenco
    fsSD.citations.add(fsCitation)
    fsSD.event = dict()
    fsSD.event['eventDate']=str(self.dato)


  
  def deGramps(self, db, citation):
    self.id = utila.get_fsftid(citation)
    self.deponejo = None  #
    self.sTitolo = None  #
    self.cTitolo = None #
    self.posizio = citation.page
    self.konfido = None #
    self.url = utila.get_url(citation)
    strFormal = utila.grdato_al_formal(citation.date)
    self.dato = gedcomx_v1.dateformal.DateFormal(strFormal)
    self.noto = "" #
    self.kolekto = None
    self.kolektoUrl = None
    if citation.source_handle :
      s = db.get_source_from_handle(citation.source_handle)
      if s :
        self.sTitolo = s.title
        if len(s.reporef_list)>0 :
          dh = s.reporef_list[0].ref
          d = db.get_repository_from_handle(dh)
          if d :
            self.deponejo = d.name
    konfido = citation.get_confidence_level()
    if konfido == Citation.CONF_VERY_HIGH :
      self.konfido = _('Very High')
    elif konfido == Citation.CONF_HIGH :
      self.konfido = _('High')
    elif konfido == Citation.CONF_NORMAL :
      self.konfido = _('Normal')
    elif konfido == Citation.CONF_LOW :
      self.konfido = _('Low')
    elif konfido == Citation.CONF_VERY_LOW :
      self.konfido = _('Very Low')


    # on cherche la première note de type Citation,
    #   le titre sera la première ligne de cette note.
    nhTitolo = None
    for nh in citation.note_list :
      n = db.get_note_from_handle(nh)
      if n.type == NoteType.CITATION :
        nhTitolo = nh
        noto = n.get()
        posRet = noto.find("\n")
        if(posRet>0) :
          self.noto = noto[posRet+1:]
          self.noto = self.noto.strip(' \n')
          self.cTitolo = noto[:posRet]
        else :
          self.cTitolo = noto
        break
    # le texte sera la concaténation des notes
    for nh in citation.note_list :
      if nh == nhTitolo : continue
      n = db.get_note_from_handle(nh)
      self.noto += n.get()

  def alGramps(self, db, txn, obj):
    # obj = objet auquel il faut rattacher la source
    # création du dépôt si nécessaire :
    rh = None
    if self.deponejo :
      db.dbapi.execute("select handle from repository where name=?",[self.deponejo])
      datumoj = db.dbapi.fetchone()
      if datumoj and datumoj[0] :
        rh = datumoj[0]
      else :
        r = Repository()
        r.set_name(self.deponejo)
        rtype = RepositoryType()
        rtype.set((RepositoryType.WEBSITE))
        r.set_type(rtype)
        if self.deponejo == 'FamilySearch' :
          url = Url()
          url.path = 'https://www.familysearch.org/'
          url.set_type(UrlType.WEB_HOME)
          r.add_url(url)
        db.add_repository(r, txn)
        db.commit_repository(r,txn)
        rh = r.handle
    s = None
    if self.sTitolo and not s and self.kolekto :
      # recherche de la source par son numéro de collection
      s = db.get_source_from_gramps_id('FS_coll_'+self.kolekto)
    if not s and self.sTitolo :
      # recherche de la source par son titre
      db.dbapi.execute("select handle from source where title=?",[self.sTitolo])
      datumoj = db.dbapi.fetchone()
      if datumoj and datumoj[0] :
        sTmp = db.get_source_from_handle(datumoj[0])
        if self.deponejo :
          # FARINDAĴO
          s = sTmp
        else:
          s = sTmp
    if not s and self.sTitolo :
      # on crée la source
      s = Source()
      if self.kolekto :
        s.gramps_id = 'FS_coll_'+self.kolekto
      s.set_title(self.sTitolo)
      if self.kolekto :
        attr = SrcAttribute()
        attr.set_type(_('Internet Address'))
        attr.set_value(self.kolektoUrl)
        s.add_attribute(attr)
      db.add_source(s,txn)
      db.commit_source(s,txn)
      if rh :
        rr = RepoRef()
        rr.ref = rh
        rr.set_media_type( SourceMediaType.ELECTRONIC)
        s.add_repo_reference(rr)
      db.commit_source(s,txn)
    # sercxi ekzistantan
    trovita = False
    citation = None
    # sercxi ekzistantan kun id
    for ch in db.get_citation_handles() :
      c = db.get_citation_from_handle(ch)
      for attr in c.get_attribute_list():
        if attr.get_type() == '_FSFTID' and attr.get_value() == self.id :
          trovita = True
          citation = c
          print(" citation trouvée _FSFTID="+self.id)
          break
      if trovita : break
    ## sercxi ekzistantan citaĵon
    #for ch in obj.citation_list :
    #  c = db.get_citation_from_handle(ch)
    #  if get_fsftid(c) == self.id :
    #    # FARINDAĴO : ajouter la citation à l'objet si elle n'y est pas déjà
    #    # obj.add_citation(c.handle)
    #    return c
    if not citation :
      print(" citation pas trouvée _FSFTID="+self.id)
      citation = Citation()
      attr = SrcAttribute()
      attr.set_type('_FSFTID')
      attr.set_value(self.id)
      citation.add_attribute(attr)
      db.add_citation(citation,txn)
    if self.posizio :
      citation.set_page(self.posizio)
    if self.konfido :
      if self.konfido == _('Very High') :
        citation.set_confidence_level(Citation.CONF_VERY_HIGH)
      elif self.konfido == _('High') :
        citation.set_confidence_level(Citation.CONF_HIGH)
      elif self.konfido == _('Normal') :
        citation.set_confidence_level(Citation.CONF_NORMAL)
      elif self.konfido == _('Low') :
        citation.set_confidence_level(Citation.CONF_LOW)
      elif self.konfido == _('Very Low') :
        citation.set_confidence_level(Citation.CONF_VERY_LOW)
    if self.dato:
      citation.date = fsdato_al_gr(self.dato)
    if s :
      citation.set_reference_handle(s.get_handle())
    if self.url :
      u0 = utila.get_url(citation)
      if not u0 :
        attr = SrcAttribute()
        attr.set_type(_("Internet Address"))
        attr.set_value(self.url)
        citation.add_attribute(attr)
    db.commit_citation(citation,txn)
    if self.cTitolo or len(self.noto) :
      note = None
      for nh in citation.note_list :
        n = db.get_note_from_handle(nh)
        if n.type == NoteType.CITATION :
          note = n
      if not note :
        n = Note()
        tags=[]
        n.set_type(NoteType(NoteType.CITATION))
        n.append(self.cTitolo or '')
        n.append('\n\n')
        tags.append(StyledTextTag(StyledTextTagType.BOLD, True,[(0, len(self.cTitolo))]))
        n.append(self.noto or '')
        n.text.set_tags(tags)
        db.add_note(n, txn)
        db.commit_note(n, txn)
        citation.add_note(n.handle)
    db.commit_citation(citation,txn)
    # voir si la citation n'est pas déjà associée.
    for ch in obj.citation_list :
      if ch == citation.handle :
        return citation
    obj.add_citation(citation.handle)
    return citation


class FsAlGr:
  # 
  fs_TreeImp = None
  active_handle = None
  # opcionoj
  nereimporti = False
  asc = 1
  desc = 1
  edz = True
  notoj = False
  fontoj = False
  vorteco = 0
  aldonaPersono = False
  refresxigxo = True
  def __init__(self) :
    self.nereimporti = False
    self.asc = 1
    self.desc = 1
    self.edz = True
    self.notoj = False
    self.fontoj = False
    self.vorteco = 0
    self.aldonaPersono = False
    self.refresxigxo = True
  def aldPersono(self, db, txn, fsPersono):
    fsid = fsPersono.id
    grPersonoHandle = utila.fs_gr.get(fsid)
    if not grPersonoHandle:
      grPerson = Person()
      aldNomoj( db, txn, fsPersono, grPerson)
      if not fsPersono.gender :
        grPerson.set_gender(Person.UNKNOWN)
      elif fsPersono.gender.type == "http://gedcomx.org/Male" :
        grPerson.set_gender(Person.MALE)
      elif fsPersono.gender.type == "http://gedcomx.org/Female" :
        grPerson.set_gender(Person.FEMALE)
      else :
        grPerson.set_gender(Person.UNKNOWN)
      # attr = Attribute()
      # attr.set_type('_FSFTID')
      # attr.set_value(fsid)
      # grPerson.add_attribute(attr)
      db.add_person(grPerson,txn)
      self.aldonaPersono = True
      utila.ligi_gr_fs(db,grPerson,fsid)
      # db.commit_person(grPerson,txn)
      utila.fs_gr[fsid] = grPerson.handle
    else :
      if self.nereimporti :
        return
      grPerson = db.get_person_from_handle(grPersonoHandle)
  
    # faktoj
    for fsFakto in fsPersono.facts:
      event = aldFakto(db, txn, fsFakto,grPerson)
      found = False
      for er in grPerson.get_event_ref_list():
        if er.ref == event.handle:
          found = True
          break
      if not found:
        er = EventRef()
        er.set_role(EventRoleType.PRIMARY)
        er.set_reference_handle(event.get_handle())
        db.commit_event(event, txn)
        grPerson.add_event_ref(er)
      if event.type == EventType.BIRTH :
        grPerson.set_birth_ref(er)
      elif event.type == EventType.DEATH :
        grPerson.set_death_ref(er)
      db.commit_person(grPerson,txn)
    # notoj
    for fsNoto in fsPersono.notes :
      noto = aldNoto(db, txn, fsNoto,grPerson.note_list)
      grPerson.add_note(noto.handle)
    # fontoj
    for fsFonto in fsPersono.sources :
      c = aldFonto(db, txn, fsFonto.descriptionId,grPerson,grPerson.citation_list)
      #db.commit_person(grPerson,txn)
    # FARINDAĴOJ : memoroj
    #for fsMemoro in fsPersono.memories :
      #print("memorie :")
      #print(fsMemoro)
      #m = Media()
      #m.path = fsMemoro.url
      #m.desc = fsMemoro.description
      #db.add_media(m, txn)
      #db.commit_media(m, txn)
      #citation = Citation()
      #citation.set_reference_handle(m.get_handle())
      #db.add_citation(citation,txn)
      #db.commit_citation(citation,txn)
      #grPerson.add_citation(citation.handle)
      #continue
      
    komparo.kompariFsGr(fsPersono,grPerson,db,None)
    db.commit_person(grPerson,txn)
  
  def importi( self, vokanto, FSFTID):

    print("import ID :"+FSFTID)
    self.FS_ID = FSFTID
    self.dbstate = vokanto.dbstate
    # Progresa stango
    progress = ProgressMeter(_("FamilySearch Importo"), _trans.gettext('Starting'),
                                      parent=vokanto.uistate.window)
    vokanto.uistate.set_busy_cursor(True)
    if self.refresxigxo :
      vokanto.dbstate.db.disable_signals()
    cnt=0
    # sercxi ĉi tiun numeron en «gramps».
    # kaj plenigas fs_gr vortaro.
    if not PersonFS.PersonFS.aki_sesio(vokanto,self.vorteco):
      WarningDialog(_('Ne konekta al FamilySearch'))
      return
    if not utila.fs_gr :
      utila.konstrui_fs_gr(vokanto,progress,11)
    #if not tree._FsSeanco:
    #  if PersonFS.PersonFS.fs_sn == '' or PersonFS.PersonFS.fs_pasvorto == '':
    #    import locale, os
    #    vokanto.top = Gtk.Builder()
    #    vokanto.top.set_translation_domain("addon")
    #    base = os.path.dirname(__file__)
    #    locale.bindtextdomain("addon", base + "/locale")
    #    glade_file = base + os.sep + "PersonFS.PersonFS.glade"
    #    vokanto.top.add_from_file(glade_file)
    #    top = vokanto.top.get_object("PersonFSPrefDialogo")
    #    top.set_transient_for(vokanto.uistate.window)
    #    parent_modal = vokanto.uistate.window.get_modal()
    #    if parent_modal:
    #      vokanto.uistate.window.set_modal(False)
    #    fsid = vokanto.top.get_object("fsid_eniro")
    #    fsid.set_text(PersonFS.PersonFS.fs_sn)
    #    fspv = vokanto.top.get_object("fspv_eniro")
    #    fspv.set_text(PersonFS.PersonFS.fs_pasvorto)
    #    top.show()
    #    res = top.run()
    #    print ("res = " + str(res))
    #    top.hide()
    #    if res == -3:
    #      PersonFS.PersonFS.fs_sn = fsid.get_text()
    #      PersonFS.PersonFS.fs_pasvorto = fspv.get_text()
    #      PersonFS.CONFIG.set("preferences.fs_sn", PersonFS.PersonFS.fs_sn)
    #      #PersonFS.CONFIG.set("preferences.fs_pasvorto", PersonFS.PersonFS.fs_pasvorto) #
    #      PersonFS.CONFIG.save()
    #      if self.vorteco >= 3:
    #        tree._FsSeanco = gedcomx_v1.FsSession(PersonFS.PersonFS.fs_sn, PersonFS.PersonFS.fs_pasvorto, True, False, 2)
    #      else :
    #        tree._FsSeanco = gedcomx_v1.FsSession(PersonFS.PersonFS.fs_sn, PersonFS.PersonFS.fs_pasvorto, False, False, 2)
    #    else :
    #      print("Vi devas enigi la ID kaj pasvorton")
    #  else:
    #    if self.vorteco >= 3:
    #      tree._FsSeanco = gedcomx_v1.FsSession(PersonFS.PersonFS.fs_sn, PersonFS.PersonFS.fs_pasvorto, True, False, 2)
    #    else :
    #      tree._FsSeanco = gedcomx_v1.FsSession(PersonFS.PersonFS.fs_sn, PersonFS.PersonFS.fs_pasvorto, False, False, 2)
    print("importo")
    if self.fs_TreeImp:
      del self.fs_TreeImp
    self.fs_TreeImp = tree.Tree()
    # Legi la personojn en «FamilySearch».
    progress.set_pass(_('Elŝutante personojn… (3/11)'), mode= ProgressMeter.MODE_ACTIVITY)
    print(_("Elŝutante personon…"))
    if self.FS_ID:
      self.fs_TreeImp.add_persons([self.FS_ID])
    else : return
    progress.set_pass(_('Elŝutante ascendantojn… (4/11)'),self.asc)
    # ascendante
    todo = set(self.fs_TreeImp._persons.keys())
    done = set()
    for i in range(self.asc):
      progress.step()
      if not todo:
        break
      done |= todo
      print( _("Elŝutante %d generaciojn de ascendantojn…") % (i + 1))
      todo = self.fs_TreeImp.add_parents(todo) - done
    # descendante
    progress.set_pass(_('Elŝutante posteulojn… (5/11)'),self.desc)
    todo = set(self.fs_TreeImp._persons.keys())
    done = set()
    for i in range(self.desc):
      progress.step()
      if not todo:
        break
      done |= todo
      print( _("Elŝutante %d generaciojn de posteulojn…") % (i + 1))
      todo = self.fs_TreeImp.add_children(todo) - done
    # edzoj
    if self.desc and not self.edz:
      print("posteuloj elŝutantaj : devigi elŝutanto de edzoj ")
      self.edz = True
    if self.edz :
      progress.set_pass(_('Elŝutante edzojn… (6/11)'), mode= ProgressMeter.MODE_ACTIVITY)
      print(_("Elŝutante edzojn…"))
      todo = set(self.fs_TreeImp._persons.keys())
      self.fs_TreeImp.add_spouses(todo)
    # notoj , fontoj kaj memoroj
    if self.notoj or self.fontoj:
      progress.set_pass(_('Elŝutante notojn… (7/11)'),len(self.fs_TreeImp.persons)+len(self.fs_TreeImp.relationships))
      print(_("Elŝutante notojn kaj fontojn…"))
      for fsPersono in self.fs_TreeImp.persons :
        progress.step()
        datumoj = tree._FsSeanco.get_jsonurl("/platform/tree/persons/%s/notes" % fsPersono.id)
        gedcomx_v1.maljsonigi(self.fs_TreeImp,datumoj)
        datumoj = tree._FsSeanco.get_jsonurl("/platform/tree/persons/%s/sources" % fsPersono.id)
        gedcomx_v1.maljsonigi(self.fs_TreeImp,datumoj)
        datumoj = tree._FsSeanco.get_jsonurl("/platform/tree/persons/%s/memories" % fsPersono.id)
        gedcomx_v1.maljsonigi(self.fs_TreeImp,datumoj)
        akFontDatoj(self.fs_TreeImp)
      for fsFam in self.fs_TreeImp.relationships :
        progress.step()
        datumoj = tree._FsSeanco.get_jsonurl("/platform/tree/couple-relationships/%s/notes" % fsFam.id)
        gedcomx_v1.maljsonigi(self.fs_TreeImp,datumoj)
        datumoj = tree._FsSeanco.get_jsonurl("/platform/tree/couple-relationships/%s/sources" % fsFam.id)
        gedcomx_v1.maljsonigi(self.fs_TreeImp,datumoj)
        akFontDatoj(self.fs_TreeImp)
    if self.vorteco >= 3:
      rezulto = gedcomx_v1.jsonigi(self.fs_TreeImp)
      f = open('importo.out.json','w')
      json.dump(rezulto,f,indent=2)
      f.close()

    print(_("Importado…"))
    # FamilySearch ŝarĝo kompleta
    # Komenco de importo
    # krei datumbazan tabelon
    fs_db.create_schema(vokanto.dbstate.db)
    if PersonFS.PersonFS.fs_etikedado :
      fs_db.create_tags(self.dbstate.db)
    self.aldonaPersono = False
    if vokanto.dbstate.db.transaction is not None :
      intr = True
      self.txn = vokanto.dbstate.db.transaction
    else :
      intr = False
      self.txn = DbTxn("FamilySearch import", vokanto.dbstate.db)
      vokanto.dbstate.db.transaction_begin(self.txn)
    #with DbTxn("FamilySearch import", vokanto.dbstate.db) as txn:
    if True :
      # importi lokoj
      progress.set_pass(_('Importado de lokoj… (8/11)'),len(self.fs_TreeImp.places))
      print(_("Importado de lokoj…"))
      for pl in self.fs_TreeImp.places :
        progress.step()
        aldLoko( vokanto.dbstate.db, self.txn, pl)
      progress.set_pass(_('Importado de personoj… (9/11)'),len(self.fs_TreeImp.persons))
      print(_("Importado de personoj…"))
      # importi personoj
      for fsPersono in self.fs_TreeImp.persons :
        progress.step()
        self.aldPersono(vokanto.dbstate.db, self.txn, fsPersono)
      progress.set_pass(_('Importado de familioj… (10/11)'),len(self.fs_TreeImp.relationships))
      print(_("Importado de familioj…"))
      # importi familioj
      for fsFam in self.fs_TreeImp.relationships :
        progress.step()
        if fsFam.type == 'http://gedcomx.org/Couple':
          self.aldFamilio(fsFam)
      progress.set_pass(_('Importado de infanoj… (11/11)'),len(self.fs_TreeImp.relationships))
      print(_("Importado de infanoj…"))
      # importi infanoj
      for fsCpr in self.fs_TreeImp.childAndParentsRelationships :
        progress.step()
        self.aldInfano(fsCpr)
    if not intr :
      vokanto.dbstate.db.transaction_commit(self.txn)
      del self.txn
    self.txn = None
    print("import fini.")
    vokanto.uistate.set_busy_cursor(False)
    progress.close()
    if self.refresxigxo :
      vokanto.dbstate.db.enable_signals()
#   FARINDAĴO : 
      if self.aldonaPersono :
        vokanto.dbstate.db.request_rebuild()

  def aldInfano(self,fsCpr):
    if fsCpr.parent1:
      grPatroHandle = utila.fs_gr.get(fsCpr.parent1.resourceId)
    else:
      grPatroHandle = None
    if fsCpr.parent2:
      grPatrinoHandle = utila.fs_gr.get(fsCpr.parent2.resourceId) 
    else:
      grPatrinoHandle = None
    familio = None
    if grPatroHandle :
      grPatro = self.dbstate.db.get_person_from_handle(grPatroHandle)
      if grPatrinoHandle :
        grPatrino = self.dbstate.db.get_person_from_handle(grPatrinoHandle)
      else :
        grPatrino = None
      for family_handle in grPatro.get_family_handle_list():
        if not family_handle: continue
        f = self.dbstate.db.get_family_from_handle(family_handle)
        if f.get_mother_handle() == grPatrinoHandle :
          familio = f
          break
    elif grPatrinoHandle :
      grPatro = None
      grPatrino = self.dbstate.db.get_person_from_handle(grPatrinoHandle)
      for family_handle in grPatrino.get_family_handle_list():
        if not family_handle: continue
        f = self.dbstate.db.get_family_from_handle(family_handle)
        if f.get_father_handle() == None :
          familio = f
          break
    else:
      print(_('sengepatra familio ???'))
      return
    if not grPatro and fsCpr.parent1 and fsCpr.parent1.resourceId: return
    if not grPatrino and fsCpr.parent2 and fsCpr.parent2.resourceId: return
    if not familio :
      familio = Family()
      familio.set_father_handle(grPatroHandle)
      familio.set_mother_handle(grPatrinoHandle)
      self.dbstate.db.add_family(familio, self.txn)
      self.dbstate.db.commit_family(familio, self.txn)
      if grPatro:
        grPatro.add_family_handle(familio.get_handle())
        self.dbstate.db.commit_person(grPatro, self.txn)
      if grPatrino:
        grPatrino.add_family_handle(familio.get_handle())
        self.dbstate.db.commit_person(grPatrino, self.txn)
    infanoHandle = utila.fs_gr.get(fsCpr.child.resourceId)
    if not infanoHandle: return
    found = False
    for cr in familio.get_child_ref_list() :
      if cr.get_reference_handle() == infanoHandle:
        found = True
        break
    if not found :
      childref = ChildRef()
      childref.set_reference_handle(infanoHandle)
      familio.add_child_ref(childref)
      self.dbstate.db.commit_family(familio, self.txn)
      infano = self.dbstate.db.get_person_from_handle(infanoHandle)
      infano.add_parent_family_handle(familio.get_handle())
      self.dbstate.db.commit_person(infano, self.txn)

  def aldFamilio(self,fsFam):
    familio = None
    grPatroHandle = utila.fs_gr.get(fsFam.person1.resourceId)
    if grPatroHandle :
      grPatro = self.dbstate.db.get_person_from_handle(grPatroHandle)
    else :
      grPatro = None
    grPatrinoHandle = utila.fs_gr.get(fsFam.person2.resourceId) 
    if grPatrinoHandle :
      grPatrino = self.dbstate.db.get_person_from_handle(grPatrinoHandle)
    else :
      grPatrino = None
    f_fsid = None
    if grPatroHandle :
      for family_handle in grPatro.get_family_handle_list():
        if not family_handle: continue
        f = self.dbstate.db.get_family_from_handle(family_handle)
        if f.get_mother_handle() == grPatrinoHandle :
          familio = f
          break
        f_fsid = get_fsftid(f)
        if f_fsid == fsFam.id :
          familio = f
          break
    if not familio and grPatrinoHandle :
      for family_handle in grPatrino.get_family_handle_list():
        if not family_handle: continue
        f = self.dbstate.db.get_family_from_handle(family_handle)
        if f.get_father_handle() == grPatroHandle :
          familio = f
          break
        f_fsid = get_fsftid(f)
        if f_fsid == fsFam.id :
          familio = f
          break
    if not grPatroHandle and not grPatrinoHandle :
      print(_('sengepatra familio ???'))
      return
    if familio and not familio.get_father_handle() and grPatroHandle :
      familio.set_father_handle(grPatroHandle)
      grPatro.add_family_handle(familio.get_handle())
      self.dbstate.db.commit_person(grPatro, self.txn)
    if familio and not familio.get_mother_handle() and grPatrinoHandle :
      familio.set_mother_handle(grPatrinoHandle)
      grPatrino.add_family_handle(familio.get_handle())
      self.dbstate.db.commit_person(grPatrino, self.txn)
    if not grPatro and fsFam.person1.resourceId:
       return
    if not grPatrino and fsFam.person2.resourceId:
       return
    if not familio :
      familio = Family()
      familio.set_father_handle(grPatroHandle)
      familio.set_mother_handle(grPatrinoHandle)
      attr = Attribute()
      attr.set_type('_FSFTID')
      attr.set_value(fsFam.id)
      familio.add_attribute(attr)
      self.dbstate.db.add_family(familio, self.txn)
      self.dbstate.db.commit_family(familio, self.txn)
      if grPatro:
        grPatro.add_family_handle(familio.get_handle())
        self.dbstate.db.commit_person(grPatro, self.txn)
      if grPatrino:
        grPatrino.add_family_handle(familio.get_handle())
        self.dbstate.db.commit_person(grPatrino, self.txn)
    # familiaj faktoj
    for fsFakto in fsFam.facts:
      event = aldFakto(self.dbstate.db, self.txn, fsFakto,familio)
      found = False
      for er in familio.get_event_ref_list():
        if er.ref == event.handle:
          found = True
          break
      if not found:
        er = EventRef()
        er.set_role(EventRoleType.FAMILY)
        er.set_reference_handle(event.get_handle())
        self.dbstate.db.commit_event(event, self.txn)
        familio.add_event_ref(er)
      
    self.dbstate.db.commit_family(familio,self.txn)

    # notoj
    for fsNoto in fsFam.notes :
      noto = aldNoto(self.dbstate.db, self.txn, fsNoto,familio.note_list)
      familio.add_note(noto.handle)
    # fontoj
    for fsFonto in fsFam.sources :
      c = aldFonto(self.dbstate.db, self.txn, fsFonto.descriptionId,familio,familio.citation_list)
      #familio.add_citation(c.handle)
    # FARINDAĴOJ : FS ID
    self.dbstate.db.commit_family(familio,self.txn)
    return


class FSImportoOpcionoj(MenuToolOptions):
  """
  " 
  """
  def __init__(self, name, person_id=None, dbstate=None):
    """
    " 
    """
    if vorteco >= 3:
      print(_("Kromprogramoj"))
    MenuToolOptions.__init__(self, name, person_id, dbstate)

  def add_menu_options(self, menu):
    """
    " 
    """
    category_name = _("FamilySearch Importo Opcionoj")
    self.__FS_ID = StringOption(_("FamilySearch ID"), 'XXXX-XXX')
    self.__FS_ID.set_help(_("identiga numero por esti prenita de FamilySearch retejo"))
    menu.add_option(category_name, "FS_ID", self.__FS_ID)
    self.__gui_asc = NumberOption(_("Nombro ascentontaj"), 0, 0, 99)
    self.__gui_asc.set_help(_("Nombro de generacioj por supreniri"))
    menu.add_option(category_name, "gui_asc", self.__gui_asc)
    self.__gui_desc = NumberOption(_("Nombro descendontaj"), 0, 0, 99)
    self.__gui_desc.set_help(_("Nombro de generacioj descendontaj"))
    menu.add_option(category_name, "gui_desc", self.__gui_desc)
    self.__gui_nereimporti = BooleanOption(_("Ne reimporti ekzistantajn personojn"), True)
    self.__gui_nereimporti.set_help(_("Importi nur neekzistantajn personojn"))
    menu.add_option(category_name, "gui_nereimporti", self.__gui_nereimporti)
    self.__gui_edz = BooleanOption(_("Aldoni geedzoj"), False)
    self.__gui_edz.set_help(_("Aldoni informojn pri geedzoj"))
    menu.add_option(category_name, "gui_edz", self.__gui_edz)
    self.__gui_fontoj = BooleanOption(_("Aldoni fontoj"), False)
    self.__gui_fontoj.set_help(_("Aldoni fontoj"))
    menu.add_option(category_name, "gui_fontoj", self.__gui_fontoj)
    self.__gui_notoj = BooleanOption(_("Aldoni notoj"), False)
    self.__gui_notoj.set_help(_("Aldoni notoj"))
    menu.add_option(category_name, "gui_notoj", self.__gui_notoj)
    self.__gui_vort = NumberOption(_("Vorteco"), 0, 0, 3)
    self.__gui_vort.set_help(_("Vorteca nivelo de 0 (minimuma) ĝis 3 (tre vorta)"))
    menu.add_option(category_name, "gui_vort", self.__gui_vort)

    if vorteco >= 3:
      print(_("Menuo Aldonita"))
  def load_previous_values(self):
    MenuToolOptions.load_previous_values(self)
    if PersonFS.PersonFS.FSID :
      self.handler.options_dict['FS_ID'] = PersonFS.PersonFS.FSID
    return

class FSImporto(PluginWindows.ToolManagedWindowBatch):
  """
  " 
  """
  def __init__(self, dbstate, user, options_class, name, callback):
    """
    " 
    """
    self.uistate = user.uistate
    PluginWindows.ToolManagedWindowBatch.__init__(self, dbstate, user, options_class, name, callback)

  def get_title(self):
    """
    " 
    """
    return _("FamilySearch Import Tool")  # tool window title

  def initial_frame(self):
    """
    " 
    """
    return _("FamilySearch Importo Opcionoj")  # tab title

  #@profile
  def run(self):
  #import cProfile
  #  cProfile.runctx('self.run2()',globals(),locals())
  #def run2(self):
    """
    " 
    """
    if not PersonFS.PersonFS.fs_Tree:
      PersonFS.PersonFS.fs_Tree = tree.Tree()
      PersonFS.PersonFS.fs_Tree._getsources = False
    importilo = FsAlGr()
    self.__get_menu_options(importilo)
    active_handle = self.uistate.get_active('Person')
    importilo.importi(self,self.FS_ID)
    self.window.hide()
    if active_handle :
      self.uistate.set_active(active_handle, 'Person')

  def __get_menu_options(self,importilo):
    menu = self.options.menu
    self.FS_ID = menu.get_option_by_name('FS_ID').get_value()
    importilo.asc = menu.get_option_by_name('gui_asc').get_value()
    importilo.desc = menu.get_option_by_name('gui_desc').get_value()
    importilo.edz = menu.get_option_by_name('gui_edz').get_value()
    importilo.notoj = menu.get_option_by_name('gui_notoj').get_value()
    importilo.fontoj = menu.get_option_by_name('gui_fontoj').get_value()
    importilo.nereimporti = menu.get_option_by_name('gui_nereimporti').get_value()
    importilo.vorteco = menu.get_option_by_name('gui_vort').get_value()

