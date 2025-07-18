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
GeneaNet Gramplet : fonctions d'import
"""

#-------------------------------------------------------------------------

import pickle

from gramps.gen.lib import Citation, Event, EventRef, EventRoleType, EventType, Name, NameType
from gramps.gen.lib import Note, NoteType, Person, Place, PlaceName, PlaceRef, RepoRef
from gramps.gen.lib import Repository, RepositoryType, Source, SourceMediaType, SrcAttribute
from gramps.gen.lib import Url, UrlType
from gramps.gen.lib.date import Today
from gramps.plugins.tool.changenames import ChangeNames
from gramps.gen.datehandler import LANG_TO_PARSER
from gramps.version import VERSION_TUPLE

from gn_constants import GN_GRAMPS_FAKTOJ, _
from geneanet import id2url
from NoteGN import convertToStyled

parserEn = LANG_TO_PARSER['en']()

def aldNomo(gr_persono, ext_nomo, ext_anomo):
  """ ajoute le nom «ext_nomo, ext_anomo» à la personne gr_persono """
  nomo = Name()
  nomo.set_type(NameType(NameType.BIRTH))
  nomo.set_first_name(ext_anomo)
  s = nomo.get_primary_surname()
  s.set_surname(ext_nomo)
  gr_persono.set_primary_name(nomo)


def aldNomoj(ext_persono, gr_persono):
  """ ajoute les noms à la personne """
  extNomo = ChangeNames.name_cap(None, ext_persono['person'].get('lastname'))
  extANomo = ext_persono['person'].get('firstname')
  aldNomo(gr_persono, extNomo, extANomo)
  # FARINDAĴO : ajouter les autres noms


def getPlaceFromTitoloV5(db, titolo, parento) -> Place:
  """ gramps < 6.0 : renvoie le lieu correspondant à titolo et fils ou petit-fils de parento """
  db.dbapi.execute(f'SELECT blob_data FROM place WHERE title = {titolo.strip(" ,")}')
  while True:
    row = db.dbapi.fetchone()
    if not row:
      break
    place = Place.create(pickle.loads(row[0]))
    if not parento:
      return place
    # ce lieu est-il un fils de parento ?
    rl = place.get_placeref_list()
    for pr in rl:
      if pr.ref == parento.handle:
        return place
    # ce lieu est-il un petit-fils de parento ?
    for pr in rl:
      p2 = db.get_place_from_handle(pr.ref)
      rl2 = p2.get_placeref_list()
      for pr2 in rl2:
        if pr2.ref == parento.handle:
          return place
  return None


def getPlaceFromTitolo(db, titolo, parento) -> Place:
  """ renvoie le lieu correspondant à titolo et fils ou petit-fils de parento """
  if VERSION_TUPLE < (6, 0, 0):
    return getPlaceFromTitoloV5(db, titolo, parento)
  db.dbapi.execute(
      f"SELECT {db.serializer.data_field} FROM place WHERE title = ?",
      [titolo.strip(" ,")],
  )
  while True:
    row = db.dbapi.fetchone()
    if not row:
      break
    datoj = db.serializer.string_to_data(row[0])
    if not parento:
      return datoj
    # ce lieu est-il un fils de parento ?
    rl = datoj.get('placeref_list')
    for pr in rl:
      if pr.get('ref') == parento.handle:
        return datoj
    # ce lieu est-il un petit-fils de parento ?
    for pr in rl:
      p2 = db.get_place_from_handle(pr.get('ref'))
      rl2 = p2.get_placeref_list()
      for pr2 in rl2:
        if pr2.ref == parento.handle:
          return datoj
  return None


def akiriLoko(nov_lokoj, db, txn, nomo):
  """ essaie de trouver le lieu nomo dans la base, ou le crée.
  "   retour : le lieu trouvé ou créé
  """
  #print("akiriLoko : %s" % nomo)
  if nomo is None or nomo.strip() == '':
    return None
  # le format de lieu recommandé par geneanet est :
  #    «[Lieu-dit, paroisse, abréviation] - Commune, code ville (INSEE ou postal - facultatif)
  #     , Sous-région (Département), Région (facultatif), Pays»
  # on va donc couper le nom selon les virgules, et le premier élément selon le '-'
  partoj = nomo.split(',')
  lieudit = None
  if partoj[0].find(' - ') >= 0:  # on a un lieu-dit
    x = partoj[0].split(' - ')
    lieudit = x[0].strip(" [](),")
    partoj[0] = x[1].strip(" [](),")
    partoj.insert(0, lieudit)
  partoj2 = []
  for x in partoj:  # suppression et mise de côté d'un éventuel code, suppression des chaînes vides
    if x.strip(" [](),").isdecimal():
      #kodo = int(x.strip(" [](),"))
      continue
    if x.strip(" [](),") == '':
      continue
    partoj2.append(x.strip(" [](),0123456789-"))
  # on cherche la hiérarchie du lieu
  parento = loko = None
  aTraiter = partoj2.copy()
  while aTraiter:
    nomo = aTraiter.pop()
    loko = getPlaceFromTitolo(db, nomo, parento)
    if loko:
      parento = loko
      continue
    # suite de la hiérarchie pas trouvée, on s'arrête là
    aTraiter.append(nomo)  # on remet le lieu non trouvé dans aTraiter
    nomo = ','.join(aTraiter)  # on concatène tout ce qui reste dans aTraiter
    # si on a déjà un lieu avec ce nom, on le prend :
    loko = getPlaceFromTitolo(db, nomo, None)
    if loko:
      return loko
    # sinon on le crée :
    loko = Place()
    placeName = PlaceName()
    placeName.set_value(nomo)
    loko.set_name(placeName)
    loko.set_title(nomo)
    if parento is not None:
      placeref = PlaceRef()
      placeref.set_reference_handle(parento.handle)
      loko.add_placeref(placeref)
    db.add_place(loko, txn)
    db.commit_place(loko, txn)
    nov_lokoj[loko.gramps_id] = nomo
    break
  return loko


def htmlAlStyled(teksto):
  """ convertit un tekte html en texte «Styled» """
  teksto = teksto.replace('<p>\n', '')
  teksto = teksto.replace('<p>', '')
  teksto = teksto.replace('</p>\n', '')
  teksto = teksto.replace('</p>', '')
  teksto = teksto.replace('<br>\n', '\n')
  return convertToStyled(teksto)


def updFakto(nov_lokoj, db, txn, gr_event, ext_fakto):
  """ met à jour gr_event depuis ext_fakto """
  dato = ext_fakto.get('dateLong')
  loko = ext_fakto.get('place')
  if dato:
    grDato = parserEn.parse(dato)
    if grDato:
      gr_event.set_date_object(grDato)
  # on ne copie le lieu que s'il est vide
  loko1H = gr_event.get_place_handle()
  if (loko1H or '') == '':
    if loko:
      grLoko = akiriLoko(nov_lokoj, db, txn, loko)
      gr_event.set_place_handle(grLoko.handle)
  db.commit_event(gr_event, txn)


def aldFakto(nov_lokoj, db, txn, ext_persono, ext_fakto):
  """ copie ext_fakto dans un event gramps et le retourne """
  event = Event()
  evtType = GN_GRAMPS_FAKTOJ.get(ext_fakto.get('type'))
  if not evtType:
    evtType = ext_fakto.get('type')
  event.set_type(evtType)
  db.add_event(event, txn)
  db.commit_event(event, txn)
  updFakto(nov_lokoj, db, txn, event, ext_fakto)
  teksto = _('okazaĵo importita el la geneanet-dosiero je la %s') % str(Today())
  citation = aldCitajxo(db, txn, ext_persono, ext_fakto, teksto)
  event.add_citation(citation.get_handle())
  db.commit_event(event, txn)
  return event

def _akiDeponejo(db, txn):
  """ récupération ou création du dépôt geneanet : """
  db.dbapi.execute("select handle from repository where name=?", ['geneanet'])
  datumoj = db.dbapi.fetchone()
  if datumoj and datumoj[0]:
    rh = datumoj[0]
  else:
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
    db.commit_repository(r, txn)
    rh = r.handle
  return rh

def aldCitajxo(db, txn, ext_persono, ext_objekto, teksto):
  """ crée une citation """
  if hasattr(ext_persono, 'grFonto'):
    s = ext_persono['grFonto']
  else:
    # récupération ou création de la source geneanet/arbre
    basePrefix = ext_persono['person'].get('baseprefix')
    db.dbapi.execute("select handle from source where gramps_id=?", [f'geneanet_{basePrefix}'])
    datumoj = db.dbapi.fetchone()
    s = None
    while datumoj and datumoj[0]:
      s = db.get_source_from_handle(datumoj[0])
      break
      #datumoj = db.dbapi.fetchone()
    if not s:
      # récupération ou création du dépôt geneanet :
      s = Source()
      s.gramps_id = f'geneanet_{basePrefix}'
      s.set_title(_(f'arbre geneanet {basePrefix}'))
      attr = SrcAttribute()
      attr.set_type(_('Internet Address'))
      attr.set_value(f"https://gw.geneanet.org/{basePrefix}")
      s.add_attribute(attr)
      rr = RepoRef()
      rr.ref = _akiDeponejo(db, txn)
      rr.set_media_type(SourceMediaType.ELECTRONIC)
      s.add_repo_reference(rr)
      db.add_source(s, txn)
      db.commit_source(s, txn)
    # on met de coté la source pour la suite :
    ext_persono['grFonto'] = s
  # création d'une citation
  citation = Citation()
  citation.set_confidence_level(Citation.CONF_LOW)
  attr = SrcAttribute()
  attr.set_type(_("Internet Address"))
  url = id2url(ext_persono)
  attr.set_value(url)
  citation.add_attribute(attr)
  citation.set_reference_handle(s.get_handle())
  db.add_citation(citation, txn)
  db.commit_citation(citation, txn)
  n = Note()
  n.set_type(NoteType(NoteType.CITATION))
  src = ext_objekto.get('src')
  if src:
    st = htmlAlStyled(teksto + '<br><br>' + src)
    n.set_styledtext(st)
  else:
    n.set(teksto)
  db.add_note(n, txn)
  db.commit_note(n, txn)
  citation.add_note(n.handle)
  db.commit_citation(citation, txn)
  return citation

class Importi:
  """ classe chargé de l'import des données geneanet dans gramps """
  def __init__(self,db,txn,progress,gn_notoj):
    self.db = db
    self.txn = txn
    self.progress = progress
    self.gn_notoj = gn_notoj

  def ald_persono(self, nov_lokoj, ext_persono):
    """ ajout de la personne ext_persono dans gramps """
    grPerson = Person()
    aldNomoj(ext_persono, grPerson)
    s = ext_persono['person'].get('sex')
    if s == 'MALE':
      grPerson.set_gender(Person.MALE)
    elif s == 'FEMALE':
      grPerson.set_gender(Person.FEMALE)
    else:
      grPerson.set_gender(Person.UNKNOWN)
    self.db.add_person(grPerson, self.txn)
    self.db.commit_person(grPerson, self.txn)
    self.progress.step()
    teksto = _('persono importita el la geneanet-dosiero je la %s') % str(Today())
    citation = aldCitajxo(self.db, self.txn, ext_persono, ext_persono, teksto)
    grPerson.add_citation(citation.get_handle())
    self.progress.step()
    # ajout des évènements :
    self.ald_faktoj(nov_lokoj, ext_persono, grPerson)
    return grPerson

  def ald_faktoj(self, nov_lokoj, ext_persono, gr_persono):
    """ ajoute les évènements de ext_persono à gr_persono """
    faktoj = ext_persono['person'].get('events')
    if faktoj is None or len(faktoj) == 0 or faktoj.get('elements') is None:
      return
    for f in faktoj.get('elements'):
      if f.get('type') == "EFAM_MARRIAGE":
        continue
      self.progress.step()
      event = aldFakto(nov_lokoj, self.db, self.txn, ext_persono, f)
      self.progress.step()
      noto = f.get('note')
      if noto:
        #print("   note evt :%s" % noto)
        grNoto = Note()
        grNoto.set_type(NoteType(_('note geneanet %s') % ext_persono['person'].get('baseprefix')))
        st = htmlAlStyled(noto)
        grNoto.set_styledtext(st)
        if f.get('type') == "EPERS_OCCUPATION":
          # on prend la première ligne de la note comme description
          teksto = grNoto.get()  # texte sans formatage
          event.set_description(teksto.splitlines(keepends=False)[0])
        if self.gn_notoj:
          self.db.add_note(grNoto, self.txn)
          self.db.commit_note(grNoto, self.txn)
          event.add_note(grNoto.handle)
      self.db.commit_event(event, self.txn)
      self.progress.step()
      teksto = _('okazaĵo importita el la geneanet-dosiero je la %s') % str(Today())
      citation = aldCitajxo(self.db, self.txn, ext_persono, f, teksto)
      event.add_citation(citation.get_handle())
      self.progress.step()
      er = EventRef()
      er.set_role(EventRoleType.PRIMARY)
      er.set_reference_handle(event.get_handle())
      self.db.commit_event(event, self.txn)
      gr_persono.add_event_ref(er)
      if event.type == EventType.BIRTH:
        gr_persono.set_birth_ref(er)
      elif event.type == EventType.DEATH:
        gr_persono.set_death_ref(er)
      self.db.commit_person(gr_persono, self.txn)
      self.progress.step()
