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

#---
import instdepGN
# dépendances obligatoires :
havLxml = instdepGN.instDep('lxml','0.1.1')
havProtobuf = instdepGN.instDep('protobuf','6.31.1')
# dépendances facultatives :
instdepGN.instDep('fake_useragent','0.1.1')

#-------------------------------------------------------------------------
#
# GTK modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk, Gdk

#------------------------------------------------------------------------
#
# Gramps modules
#
#------------------------------------------------------------------------
from gramps.gen.db import DbTxn
from gramps.gen.config import config
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext
from gramps.gen.constfunc import win
from gramps.gen.datehandler import get_date
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.display.place import displayer as _pd
from gramps.gen.errors import WindowActiveError
from gramps.gen.lib import Citation, Date, Event, EventRef, EventType, EventRoleType, Name, NameType, NoteType, Person, StyledText, StyledTextTag, StyledTextTagType, Tag, Note
from gramps.gen.lib import ChildRef, Family
from gramps.gen.plug import Gramplet, PluginRegister
from gramps.gui.dialog import OptionDialog, OkDialog , WarningDialog
from gramps.gui.editors import EditCitation, EditNote, EditPerson, EditEvent
from gramps.gui.listmodel import ListModel, NOSORT, COLOR, TOGGLE
from gramps.gui.utils import ProgressMeter
from gramps.gen.datehandler import LANG_TO_PARSER
parserEn = LANG_TO_PARSER['en']()

if not havLxml or not havProtobuf :
  teksto=''
  if not havLxml and not havProtobuf :
    teksto = _('lxml kaj protobuf.')
  elif not havLxml :
    teksto = _('lxml.')
  else :
    teksto = _('protobuf.')
  teksto = teksto + '\n\n' + _('Se vi uzas Debian aŭ Ubuntu, provu:\nsudo apt install python3-lxml python3-pip python3-protobuf')
  teksto = teksto + '\n\n' + _('Se vi uzas fedora, provu:\nsudo dnf install python3-lxml python3-pip python3-protobuf')
  WarningDialog(_('La geneanet-grampleto havas neplenumitajn dependecojn.')
          ,teksto)

from html import unescape
try :
  from lxml import html
except :
  pass
from urllib.parse import urlparse, parse_qs , quote_plus
import json

from utilaGN import get_grevent

try :
  import geneanet
except :
  pass
from komparoGN import kompariGrExt
from ImportoGN import aldPersono, akiriLoko, aldFakto, updFakto



#-------------------------------------------------------------------------
#
# configuration
#
#-------------------------------------------------------------------------

GRAMPLET_CONFIG_NAME = "PersonGN"
CONFIG = config.register_manager(GRAMPLET_CONFIG_NAME)
# salutnomo kaj pasvorto por FamilySearch
CONFIG.register("preferences.gn_osm", '')
CONFIG.register("preferences.gn_notoj", '')
CONFIG.load()


#from objbrowser import browse ;browse(locals())
#import pdb; pdb.set_trace()

