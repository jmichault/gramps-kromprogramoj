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
GeneaNet Gramplet.
"""

from html import unescape
import json
from urllib.parse import urlparse, parse_qs, quote_plus
import locale
import os
import xml.etree.ElementTree as ET
from ast import literal_eval

#-------------------------------------------------------------------------
# GTK modules
#-------------------------------------------------------------------------
from gi.repository import Gtk, Gdk

#------------------------------------------------------------------------
# Gramps modules
#------------------------------------------------------------------------
from gramps.gen.db import DbTxn
from gramps.gen.config import config
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.display.place import displayer as _pd
from gramps.gen.errors import WindowActiveError
from gramps.gen.lib import Event, EventRef, EventType, EventRoleType
from gramps.gen.lib import ChildRef, Family, Person
from gramps.gen.plug import Gramplet
from gramps.gui.dialog import QuestionDialog, OkDialog, WarningDialog
from gramps.gui.editors import EditCitation, EditMedia, EditNote, EditPerson, EditEvent
from gramps.gui.listmodel import ListModel, NOSORT, COLOR, TOGGLE
from gramps.gui.utils import ProgressMeter
from gramps.gen.datehandler import LANG_TO_PARSER

#-----------
import instdepGN
#-----------

# dépendances obligatoires :
HavLxml = instdepGN.instDep('lxml', '0.1.1')
HavProtobuf = instdepGN.instDep('protobuf', '6.31.1')
# dépendances facultatives :
instdepGN.instDep('fake_useragent', '0.1.1')

from utilaGN import getGrevent, getUrl, getBirth
from komparoGN import Kompari
from ImportoGN import akiriLoko, aldFakto, updFakto, Importi
from gn_constants import _

parserEn = LANG_TO_PARSER['en']()

if not HavLxml or not HavProtobuf:
  wTeksto = _('La geneanet-grampleto havas neplenumitajn dependecojn :\n')
  if not HavLxml and not HavProtobuf:
    wTeksto = _('lxml kaj protobuf.')
  elif not HavLxml:
    wTeksto = _('lxml.')
  else:
    wTeksto = _('protobuf.')
  wTeksto = wTeksto + '\n\n' + _('Se vi uzas Debian aŭ Ubuntu, provu:\n"\
                               "sudo apt install python3-lxml python3-pip python3-protobuf')
  wTeksto = wTeksto + '\n\n' + _('Se vi uzas fedora, provu:\n"\
                               "sudo dnf install python3-lxml python3-pip python3-protobuf')
  WarningDialog(_('neplenumitajn dependecojn.')
                , wTeksto)

try:
  from lxml import html
except ImportError:
  pass
try:
  import geneanet
except ImportError:
  pass

#-------------------------------------------------------------------------
# configuration
#-------------------------------------------------------------------------

GrampletConfigName = "PersonGN"
CONFIG = config.register_manager(GrampletConfigName)
# salutnomo kaj pasvorto por FamilySearch
CONFIG.register("preferences.gn_notoj", '')
CONFIG.load()

class PersonGN(Gramplet):
  """ classe principale du Gramplet """
  sercxi = None
  model_res = None
  GnPersonoj = {}  # pour mémoriser les résultats de get_persono
  # préférences :
  gn_notoj = CONFIG.get("preferences.gn_notoj") == 'True'
  try:
    lingvo = config.get('preferences.place-lang')
  except AttributeError:
    lingvo = _pd.get_formats()[config.get('preferences.place-format')].language
  if len(lingvo) != 2:
    lingvo = lingvo[:2] or glocale.language[0]
  gn = geneanet.Api()

  def __init__(self, gui):
    self.top = None
    self.lasta_pagxo = None
    self.ok = None
    self.model_komp = None
    self.cb_url = None
    Gramplet.__init__(self, gui)

  def init(self):
    """ kreas GUI """
    self._krei_gui()

  def _krei_gui(self):
    """ kreas GUI interfacon.  """
    self.top = Gtk.Builder()
    self.top.set_translation_domain("addon")
    base = os.path.dirname(__file__)
    gladeFile = base + os.sep + "PersonGN.glade"
    if os.name in ( 'win32', 'nt'):
      xtree = ET.parse(gladeFile)
      for node in xtree.iter():
        if 'translatable' in node.attrib:
          node.text = _(node.text)
      xmlText = ET.tostring(xtree.getroot(), encoding='unicode', method='xml')
      self.top.add_from_string(xmlText)
    else:
      locale.bindtextdomain("addon", base + "/locale")
      self.top.add_from_file(gladeFile)

    res = self.top.get_object("PersonGNTop")
    self.cb_url = self.top.get_object("CB_Url")
    self.top.connect_signals({  # pylint: disable=no-member ; (pylint bug #6352)
        "on_pref_clicked": self.pref_clicked,
        "on_ButSercxi_clicked": self.butsercxi_clicked,
        "on_ButAldoni_clicked": self.butaldoni_clicked,
        "on_ButLancxi_clicked": self.butlancxi_clicked,
        "on_ButPli_clicked": self.butpli_clicked,
        "on_CB_Url_changed": self.cb_url_changed,
        "on_ButRefresxigi_clicked": self.butrefresxigi_clicked,
        "on_ButImporti_clicked": self.butimporti_clicked,
    })
    titlesKomp = [
        (_('Koloro'), 1, 40, COLOR),
        (_('Propreco'), 2, 100),
        (_('Dato'), 3, 120),
        (_('Gramps Valoro'), 4, 300),
        (_('GN Dato'), 5, 120),
        (_('GN Valoro'), 6, 300),
        (' ', NOSORT, 1),
        ('x', 8, 5, TOGGLE, True, self.toggled),
        (_('xTipo'), NOSORT, 0),
        (_('xGr'), NOSORT, 0),
        (_('xGn'), NOSORT, 0),
        (_('xGr2'), NOSORT, 0),
        (_('xGn2'), NOSORT, 0),
    ]
    propKomp = self.top.get_object("propKomp")
    self.model_komp = ListModel(
        propKomp,
        titlesKomp,
        list_mode="tree",
        event_func=self.l_duobla_klako,
        right_click=self.l_dekstra_klako)

    self.gui.WIDGET = res
    self.gui.get_container_widget().remove(self.gui.textview)
    self.gui.get_container_widget().add_with_viewport(self.gui.WIDGET)
    self.gui.WIDGET.show_all()

  def toggled(self, path, _val=None):
    """ url changée """
    row = self.model_komp.model.get_iter((path,))
    tipo = self.model_komp.model.get_value(row, 8)
    if tipo not in ('edzo', 'infano', 'patro', 'patrino', 'fakto', 'edzoFakto'):
      self.model_komp.model.set_value(row, 7, False)
      OkDialog(_('Pardonu, nur edzaj, eventaj, patraj, aŭ infanaj linioj povas esti elektitaj.'))

  def l_duobla_klako(self, treeview):
    """ double clic sur une ligne """
    (model, _iter) = treeview.get_selection().get_selected()
    if not _iter:
      return
    tipo = model.get_value(_iter, 8)
    handle = model.get_value(_iter, 9)
    if handle and tipo in ('infano', 'patro', 'patrino', 'edzo'):
      self.uistate.set_active(handle, 'Person')
    elif handle and tipo in ('fakto', 'edzoFakto'):
      event = self.dbstate.db.get_event_from_handle(handle)
      try:
        EditEvent(self.dbstate, self.uistate, [], event)
      except WindowActiveError:
        pass
    elif handle and tipo in('NotoP', 'NotoF'):
      noto = self.dbstate.db.get_note_from_handle(model.get_value(_iter, 10))
      try:
        EditNote(self.dbstate, self.uistate, [], noto)
      except WindowActiveError:
        pass
    elif (handle and (tipo == 'Fonto')):
      cit = self.dbstate.db.get_citation_from_handle(handle)
      try:
        EditCitation(self.dbstate, self.uistate, [], cit)
      except WindowActiveError:
        pass

  def set_ok(self):
    """ positionne le flag OK pour savoir quel bouton a été choisi """
    self.ok = True

  def _kopii_al_gramps(self, _treeview):
    """ copier la sélection vers gramps """
    self.uistate.set_busy_cursor(True)
    progress = ProgressMeter(_("Geneanet Kopio"), _('Kopio')
                  , can_cancel=True, parent=self.uistate.window)
    progress.set_pass(_('Kopiante… '), mode=ProgressMeter.MODE_ACTIVITY)
    model = self.model_komp.model
    activeHandle = self.get_active('Person')
    grPersono = self.dbstate.db.get_person_from_handle(activeHandle)
    url = 'https://gw.geneanet.org/' + self.cb_url.get_active_text()
    extPersono = self._get_persono(url)
    if self.dbstate.db.transaction:
      print("??? transaction en cours ???")
      self.dbstate.db.transaction_commit(self.dbstate.db.transaction)
    db = self.dbstate.db
    novLokoj = {}
    with DbTxn(_("kopii al gramps"), db) as txn:
      importi = Importi(db,txn,progress,PersonGN.gn_notoj)
      for x in model:
        l = [x]
        l.extend(x.iterchildren())
        progress.set_pass(_('Kopiante… '), mode=ProgressMeter.MODE_ACTIVITY)
        memFH = None  # familioHandle mémorisé
        for linio in l:
          progress.step()
          tipolinio = linio[8]
          if tipolinio not in ('edzoFakto', 'infano'):
            memFH = None
          if not linio[7]:  # si la ligne n'est pas cochée
            continue
          if tipolinio in ('nomo', 'nomo1') and linio[5]:
            print(_("nomimporto ankoraŭ ne efektivigita_"))
          elif tipolinio == 'patro':
            extPatro = extPersono['person']['father']  # fiche simplifiée du père
            urlPatro = geneanet.id2url(extPatro)
            extPatro = self._get_persono(urlPatro)  # fiche détaillée du père
            grPatro = importi.ald_persono(novLokoj, extPatro)
            familioHandle = grPersono.get_main_parents_family_handle()
            if familioHandle:
              familio = db.get_family_from_handle(familioHandle)
              patroHandle = familio.get_father_handle()
              if patroHandle:
                OkDialog(_('Ĉi tiu persono jam havas patron'))
                continue
              familio.set_father_handle(grPatro.get_handle())
              grPatro.add_family_handle(familio.get_handle())
              db.commit_family(familio, txn)
              db.commit_person(grPatro, txn)
            else:
              familio = Family()
              familio.set_father_handle(grPatro.get_handle())
              db.add_family(familio, txn)
              db.commit_family(familio, txn)
              grPatro.add_family_handle(familio.get_handle())
              childref = ChildRef()
              childref.set_reference_handle(activeHandle)
              familio.add_child_ref(childref)
              grPersono.add_parent_family_handle(familio.get_handle())
              db.commit_family(familio, txn)
              db.commit_person(grPatro, txn)
              db.commit_person(grPersono, txn)
          elif tipolinio == 'patrino':
            extPatrino = extPersono['person']['mother']  # fiche simplifiée de la mère
            urlPatrino = geneanet.id2url(extPatrino)
            extPatrino = self._get_persono(urlPatrino)  # fiche détaillée de la mère
            grPatrino = importi.ald_persono(novLokoj, extPatrino)
            familioHandle = grPersono.get_main_parents_family_handle()
            if familioHandle:
              familio = db.get_family_from_handle(familioHandle)
              patrinoHandle = familio.get_mother_handle()
              if patrinoHandle:
                OkDialog(_('Ĉi tiu individuo jam havas patrinon'))
                continue
              familio.set_mother_handle(grPatrino.get_handle())
              grPatrino.add_family_handle(familio.get_handle())
              db.commit_family(familio, txn)
              db.commit_person(grPatrino, txn)
            else:
              familio = Family()
              familio.set_mother_handle(grPatrino.get_handle())
              db.add_family(familio, txn)
              db.commit_family(familio, txn)
              grPatrino.add_family_handle(familio.get_handle())
              childref = ChildRef()
              childref.set_reference_handle(activeHandle)
              familio.add_child_ref(childref)
              grPersono.add_parent_family_handle(familio.get_handle())
              db.commit_family(familio, txn)
              db.commit_person(grPatrino, txn)
              db.commit_person(grPersono, txn)
          elif tipolinio == 'fakto' and (linio[10] or '') != '':
            extFakto = literal_eval(linio[10])
            grFaktoH = linio[9]
            if grFaktoH:
              event = db.get_event_from_handle(grFaktoH)
              updFakto(novLokoj, db, txn, event, extFakto)
            else:
              event = aldFakto(novLokoj, db, txn, extPersono, extFakto)
            found = False
            for er in grPersono.get_event_ref_list():
              if er.ref == event.handle:
                found = True
                break
            if not found:
              er = EventRef()
              er.set_role(EventRoleType.PRIMARY)
              er.set_reference_handle(event.get_handle())
              self.dbstate.db.commit_event(event, txn)
              grPersono.add_event_ref(er)
            if event.type == EventType.BIRTH:
              grPersono.set_birth_ref(er)
            elif event.type == EventType.DEATH:
              grPersono.set_death_ref(er)
          elif tipolinio == 'edzo' and linio[12] :
            extFamId = int(linio[12])
            for f in extPersono['person'].get('families'):
              if f.get('index') == extFamId:
                extFamilio = f
                break
            extEdzo = extFamilio.get('spouse')  # fiche simplifiée du conjoint
            urlEdzo = geneanet.id2url(extEdzo)
            extEdzo = self._get_persono(urlEdzo)  # fiche détaillée du conjoint
            grEdzo = importi.ald_persono(novLokoj, extEdzo)
            familio = Family()
            db.add_family(familio, txn)
            if grPersono.get_gender() == Person.MALE:
              familio.set_father_handle(grPersono.get_handle())
              familio.set_mother_handle(grEdzo.get_handle())
            else:
              familio.set_mother_handle(grPersono.get_handle())
              familio.set_father_handle(grEdzo.get_handle())
            db.commit_family(familio, txn)
            # répercuter la famille sur les lignes d'enfant
            memFH = familio.handle
            grPersono.add_family_handle(familio.get_handle())
            db.commit_person(grPersono, txn)
            grEdzo.add_family_handle(familio.get_handle())
            db.commit_person(grEdzo, txn)
            if ((extFamilio.get('marriageDateLong') or '') != '' or
                (extFamilio.get('marriagePlace') or '') != ''):
              event = Event()
              dato = extFamilio.get('marriageDateLong')
              if dato:
                grDato = parserEn.parse(dato)
                if grDato:
                  event.set_date_object(grDato)
              loko = unescape(extFamilio.get('marriagePlace') or '')
              if loko != '':
                grLoko = akiriLoko(novLokoj, db, txn, loko)
                event.set_place_handle(grLoko.handle)
              if extFamilio.get('marriageType') == "MARRIED":
                event.set_type(EventType.MARRIAGE)
              else:
                print(f"type de mariage à traiter : {extFamilio.get('marriageType')}")
              db.add_event(event, txn)
              db.commit_event(event, txn)
              er = EventRef()
              er.set_role(EventRoleType.PRIMARY)
              er.set_reference_handle(event.get_handle())
              db.commit_event(event, txn)
              familio.add_event_ref(er)
              db.commit_family(familio, txn)
          elif tipolinio == 'edzoFakto' and (linio[9] or '') != '' and (linio[10] or '') != '':
            grFamHandle = linio[9]
            extFamId = int(linio[10])
            for f in extPersono['person'].get('families'):
              if f.get('index') == extFamId:
                extFamilio = f
                break
            extEdzo = extFamilio.get('spouse')  # fiche simplifiée du conjoint
            grFaktoH = linio[11]
            extFakto = literal_eval(linio[12])
            if grFaktoH:
              event = db.get_event_from_handle(grFaktoH)
              updFakto(novLokoj, db, txn, event, extFakto)
            else:
              event = aldFakto(novLokoj, db, txn, extPersono, extFakto)
              er = EventRef()
              er.set_role(EventRoleType.PRIMARY)
              er.set_reference_handle(event.get_handle())
              db.commit_event(event, txn)
              familio = db.get_family_from_handle(grFamHandle)
              familio.add_event_ref(er)
              db.commit_family(familio, txn)
          elif tipolinio == 'infano':
            urlInfano = linio[10]
            extInfano = self._get_persono(urlInfano)  # fiche détaillée de l'enfant
            familioHandle = linio[11]
            if familioHandle is None:
              familioHandle = memFH  # on vient de créer la famille
            if familioHandle is None:
              self.ok = False
              x = QuestionDialog(_("Konfirmo necesa")
                      , _("Ĉu vi certas, ke vi volas importi infanon\n"\
                          "<b>antaŭ ol importi la edzinon/edzon?</b>")
                      , _("Jes, mi scias, kion mi faras."), self.set_ok)
              if not self.ok:
                continue
            grInfano = importi.ald_persono(novLokoj, extInfano)
            if familioHandle:
              familio = db.get_family_from_handle(familioHandle)
              childref = ChildRef()
              childref.set_reference_handle(grInfano.get_handle())
              familio.add_child_ref(childref)
              db.commit_family(familio, txn)
              grInfano.add_parent_family_handle(familioHandle)
              db.commit_person(grInfano, txn)
          else:
            print(f" import de {tipolinio} pas encore implémenté…")
      db.commit_person(grPersono, txn)
      db.transaction_commit(txn)
    db.enable_signals()
    progress.close()
    self.uistate.set_busy_cursor(False)
    self.butrefresxigi_clicked(None)
    if len(novLokoj) > 0:
      teksto = (
          _('\tLa jenaj lokoj estis kreitaj dum la importado,\n vi devus kontroli ilin nun:\n\n')
           + '\n'.join([f'{k} : {v}'  for k,v in novLokoj.items()]))
      WarningDialog(_('lokoj kreitaj !!!')
                    , teksto)

  def l_dekstra_klako(self, treeview, event):
    """ clic droit : afficher le menu """
    menu = Gtk.Menu()
    menu.set_reserve_toggle_size(False)
    (model, _iter) = treeview.get_selection().get_selected()
    if _iter:
      tipo = model.get_value(_iter, 8)
      if (model.get_value(_iter, 10)
           and tipo in ('infano', 'patro', 'patrino', 'edzo')):
        item = Gtk.MenuItem(label=_('Kopii json-datumojn al tondujo'))
        item.set_sensitive(1)
        item.connect("activate", lambda obj: self.kopiijson(treeview))
        item.show()
        menu.append(item)
      if (model.get_value(_iter, 9)
           and tipo in ('infano', 'patro', 'patrino', 'edzo', 'fakto', 'edzoFakto', 'Bildo')):
        item = Gtk.MenuItem(label=_('Redakti : %s - %s - %s') % (model.get_value(_iter, 1)
                   , model.get_value(_iter, 2), model.get_value(_iter, 3)))
        item.set_sensitive(1)
        item.connect("activate", lambda obj: self.redakti(treeview))
        item.show()
        menu.append(item)
    # est-ce qu'il y a une ligne cochée copiable vers gramps ?
    # est-ce qu'on a coché un conjoint gramps et un conjoint geneanet qu'on veut comparer ?
    cpt = cptEdzGr = cptEdzExt = 0
    for x in self.model_komp.model:
      l=[x]
      l.extend(x.iterchildren())
      #import pdb; pdb.set_trace()
      for linio in l:
        if not linio[7]:
          continue
        tipolinio = linio[8]
        grHandle = linio[9]
        if (tipolinio == 'edzo') and not grHandle:
          cptEdzExt += 1
        if (tipolinio == 'edzo') and grHandle:
          cptEdzGr += 1
        if ( (tipolinio in ('patro', 'patrino', 'edzo', 'infano') and not grHandle)
            or (tipolinio == 'fakto' and (linio[10] or '') != '')):
          cpt += 1
        elif (tipolinio == 'edzoFakto' and (linio[10] or '') != ''):
          cpt += 1
    if cpt > 0:
      item = Gtk.MenuItem(label=_('Kopii elekton de Geneanet al gramps'))
      item.set_sensitive(1)
      item.connect("activate", lambda obj: self._kopii_al_gramps(treeview))
      item.show()
      menu.append(item)
    if cptEdzGr == 1 and cptEdzExt == 1:
      item = Gtk.MenuItem(label=_('Kompari infanoj'))
      item.set_sensitive(1)
      item.connect("activate", lambda obj: self.kmp_inf(treeview))
      item.show()
      menu.append(item)
    menu.popup(None, None, None, None, event.button, event.time)

  def kmp_inf(self, _treeview):
    """ on considère les deux conjoints comme identique pour comparer les enfants """
    model = self.model_komp.model
    url = 'https://gw.geneanet.org/' + self.cb_url.get_active_text()
    extPersono = self._get_persono(url)
    extFamilio = {}
    grEdzH = None
    for x in model:
      l = [x]
      l.extend(x.iterchildren())
      for linio in l:
        if not linio[7]:
          continue
        tipolinio = linio[8]
        grHandle = linio[9]
        if (tipolinio == 'edzo') and not grHandle:
          extFamId = int(linio[12])
          for f in extPersono['person'].get('families'):
            if f.get('index') == extFamId:
              extFamilio = f
              break
        if (tipolinio == 'edzo') and grHandle:
          grEdzH = grHandle
    extFamilio['_grEdzHandle'] = grEdzH
    self.butrefresxigi_clicked(None)

  def redakti(self, treeview):
    """ on édite l'une des lignes """
    (model, _iter) = treeview.get_selection().get_selected()
    if not _iter:
      return
    tipo = model.get_value(_iter, 8)
    handle = model.get_value(_iter, 9)
    if not handle:
      return
    if tipo in ('infano', 'patro', 'patrino', 'edzo'):
      person = self.dbstate.db.get_person_from_handle(handle)
      try:
        EditPerson(self.dbstate, self.uistate, [], person)
      except WindowActiveError:
        pass
    elif tipo in('fakto', 'edzoFakto'):
      event = self.dbstate.db.get_event_from_handle(handle)
      try:
        EditEvent(self.dbstate, self.uistate, [], event)
      except WindowActiveError:
        pass
    elif tipo == 'Bildo':
      m = self.dbstate.db.get_media_from_handle(handle)
      try:
        EditMedia(self.dbstate, self.uistate, [], m)
      except WindowActiveError:
        pass

  def kopiijson(self, treeview):
    """ copier le json de la personne dans le presse-papiers """
    (model, _iter) = treeview.get_selection().get_selected()
    if not _iter:
      return
    extUrl = model.get_value(_iter, 10)
    extPersono = self._get_persono(extUrl)
    self.uistate.window.get_clipboard(Gdk.SELECTION_CLIPBOARD).set_text(
        json.dumps(extPersono, indent=2, default=str), -1)

  def ser_sel_cxango(self, _dummy):
    """ traitement de sélection d'une ligne de résultat """
    model, _iter = self.top.get_object("PersonGNResRes").get_selection().get_selected()
    if _iter:
      lien = 'https://gw.geneanet.org/' + model.get_value(_iter, 0)
      self.top.get_object("LinkoButonoSercxi").set_label(_('Vidu ĉe Geneanet'))
      self.top.get_object("LinkoButonoSercxi").set_uri(lien)
    else:
      self.top.get_object("LinkoButonoSercxi").set_label('xxxx')
      self.top.get_object("LinkoButonoSercxi").set_uri('https://www.geneanet.org/')

  def _get_persono(self, url):
    """ chargement d'une fiche geneanet """
    extPersono = PersonGN.GnPersonoj.get(url)
    if extPersono is None:
      tmp = urlparse(url)
      q = parse_qs(tmp.query)
      x = {}
      x['tree'] = tmp.path[1:]
      if 'n' in q:
        x['n'] = q['n'][0]
      if 'p' in q:
        x['p'] = q['p'][0]
      if 'oc' in q:
        x['oc'] = int(q['oc'][0])
      url = geneanet.id2url(x)
      extPersono = PersonGN.GnPersonoj.get(url)
    if extPersono is None:
      extPersono = PersonGN.gn.get_person(x)
      if extPersono is None:
        extPersono = PersonGN.gn.get_person(x)
      if extPersono is None:
        return None
      PersonGN.GnPersonoj[geneanet.id2url(extPersono)] = extPersono
      if len(PersonGN.GnPersonoj) > 100:  # ne pas garder plus de 100 personnes en mémoire
        PersonGN.GnPersonoj.pop(next(iter(PersonGN.GnPersonoj)))
    return extPersono

  def butimporti_clicked(self, _dummy):
    """ import de geneanet vers gramps """
    activeHandle = self.get_active('Person')
    if (activeHandle or '') == '':
      WarningDialog(_('neniu aktiva persono !!!')
                    , _('Vi devas unue elekti personon!'))
      return
    self._kopii_al_gramps(None)

  def butrefresxigi_clicked(self, _dummy):
    """ rafraîchissement de la comparaison """
    self.model_komp.clear()
    activeHandle = self.get_active('Person')
    if (activeHandle or '') == '':
      WarningDialog(_('neniu aktiva persono !!!')
                    , _('Vi devas unue elekti personon!'))
      return
    url = self.cb_url.get_active_text()
    if url is None or url == '':
      return
    url = 'https://gw.geneanet.org/' + url
    extPersono = self._get_persono(url)
    grPersono = self.dbstate.db.get_person_from_handle(activeHandle)
    self.model_komp.cid = None
    self.model_komp.model.set_sort_column_id(-2, 0)
    self.model_komp.clear()
    if activeHandle:
      self.set_has_data(True)
      k = Kompari(grPersono, extPersono, self.dbstate.db, self.model_komp)
      k.kompari_gr_ext()
    else:
      self.set_has_data(False)

  def get_has_data(self, active_handle):
    """
    " Return True if the gramplet has data, else return False.
    """
    if active_handle:
      return True
    return False

  def db_changed(self):
    self.active_changed('')

  def active_changed(self, handle):
    if not hasattr(self,'cb_url'):
      return
    self.cb_url.insert_text(0, '')
    self.cb_url.set_active(0)
    self.cb_url.remove_all()
    self.model_komp.clear()
    # on ajoute dans cb_url les sources geneanet déjà citées
    activeHandle = self.get_active('Person')
    grPersono = self.dbstate.db.get_person_from_handle(activeHandle)
    urls = set()
    for ch in grPersono.get_all_citation_lists():
      cit = self.dbstate.db.get_citation_from_handle(ch)
      url = getUrl(cit)
      if url is not None:
        urls.add(url)
    for evtRef in grPersono.get_event_ref_list() or []:
      event = self.dbstate.db.get_event_from_handle(evtRef.ref)
      for ch in event.get_citation_list():
        cit = self.dbstate.db.get_citation_from_handle(ch)
        url = getUrl(cit)
        if url is not None:
          urls.add(url)
    if len(urls) > 0:
      self.cb_url.insert_text(0, '')
    for url in urls:
      self.cb_url.insert_text(-1, url)
    self.cb_url.set_active(0)

  def pref_clicked(self, _dummy):
    """ lancement du dialogue des préférences """
    parent = self.uistate.window
    for win in Gtk.Window.list_toplevels():
      if win.is_active():
        parent = win
        break
    top = self.top.get_object("PersonGNPrefDialogo")
    top.set_transient_for(parent)
    parentModal = self.uistate.window.get_modal()
    if parentModal:
      self.uistate.window.set_modal(False)
    gnNotoj = self.top.get_object("gn_notoj")
    gnNotoj.set_active(PersonGN.gn_notoj)
    top.show()
    res = top.run()
    top.hide()
    if res == -3:
      PersonGN.gn_notoj = gnNotoj.get_active()
      CONFIG.set("preferences.gn_notoj", str(PersonGN.gn_notoj))
      CONFIG.save()

  def cb_url_changed(self, dummy):
    """ nouvelle url choisie """
    self.butrefresxigi_clicked(dummy)

  def _konstrui_mendo(self,pagxo):
    mendo = "https://www.geneanet.org/fonds/individus/?go=1&categories_1__arbres__=arbres"\
            "&categories_2__arbres%23utilisateur__=arbres%23utilisateur"
    grNomo = self.top.get_object("gn_nomo_eniro").get_text()
    if grNomo:
      mendo = mendo + "&nom=" + quote_plus(grNomo)
    grANomo = self.top.get_object("gn_anomo_eniro").get_text()
    if grANomo:
      mendo = mendo + "&prenom=" + quote_plus(grANomo)
    sekso = self.top.get_object("gn_sekso_eniro").get_text()
    if sekso:
      if sekso[0] == 'M':
        mendo += "&sexe=1"
      elif sekso[0] == 'F':
        mendo += "&sexe=2"
    dato1 = self.top.get_object("gn_dato1").get_text()
    dato2 = self.top.get_object("gn_dato2").get_text()
    if dato1 and dato2:
      mendo = mendo + "&type_periode=between&from=" + quote_plus(dato1) + "&to=" + quote_plus(dato2)
    elif dato1:
      mendo = mendo + "&type_periode=after&from=" + dato1
    elif dato2:
      mendo = mendo + "&type_periode=before&from=&to" + dato2
    loko = self.top.get_object("gn_loko_eniro").get_text()
    if loko:
      mendo += "&place__0__=" + quote_plus(loko)
    if pagxo > 1:
      mendo += f"&page={pagxo}"
    return mendo

  def _analizi_url(self,url):
    """ analyse une ligne de résultat et l'affiche """
    p = self._get_persono(url)
    if not p:
      return
    parents = ''
    conjoints = ''
    sosa = ''
    naissance = ''
    deces = ''
    if 'person' in p:
      nom = (p['person'].get('lastname') or '?') + ' ' + (p['person'].get('firstname') or '?')
      sosa = p['person'].get('sosaNb') or ''
      if 'father' in p['person']:
        parents = ((p['person']['father'].get('lastname') or '?') + ' ' +
                   (p['person']['father'].get('firstname') or '?'))
      if 'mother' in p['person']:
        parents += ('\n' + (p['person']['mother'].get('lastname') or '?') + ' ' +
                    (p['person']['mother'].get('firstname') or '?'))
      naissance = p['person'].get('birthDate') or ''
      if 'birthPlace' in p['person']:
        naissance += '\n' + p['person']['birthPlace']
      deces = p['person'].get('deathDate') or ''
      if 'deathPlace' in p['person']:
        deces += '\n' + p['person']['deathPlace']
      if 'families' in p['person']:
        for f in p['person']['families']:
          nbInfanoj = len(f.get('children') or '')
          if 'spouse' in f:
            if conjoints != '':
              conjoints += "\n"
              sosa += "\n"
            sp = f['spouse']
            conjoints += (
                str(nbInfanoj) + ', ' + (sp.get('lastname') or '?') + ' ' +
                (sp.get('firstname') or '?'))
    else:
      nom = (p.get('n') or '?') + ' ' + (p.get('p') or '?')
    self.model_res.add((url.removeprefix('https://gw.geneanet.org/'), sosa, nom, naissance,
                       deces, parents, conjoints))

  def _analizi_tabelo(self,tableau,progress):
    linio = 1
    prevUrl = None
    for r in tableau:
      if progress.get_cancelled():
        break
      progress.set_header(_('Elŝutante personojn… (%s/10)') % linio)
      linio += 1
      url = r.xpath('attribute::href')[0]
      if url == prevUrl:
        continue
      prevUrl = url
      self._analizi_url(url)
      progress.step()

  def _fari_sercxi(self, pagxo=1):
    """ exécution de la recherche """
    self.lasta_pagxo = pagxo
    treeRes = self.top.get_object("PersonGNResRes")
    treeRes.hide()
    self.krei_sercxi_model()
    treeRes.set_fixed_height_mode(False)
    parent = self.uistate.window
    for win in Gtk.Window.list_toplevels():
      if win.is_active():
        parent = win
        break
    progress = ProgressMeter(_("Geneanet Serĉo"), _('Serĉante')
               , can_cancel=True, parent=parent)
    self.uistate.set_busy_cursor(True)
    progress.set_pass(_('Serĉante… '), 12, mode=ProgressMeter.MODE_FRACTION)
    progress.step()
    r = PersonGN.gn.urlopen(self._konstrui_mendo(pagxo))
    if r == b'': # deuxième essai
      PersonGN.gn.reinit()
      r = PersonGN.gn.urlopen(self._konstrui_mendo(pagxo))
    progress.step()
    if r is None or r == b'':
      print(_('Eraro: neniuj datumoj.'))
    else:
      try:
        tree = html.fromstring(r.decode('utf-8'))
      except (TypeError,ValueError,html.etree.ParseError, html.etree.ParserError) as e:
        print(_(f"Unable to perform HTML analysis. {e}"))
      tableau = tree.xpath('//div[@id="table-resultats"]//a')
      self._analizi_tabelo(tableau,progress)
    self.uistate.set_busy_cursor(False)
    progress.close()
    treeRes.show()

  def butlancxi_clicked(self, _dummy):
    """ affichage de la page de résultats suivante """
    self._fari_sercxi()

  def butpli_clicked(self, _dummy):
    """ page suivante """
    self._fari_sercxi(self.lasta_pagxo + 1)

  def butaldoni_clicked(self, _dummy):
    """ on lance la comparaison """
    model, _iter = self.top.get_object("PersonGNResRes").get_selection().get_selected()
    if _iter:
      lien = model.get_value(_iter, 0)
      self.sercxi.hide()
      # on crée notre liste, et on y ajoute les liens de la combobox
      s = {'', lien}
      for c in self.cb_url.get_model():
        s.add(c[0])
      l = sorted(s)
      self.cb_url.remove_all()
      for x in l:
        self.cb_url.insert_text(-1, x)
      index = l.index(lien)
      self.cb_url.set_active(index)  # rendre la ligne active va lancer la comparaison

  def krei_sercxi_model(self):
    """ création du modèle de données pour l'affichage des résultats """
    titles = [
        (_('URL'), 1, 80),
        (_('Sosa'), 2, 40),
        (_('Nomo, antaŭnomo'), 3, 200),
        (_('Naskiĝo'), 4, 250),
        (_('Morto'), 5, 250),
        (_('Gepatroj'), 6, 250),
        (_('Nb Inf., Geedzoj'), 7, 250),
    ]
    treeRes = self.top.get_object("PersonGNResRes")
    treeRes.set_model(None)
    if self.model_res:
      self.model_res.clear()
      del self.model_res
    for col in treeRes.get_columns():
      treeRes.remove_column(col)
    self.model_res = ListModel(treeRes, titles, self.ser_sel_cxango)

  def _sercxi_ini_tekstoj(self,person):
    """ initialise les champs de la recherche """
    self.top.get_object("gn_nomo_eniro").set_text(person.primary_name.get_surname())
    self.top.get_object("gn_anomo_eniro").set_text(person.primary_name.first_name)
    if person.get_gender() == Person.MALE:
      self.top.get_object("gn_sekso_eniro").set_text('M')
    elif person.get_gender() == Person.FEMALE:
      self.top.get_object("gn_sekso_eniro").set_text('F')
    grBirth = getBirth(self.dbstate.db, person)
    if grBirth and grBirth.date and not grBirth.date.is_empty():
      self.top.get_object("gn_dato1").set_text(f"{grBirth.date.get_year()}")
    else:
      self.top.get_object("gn_dato1").set_text('')
    grDeath = getGrevent(self.dbstate.db, person, EventType(EventType.DEATH))
    if grDeath is None or grDeath.date is None or grDeath.date.is_empty():
      grDeath = getGrevent(self.dbstate.db, person, EventType(EventType.BURIAL))
    if grDeath is None or grDeath.date is None or grDeath.date.is_empty():
      grDeath = getGrevent(self.dbstate.db, person, EventType(EventType.CREMATION))
    if grDeath and grDeath.date and not grDeath.date.is_empty():
      self.top.get_object("gn_dato2").set_text(f"{grDeath.date.get_year()}")
    else:
      self.top.get_object("gn_dato2").set_text('')

    if grBirth and grBirth.place and grBirth.place != '':
      place = self.dbstate.db.get_place_from_handle(grBirth.place)
      posv = place.name.value.find(',')
      if posv > 3 :
        self.top.get_object("gn_loko_eniro").set_text(place.name.value[:posv])
      else:
        self.top.get_object("gn_loko_eniro").set_text(place.name.value)
    else:
      self.top.get_object("gn_loko_eniro").set_text('')

  def butsercxi_clicked(self, _dummy):
    """ lancement d'une recherche """
    activeHandle = self.get_active('Person')
    if (activeHandle or '') == '':
      WarningDialog(_('neniu aktiva persono !!!')
                    , _('Vi devas unue elekti personon!'))
      return
    parent = self.uistate.window
    for win in Gtk.Window.list_toplevels():
      if win.is_active():
        parent = win
        break
    if not self.sercxi:
      self.sercxi = self.top.get_object("PersonGNRes")
      self.sercxi.set_title(_("Geneanet serĉo"))
    parentModal = parent.get_modal()
    if parentModal:
      parent.set_modal(False)
    self.sercxi.set_transient_for(parent)
    person = self.dbstate.db.get_person_from_handle(activeHandle)
    self._sercxi_ini_tekstoj(person)
    self.butlancxi_clicked(None)
    self.sercxi.show()
    self.sercxi.run()
    self.sercxi.hide()
    return
