#
# Gramplet - fs (interfaco por familysearch)
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
fs Gramplet.
"""

import json
import email.utils

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
from gramps.gen.datehandler import get_date
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.display.place import displayer as _pd
from gramps.gen.errors import WindowActiveError
from gramps.gen.lib import Citation, Date, EventRef, EventType, EventRoleType, Name, NameType, NoteType, Person, StyledText, StyledTextTag, StyledTextTagType, Tag, Note
from gramps.gen.plug import Gramplet, PluginRegister
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback

from gramps.gui.dialog import OptionDialog, OkDialog , WarningDialog
from gramps.gui.editors import EditCitation, EditPerson, EditEvent
from gramps.gui.listmodel import ListModel, NOSORT, COLOR, TOGGLE
from gramps.gui.viewmanager import run_plugin
from gramps.gui.widgets.buttons import IconButton
from gramps.gui.widgets.styledtexteditor import StyledTextEditor

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

# gedcomx_v1 biblioteko. Instalu kun `pip install --user --upgrade --break-system-packages gedcomx_v1`
mingedcomx="1.0.21"
import importlib
from importlib.metadata import version
try:
  v = version('gedcomx_v1')
except :
  v="0.0.0"
from packaging.version import parse
if parse(v) < parse(mingedcomx) :
  print (_('gedcomx_v1 ne trovita aŭ < %s' % mingedcomx))
  import pip
  pip.main(['install', '--user', '--upgrade', '--break-system-packages', 'gedcomx_v1'])
import gedcomx_v1

# lokaloj importadoj
from constants import GRAMPS_GEDCOMX_FAKTOJ
import fs_db
import komparo
import tree
import utila
import Importo
from utila import get_fsftid, get_grevent, get_fsfact, grdato_al_formal

import sys
import os
import time


#from objbrowser import browse ;browse(locals())
#import pdb; pdb.set_trace()

#-------------------------------------------------------------------------
#
# configuration
#
#-------------------------------------------------------------------------

GRAMPLET_CONFIG_NAME = "PersonFS"
CONFIG = config.register_manager(GRAMPLET_CONFIG_NAME)
# salutnomo kaj pasvorto por FamilySearch
CONFIG.register("preferences.fs_sn", '')
CONFIG.register("preferences.fs_pasvorto", '') #
CONFIG.register("preferences.fs_etikedado", '') #
CONFIG.register("preferences.fs_client_id", '') #
CONFIG.load()


class PersonFS(Gramplet):
  """
  " Interfaco kun familySearch
  """
  fs_sn = CONFIG.get("preferences.fs_sn")
  fs_pasvorto = ''
  fs_pasvorto = CONFIG.get("preferences.fs_pasvorto") #
  fs_client_id = CONFIG.get("preferences.fs_client_id") #
  # fs_etikedado = True se ne definita
  fs_etikedado = not CONFIG.get("preferences.fs_etikedado") == 'False'
  print("fs_etikedado="+str(fs_etikedado))
  fs_Tree = None
  fs_TreeSercxo = None
  Sercxi = None
  Dup = None
  lingvo = None
  FSID = None
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

  def aki_sesio(vokanto,vorteco=0):
    if not tree._FsSeanco:
      if PersonFS.fs_sn == '' or PersonFS.fs_pasvorto == '':
        import locale, os
        gtk = Gtk.Builder()
        gtk.set_translation_domain("addon")
        base = os.path.dirname(__file__)
        glade_file = base + os.sep + "PersonFS.glade"
        if os.name == 'win32' or os.name == 'nt' :
          import xml.etree.ElementTree as ET
          xtree = ET.parse(glade_file)
          for node in xtree.iter() :
            if 'translatable' in node.attrib :
              node.text = _(node.text)
          xml_text = ET.tostring(xtree.getroot(),encoding='unicode',method='xml')
          gtk.add_from_string(xml_text)
        else:
          locale.bindtextdomain("addon", base + "/locale")
          gtk.add_from_file(glade_file)

        top = gtk.get_object("PersonFSPrefDialogo")
        top.set_transient_for(vokanto.uistate.window)
        parent_modal = vokanto.uistate.window.get_modal()
        if parent_modal:
          vokanto.uistate.window.set_modal(False)
        xfsid = gtk.get_object("fssn_eniro")
        xfsid.set_text(PersonFS.fs_sn)
        fspv = gtk.get_object("fspv_eniro")
        fspv.set_text(PersonFS.fs_pasvorto)
        fsetik = gtk.get_object("fsetik_eniro")
        fsetik.set_active(PersonFS.fs_etikedado)
        top.show()
        res = top.run()
        top.hide()
        if res == -3:
          PersonFS.fs_sn = xfsid.get_text()
          PersonFS.fs_pasvorto = fspv.get_text()
          PersonFS.fs_etikedado = fsetik.get_active()
          print("PersonFS.fs_etikedado="+str(PersonFS.fs_etikedado))
          CONFIG.set("preferences.fs_sn", PersonFS.fs_sn)
          #CONFIG.set("preferences.fs_pasvorto", PersonFS.fs_pasvorto) #
          CONFIG.set("preferences.fs_etikedado", str(PersonFS.fs_etikedado))
          CONFIG.save()
          if vorteco >= 3:
            tree._FsSeanco = gedcomx_v1.FsSession(PersonFS.fs_sn, PersonFS.fs_pasvorto, True, False, 2, PersonFS.lingvo)
          else :
            tree._FsSeanco = gedcomx_v1.FsSession(PersonFS.fs_sn, PersonFS.fs_pasvorto, False, False, 2, PersonFS.lingvo)
          if PersonFS.fs_client_id != '':
            tree._FsSeanco.client_id=PersonFS.fs_client_id
          #else :
          #tree._FsSeanco = gedcomx_v1.FsSession(PersonFS.fs_sn, PersonFS.fs_pasvorto, False, False, 2, PersonFS.lingvo)
        else :
          print("Vi devas enigi la ID kaj pasvorton")
      else:
        if vorteco >= 3:
          tree._FsSeanco = gedcomx_v1.FsSession(PersonFS.fs_sn, PersonFS.fs_pasvorto, True, False, 2, PersonFS.lingvo)
        else :
          tree._FsSeanco = gedcomx_v1.FsSession(PersonFS.fs_sn, PersonFS.fs_pasvorto, False, False, 2, PersonFS.lingvo)
          if PersonFS.fs_client_id != '':
            tree._FsSeanco.client_id=PersonFS.fs_client_id
        tree._FsSeanco.login()
      print(" langage session FS = "+tree._FsSeanco.lingvo);
      if tree._FsSeanco.stato == gedcomx_v1.fs_session.STATO_PASVORTA_ERARO :
         WarningDialog(_('Pasvorta erraro. La funkcioj de FamilySearch ne estos disponeblaj.'))
      elif not tree._FsSeanco.logged :
        WarningDialog(_('Malsukcesa konekto. La funkcioj de FamilySearch ne estos disponeblaj.'))

    return tree._FsSeanco


  def init(self):
    """
    " kreas GUI kaj konektas al FamilySearch
    """
    # FARINDAĴO : uzi PersonFS.lingvo

    self.gui.WIDGET = self.krei_gui()
    self.gui.get_container_widget().remove(self.gui.textview)
    self.gui.get_container_widget().add_with_viewport(self.gui.WIDGET)
    self.gui.WIDGET.show_all()


  def konekti_FS(self):
    if PersonFS.fs_sn == '' or PersonFS.fs_pasvorto == '':
      self.pref_clicked(None)
    if not tree._FsSeanco:
      print("konektas al FS")
      tree._FsSeanco = gedcomx_v1.FsSession(PersonFS.fs_sn, PersonFS.fs_pasvorto, True, False, 2, PersonFS.lingvo)
      #tree._FsSeanco = gedcomx_v1.FsSession(PersonFS.fs_sn, PersonFS.fs_pasvorto, False, False, 2, PersonFS.lingvo)
      if PersonFS.fs_client_id != '':
        tree._FsSeanco.client_id=PersonFS.fs_client_id
      tree._FsSeanco.login()
    if tree._FsSeanco.stato == gedcomx_v1.fs_session.STATO_PASVORTA_ERARO :
      WarningDialog(_('Pasvorta eraro. La funkcioj de FamilySearch ne estos disponeblaj.'))
      return
    elif not tree._FsSeanco.logged :
      WarningDialog(_('Malsukcesa konekto. La funkcioj de FamilySearch ne estos disponeblaj.'))
      return
    if not PersonFS.fs_Tree:
      PersonFS.fs_Tree = tree.Tree()
      PersonFS.fs_Tree._getsources = False

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
         and (tipo == 'Fonto' )) :
      cit = self.dbstate.db.get_citation_from_handle(handle)
      try:
        EditCitation(self.dbstate, self.uistate, [], cit)
      except WindowActiveError:
        pass



  def redakti(self, treeview):
    (model, iter_) = treeview.get_selection().get_selected()
    if not iter_:
      return
    tipo=model.get_value(iter_, 8)
    handle = model.get_value(iter_, 9)
    if ( handle
         and ( tipo == 'infano' or tipo == 'patro'
            or tipo == 'patrino' or tipo == 'edzo')) :
      person = self.dbstate.db.get_person_from_handle(handle)
      try:
        EditPerson(self.dbstate, self.uistate, [], person)
      except WindowActiveError:
        pass
    elif ( handle
         and (tipo == 'fakto' or tipo == 'edzoFakto')) :
      event = self.dbstate.db.get_event_from_handle(handle)
      try:
        EditEvent(self.dbstate, self.uistate, [], event)
      except WindowActiveError:
        pass

  def kopii_al_FS(self, treeview):
    print("kopii_al_FS")
    model = self.modelKomp.model
    active_handle = self.get_active('Person')
    grPersono = self.dbstate.db.get_person_from_handle(active_handle)
    # on va construire 2 gedcomx_v1 :
    # fsTP va contenir la personne principale, avec ses évènements, notes, …
    fsTP = gedcomx_v1.Gedcomx()
    # fsTR va contenir les personnes reliées, avec leurs évènement, notes, …
    fsTR = gedcomx_v1.Gedcomx()
    # fsP est la personne principale
    fsP = gedcomx_v1.Person()
    for x in model:
     l = [x]
     l.extend(x.iterchildren())
     for linio in l :
      if linio[7] : 
        tipolinio = linio[8]
        if ( (tipolinio == 'fakto' or tipolinio == 'edzoFakto')
             and linio[9] ) :
          grHandle = linio[9]
          event = self.dbstate.db.get_event_from_handle(grHandle)
          titolo = str(EventType(event.type))
          grFaktoPriskribo = event.description or ''
          grFaktoDato = grdato_al_formal(event.date)
          if event.place and event.place != None :
            place = self.dbstate.db.get_place_from_handle(event.place)
            grFaktoLoko = _pd.display(self.dbstate.db,place)
          else :
            grFaktoLoko = ''
          # FARINDAĴO : norma loknomo
          if grFaktoLoko == '' :
            grValoro = grFaktoPriskribo
          else :
            grValoro = grFaktoPriskribo +' @ '+ grFaktoLoko
          fsFakto = gedcomx_v1.Fact()
          fsFaktoId = get_fsftid(event)
          if fsFaktoId != '' :
            fsFakto.id = fsFaktoId
          grTag = int(event.type)
          tipo = GRAMPS_GEDCOMX_FAKTOJ.get(grTag) or GRAMPS_GEDCOMX_FAKTOJ.get(str(event.type)) or str(event.type)
          if tipo[:6] == 'http:/' or tipo[:6] == 'data:,' :
            fsFakto.type = tipo
          else :
            fsFakto.type = 'data:,'+tipo
          fsFakto.value = grFaktoPriskribo
          if grFaktoDato :
            fsFakto.date = gedcomx_v1.Date()
            fsFakto.date.original = event.date.text
            if not fsFakto.date.original or fsFakto.date.original=='' :
              fsFakto.date.original = get_date(event)
            fsFakto.date.formal = gedcomx_v1.DateFormal(grFaktoDato)
            if str(fsFakto.date.formal) == '' :
              fsFakto.date.formal = None
          if grFaktoLoko :
            fsFakto.place = gedcomx_v1.PlaceReference()
            fsFakto.place.original = grFaktoLoko
          if tipolinio == 'fakto' :
            fsTP.persons.add(fsP)
            fsP.facts.add(fsFakto)
          elif tipolinio == 'edzoFakto' :
            # FS n'accepte que les évènements suivants sur un mariage : «Mariage», «Annulation»,«Divorce»,«Mariage de droit coutumier»,«A vécu maritalement», «Aucun enfant».
            # ni konvertas MARR_CONTR,ENGAGEMENT al MARRIAGE + klarigo
            if ( grTag == EventType.MARR_CONTR
                  or grTag == EventType.MARR_BANNS
                  or grTag == EventType.ENGAGEMENT ) :
              tipo = GRAMPS_GEDCOMX_FAKTOJ.get(EventType.MARRIAGE)
              fsFakto.type = tipo
              fsFakto.attribution = gedcomx_v1.Attribution()
              fsFakto.attribution.changeMessage = GRAMPS_GEDCOMX_FAKTOJ.get(grTag) + '\n' + str(event)
            fsTR = gedcomx_v1.Gedcomx()
            grFamilyHandle = linio[11]
            RSfsid = linio[12]
            grFamily = self.dbstate.db.get_family_from_handle(grFamilyHandle)
            fsRS = gedcomx_v1.Relationship()
            fsRS.id = RSfsid
            fsRS.facts.add(fsFakto)
            fsTR.relationships.add(fsRS)
            peto = gedcomx_v1.jsonigi(fsTR)
            jsonpeto = json.dumps(peto)
            if RSfsid :
              res = tree._FsSeanco.post_url( "/platform/tree/couple-relationships/"+RSfsid, jsonpeto )
              if res.status_code == 201 or res.status_code == 204:
                print("ĝisdatigo sukceso")
              if res.status_code != 201 and res.status_code != 204 :
                print("ĝisdatigo rezulto :")
                print(" jsonpeto = "+jsonpeto)
                print(" res.status_code="+str(res.status_code))
                print (res.headers)
                print (res.text)
            #else : FARINDAĴO
        elif ( (tipolinio == 'nomo' or tipolinio == 'nomo1')
             and linio[9] ) :
          strNomo = linio[9]
          grSurname = linio[11]
          grGiven = linio[12]
          fsNomoId = linio[10]
          if tipolinio == 'nomo1' :
            grNomo = grPersono.primary_name
          else :
            grNomo = None
            for grN in grPersono.alternate_names :
              if strNomo == str(grN) :
                grNomo = grN
                break
            if not grNomo :
              for grNomo in grPersono.alternate_names :
                if (     grNomo.get_surname() == grSurname
                     and grNomo.first_name == grGiven) :
                  break
          fsNomo = gedcomx_v1.Name()
          if tipolinio == 'nomo1':
            fsNomo.preferred = True
          else:
            fsNomo.preferred = False
          if fsNomoId :
            fsNomo.id = fsNomoId
          if grNomo.type == NameType(NameType.MARRIED) :
            fsNomo.type = 'http://gedcomx.org/MarriedName'
          elif grNomo.type ==  NameType(NameType.AKA) :
            fsNomo.type = 'http://gedcomx.org/AlsoKnownAs'
          elif grNomo.type == NameType(NameType.BIRTH) :
             fsNomo.type = 'http://gedcomx.org/BirthName'
          else : 
            fsNomo.type = "http://gedcomx.org/BirthName"
          fsNF = gedcomx_v1.NameForm()
          fsNP = gedcomx_v1.NamePart()
          fsNP.type = "http://gedcomx.org/Surname"
          fsNP.value = grSurname
          fsNF.parts.add (fsNP)
          fsNP = gedcomx_v1.NamePart()
          fsNP.type = "http://gedcomx.org/Given"
          fsNP.value = grGiven
          fsNF.parts.add (fsNP)
          fsNomo.nameForms.add(fsNF)
          fsP.names.add(fsNomo)
          fsP.id = self.FSID
          fsTP.persons.add(fsP)
        elif ( (tipolinio == 'edzo' )
             and linio[9] ) :
          grEdzo = self.dbstate.db.get_person_from_handle(linio[8])
          fsTR = gedcomx_v1.Gedcomx()
          grFamilyHandle = linio[11]
          RSfsid = linio[12]
          grFamily = self.dbstate.db.get_family_from_handle(grFamilyHandle)
          fsRS = gedcomx_v1.Relationship()
          fsRS.person1 = gedcomx_v1.ResourceReference()
          fsRS.person2 = gedcomx_v1.ResourceReference()
          fsRS.id = RSfsid
          fsRS.type = "http://gedcomx.org/Couple"
          if grEdzo.get_gender() == Person.MALE :
            fsRS.person1.resourceId = get_fsftid(grEdzo)
            fsRS.person2.resourceId = get_fsftid(grPersono)
          else:
            fsRS.person2.resourceId = get_fsftid(grEdzo)
            fsRS.person1.resourceId = get_fsftid(grPersono)
          fsRS.person1.resource = "https://api.familysearch.org/platform/tree/persons/" + fsRS.person1.resourceId
          fsRS.person2.resource = "https://api.familysearch.org/platform/tree/persons/" + fsRS.person2.resourceId
          fsTR.relationships.add(fsRS)
          peto = gedcomx_v1.jsonigi(fsTR)
          jsonpeto = json.dumps(peto)
          if RSfsid and RSfsid != '' :
            res = tree._FsSeanco.post_url( "/platform/tree/couple-relationships/"+RSfsid, jsonpeto )
          else :
            res = tree._FsSeanco.post_url( "/platform/tree/relationships", jsonpeto )
          if res.status_code == 201 or res.status_code == 204:
            print("ĝisdatigo sukceso")
          if res.status_code != 201 and res.status_code != 204 :
            print("ĝisdatigo rezulto :")
            print(" jsonpeto = "+jsonpeto)
            print(" res.status_code="+str(res.status_code))
            print (res.headers)
            print (res.text)
        elif ( (tipolinio == 'infano' )
             and linio[9] and linio[10] == '') : # infano estas en gramps, ne en FS.
          grFamilyHandle = linio[11]
          fsFamId = linio[12]
          child_ref = linio[9]
          fsTR = gedcomx_v1.Gedcomx()
          fsCPRS = gedcomx_v1.ChildAndParentsRelationship()
          grFamily = self.dbstate.db.get_family_from_handle(grFamilyHandle)
          child = self.dbstate.db.get_person_from_handle(child_ref)
          fsCPRS.child = gedcomx_v1.ResourceReference()
          fsCPRS.child.resourceId = utila.get_fsftid(child)
          fsCPRS.child.resource = "https://api.familysearch.org/platform/tree/persons/" + fsCPRS.child.resourceId
          grhusband_handle = grFamily.get_father_handle()
          if grhusband_handle :
            gepatro1 = self.dbstate.db.get_person_from_handle(grhusband_handle)
            fsCPRS.parent1 = gedcomx_v1.ResourceReference()
            fsCPRS.parent1.resourceId = utila.get_fsftid(gepatro1)
            fsCPRS.parent1.resource = "https://api.familysearch.org/platform/tree/persons/" + fsCPRS.parent1.resourceId
          spouse_handle = grFamily.get_mother_handle()
          if spouse_handle :
            gepatro2 = self.dbstate.db.get_person_from_handle(spouse_handle)
            fsCPRS.parent2 = gedcomx_v1.ResourceReference()
            fsCPRS.parent2.resourceId = utila.get_fsftid(gepatro2)
            fsCPRS.parent2.resource = "https://api.familysearch.org/platform/tree/persons/" + fsCPRS.parent2.resourceId
          fsTR.childAndParentsRelationships.add(fsCPRS)
          peto = gedcomx_v1.jsonigi(fsTR)
          jsonpeto = json.dumps(peto)
          res = tree._FsSeanco.post_url( "/platform/tree/relationships", jsonpeto )
          if res.status_code == 201 or res.status_code == 204:
            print("ĝisdatigo sukceso")
          if res.status_code != 201 and res.status_code != 204 :
            print("ĝisdatigo rezulto :")
            print(" jsonpeto = "+jsonpeto)
            print(" res.status_code="+str(res.status_code))
            print (res.headers)
            print (res.text)
        elif ( (tipolinio == 'NotoF' )
             and linio[9] ) :
          print("NotoF gramps-->FS")
          # self.modelKomp.add(['white',titolo,_('Familio'),teksto,'',fsTeksto,'',False,'NotoF',nh,family_handle,fsParoId,fsNoto.id] )
          fsNoto = gedcomx_v1.Note()
          fsNoto.subject = linio[2]
          if len(linio[3]) >1 and linio[3][0:1] == '\ufeff' :
            fsNoto.text = linio[3][1:]
          else :
            fsNoto.text = linio[3]
          fsNoto.id = linio[12]
          fsTR = gedcomx_v1.Gedcomx()
          grFamilyHandle = linio[10]
          RSfsid = linio[11]
          grFamily = self.dbstate.db.get_family_from_handle(grFamilyHandle)
          fsRS = gedcomx_v1.Relationship()
          fsRS.id = RSfsid
          fsRS.notes.add(fsNoto)
          fsTR.relationships.add(fsRS)
          peto = gedcomx_v1.jsonigi(fsTR)
          jsonpeto = json.dumps(peto)
          print(" jsonpeto = "+jsonpeto)
          if RSfsid :
            res = tree._FsSeanco.post_url( "/platform/tree/couple-relationships/"+RSfsid, jsonpeto )
            if res.status_code == 201 or res.status_code == 204:
              print("ĝisdatigo sukceso")
            if res.status_code != 201 and res.status_code != 204 :
              print("ĝisdatigo rezulto :")
              print(" jsonpeto = "+jsonpeto)
              print(" res.status_code="+str(res.status_code))
              print (res.headers)
              print (res.text)
        elif ( (tipolinio == 'NotoP' )
             and linio[3] ) :
          print("NotoP gramps-->FS")
          fsNoto = gedcomx_v1.Note()
          fsNoto.subject = linio[2]
          if len(linio[3]) >1 and linio[3][0:1] == '\ufeff' :
            fsNoto.text = linio[3][1:]
          else :
            fsNoto.text = linio[3]
          fsNoto.id = linio[12]
          fsP.notes.add(fsNoto)
          fsP.id = self.FSID
          fsTP.persons.add(fsP)
        elif ( (tipolinio == 'Fonto' )
             and linio[2] ) :
          #### self.modelKomp.add([koloro,dato,titolo,grURL,fsDato,fsTitolo,fsURL,False,'Fonto',c.handle,sd_id,teksto,fsTeksto] )
          print("Fonto gramps-->FS")
          c = self.dbstate.db.get_citation_from_handle(linio[9])
          sd_id = utila.get_fsftid(c)
          fsFonto = gedcomx_v1.SourceDescription()
          fsFontoRef = gedcomx_v1.SourceReference()
          mFonto = Importo.MezaFonto()
          mFonto.deGramps(self.dbstate.db, c)
          mFonto.alFS(fsFonto,fsFontoRef)
          fsFonto.lang = PersonFS.lingvo
          if ( sd_id == '' or
               linio[1] != linio[4] or
               linio[2] != linio[5] or
               linio[3] != linio[6] or
               linio[11] != linio[12] ) :
            # il faut créer ou mettre à jour la source dans FS
            # créer la source :
            fsTPs = gedcomx_v1.Gedcomx()
            fsTPs.sourceDescriptions.add(fsFonto)
            peto = gedcomx_v1.jsonigi(fsTPs)
            jsonpeto = json.dumps(peto)
            if fsFonto.id :
              res = tree._FsSeanco.post_url( "/platform/sources/descriptions/"+fsFonto.id, jsonpeto )
            else :
              res = tree._FsSeanco.post_url( "/platform/sources/descriptions", jsonpeto )
            if not res :
              print("la ĝisdatigo ne havis rezulton por:")
              print(" jsonpeto = "+jsonpeto)
            else :
              print("ĝisdatigo rezulto :")
              print(" jsonpeto = "+jsonpeto)
              print(" res.status_code="+str(res.status_code))
              print (res.headers)
              print (res.text)
              # et récupérer son id :
              if sd_id=='' and res.headers.get('x-entity-id') :
                sd_id = res.headers['x-entity-id']
                fsFonto.id = sd_id
                fsFontoRef.id = sd_id
                utila.ligi_gr_fs(self.dbstate.db,c,sd_id)
            if linio[1] != linio[4] :
              # on passe par l'interface service, car l'interface api ne sait pas mettre à jour la date
              tmpFonto = gedcomx_v1.SourceDescription()
              tmpFonto.id = sd_id
              tmpFonto.title = mFonto.cTitolo
              tmpFonto.citation = mFonto.referenco
              tmpFonto.notes = mFonto.teksto
              tmpFonto.event = dict()
              tmpFonto.event['eventDate']=linio[1]
              tmpFonto.uri = dict()
              tmpFonto.uri['uri']=grURL
              peto = gedcomx_v1.jsonigi(tmpFonto)
              jsonpeto = json.dumps(peto)
              headers = {"Accept": "application/json","Content-Type": "application/json"}
              res = tree._FsSeanco.put_url( "https://www.familysearch.org/service/tree/links/source/"+sd_id+"?result=full", jsonpeto, headers )
              if not res :
                print("la ĝisdatigo ne havis rezulton por:")
                print(" jsonpeto = "+jsonpeto)
              else :
                print("ĝisdatigo rezulto :")
                print(" jsonpeto = "+jsonpeto)
                print(" res.status_code="+str(res.status_code))
                print (res.headers)
                print (res.text)
          fsP.sources.add(fsFontoRef)
          fsP.id = self.FSID
          fsTP.persons.add(fsP)
     # FARINDAĴO : gepatroj, infanoj,…

    if len(fsTP.persons) >0 :
      peto = gedcomx_v1.jsonigi(fsTP)
      jsonpeto = json.dumps(peto)
      res = tree._FsSeanco.post_url( "/platform/tree/persons/"+self.FSID, jsonpeto )
      if not res :
        print("la ĝisdatigo ne havis rezulton por:")
        print(" jsonpeto = "+jsonpeto)
      elif res.status_code == 201 or res.status_code == 204:
        print("ĝisdatigo sukceso")
      else :
        print("ĝisdatigo rezulto :")
        print(" jsonpeto = "+jsonpeto)
        print(" res.status_code="+str(res.status_code))
        print (res.headers)
        print (res.text)
    if len(fsTP.persons) >0 or len(fsTR.relationships) >0 :
      self.ButRefresxigi_clicked(None)
    
  def kopii_al_gramps(self, treeview):
    print("kopii_al_gramps")
    model = self.modelKomp.model
    active_handle = self.get_active('Person')
    grPersono = self.dbstate.db.get_person_from_handle(active_handle)
    fsPersono = gedcomx_v1.Person._indekso.get(self.FSID) 
    if self.dbstate.db.transaction :
      print("??? transaction en cours ???")
      self.dbstate.db.transaction_commit(self.dbstate.db.transaction)
    #  intr = True
    #  txn=self.dbstate.db.transaction
    #else :
    #  intr = False
    #  txn = DbTxn(_("kopii al gramps"), self.dbstate.db)
    #if txn :
    regximo = self.cbReg.get_active_id()
    with DbTxn(_("kopii al gramps"), self.dbstate.db) as txn:
      for x in model:
       l = [x]
       l.extend(x.iterchildren())
       for linio in l :
        tipolinio = linio[8]
        if ( (tipolinio == 'fakto' )
             and linio[7] 
             and linio[10] ) :
            fsFakto_id = linio[10]
            grFaktoH = linio[9]
            if fsPersono.facts:
              for fsFakto in fsPersono.facts :
                if fsFakto.id == fsFakto_id : break
              if fsFakto.id == fsFakto_id :
                print("importas fakto "+fsFakto_id+" por "+self.FSID)
                if grFaktoH :
                  event = self.dbstate.db.get_event_from_handle(grFaktoH)
                  Importo.updFakto(self.dbstate.db,txn,fsFakto,event)
                else :
                  event = Importo.aldFakto(self.dbstate.db,txn,fsFakto,grPersono)
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
        elif ( (tipolinio == 'edzoFakto')
             and linio[7] 
             and linio[10] 
             and linio[11] ) :
            grFaktoH = linio[9]
            fsFakto_id = linio[10]
            grParoH = linio[11]
            fsParo_id = linio[12]
            grParo = self.dbstate.db.get_family_from_handle(grParoH)
            fsParo = gedcomx_v1.Relationship._indekso[fsParo_id]
            for fsFakto in fsParo.facts :
              if fsFakto.id == fsFakto_id : break
            if grFaktoH :
              event = self.dbstate.db.get_event_from_handle(grFaktoH)
              Importo.updFakto(self.dbstate.db,txn,fsFakto,event)
            else :
              event = Importo.aldFakto(self.dbstate.db,txn,fsFakto,grParo)
            found = False
            for er in grParo.get_event_ref_list():
              if er.ref == event.handle:
                found = True
                break
            if not found:
              er = EventRef()
              er.set_role(EventRoleType.FAMILY)
              er.set_reference_handle(event.get_handle())
              self.dbstate.db.commit_event(event, txn)
              grParo.add_event_ref(er)
      
            self.dbstate.db.commit_family(grParo,txn)
        elif ( (tipolinio == 'nomo' or tipolinio == 'nomo1')
             and linio[7] 
             and linio[10] ) :
            grNomo_str = linio[9]
            fsNomo_id = linio[10]
            for fsNomo in fsPersono.names :
              if fsNomo.id == fsNomo_id : break
            Importo.aldNomo(self.dbstate.db, txn, fsNomo, grPersono)
        elif ( (tipolinio == 'NotoF' )
             and linio[7] 
              and linio[6] and linio[12] ) :
            print("NotoF FS-->gramps")
            # self.modelKomp.add(['white',_('Familio'),titolo,teksto,fsTitolo,fsTeksto,'',False,'NotoF',family_handle,nh,fsParoId,fsNoto.id] )
            grParoH = linio[9]
            grParo = self.dbstate.db.get_family_from_handle(grParoH)
            nh=linio[10]
            if nh :
              grNoto = self.dbstate.db.get_note_from_handle(nh)
            else :
              grNoto = Note()
            grNoto.set_type(NoteType(linio[4]))
            # on met un tag de type lien sur le premier caractère pour mémoriser l'ID FamilySearch :
            tags = [  StyledTextTag(StyledTextTagType.LINK,"_fsftid="+ linio[12],[(0, 1)])]
            # on ajoute un caractère invisible en début de texte :
            grNoto.set_styledtext(StyledText("\ufeff"+linio[5], tags))
            if not nh :
              self.dbstate.db.add_note(grNoto, txn)
            self.dbstate.db.commit_note(grNoto, txn)
            grParo.add_note(grNoto.handle)
            self.dbstate.db.commit_family(grParo,txn)
        elif ( (tipolinio == 'NotoP' )
             and linio[7] 
              and linio[6] and linio[12] ) :
            print("NotoP FS-->gramps")
            nh=linio[10]
            if nh :
              grNoto = self.dbstate.db.get_note_from_handle(nh)
            else :
              grNoto = Note()
            grNoto.set_type(NoteType(linio[4]))
            # on met un tag de type lien sur le premier caractère pour mémoriser l'ID FamilySearch :
            tags = [  StyledTextTag(StyledTextTagType.LINK,"_fsftid="+ linio[12],[(0, 1)])]
            # on ajoute un caractère invisible en début de texte :
            grNoto.set_styledtext(StyledText("\ufeff"+linio[5], tags))
            if not nh :
              self.dbstate.db.add_note(grNoto, txn)
            self.dbstate.db.commit_note(grNoto, txn)
            grPersono.add_note(grNoto.handle)
        elif ( (tipolinio == 'Fonto' ) and linio[10] and linio[7]) :
          fsSdId = linio[10]
          fh = linio[9]
          print(" fonto FS --> gramps, id="+fsSdId)
          citation = Importo.aldFonto(self.dbstate.db,txn,fsSdId,grPersono,grPersono.citation_list)
      self.dbstate.db.commit_person(grPersono,txn)
      self.dbstate.db.transaction_commit(txn)
    self.ButRefresxigi_clicked(None)

  def l_dekstra_klako(self, treeview, event):
    menu = Gtk.Menu()
    menu.set_reserve_toggle_size(False)
    (model, iter_) = treeview.get_selection().get_selected()
    if iter_:
      tipo=model.get_value(iter_, 8)
      handle = model.get_value(iter_, 9)
      if ( handle
         and (    tipo == 'infano' or tipo == 'patro'
               or tipo == 'patrino' or tipo == 'edzo'
               or tipo == 'fakto' or tipo == 'edzoFakto'
            )) :
        item  = Gtk.MenuItem(label=_('Redakti : %s - %s - %s')% (model.get_value(iter_,1),model.get_value(iter_,2),model.get_value(iter_,3)))
        item.set_sensitive(1)
        item.connect("activate",lambda obj: self.redakti(treeview))
        item.show()
        menu.append(item)
    item  = Gtk.MenuItem(label=_('Kopii elekton de gramps al FS'))
    item.set_sensitive(1)
    item.connect("activate",lambda obj: self.kopii_al_FS(treeview))
    item.show()
    menu.append(item)
    item  = Gtk.MenuItem(label=_('Kopii elekton de FS al gramps'))
    item.set_sensitive(1)
    item.connect("activate",lambda obj: self.kopii_al_gramps(treeview))
    item.show()
    menu.append(item)
    self.menu = menu
    self.menu.popup(None, None, None, None, event.button, event.time)


  def krei_gui(self):
    """
    " kreas GUI interfacon.
    """
    import locale,gettext, os
    self.top = Gtk.Builder()
    self.top.set_translation_domain("addon")
    base = os.path.dirname(__file__)
    glade_file = base + os.sep + "PersonFS.glade"
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

    self.res = self.top.get_object("PersonFSTop")
    self.propKomp = self.top.get_object("propKomp")
    self.cbReg = self.top.get_object("CB_Regximo")
    self.CB_Regximo_changed(None)
    self.top.connect_signals({
            "on_pref_clicked"      : self.pref_clicked,
            "on_ButImp1K_clicked"      : self.ButImp1K_clicked,
            "on_kopii_clicked"      : self.ButKopii_clicked,
            "on_ButSercxi_clicked"      : self.ButSercxi_clicked,
            "on_ButDup_clicked"      : self.ButDup_clicked,
            "on_ButLancxi_clicked"      : self.ButLancxi_clicked,
            "on_ButAldoni_clicked"      : self.ButAldoni_clicked,
            "on_ButLigi_clicked"      : self.ButLigi_clicked,
            "on_ButRefresxigi_clicked"      : self.ButRefresxigi_clicked,
            "on_ButImporti_clicked"      : self.ButImporti_clicked,
            "on_ButBaskKonf_toggled"      : self.ButBaskKonf_toggled,
            "on_CB_Regximo_changed"      : self.CB_Regximo_changed,
	})

    return self.res

  def toggled(self, path, val=None):
    row = self.modelKomp.model.get_iter((path,))
    regximo = self.cbReg.get_active_id()
    if regximo != 'REG_fontoj' :
      tipo=self.modelKomp.model.get_value(row, 8)
      #if tipo != 'fakto' and tipo != 'edzoFakto' :
      if (     tipo != 'fakto' and tipo != 'edzoFakto' and tipo != 'nomo' and tipo != 'nomo1' and tipo != 'edzo' 
         and tipo != 'NotoP' and tipo != 'NotoF'
         and tipo != 'infano'
         ) :
        self.modelKomp.model.set_value(row, 7, False)
        OkDialog(_('Pardonu, nur edzaj, eventaj, nomaj aŭ notaj linioj povas esti elektitaj.'))
        print("  toggled:tipo="+str(tipo))


  def CB_Regximo_changed(self, dummy):
    titles_komp_cxefa = [  
        (_('Koloro'), 1, 40,COLOR),
        ( _('Propreco'), 2, 100),
        ( _('Dato'), 3, 120),
        (_('Gramps Valoro'), 4, 300),
        (_('FS Dato'), 5, 120),
        (_('FS Valoro'), 6, 300),
        (' ', NOSORT, 1),
        ('x', 8, 5, TOGGLE,True,self.toggled),
        (_('xTipo'), NOSORT, 0),
        (_('xGr'), NOSORT, 0),
        (_('xFs'), NOSORT, 0),
        (_('xGr2'), NOSORT, 0),
        (_('xFs2'), NOSORT, 0),
     ]
    titles_komp_notoj = [  
        (_('Koloro'), 1, 40,COLOR),
        ( _('Propreco'), 2, 100),
        ( _('Titolo'), 3, 120),
        (_('Gramps Valoro'), 4, 300),
        (_('FS Titolo'), 5, 120),
        (_('FS Valoro'), 6, 300),
        (' ', NOSORT, 1),
        ('x', 8, 10, TOGGLE,True,self.toggled),
        (_('xTipo'), NOSORT, 0),
        (_('xGr'), NOSORT, 0),
        (_('xFs'), NOSORT, 0),
        (_('xGr2'), NOSORT, 0),
        (_('xFs2'), NOSORT, 0),
     ]
    titles_komp_fontoj = [  
        (_('Koloro'), 1, 40,COLOR),
        ( _('Dato'), 2, 100),
        ( _('Titolo'), 3, 120),
        (_('Gramps URL'), 4, 200),
        (_('FS Dato'), 5, 100),
        (_('FS Titolo'), 6, 120),
        (_('FS URL'), 7, 200),
        ('x', 8, 10, TOGGLE,True,self.toggled),
        (_('xTipo'), NOSORT, 0),
        (_('xGr'), NOSORT, 0),
        (_('xFs'), NOSORT, 0),
        (_('xGr2'), NOSORT, 0),
        (_('xFs2'), NOSORT, 0),
     ]
    regximo = self.cbReg.get_active_id()
    self.propKomp.set_model(None)
    if hasattr(self,'modelKomp') :
      del self.modelKomp
    for col in self.propKomp.get_columns() :
      self.propKomp.remove_column(col)
    if regximo == 'REG_fontoj' :
      self.modelKomp = ListModel(self.propKomp, titles_komp_fontoj, list_mode="tree"
                 ,event_func=self.l_duobla_klako
                 ,right_click=self.l_dekstra_klako)
    elif regximo == 'REG_notoj' :
      self.modelKomp = ListModel(self.propKomp, titles_komp_notoj, list_mode="tree"
                 ,event_func=self.l_duobla_klako
                 ,right_click=self.l_dekstra_klako)
    else :
      self.modelKomp = ListModel(self.propKomp, titles_komp_cxefa, list_mode="tree"
                 ,event_func=self.l_duobla_klako
                 ,right_click=self.l_dekstra_klako)
    self.ButRefresxigi_clicked(dummy)

  def ButBaskKonf_toggled(self, dummy):
   with DbTxn(_("FamilySearch etikedoj"), self.dbstate.db) as txn:
    val = self.top.get_object("ButBaskKonf").get_active()
    tag_fs = self.dbstate.db.get_tag_from_name('FS_Konf')
    active_handle = self.get_active('Person')
    grPersono = self.dbstate.db.get_person_from_handle(active_handle)
    if not val and tag_fs.handle in grPersono.tag_list:
      grPersono.remove_tag(tag_fs.handle)
    if tag_fs and val and tag_fs.handle not in grPersono.tag_list:
      grPersono.add_tag(tag_fs.handle)
      dbPersono= fs_db.db_stato(self.dbstate.db,grPersono.handle)
      dbPersono.get()
      dbPersono.konf = val
      dbPersono.commit(txn)
    self.dbstate.db.commit_person(grPersono, txn, grPersono.change)
    self.dbstate.db.transaction_commit(txn)

  def ButRefresxigi_clicked(self, dummy):
    if self.FSID :
      fsPersono = gedcomx_v1.Person._indekso.get(self.FSID)
      if fsPersono:
        for paro in fsPersono._paroj :
          paro.person1=None
          paro.person2=None
          paro.facts=set()
        fsPersono.facts=set()
        fsPersono.names=set()
        fsPersono.notes=set()
        fsPersono.sources=set()
        fsPersono._gepatroj =set()
        fsPersono._infanoj=set()
        fsPersono._paroj=set()
        fsPersono._infanojCP = set()
        fsPersono._gepatrojCP=set()
        fsPersono.sortKey = None
      for sd in gedcomx_v1.SourceDescription._indekso.values() :
        sd.notes=set()
        sd.citations=set()
      if PersonFS.fs_Tree and self.FSID in PersonFS.fs_Tree._persons :
        PersonFS.fs_Tree._persons.pop(self.FSID)
      PersonFS.fs_Tree.add_persons([self.FSID])
    #rezulto = gedcomx_v1.jsonigi(PersonFS.fs_Tree)
    #f = open('arbo2.out.json','w')
    #json.dump(rezulto,f,indent=2)
    #f.close()

    active_handle = self.get_active('Person')
    self.modelKomp.cid=None
    self.modelKomp.model.set_sort_column_id(-2,0)
    self.modelKomp.clear()
    if active_handle:
      self.kompariFs(active_handle,True)
      self.set_has_data(self.get_has_data(active_handle))
    else:
      self.set_has_data(False)

  def ButImporti_clicked(self, dummy):
    gpr = PluginRegister.get_instance()
    plg = gpr.get_plugin('Importo de FamilySearch')
    run_plugin(plg,self.dbstate,self.uistate)

  def ButAldoni_clicked(self, dummy):
    active_handle = self.get_active('Person')
    person = self.dbstate.db.get_person_from_handle(active_handle)
    fsPerso = gedcomx_v1.Person()
    fsPerso.gender = gedcomx_v1.Gender()
    fsPerso.living = False
    if person.get_gender() == Person.MALE :
      fsPerso.gender.type = "http://gedcomx.org/Male"
    elif person.get_gender() == Person.FEMALE :
      fsPerso.gender.type = "http://gedcomx.org/Female"
    else:
      fsPerso.gender.type = "http://gedcomx.org/Unknown"
    grNomo = person.primary_name
    nomo = gedcomx_v1.Name()
    nomo.surname = None
    if grNomo.type == 3 :
      nomo.type = 'http://gedcomx.org/MarriedName'
    elif grNomo.type == 1 :
      nomo.type = 'http://gedcomx.org/AlsoKnownAs'
    else :
      nomo.type = 'http://gedcomx.org/BirthName'
    nf = gedcomx_v1.NameForm()
    nomo.nameForms = set()
    nomo.nameForms.add(nf)
    nf.parts = set()
    np1=gedcomx_v1.NamePart()
    np1.type = "http://gedcomx.org/Given"
    np1.value = grNomo.first_name
    nf.parts.add(np1)
    np2=gedcomx_v1.NamePart()
    np2.type = "http://gedcomx.org/Surname"
    np2.value = grNomo.get_surname()
    nf.parts.add(np2)
    nomo.preferred = True
    fsPerso.names.add(nomo)
    # FARINDAĴO : aliaj nomoj
    #grFaktoj = person.event_ref_list
    #for grFakto in grFaktoj :
    #  if int(grFakto.get_role()) != EventRoleType.PRIMARY:
    #    continue
    #  event = self.dbstate.db.get_event_from_handle(grFakto.ref)
    #  titolo = str(EventType(event.type))
    #  grFaktoPriskribo = event.description or ''
    #  grFaktoDato = grdato_al_formal(event.date)
    #  if event.place and event.place != None :
    #    place = self.dbstate.db.get_place_from_handle(event.place)
    #    grFaktoLoko = place.name.value
    #  else :
    #    grFaktoLoko = ''
    #  # FARINDAĴO : norma loknomo
    #  if grFaktoLoko == '' :
    #    grValoro = grFaktoPriskribo
    #  else :
    #    grValoro = grFaktoPriskribo +' @ '+ grFaktoLoko
    #  grTag = PERSONALCONSTANTEVENTS.get(int(event.type), "").strip() or event.type
    #  fsFakto = gedcomx_v1.Fact()
    #  fsFakto.date = gedcomx_v1.Date()
    #  fsFakto.date.original = grFaktoDato
    #  fsFakto.type = GRAMPS_GEDCOMX_FAKTOJ.get(grTag)
    #  fsFakto.place = grFaktoLoko
    #  fsFakto.value = grFaktoPriskribo
    #  fsPerso.facts.add(fsFakto)
    # FARINDAĴOJ : fontoj, …
    peto = {'persons' : [gedcomx_v1.jsonigi(fsPerso)]}
    jsonpeto = json.dumps(peto)
    res = tree._FsSeanco.post_url( "/platform/tree/persons", jsonpeto )
    if res :
      if res.status_code==201 and res.headers and "X-Entity-Id" in res.headers :
        fsid = res.headers['X-Entity-Id']
        utila.ligi_gr_fs(self.dbstate.db, person, fsid)
        self.FSID = fsid
        self.ButRefresxigi_clicked(None)
        self.Sercxi.hide()
      else :
        print (res.headers)
    #  FARINDAĴOJ :
    #     1-  mettre à jour avec les noms et faits
    #     2-  lier aux parents
    #     3-  lier aux conjoints
    #     4-  lier aux enfants
    return

  def ButKopii_clicked(self, dummy):
    #self.FSID
    clipboard = Gtk.Clipboard.get_for_display(Gdk.Display.get_default(),
                        Gdk.SELECTION_CLIPBOARD)
    clipboard.set_text(self.FSID, -1)
    clipboard = Gtk.Clipboard.get_for_display(Gdk.Display.get_default(),
                        Gdk.SELECTION_PRIMARY)
    clipboard.set_text(self.FSID, -1)

    return

  def ButLigi_clicked(self, dummy):
    model, iter_ = self.top.get_object("PersonFSResRes").get_selection().get_selected()
    if iter_ :
      fsid = model.get_value(iter_, 1)
      #print(fsid)
      active_handle = self.get_active('Person')
      grPersono = self.dbstate.db.get_person_from_handle(active_handle)
      utila.ligi_gr_fs(self.dbstate.db, grPersono, fsid)
      self.ButRefresxigi_clicked(None)
      self.Sercxi.hide()
    return

  def SerSelCxangxo(self, dummy):
    model, iter_ = self.top.get_object("PersonFSResRes").get_selection().get_selected()
    if iter_ :
      fsid = model.get_value(iter_, 1)
      #print(fsid)
      self.top.get_object("LinkoButonoSercxi").set_label(fsid)
      lien = 'https://familysearch.org/tree/person/' + fsid
      self.top.get_object("LinkoButonoSercxi").set_uri(lien)
    else :
      self.top.get_object("LinkoButonoSercxi").set_label('xxxx-xxx')
      self.top.get_object("LinkoButonoSercxi").set_uri('https://familysearch.org/')

  def SerDupCxangxo(self, dummy):
    model, iter_ = self.top.get_object("PersonFSDupRes").get_selection().get_selected()
    if iter_ :
      fsid = model.get_value(iter_, 1)
      #print(fsid)
      self.top.get_object("LinkoButonoDup").set_label(fsid)
      lien = 'https://familysearch.org/tree/person/' + fsid
      self.top.get_object("LinkoButonoDup").set_uri(lien)
      self.top.get_object("LinkoButonoKunfando").set_label(self.FSID+'+'+fsid)
      lien = 'https://familysearch.org/tree/person/merge/verify/' +self.FSID+'/'  + fsid
      self.top.get_object("LinkoButonoKunfando").set_uri(lien)
    else :
      self.top.get_object("LinkoButonoDup").set_label('xxxx-xxx')
      self.top.get_object("LinkoButonoDup").set_uri('https://familysearch.org/')
      self.top.get_object("LinkoButonoKunfando").set_label('………')
      self.top.get_object("LinkoButonoKunfando").set_uri('https://familysearch.org/')
    return

  def ButDup_clicked(self, dummy):
    if not self.Dup :
      self.Dup = self.top.get_object("PersonFSDup")
      self.Dup.set_transient_for(self.uistate.window)
      parent_modal = self.uistate.window.get_modal()
      if parent_modal:
        self.uistate.window.set_modal(False)
      TreeRes = self.top.get_object("PersonFSDupRes")
      titles = [  
                (_trans.gettext('score'), 1, 80),
                (_('FS Id'), 2, 90),
                (_('Nomo, antaŭnomo'), 3, 200),
                (_trans.gettext('Birth'), 4, 250),
                (_trans.gettext('Death'), 5, 250),
                (_trans.gettext('Parents'), 6, 250),
                (_trans.gettext('Spouses'), 7, 250),
             ]
      self.modelRes = ListModel(TreeRes, titles,self.SerDupCxangxo)
    active_handle = self.get_active('Person')
    person = self.dbstate.db.get_person_from_handle(active_handle)
    grNomo = person.primary_name

    if not PersonFS.fs_TreeSercxo:
      PersonFS.fs_TreeSercxo = tree.Tree()
      PersonFS.fs_TreeSercxo._getsources = False
    self.modelRes.cid=None
    self.modelRes.model.set_sort_column_id(-2,0)
    self.modelRes.clear()
    mendo = "/platform/tree/persons/"+self.FSID+"/matches"
    r = tree._FsSeanco.get_url(
                    mendo ,{"Accept": "application/x-gedcomx-atom+json"}
                )
    if r == None :
      OkDialog(_('Eraro: neniuj datumoj.'))
    elif r.status_code == 200 :
      self.DatRes(r.json())
      self.Dup.show()
      res = self.Dup.run()
      print ("res = " + str(res))
      self.Dup.hide()
    elif r.status_code == 204 :
      OkDialog(_('Neniuj verŝajnaj duplikatoj por la persono %s trovita de la retejo "FamilySearch".')% self.FSID)
    return

  def ButSercxi_clicked(self, dummy):
    if not self.Sercxi :
      self.Sercxi = self.top.get_object("PersonFSRes")
      self.Sercxi.set_transient_for(self.uistate.window)
      parent_modal = self.uistate.window.get_modal()
      if parent_modal:
        self.uistate.window.set_modal(False)
      TreeRes = self.top.get_object("PersonFSResRes")
      titles = [  
                (_trans.gettext('score'), 1, 80),
                (_('FS Id'), 2, 90),
                (_('Nomo, antaŭnomo'), 3, 200),
                (_trans.gettext('Birth'), 4, 250),
                (_trans.gettext('Death'), 5, 250),
                (_trans.gettext('Parents'), 6, 250),
                (_trans.gettext('Spouses'), 7, 250),
             ]
      self.modelRes = ListModel(TreeRes, titles,self.SerSelCxangxo)
    active_handle = self.get_active('Person')
    person = self.dbstate.db.get_person_from_handle(active_handle)
    grNomo = person.primary_name
    self.top.get_object("fs_nomo_eniro").set_text(person.primary_name.get_surname())
    self.top.get_object("fs_anomo_eniro").set_text(person.primary_name.first_name)
    if person.get_gender() == Person.MALE :
      self.top.get_object("fs_sekso_eniro").set_text('Male')
    elif person.get_gender() == Person.FEMALE :
      self.top.get_object("fs_sekso_eniro").set_text('Female')
    grBirth = get_grevent(self.dbstate.db, person, EventType(EventType.BIRTH))
    if grBirth == None or grBirth.date == None or grBirth.date.is_empty() :
      grBirth = get_grevent(self.dbstate.db, person, EventType(EventType.CHRISTEN))
    if grBirth == None or grBirth.date == None or grBirth.date.is_empty() :
      grBirth = get_grevent(self.dbstate.db, person, EventType(EventType.ADULT_CHRISTEN))
    if grBirth == None or grBirth.date == None or grBirth.date.is_empty() :
      grBirth = get_grevent(self.dbstate.db, person, EventType(EventType.BAPTISM))
    if grBirth and grBirth.date and not grBirth.date.is_empty() :
      naskoDato = grdato_al_formal(grBirth.date)
      if len(naskoDato) >0 and naskoDato[0] == 'A' : naskoDato = naskoDato[1:]
      if len(naskoDato) >0 and naskoDato[0] == '/' : naskoDato = naskoDato[1:]
      posOblikvo = naskoDato.find('/')
      if posOblikvo > 1 : naskoDato = naskoDato[:posOblikvo]
      self.top.get_object("fs_nasko_eniro").set_text( naskoDato)
    else:
      self.top.get_object("fs_nasko_eniro").set_text( '')

    grDeath = get_grevent(self.dbstate.db, person, EventType(EventType.DEATH))
    if grDeath == None or grDeath.date == None or grDeath.date.is_empty() :
      grDeath = get_grevent(self.dbstate.db, person, EventType(EventType.BURIAL))
    if grDeath == None or grDeath.date == None or grDeath.date.is_empty() :
      grDeath = get_grevent(self.dbstate.db, person, EventType(EventType.CREMATION))
    if grDeath and grDeath.date and not grDeath.date.is_empty() :
      mortoDato = grdato_al_formal(grDeath.date)
      if len(mortoDato) >0 and mortoDato[0] == 'A' : mortoDato = mortoDato[1:]
      if len(mortoDato) >0 and mortoDato[0] == '/' : mortoDato = mortoDato[1:]
      posOblikvo = mortoDato.find('/')
      if posOblikvo > 1 : mortoDato = mortoDato[:posOblikvo]
      self.top.get_object("fs_morto_eniro").set_text( mortoDato)
    else:
      self.top.get_object("fs_morto_eniro").set_text( '')

    if grBirth and grBirth.place and grBirth.place != None :
      place = self.dbstate.db.get_place_from_handle(grBirth.place)
      self.top.get_object("fs_loko_eniro").set_text( place.name.value)
    else :
      self.top.get_object("fs_loko_eniro").set_text( '')

    self.ButLancxi_clicked(None)
    self.Sercxi.show()
    res = self.Sercxi.run()
    print ("res = " + str(res))
    self.Sercxi.hide()
    return

  def ButLancxi_clicked(self, dummy):
    if not PersonFS.fs_TreeSercxo:
      PersonFS.fs_TreeSercxo = tree.Tree()
      PersonFS.fs_TreeSercxo._getsources = False
    self.modelRes.cid=None
    self.modelRes.model.set_sort_column_id(-2,0)
    self.modelRes.clear()
    mendo = "/platform/tree/search?"
    grNomo = self.top.get_object("fs_nomo_eniro").get_text()
    if grNomo :
      mendo = mendo + "q.surname=%s&" % grNomo
    grANomo = self.top.get_object("fs_anomo_eniro").get_text()
    if grANomo :
      mendo = mendo + "q.givenName=%s&" % grANomo
    sekso = self.top.get_object("fs_sekso_eniro").get_text()
    if sekso :
      mendo = mendo + "q.sex=%s&" % sekso
    nasko = self.top.get_object("fs_nasko_eniro").get_text()
    if nasko :
      mendo = mendo + "q.birthLikeDate=%s&" % nasko
    morto = self.top.get_object("fs_morto_eniro").get_text()
    if morto :
      mendo = mendo + "q.deathLikeDate=%s&" % morto
    loko = self.top.get_object("fs_loko_eniro").get_text()
    if loko :
      mendo = mendo + "q.anyPlace=%s&" % loko
    mendo = mendo + "offset=0&count=50"
    datumoj = tree._FsSeanco.get_jsonurl(
                    mendo ,{"Accept": "application/x-gedcomx-atom+json"}
                )
    if not datumoj :
      return
    #tot = datumoj["results"]
    #print ("nb résultats = "+str(tot))
    self.DatRes(datumoj)
    self.Sercxi.show()

  def DatRes(self,datumoj):
    for entry in datumoj["entries"] :
      #print (entry.get("id")+ ";  score = "+str(entry.get("score")))
      fsId = entry.get("id")
      data=entry["content"]["gedcomx"]
      # bizare, FamilySearch ne uzas gedcomx-formaton
      #gedcomx.maljsonigi(PersonFS.fs_TreeSercxo, data )
      if "places" in data:
        for place in data["places"]:
          if place["id"] not in PersonFS.fs_TreeSercxo._places:
            if 'latitude' in place and 'longitude' in place :
              PersonFS.fs_TreeSercxo._places[place["id"]] = (
                                str(place["latitude"]),
                                str(place["longitude"]),
                            )
      father = None
      fatherId = None
      mother = None
      motherId = None
      if "persons" in data:
        for person in data["persons"]:
          PersonFS.fs_TreeSercxo._persons[person["id"]] = gedcomx_v1.Person(person["id"], PersonFS.fs_TreeSercxo)
          gedcomx_v1.maljsonigi(PersonFS.fs_TreeSercxo._persons[person["id"]],person)
        for person in data["persons"]:
          if "ascendancyNumber" in person["display"] and person["display"]["ascendancyNumber"] == 1 :
            if person["gender"]["type"] == "http://gedcomx.org/Female" :
              motherId=person["id"]
              mother=PersonFS.fs_TreeSercxo._persons[person["id"]]
            elif person["gender"]["type"] == "http://gedcomx.org/Male" :
              fatherId=person["id"]
              father=PersonFS.fs_TreeSercxo._persons[person["id"]]
      fsPerso = PersonFS.fs_TreeSercxo._persons.get(fsId) or gedcomx_v1.Person()
      edzoj = ''
      if "relationships" in data:
        for rel in data["relationships"]:
          if rel["type"] == "http://gedcomx.org/Couple":
            person1Id = rel["person1"]["resourceId"]
            person2Id = rel["person2"]["resourceId"]
            edzoId = None
            if person2Id==fsId:
              edzoId = person1Id
            elif person1Id==fsId:
              edzoId = person2Id
            if edzoId:
              fsEdzo = PersonFS.fs_TreeSercxo._persons.get(edzoId) or gedcomx_v1.Person()
              fsEdzoNomo = fsEdzo.akPrefNomo()
              if edzoj != '': edzoj = edzoj + "\n"
              edzoj = edzoj + fsEdzoNomo.akSurname() +  ', ' + fsEdzoNomo.akGiven()
          elif rel["type"] == "http://gedcomx.org/ParentChild":
            person1Id = rel["person1"]["resourceId"]
            person2Id = rel["person2"]["resourceId"]
            if person2Id == fsId :
              person1=PersonFS.fs_TreeSercxo._persons[person1Id]
              if not father and person1.gender.type == "http://gedcomx.org/Male" :
                father = person1
              elif not mother and person1.gender.type == "http://gedcomx.org/Female" :
                mother = person1
              
      fsNomo = fsPerso.akPrefNomo()
      fsBirth = get_fsfact (fsPerso, 'http://gedcomx.org/Birth' ) or gedcomx_v1.Fact()
      fsBirthLoko = fsBirth.place 
      if fsBirthLoko :
        fsBirth = str(fsBirth.date or '') + ' \n@ ' +fsBirthLoko.original
      else :
        fsBirth = str(fsBirth.date or '')
      fsDeath = get_fsfact (fsPerso, 'http://gedcomx.org/Death' ) or gedcomx_v1.Fact()
      fsDeathLoko = fsDeath.place 
      if fsDeathLoko :
        fsDeath = str(fsDeath.date or '') + ' \n@ ' +fsDeathLoko.original
      else :
        fsDeath = str(fsDeath.date or '')
      if father :
        fsPatroNomo = father.akPrefNomo()
      else:
        fsPatroNomo = gedcomx_v1.Name()
      if mother :
        fsPatrinoNomo = mother.akPrefNomo()
      else:
        fsPatrinoNomo = gedcomx_v1.Name()
      self.modelRes.add( ( 
		  str(entry.get("score"))
		, fsId
		, fsNomo.akSurname() +  ', ' + fsNomo.akGiven()
		, fsBirth
		, fsDeath
                , fsPatroNomo.akSurname() +  ', ' + fsPatroNomo.akGiven()
                   + '\n'+fsPatrinoNomo.akSurname() +  ', ' + fsPatrinoNomo.akGiven()
		, edzoj
		) )
    return

  def ButImp1K_clicked(self, dummy):
    active_handle = self.get_active('Person')
    grPersono = self.dbstate.db.get_person_from_handle(active_handle)
    importilo = Importo.FsAlGr()
    fsid = get_fsftid(grPersono)
    importilo.importi(self, fsid)
    #import cProfile
    #cProfile.runctx('importilo.importi(self, fsid)',globals(),locals())
    self.uistate.set_active(active_handle, 'Person')

  def pref_clicked(self, dummy):
    top = self.top.get_object("PersonFSPrefDialogo")
    top.set_transient_for(self.uistate.window)
    parent_modal = self.uistate.window.get_modal()
    if parent_modal:
      self.uistate.window.set_modal(False)
    fssn = self.top.get_object("fssn_eniro")
    fssn.set_text(PersonFS.fs_sn)
    fspv = self.top.get_object("fspv_eniro")
    fspv.set_text(PersonFS.fs_pasvorto)
    fsetik = self.top.get_object("fsetik_eniro")
    print("fs_etikedado="+str(PersonFS.fs_etikedado))
    fsetik.set_active(PersonFS.fs_etikedado)
    top.show()
    res = top.run()
    top.hide()
    if res == -3:
      PersonFS.fs_sn = fssn.get_text()
      PersonFS.fs_pasvorto = fspv.get_text()
      PersonFS.fs_etikedado = fsetik.get_active()
      print("fs_etikedado="+str(PersonFS.fs_etikedado))
      CONFIG.set("preferences.fs_sn", PersonFS.fs_sn)
      #CONFIG.set("preferences.fs_pasvorto", PersonFS.fs_pasvorto) #
      CONFIG.set("preferences.fs_etikedado", str(PersonFS.fs_etikedado))
      CONFIG.save()
      self.konekti_FS()
    

  def get_has_data(self, active_handle):
    """
    " Return True if the gramplet has data, else return False.
    """
    if active_handle:
      return True
    return False

  def db_changed(self):
    self.update()

  def active_changed(self, handle):
    self.update()

  def update_has_data(self):
    active_handle = self.get_active('Person')
    if active_handle:
      self.set_has_data(self.get_has_data(active_handle))
    else:
      self.set_has_data(False)

  def main(self):
    if not tree._FsSeanco:
      self.konekti_FS()
    active_handle = self.get_active('Person')
    self.modelKomp.cid=None
    self.modelKomp.model.set_sort_column_id(-2,0)
    self.modelKomp.clear()
    if active_handle:
      self.kompariFs(active_handle,False)
      self.set_has_data(self.get_has_data(active_handle))
    else:
      self.set_has_data(False)

  def kompariFs(self, person_handle, getfs):
    """
    " Komparas gramps kaj FamilySearch
    """
    fs_db.create_schema(self.dbstate.db)
    if PersonFS.fs_etikedado :
      fs_db.create_tags(self.dbstate.db)
    self.FSID = None
    grPersono = self.dbstate.db.get_person_from_handle(person_handle)
    tag_fs = self.dbstate.db.get_tag_from_name('FS_Konf')
    if tag_fs and tag_fs.handle in grPersono.tag_list :
      self.top.get_object("ButBaskKonf").set_active(True)
    else :
      self.top.get_object("ButBaskKonf").set_active(False)
      
    fsid = get_fsftid(grPersono)
    self.FSID = fsid
    if fsid == '' :
      fsid = 'xxxx-xxx'
      lien = 'https://familysearch.org/'
    else :
      lien = 'https://familysearch.org/tree/person/' + fsid
    self.top.get_object("LinkoButono").set_label(fsid)
    self.top.get_object("LinkoButono").set_uri(lien)
    ## Se fsid ne estas specifita: nenio pli :
    ##if fsid == '' or fsid == 'xxxx-xxx' :
    ##  return

    ### Se ĝi ne estas konektita al familysearch: nenio pli.
    ##if tree._FsSeanco == None or not tree._FsSeanco.logged:
    ##  return
    #
    PersonFS.FSID = self.FSID
    fsPerso = gedcomx_v1.Person()
    if PersonFS.FSID != '' and PersonFS.fs_Tree :
      # ŝarĝante individuan "FamilySearch" :
      PersonFS.fs_Tree.add_persons([fsid])
      #fsPerso = gedcomx_v1.Person._indekso.get(fsid) 
      fsPerso = PersonFS.fs_Tree._persons.get(fsid)
      # legas persona kaplinio
      mendo = "/platform/tree/persons/"+fsid
      r = tree._FsSeanco.head_url( mendo )
      if r and r.status_code == 301 and 'X-Entity-Forwarded-Id' in r.headers :
        fsid = r.headers['X-Entity-Forwarded-Id']
        PersonFS.FSID = fsid
        utila.ligi_gr_fs(self.dbstate.db, grPersono, fsid)
        mendo = "/platform/tree/persons/"+fsid
        r = tree._FsSeanco.head_url( mendo )
      if r :
        datemod = int(time.mktime(email.utils.parsedate(r.headers['Last-Modified'])))
        etag = r.headers['Etag']
      if not fsPerso :
        PersonFS.fs_Tree.add_persons([fsid])
        fsPerso = gedcomx_v1.Person._indekso.get(fsid) or gedcomx_v1.Person()
      if fsPerso and fsid != PersonFS.FSID :
        fsPerso.id=fsid

      if getfs == True :
        PersonFS.fs_Tree.add_spouses([fsid])
        PersonFS.fs_Tree.add_children([fsid])
    regximo = self.cbReg.get_active_id()
    if regximo == 'REG_fontoj' :
      datumoj = tree._FsSeanco.get_jsonurl("/platform/tree/persons/%s/sources" % fsPerso.id)
      gedcomx_v1.maljsonigi(PersonFS.fs_Tree,datumoj)
      if not PersonFS.fs_Tree:
        colFS = _('Ne konektita al FamilySearch')
      else :
        colFS = '===================='
      # création de la liste des sources : sources de la personne
      fsFontIdj = dict()
      for x in fsPerso.sources :
        fsFontIdj[x.descriptionId]=None
      # ajout des sources des familles :
      for paro in fsPerso._paroj :
        for x in paro.sources :
          fsFontIdj[x.descriptionId]=None
      # on efface les dates des sources, pour forcer leur mise à jour
      for x in fsFontIdj :
        sd =  gedcomx_v1.SourceDescription._indekso.get(x) or gedcomx_v1.SourceDescription()
        fsFontIdj[x] = sd
        if hasattr(sd,'_date') :
          delattr(sd,'_date')
      # on récupère les données manquantes des sources (date, note, collection, film)
      Importo.akFontDatoj(PersonFS.fs_Tree)
      # on crée la liste des citations gramps
      cl = set(grPersono.get_citation_list())
      # ajout des citations liées aux évènements
      for er in grPersono.get_event_ref_list() :
        event = self.dbstate.db.get_event_from_handle(er.ref)
        cl.update(event.get_citation_list())
      # ajout des citations liées aux familles
      for family_handle in grPersono.get_family_handle_list():
        family = self.dbstate.db.get_family_from_handle(family_handle)
        cl.update(family.get_citation_list())
        # ajout des citations liées aux évènements des familles
        for er in family.get_event_ref_list() :
          event = self.dbstate.db.get_event_from_handle(er.ref)
          cl.update(event.get_citation_list())
      for ch in cl :
        c = self.dbstate.db.get_citation_from_handle(ch)
        titolo = ""
        # on cherche la première note de type Citation,
        #   le titre sera la première ligne de cette note.
        for nh in c.note_list :
          n = self.dbstate.db.get_note_from_handle(nh)
          if n.type == NoteType.CITATION :
            titolo = n.get()
            posRet = titolo.find("\n")
            if(posRet>0) :
              titolo = titolo[:posRet]
            break
        teksto = ""
        # le texte sera la concaténation des notes
        for nh in c.note_list :
          n = self.dbstate.db.get_note_from_handle(nh)
          teksto += n.get()
        dato = utila.grdato_al_formal(c.date)
        grURL = utila.get_url(c)
        referenco = c.page
        # la référence sera : titre dépôt + titre source + volume/page --> référence
        if c.source_handle :
          s = self.dbstate.db.get_source_from_handle(c.source_handle)
          if s :
            referenco = s.title + '\n' + referenco
            if len(s.reporef_list)>0 :
              dh = s.reporef_list[0].ref
              d = self.dbstate.db.get_repository_from_handle(dh)
              if d :
                referenco = d.name + '\n' + referenco
        koloro = "white"
        fsTeksto = colFS
        fsURL = ""
        fsDato = ""
        fsTitolo = ""
        sd_id=""
        fsid = utila.get_fsftid(c)
        sd = fsFontIdj.get(fsid)
        if sd :
            sd_id = sd.id
            for y in sd.titles :
              fsTitolo += y.value
            if len(sd.titles):
              cTitolo = next(iter(sd.titles)).value
            else:
              cTitolo=''
            komNoto = '\n'
            if sd.resourceType == 'FSREADONLY':
              linioj = next(iter(sd.citations)).value.split("\"")
              if len(linioj) >=3 :
                sTitolo = linioj[1]
                komNoto = komNoto + '\n'.join(linioj[2:])
            fsTeksto=cTitolo+komNoto
            for fsN in sd.notes :
              if fsN.subject :
                fsTeksto = fsTeksto+'\n'+fsN.subject
              if fsN.text :
                fsTeksto = fsTeksto+'\n'+fsN.text
            if hasattr(sd,'_date'):
              fsDato = str(sd._date)
            if hasattr(sd,'about'):
              fsURL=sd.about
            koloro = "orange"
            teksto = teksto.strip(' \n')
            fsTeksto = fsTeksto.strip(' \n')
            if fsDato == dato and fsTitolo==titolo and fsURL == grURL :
              koloro = "yellow"
              if fsTeksto == teksto :
                koloro = "green"
            fsFontIdj.pop(fsid)
        self.modelKomp.add([koloro,dato,titolo,grURL,fsDato,fsTitolo,fsURL,False,'Fonto',c.handle,sd_id,teksto,fsTeksto] )
      for sd in fsFontIdj.values() :
        fsTitolo = ""
        for x in sd.titles :
          fsTitolo += x.value
        teksto=""
        fsURL = ""
        if hasattr(sd,'_date'):
          fsDato = str(sd._date)
        else :
          fsDato = ""
        if hasattr(sd,'about'):
          fsURL=sd.about
        koloro = "white"
        self.modelKomp.add([koloro,'===','===','===',fsDato,fsTitolo,fsURL,False,'Fonto',None,sd.id,None,None] )
    elif regximo == 'REG_notoj' :
      datumoj = tree._FsSeanco.get_jsonurl("/platform/tree/persons/%s/notes" % fsPerso.id)
      gedcomx_v1.maljsonigi(PersonFS.fs_Tree,datumoj)
      if not PersonFS.fs_Tree:
        colFS = _('Ne konektita al FamilySearch')
      else :
        colFS = '===================='
      nl = grPersono.get_note_list()
      fsNotoj = fsPerso.notes.copy()
      for nh in nl :
        n = self.dbstate.db.get_note_from_handle(nh)
        #teksto = n.get_styledtext()
        teksto = n.get()
        fsTeksto = colFS
        titolo = _(n.type.xml_str())
        fsTitolo = ""
        grNoto_id = None
        for t in n.text.get_tags():
          if t.name == StyledTextTagType.LINK and t.value[0:8] == "_fsftid=":
            grNoto_id = t.value[8:]
        koloro = "white"
        fsNoto_id = None
        for x in fsNotoj :
          if x.id == grNoto_id :
            fsTeksto = x.text
            fsTitolo = x.subject
            fsNoto_id = x.id
            fsNotoj.remove(x)
            break
        if not fsNoto_id :
         for x in fsNotoj :
          if x.subject == titolo :
            fsTeksto = x.text
            fsTitolo = x.subject
            fsNoto_id = x.id
            fsNotoj.remove(x)
            break
        if fsTitolo == titolo and (fsTeksto == teksto 
           or (teksto[0:1] == '\ufeff' and fsTeksto == teksto[1:] )) :
          koloro = "green"
        else :
          koloro = "yellow"
        self.modelKomp.add([koloro,_('Persono'),titolo,teksto,fsTitolo,fsTeksto,'',False,'NotoP',None,nh,fsPerso.id,fsNoto_id] )
      for fsNoto in fsNotoj :
        if fsNoto.id :
          print ("Note avec Id : "+fsNoto.id)
        fsTeksto = fsNoto.text
        fsTitolo = fsNoto.subject
        self.modelKomp.add(['white',_('Persono'),'','============================',fsTitolo,fsTeksto,'',False,'NotoP',None,None,fsPerso.id,fsNoto.id] )
      fsEdzoj = fsPerso._paroj.copy()
      for family_handle in grPersono.get_family_handle_list():
        family = self.dbstate.db.get_family_from_handle(family_handle)
        if family :
          edzo_handle = family.mother_handle
          if edzo_handle == grPersono.handle :
            edzo_handle = family.father_handle
          if edzo_handle :
            edzo = self.dbstate.db.get_person_from_handle(edzo_handle)
          else :
            edzo = Person()
          edzoNomo = edzo.primary_name
          edzoFsid = utila.get_fsftid(edzo)
          fsEdzoId = ''
          fsParo = None
          fsParoId = None
          for paro in fsEdzoj :
            if ( (paro.person1 and paro.person1.resourceId == edzoFsid)
                or( (paro.person1==None or paro.person1.resourceId== '') and edzoFsid == '')) :
              fsEdzoId = edzoFsid
              fsParo = paro
              fsParoId = paro.id
              fsEdzoj.remove(paro)
              break
            elif ( (paro.person2 and paro.person2.resourceId == edzoFsid)
                or( (paro.person2==None or paro.person2.resourceId== '') and edzoFsid == '')) :
              fsEdzoId = edzoFsid
              fsParo = paro
              fsParoId = paro.id
              fsEdzoj.remove(paro)
              break
          if fsParo :
            datumoj = tree._FsSeanco.get_jsonurl("/platform/tree/couple-relationships/%s/notes" % fsParo.id)
            gedcomx_v1.maljsonigi(PersonFS.fs_Tree,datumoj)
            fsNotoj = fsParo.notes.copy()
          else :
            fsNotoj = set()
          if PersonFS.fs_Tree :
            fsEdzo = PersonFS.fs_Tree._persons.get(fsEdzoId) or gedcomx_v1.Person()
          else :
            fsEdzo = gedcomx_v1.Person()
          fsNomo = fsEdzo.akPrefNomo()
          nl = family.get_note_list()
          for nh in nl :
            n = self.dbstate.db.get_note_from_handle(nh)
            #teksto = n.get_styledtext()
            teksto = n.get()
            titolo = _(n.type.xml_str())
            grNoto_id = None
            for t in n.text.get_tags():
              if t.name == StyledTextTagType.LINK and t.value[0:8] == "_fsftid=":
                grNoto_id = t.value[8:]
            koloro = "white"
            fsTeksto = colFS
            fsTitolo = None
            fsNotoId = None
            for x in fsNotoj :
              if x.id == grNoto_id :
                fsTeksto = x.text
                fsTitolo = x.subject
                fsNotoId = x.id
                fsNotoj.remove(x)
                break
            if not fsNotoId :
             for x in fsNotoj :
              if x.subject == titolo :
                fsTeksto = x.text
                fsTitolo = x.subject
                fsNotoId = x.id
                fsNotoj.remove(x)
                break
            if fsTitolo == titolo and (fsTeksto == teksto 
               or (teksto[0:1] == '\ufeff' and fsTeksto == teksto[1:] )) :
              koloro = "green"
            else :
              koloro = "yellow"
            self.modelKomp.add([koloro,_('Familio'),titolo,teksto,fsTitolo,fsTeksto,'',False,'NotoF',family_handle,nh,fsParoId,fsNotoId] )
          for fsNoto in fsNotoj :
            self.modelKomp.add(['white',_('Familio'),'','============================',fsNoto.subject,fsNoto.text,'',False,'NotoF',family_handle,None,fsParoId,fsNoto.id] )
          #, False, 'edzo', edzo_handle ,fsEdzoId , family.handle, fsParoId
      #for fsFam in fsEdzoj :
      #  datumoj = tree._FsSeanco.get_jsonurl("/platform/tree/couple-relationships/%s/notes" % fsFam.id)
      #  gedcomx_v1.maljsonigi(PersonFS.fs_Tree,datumoj)
      #  for fsNoto in fsFam.notes :
      #    fsTeksto = fsNoto.text
      #    fsTitolo = fsNoto.subject
      #    self.modelKomp.add(['white',_('Familio'),'','============================',fsTitolo,fsTeksto,'',False,'NotoF',None,None,fsFam.id,fsNoto.id] )
    elif regximo == 'REG_bildoj' :
      pass
    else : # REG_cxefa
      kompRet = komparo.kompariFsGr(fsPerso, grPersono, self.dbstate.db, self.modelKomp,getfs)
      for row in self.modelKomp.model :
        if row[0] == 'red' :
          self.propKomp.expand_row(row.path,1)
      if not PersonFS.fs_Tree:
        return
      box1 = self.top.get_object("Box1")
      if ('FS_Esenco' in kompRet) :
        box1.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(1.0, 0.0, 0.0, 1.0))
      else:
        box1.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(0.0, 1.0, 0.0, 1.0))
      box2 = self.top.get_object("Box2")
      if ('FS_Gepatro' in kompRet) or ('FS_Familio' in kompRet) :
        box2.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(1.0, 0.0, 0.0, 1.0))
      else:
        box2.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(0.0, 1.0, 0.0, 1.0))
      box3 = self.top.get_object("Box3")
      if ('FS_Fakto' in kompRet) :
        box3.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(1.0, 0.0, 0.0, 1.0))
      else:
        box3.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(0.0, 1.0, 0.0, 1.0))
      box4 = self.top.get_object("Box4")
      if ('FS_Dok' in kompRet) :
        box4.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(1.0, 0.0, 0.0, 1.0))
      else:
        box4.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(0.0, 1.0, 0.0, 1.0))
      box5 = self.top.get_object("Box5")
      if ('FS_Dup' in kompRet) :
        box5.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(1.0, 0.0, 0.0, 1.0))
      else:
        box5.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(0.0, 1.0, 0.0, 1.0))

    

    return

  # FARINDAĴOJ : kopii, redundoj, esploro, …