class PersonGN(Gramplet):
  lingvo = None
  Sercxi = None
  modelRes = None
  GnPersonoj = dict() # pour mémoriser les résultats de getPerson
  # préférences :
  gn_osm = (CONFIG.get("preferences.gn_osm") == 'True' )
  gn_notoj = (CONFIG.get("preferences.gn_notoj") == 'True' )
  try:
      lingvo = config.get('preferences.place-lang')
  except AttributeError:
      fmt = config.get('preferences.place-format')
      pf = _pd.get_formats()[fmt]
      lingvo = pf.language
  if len(lingvo) != 2:
      lingvo = lingvo[:2]
  if not lingvo :
    lingvo = glocale.language[0]

  def init(self):
    """
    " kreas GUI 
    """
    self.gui.WIDGET = self.krei_gui()
    self.gui.get_container_widget().remove(self.gui.textview)
    self.gui.get_container_widget().add_with_viewport(self.gui.WIDGET)
    self.gui.WIDGET.show_all()
    self.gn = geneanet.Api()


  def krei_gui(self):
    """
    " kreas GUI interfacon.
    """
    import locale,gettext, os
    self.top = Gtk.Builder()
    self.top.set_translation_domain("addon")
    base = os.path.dirname(__file__)
    glade_file = base + os.sep + "PersonGN.glade"
    if os.name == 'win32' or os.name == 'nt' :
      import xml.etree.ElementTree as ET
      xtree = ET.parse(glade_file)
      for node in xtree.iter() :
        if 'translatable' in node.attrib :
          node.text = _(node.text)
      xml_text = ET.tostring(xtree.getroot(),encoding='unicode',method='xml')
      self.top.add_from_string(xml_text)
    else:
      locale.bindtextdomain("addon", base + "/locale")
      self.top.add_from_file(glade_file)

    self.res = self.top.get_object("PersonGNTop")
    self.cbReg = self.top.get_object("CB_Regximo")
    self.top.connect_signals({
            "on_pref_clicked"      : self.pref_clicked,
            "on_ButSercxi_clicked"      : self.ButSercxi_clicked,
            "on_ButAldoni_clicked"      : self.ButAldoni_clicked,
            "on_ButLancxi_clicked"      : self.ButLancxi_clicked,
            "on_CB_Regximo_changed"      : self.CB_Regximo_changed,
            "on_ButRefresxigi_clicked"      : self.ButRefresxigi_clicked,
	})
    titles_komp = [
        (_('Koloro'), 1, 40,COLOR),
        ( _('Propreco'), 2, 100),
        ( _('Dato'), 3, 120),
        (_('Gramps Valoro'), 4, 300),
        (_('GN Dato'), 5, 120),
        (_('GN Valoro'), 6, 300),
        (' ', NOSORT, 1),
        ('x', 8, 5, TOGGLE,True,self.toggled),
        (_('xTipo'), NOSORT, 0),
        (_('xGr'), NOSORT, 0),
        (_('xGn'), NOSORT, 0),
        (_('xGr2'), NOSORT, 0),
        (_('xGn2'), NOSORT, 0),
     ]
    self.propKomp = self.top.get_object("propKomp")
    self.modelKomp = ListModel(self.propKomp, titles_komp, list_mode="tree"
                 ,event_func=self.l_duobla_klako
                 ,right_click=self.l_dekstra_klako)


    return self.res

  def toggled(self, path, val=None):
    url = self.cbReg.get_active_text()
    extPersono = self.getPersono(url)
    row = self.modelKomp.model.get_iter((path,))
    tipo=self.modelKomp.model.get_value(row, 8)
    if (     tipo != 'edzo'
         and tipo != 'infano' and tipo != 'patro' and tipo != 'patrino'
         and tipo != 'fakto' 
         #and tipo != 'fakto' and tipo != 'nomo' and tipo != 'nomo1'
         ) :
      self.modelKomp.model.set_value(row, 7, False)
      #OkDialog(_('Pardonu, nur edzaj, eventaj, patraj, nomaj aŭ infanaj linioj povas esti elektitaj.'))
      OkDialog(_('Pardonu, nur edzaj, eventaj, patraj, aŭ infanaj linioj povas esti elektitaj.'))
      #print("  toggled:tipo="+str(tipo))

  def l_duobla_klako(self, treeview):
    (model, iter_) = treeview.get_selection().get_selected()
    if not iter_:
      return
    tipo=model.get_value(iter_, 8)
    handle = model.get_value(iter_, 9)
    if ( handle
         and ( tipo == 'infano' or tipo == 'patro'
            or tipo == 'patrino' or tipo == 'edzo')) :
      self.uistate.set_active(handle, 'Person')
    elif ( handle
         and (tipo == 'fakto' or tipo == 'edzoFakto')) :
      event = self.dbstate.db.get_event_from_handle(handle)
      try:
        EditEvent(self.dbstate, self.uistate, [], event)
      except WindowActiveError:
        pass
    elif ( handle
         and (tipo == 'NotoP' or tipo == 'NotoF' )) :
      noto = self.dbstate.db.get_note_from_handle(model.get_value(iter_, 10))
      try:
        EditNote(self.dbstate, self.uistate, [], noto)
      except WindowActiveError:
        pass
    elif ( handle
         and (tipo == 'Fonto' )) :
      cit = self.dbstate.db.get_citation_from_handle(handle)
      try:
        EditCitation(self.dbstate, self.uistate, [], cit)
      except WindowActiveError:
        pass

  def kopii_al_gramps(self, treeview):
    #print("kopii_al_gramps")
    self.uistate.set_busy_cursor(True)
    progress = ProgressMeter(_("Geneanet Kopio"), _('Kopio'),can_cancel=True,parent=self.uistate.window)
    progress.set_pass(_('Kopiante… ') , mode= ProgressMeter.MODE_ACTIVITY)
    model = self.modelKomp.model
    active_handle = self.get_active('Person')
    grPersono = self.dbstate.db.get_person_from_handle(active_handle)
    url = self.cbReg.get_active_text()
    extPersono = self.getPersono(url)
    if self.dbstate.db.transaction :
      print("??? transaction en cours ???")
      self.dbstate.db.transaction_commit(self.dbstate.db.transaction)
    db = self.dbstate.db
    novLokoj = dict()
    with DbTxn(_("kopii al gramps"), db) as txn:
      for x in model:
       l = [x]
       l.extend(x.iterchildren())
       progress.set_pass(_('Kopiante… ') , mode= ProgressMeter.MODE_ACTIVITY)
       for linio in l :
        progress.step()
        if not linio[7] : # si la ligne n'est pas cochée
          continue
        tipolinio = linio[8]
        if ( (tipolinio == 'nomo' or tipolinio == 'nomo1')
             and linio[5] ) :
          grNomo_str = linio[9]
          print(_("nomimporto ankoraŭ ne efektivigita_"))
          #ImportoGN.aldNomo(db, txn, fsNomo, grPersono)
        elif tipolinio == 'patro' :
          extPatro = extPersono['person']['father']  # fiche simplifiée du père
          urlPatro = geneanet.id2url(extPatro)
          extPatro = self.getPersono(urlPatro)  # fiche détaillée du père
          grPatro = aldPersono(novLokoj, db, txn, extPatro, progress, PersonGN.gn_notoj, PersonGN.gn_osm)
          family_handle = grPersono.get_main_parents_family_handle()
          if family_handle:
            familio = db.get_family_from_handle(family_handle)
            father_handle = familio.get_father_handle()
            if father_handle:
              OkDialog(_('Ĉi tiu persono jam havas patron'))
              continue
            familio.set_father_handle(grPatro.get_handle())
            grPatro.add_family_handle(familio.get_handle())
            db.commit_family(familio, txn)
            db.commit_person(grPatro, txn)
          else :
            familio = Family()
            familio.set_father_handle(grPatro.get_handle())
            db.add_family(familio, txn)
            db.commit_family(familio, txn)
            grPatro.add_family_handle(familio.get_handle())
            childref = ChildRef()
            childref.set_reference_handle(active_handle)
            familio.add_child_ref(childref)
            grPersono.add_parent_family_handle(familio.get_handle())
            db.commit_family(familio, txn)
            db.commit_person(grPatro, txn)
            db.commit_person(grPersono, txn)
        elif tipolinio == 'patrino' :
          extPatrino = extPersono['person']['mother']  # fiche simplifiée de la mère
          urlPatrino = geneanet.id2url(extPatrino)
          extPatrino = self.getPersono(urlPatrino)  # fiche détaillée de la mère
          grPatrino = aldPersono(novLokoj, db, txn, extPatrino, progress, PersonGN.gn_notoj, PersonGN.gn_osm)
          family_handle = grPersono.get_main_parents_family_handle()
          if family_handle:
            familio = db.get_family_from_handle(family_handle)
            mother_handle = familio.get_mother_handle()
            if mother_handle:
              OkDialog(_('Ĉi tiu individuo jam havas patrinon'))
              continue
            familio.set_mother_handle(grPatrino.get_handle())
            grPatrino.add_family_handle(familio.get_handle())
            db.commit_family(familio, txn)
            db.commit_person(grPatrino, txn)
          else :
            familio = Family()
            familio.set_mother_handle(grPatrino.get_handle())
            db.add_family(familio, txn)
            db.commit_family(familio, txn)
            grPatrino.add_family_handle(familio.get_handle())
            childref = ChildRef()
            childref.set_reference_handle(active_handle)
            familio.add_child_ref(childref)
            grPersono.add_parent_family_handle(familio.get_handle())
            db.commit_family(familio, txn)
            db.commit_person(grPatrino, txn)
            db.commit_person(grPersono, txn)
        elif tipolinio == 'fakto' and (linio[10] or '') != '' :
          extFakto = eval(linio[10])
          grFaktoH = linio[9]
          if grFaktoH :
            event = db.get_event_from_handle(grFaktoH)
            updFakto(novLokoj, db,txn,grPersono,extPersono,event,extFakto)
          else :
            event = aldFakto(novLokoj, db,txn,grPersono,extPersono,extFakto)
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
          if event.type == EventType.BIRTH :
            grPersono.set_birth_ref(er)
          elif event.type == EventType.DEATH :
            grPersono.set_death_ref(er)
        elif tipolinio == 'edzo' and linio[12] :
          extFamId = int(linio[12])
          for f in extPersono['person'].get('families') :
            if f.get('index')==extFamId :
              extFamilio = f
              break
          extEdzo = extFamilio.get('spouse')  # fiche simplifiée du conjoint
          urlEdzo = geneanet.id2url(extEdzo)
          extEdzo = self.getPersono(urlEdzo)  # fiche détaillée du conjoint
          grEdzo = aldPersono(novLokoj, db, txn, extEdzo, progress, PersonGN.gn_notoj, PersonGN.gn_osm)
          familio = Family()
          db.add_family(familio, txn)
          if grPersono.get_gender() == Person.MALE :
            familio.set_father_handle(grPersono.get_handle())
            familio.set_mother_handle(grEdzo.get_handle())
          else :
            familio.set_mother_handle(grPersono.get_handle())
            familio.set_father_handle(grEdzo.get_handle())
          db.commit_family(familio, txn)
          grPersono.add_family_handle(familio.get_handle())
          db.commit_person(grPersono, txn)
          grEdzo.add_family_handle(familio.get_handle())
          db.commit_person(grEdzo, txn)
          if ((extFamilio.get('marriageDateLong') or '') != '' 
             or (extFamilio.get('marriagePlace') or '') != '' ):
            event = Event()
            dato = extFamilio.get('marriageDateLong')
            if dato :
              grDato = parserEn.parse(dato)
              if grDato :
                event.set_date_object( grDato )
            loko = unescape(extFamilio.get('marriagePlace') or '')
            if loko != '' :
              grLoko = akiriLoko(novLokoj, db, txn, loko, PersonGN.gn_osm)
              event.set_place_handle(grLoko.handle)
            if extFamilio.get('marriageType') == "MARRIED" :
              event.set_type(EventType.MARRIAGE)
            else :
              print("type de mariage à traiter : %s" % extFamilio.get('marriageType'))
            db.add_event(event, txn)
            db.commit_event(event, txn)
            er = EventRef()
            er.set_role(EventRoleType.PRIMARY)
            er.set_reference_handle(event.get_handle())
            db.commit_event(event, txn)
            familio.add_event_ref(er)
            db.commit_family(familio, txn)

        elif tipolinio == 'infano' :
          urlInfano = linio[10]
          extInfano = self.getPersono(urlInfano)  # fiche détaillée de l'enfant
          grInfano = aldPersono(novLokoj, db, txn, extInfano, progress, PersonGN.gn_notoj, PersonGN.gn_osm)
          family_handle = linio[11]
          if family_handle:
            familio = db.get_family_from_handle(family_handle)
            childref = ChildRef()
            childref.set_reference_handle(grInfano.get_handle())
            familio.add_child_ref(childref)
            db.commit_family(familio, txn)
            grInfano.add_parent_family_handle(family_handle)
            db.commit_person(grInfano, txn)
        else :
          print(" import de %s pas encore implémenté_" % tipolinio)
      db.commit_person(grPersono,txn)
      db.transaction_commit(txn)
    db.enable_signals()
    progress.close()
    self.uistate.set_busy_cursor(False)
    self.ButRefresxigi_clicked(None)
    if len(novLokoj) > 0 :
      WarningDialog(_('\tLa jenaj lokoj estis kreitaj dum la importado,\n vi devus kontroli ilin nun:\n\n')
         , '\n'.join(['%s : %s' % kv for kv in novLokoj.items()]))

  def l_dekstra_klako(self, treeview, event):
    menu = Gtk.Menu()
    menu.set_reserve_toggle_size(False)
    (model, iter_) = treeview.get_selection().get_selected()
    if iter_:
      tipo=model.get_value(iter_, 8)
      handle = model.get_value(iter_, 9)
      extUrl = model.get_value(iter_, 10)
      if ( extUrl
         and (    tipo == 'infano' or tipo == 'patro'
               or tipo == 'patrino' or tipo == 'edzo'
            )) :
        item = Gtk.MenuItem(label=_('Kopii json-datumojn al tondujo'))
        item.set_sensitive(1)
        item.connect("activate",lambda obj: self.kopiijson(treeview))
        item.show()
        menu.append(item)
      if ( handle
         and (    tipo == 'infano' or tipo == 'patro'
               or tipo == 'patrino' or tipo == 'edzo'
               or tipo == 'fakto' or tipo == 'edzoFakto'
               or tipo == 'Bildo'
            )) :
        item = Gtk.MenuItem(label=_('Redakti : %s - %s - %s')% (model.get_value(iter_,1),model.get_value(iter_,2),model.get_value(iter_,3)))
        item.set_sensitive(1)
        item.connect("activate",lambda obj: self.redakti(treeview))
        item.show()
        menu.append(item)
    model = self.modelKomp.model
    # est-ce qu'il y a une ligne cochée copiable vers gramps ?
    cpt = 0
    for x in model:
     l = [x]
     l.extend(x.iterchildren())
     for linio in l :
      if not linio[7] :
        continue
      tipolinio = linio[8]
      grHandle = linio[9]
      if ( ( (tipolinio == 'patro' or tipolinio=='patrino' or tipolinio=='edzo' or tipolinio=='infano'
             )
             and grHandle is None)
         ) :
        cpt += 1
      elif ( tipolinio == 'fakto' and (linio[10] or '') != '' ) :
        cpt += 1
    if cpt >0 :
      item = Gtk.MenuItem(label=_('Kopii elekton de Geneanet al gramps'))
      item.set_sensitive(1)
      item.connect("activate",lambda obj: self.kopii_al_gramps(treeview))
      item.show()
      menu.append(item)
    self.menu = menu
    self.menu.popup(None, None, None, None, event.button, event.time)

  def redakti(self, treeview):
    (model, iter_) = treeview.get_selection().get_selected()
    if not iter_:
      return
    tipo=model.get_value(iter_, 8)
    handle = model.get_value(iter_, 9)
    if not handle :
      return
    if ( tipo == 'infano' or tipo == 'patro'
            or tipo == 'patrino' or tipo == 'edzo') :
      person = self.dbstate.db.get_person_from_handle(handle)
      try:
        EditPerson(self.dbstate, self.uistate, [], person)
      except WindowActiveError:
        pass
    elif (tipo == 'fakto' or tipo == 'edzoFakto') :
      event = self.dbstate.db.get_event_from_handle(handle)
      try:
        EditEvent(self.dbstate, self.uistate, [], event)
      except WindowActiveError:
        pass
    elif (tipo == 'Bildo' ) :
      m = self.dbstate.db.get_media_from_handle(handle)
      try:
        EditMedia(self.dbstate, self.uistate, [],m)
      except WindowActiveError:
        pass

  def kopiijson(self, treeview):
    (model, iter_) = treeview.get_selection().get_selected()
    if not iter_:
      return
    tipo=model.get_value(iter_, 8)
    extUrl = model.get_value(iter_, 10)
    extPersono = self.getPersono(extUrl)
    self.uistate.window.get_clipboard(Gdk.SELECTION_CLIPBOARD).set_text(json.dumps(extPersono, indent=2, default = str), -1)

  def SerSelCxangxo(self, dummy):
    model, iter_ = self.top.get_object("PersonGNResRes").get_selection().get_selected()
    if iter_ :
      lien = 'https://gw.geneanet.org/'+model.get_value(iter_, 0)
      self.top.get_object("LinkoButonoSercxi").set_label('voir sur geneanet')
      self.top.get_object("LinkoButonoSercxi").set_uri(lien)
    else :
      self.top.get_object("LinkoButonoSercxi").set_label('xxxx')
      self.top.get_object("LinkoButonoSercxi").set_uri('https://www.geneanet.org/')

  def getPersono(self, url) :
    extPersono = PersonGN.GnPersonoj.get(url)
    if extPersono is None :
      tmp = urlparse(url)
      q = parse_qs(tmp.query)
      x=dict()
      x['tree']= tmp.path[1:]
      if 'n' in q :
        x['n']=q['n'][0]
      if 'p' in q :
        x['p']=q['p'][0]
      if 'oc' in q :
        x['oc']=int(q['oc'][0])
      url=geneanet.id2url(x)
      extPersono = PersonGN.GnPersonoj.get(url)
    if extPersono is None :
      extPersono = self.gn.getPerson(x)
      PersonGN.GnPersonoj[geneanet.id2url(extPersono)] = extPersono
      if len(PersonGN.GnPersonoj) >100 : # ne pas garder plus de 100 personnes en mémoire
        PersonGN.GnPersonoj.pop(next(iter(PersonGN.GnPersonoj)))
    return extPersono


  def ButRefresxigi_clicked(self, dummy):
    url = self.cbReg.get_active_text()
    extPersono = self.getPersono(url)
    active_handle = self.get_active('Person')
    grPersono = self.dbstate.db.get_person_from_handle(active_handle)
    self.modelKomp.cid=None
    self.modelKomp.model.set_sort_column_id(-2,0)
    self.modelKomp.clear()
    if active_handle:
      self.set_has_data(True)
      kompariGrExt(grPersono , extPersono , self.dbstate.db , self.modelKomp)
    else:
      self.set_has_data(False)

  def get_has_data(self, active_handle):
    """
    " Return True if the gramplet has data, else return False.
    """
    if active_handle:
      return True
    return False

  def active_changed(self,handle) :
    self.cbReg.clear()
    self.modelKomp.clear()

  def pref_clicked(self, dummy):
    top = self.top.get_object("PersonGNPrefDialogo")
    top.set_transient_for(self.uistate.window)
    parent_modal = self.uistate.window.get_modal()
    if parent_modal:
      self.uistate.window.set_modal(False)
    gn_osm = self.top.get_object("gn_osm")
    gn_osm.set_active(PersonGN.gn_osm)
    gn_notoj = self.top.get_object("gn_notoj")
    gn_notoj.set_active(PersonGN.gn_notoj)
    top.show()
    res = top.run()
    top.hide()
    if res == -3: 
      PersonGN.gn_osm = gn_osm.get_active()
      CONFIG.set("preferences.gn_osm", str(PersonGN.gn_osm))
      PersonGN.gn_notoj = gn_notoj.get_active()
      CONFIG.set("preferences.gn_notoj", str(PersonGN.gn_notoj))
      CONFIG.save()

  def CB_Regximo_changed(self, dummy):
    self.ButRefresxigi_clicked(dummy)

  def ButLancxi_clicked(self, dummy):
    self.TreeRes.hide()
    self.KreiSercxiModel()
    self.top.get_object("PersonGNResRes").set_fixed_height_mode(False)
    progress = ProgressMeter(_("Geneanet Serĉo"), _trans.gettext('Serĉante'),can_cancel=True,parent=self.uistate.window)
    self.uistate.set_busy_cursor(True)
    progress.set_pass(_('Serĉante… ') , 12, mode= ProgressMeter.MODE_FRACTION)
    logged = self.gn.logged()
    progress.step()
    mendo = "https://www.geneanet.org/fonds/individus/?go=1&categories_1__arbres__=arbres&categories_2__arbres%23utilisateur__=arbres%23utilisateur"
    grNomo = self.top.get_object("gn_nomo_eniro").get_text()
    if grNomo :
      mendo = mendo + "&nom=%s" % quote_plus(grNomo)
    grANomo = self.top.get_object("gn_anomo_eniro").get_text()
    if grANomo :
      mendo = mendo + "&prenom=%s" % quote_plus(grANomo)
    sekso = self.top.get_object("gn_sekso_eniro").get_text()
    if sekso :
      if sekso[0] == 'M':
        mendo += "&sexe=1"
      elif sekso[0] == 'F':
        mendo += "&sexe=2"
    dato1 = self.top.get_object("gn_dato1").get_text()
    dato2 = self.top.get_object("gn_dato2").get_text()
    if dato1 and dato2 :
      mendo = mendo + "&type_periode=between&from="+quote_plus(dato1)+"&to="+quote_plus(dato2)
    elif dato1 :
      mendo = mendo + "&type_periode=after&from="+dato1
    elif dato2 :
      mendo = mendo + "&type_periode=before&from=&to"+dato2
    loko = self.top.get_object("gn_loko_eniro").get_text()
    if loko :
      mendo += "&place__0__="+quote_plus(loko)
    #print ("Genanet Serĉo : %s." % mendo )
    r = self.gn.urlopen(mendo)
    progress.step()
    if r == None :
      print(_('Eraro: neniuj datumoj.'))
    else :
      #print("réception ok")
      try:
        tree = html.fromstring(r.decode('utf-8'))
      except:
        print(_("Unable to perform HTML analysis"))
      tableau = tree.xpath('//div[@id="table-resultats"]//a')
      linio = 1
      PrevUrl = None
      for r in tableau :
        if progress.get_cancelled():
          break;
        progress.set_header(_('Elŝutante personojn… (%s/10)') % linio )
        linio += 1
        url = r.xpath('attribute::href')[0]
        if url == PrevUrl :
          continue
        PrevUrl = url
        #print(" url=",url)
        p = self.getPersono(url)
        sosa=''
        parents = ''
        naissance=''
        deces=''
        conjoints=''
        if 'person' in p :
          nom = ( p['person'].get('lastname') or '?') + ' ' + ( p['person'].get('firstname') or '?')
          if 'sosa' in p['person'] and p['person']['sosa']=='SOSA' :
            sosa = p['person'].get('sosaNb') or 'X'
          if 'father' in p['person'] :
            parents = ( p['person']['father'].get('lastname') or '?' ) + ' ' + ( p['person']['father'].get('firstname') or '?')
          if 'mother' in p['person'] :
            parents += '\n' + ( p['person']['mother'].get('lastname') or '?' ) + ' ' + ( p['person']['mother'].get('firstname') or '?')
          if 'birthDate' in p['person'] :
            naissance = p['person']['birthDate']
          if 'birthPlace' in p['person'] :
            naissance += '\n'+ p['person']['birthPlace']
          if 'deathDate' in p['person'] :
            deces = p['person']['deathDate']
          if 'deathPlace' in p['person'] :
            deces += '\n'+ p['person']['deathPlace']
          if 'families' in p['person'] :
            for f in p['person']['families'] :
              if 'children' in f :
                nbInfanoj = len(f['children'])
              else :
                nbInfanoj = 0
              if 'spouse' in f :
                if conjoints != '' :
                  conjoints +="\n"
                  sosa +="\n"
                sp = f['spouse']
                conjoints += str(nbInfanoj) + ', ' + ( sp.get('lastname') or '?' ) + ' ' + ( sp.get('firstname') or '?' )
        else :
          nom = ( p.get('n') or '?' ) +' ' + ( p.get('p') or '?' )
        self.modelRes.add( (url.removeprefix('https://gw.geneanet.org/'),sosa,nom,naissance,deces,parents,conjoints));
        progress.step()
    self.uistate.set_busy_cursor(False)
    progress.close()
    self.TreeRes.show()

  def ButAldoni_clicked(self, dummy):
    model, iter_ = self.top.get_object("PersonGNResRes").get_selection().get_selected()
    if iter_ :
      lien = 'https://gw.geneanet.org/'+model.get_value(iter_, 0)
      active_handle = self.get_active('Person')
      grPersono = self.dbstate.db.get_person_from_handle(active_handle)
      self.Sercxi.hide()
      self.cbReg.insert_text(0,lien)
      self.cbReg.set_active(0)

  def KreiSercxiModel(self) :
    titles = [  
                (_trans.gettext('URL'), 1, 80),
                (_trans.gettext('Sosa'), 2, 40),
                (_('Nomo, antaŭnomo'), 3, 200),
                (_trans.gettext('Naskiĝo'), 4, 250),
                (_trans.gettext('Morto'), 5, 250),
                (_trans.gettext('Gepatroj'), 6, 250),
                (_trans.gettext('Nb Inf., Geedzoj'), 7, 250),
             ]
    self.TreeRes.set_model(None)
    if self.modelRes :
      self.modelRes.clear()
      del self.modelRes
    for col in self.TreeRes.get_columns() :
      self.TreeRes.remove_column(col)
    self.modelRes = ListModel(self.TreeRes, titles,self.SerSelCxangxo)

  def ButSercxi_clicked(self, dummy):
    if not self.Sercxi :
      self.Sercxi = self.top.get_object("PersonGNRes")
      self.Sercxi.set_transient_for(self.uistate.window)
      parent_modal = self.uistate.window.get_modal()
      if parent_modal:
        self.uistate.window.set_modal(False)
      self.TreeRes = self.top.get_object("PersonGNResRes")
    active_handle = self.get_active('Person')
    person = self.dbstate.db.get_person_from_handle(active_handle)
    grNomo = person.primary_name
    self.top.get_object("gn_nomo_eniro").set_text(person.primary_name.get_surname())
    self.top.get_object("gn_anomo_eniro").set_text(person.primary_name.first_name)
    if person.get_gender() == Person.MALE :
      self.top.get_object("gn_sekso_eniro").set_text('M')
    elif person.get_gender() == Person.FEMALE :
      self.top.get_object("gn_sekso_eniro").set_text('F')
    grBirth = get_grevent(self.dbstate.db, person, EventType(EventType.BIRTH))
    if grBirth == None or grBirth.date == None or grBirth.date.is_empty() :
      grBirth = get_grevent(self.dbstate.db, person, EventType(EventType.CHRISTEN))
    if grBirth == None or grBirth.date == None or grBirth.date.is_empty() :
      grBirth = get_grevent(self.dbstate.db, person, EventType(EventType.ADULT_CHRISTEN))
    if grBirth == None or grBirth.date == None or grBirth.date.is_empty() :
      grBirth = get_grevent(self.dbstate.db, person, EventType(EventType.BAPTISM))
    if grBirth and grBirth.date and not grBirth.date.is_empty() :
      naskoDato = str(grBirth.date)
      if len(naskoDato) >0 and naskoDato[0] == 'A' : naskoDato = naskoDato[1:]
      elif len(naskoDato) >0 and naskoDato[0] == '/' : naskoDato = naskoDato[1:]
      posSep = naskoDato.find('/')
      if posSep > 1 : naskoDato = naskoDato[:posSep]
      posSep = naskoDato.find('-')
      if posSep > 1 : naskoDato = naskoDato[:posSep]
      posSep = naskoDato.find(' ')
      if posSep > 1 : naskoDato = naskoDato[posSep+1:]
      self.top.get_object("gn_dato1").set_text( naskoDato)
      #self.top.get_object("gn_dato1").set_text( str(grBirth.date.year()))
    else:
      self.top.get_object("gn_dato1").set_text( '')

    grDeath = get_grevent(self.dbstate.db, person, EventType(EventType.DEATH))
    if grDeath == None or grDeath.date == None or grDeath.date.is_empty() :
      grDeath = get_grevent(self.dbstate.db, person, EventType(EventType.BURIAL))
    if grDeath == None or grDeath.date == None or grDeath.date.is_empty() :
      grDeath = get_grevent(self.dbstate.db, person, EventType(EventType.CREMATION))
    if grDeath and grDeath.date and not grDeath.date.is_empty() :
      mortoDato = str(grDeath.date)
      if len(mortoDato) >0 and mortoDato[0] == 'A' : mortoDato = mortoDato[1:]
      if len(mortoDato) >0 and mortoDato[0] == '/' : mortoDato = mortoDato[1:]
      posSep = mortoDato.find('/')
      if posSep > 1 : mortoDato = mortoDato[:posSep]
      posSep = mortoDato.find('-')
      if posSep > 1 : mortoDato = mortoDato[:posSep]
      self.top.get_object("gn_dato2").set_text( mortoDato)
    else:
      self.top.get_object("gn_dato2").set_text( '')

    if grBirth and grBirth.place and grBirth.place != None :
      place = self.dbstate.db.get_place_from_handle(grBirth.place)
      self.top.get_object("gn_loko_eniro").set_text( place.name.value)
    else :
      self.top.get_object("gn_loko_eniro").set_text( '')

    self.ButLancxi_clicked(None)
    self.Sercxi.show()
    res = self.Sercxi.run()
    #print ("res = " + str(res))
    self.Sercxi.hide()
    #"""
    return

