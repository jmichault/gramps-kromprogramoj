# -*- coding: utf-8 -*-
#
# Lokpurigado Gramplet.

# Kopirajto © 2023 Jean Michault
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

#------------------------------------------------------------------------
#
# Python modules
#
#------------------------------------------------------------------------
from urllib.request import urlopen, URLError, quote
import os
import sys
import ctypes
import locale
import socket
import json

#import pdb; pdb.set_trace()

#------------------------------------------------------------------------
#
# GTK modules
#
#------------------------------------------------------------------------
from gi.repository import Gtk

#------------------------------------------------------------------------
#
# Gramps modules
#
#------------------------------------------------------------------------
from gramps.gen.merge.mergeplacequery import MergePlaceQuery
from gramps.gui.dialog import ErrorDialog, WarningDialog
from gramps.gen.plug import Gramplet
from gramps.gen.db import DbTxn
from gramps.gen.lib import Citation
from gramps.gen.lib import Place, PlaceName, PlaceType, PlaceRef, Url, UrlType
from gramps.gen.lib import Note, NoteType, Repository, RepositoryType, RepoRef
from gramps.gen.lib import StyledText, StyledTextTag, StyledTextTagType
from gramps.gen.lib import Source, SourceMediaType
from gramps.gen.datehandler import get_date
from gramps.gen.config import config
from gramps.gen.constfunc import win
from gramps.gui.display import display_url
from gramps.gui.autocomp import StandardCustomSelector
from gramps.gen.display.place import displayer as _pd
from gramps.gen.utils.location import located_in


#------------------------------------------------------------------------
#
# Internationalisation
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
  _trans = glocale.get_addon_translator(__file__)
except ValueError:
  _trans = glocale.translation
_ = _trans.gettext

#-------------------------------------------------------------------------
#
# configuration
#
#-------------------------------------------------------------------------

GRAMPLET_CONFIG_NAME = "lokpurigado_gramplet"
CONFIG = config.register_manager(GRAMPLET_CONFIG_NAME)
CONFIG.register("preferences.web_links", True)
CONFIG.register("preferences.keep_enclosure", True)
CONFIG.register("preferences.keep_lang", "fr oc eo")
CONFIG.load()


#------------------------------------------------------------------------
#
# Lokpurigado class
#
#------------------------------------------------------------------------
class Lokpurigado(Gramplet):
  """
  Gramplet por purigi la lokojn.
     Povas serĉi lokon, kiu bezonas atenton aŭ labori pri nuna loko.
     Povas serĉi viajn proprajn lokojn kaj kunfandi aktualan kun alia.
     Povas serĉi OpenStreetMap-datumojn kaj alŝuti datumojn al loko.
     Datumoj inkluzivas Lat/Lon, tipon, INSEE aŭ poŝtkodon kaj
     alternativaj nomoj.
  """
  def init(self):
    """
    Komencu la gramplet.
    """
    self.keepweb = CONFIG.get("preferences.web_links")
    self.keep_enclosure = CONFIG.get("preferences.keep_enclosure")
    allowed_languages = CONFIG.get("preferences.keep_lang")
    self.allowed_languages = allowed_languages.split()
    self.incomp_hndl = ''  # lasta uzata tenilo por nekompletaj lokoj
    self.matches_warn = True  # Ĉu mi montru la averton 'tro da kongruoj'?
    root = self.__create_gui()
    self.gui.get_container_widget().remove(self.gui.textview)
    self.gui.get_container_widget().add(root)
    root.show_all()

  def __create_gui(self):
    """
    Kreu kaj montru la GUI-komponentojn de la gramplet.
    """
    self.top = Gtk.Builder()
    # Glade ne subtenas tradukojn por kromaĵojn, do devas fari ĝin permane.
    base = os.path.dirname(__file__)
    glade_file = base + os.sep + "lokpurigado.glade"
    # Ĉi tio estas bezonata por ke gtk.Builder funkciu
    #specifante la tradukdosierujon en aparta "domajno".
    try:
      localedomain = "addon"
      localepath = base + os.sep + "locale"
      if hasattr(locale, 'bindtextdomain'):
        libintl = locale
      elif win():  # win ŝajne volas bajtajn ĉenojn
        localedomain = localedomain.encode('utf-8')
        localepath = localepath.encode('utf-8')
        libintl = ctypes.cdll.LoadLibrary('libintl-8.dll')
      else:  # mac
        libintl = ctypes.cdll.LoadLibrary('libintl.dylib')

      libintl.bindtextdomain(localedomain, localepath)
      libintl.textdomain(localedomain)
      libintl.bind_textdomain_codeset(localedomain, "UTF-8")
      # kaj fine, diru al Gtk Builder uzi tiun domajnon
      self.top.set_translation_domain("addon")
    except (OSError, AttributeError):
      # Lasos ĝin en la esperanta
      print("Localization of Lokpurigado failed!")

    self.top.add_from_file(glade_file)
    # the results screen items
    self.results_win = self.top.get_object("results")
    self.alt_store = self.top.get_object("alt_names_liststore")
    self.alt_selection = self.top.get_object("alt_names_selection")
    self.res_lbl = self.top.get_object("res_label")
    self.postal_lbl = self.top.get_object("postal_label")
    self.find_but = self.top.get_object("find_but")
    self.top.connect_signals({
        # for results screen
        "on_res_ok_clicked"      : self.on_res_ok_clicked,
        "on_res_cancel_clicked"  : self.on_res_cancel_clicked,
        "on_keep_clicked"        : self.on_keep_clicked,
        "on_prim_clicked"        : self.on_prim_clicked,
        "on_disc_clicked"        : self.on_disc_clicked,
        "on_alt_row_activated"   : self.on_alt_row_activated,
        "on_latloncheck"         : self.on_latloncheck,
        "on_postalcheck"         : self.on_postalcheck,
        "on_typecheck"           : self.on_typecheck,
        "on_idcheck"             : self.on_idcheck,
        # Preferences screen item
        "on_pref_help_clicked"   : self.on_pref_help_clicked,
        # main screen items
        "on_find_clicked"        : self.on_find_clicked,
        "on_prefs_clicked"       : self.on_prefs_clicked,
        "on_select_clicked"      : self.on_select_clicked,
        "on_edit_clicked"        : self.on_edit_clicked,
        "on_next_clicked"        : self.on_next_clicked,
        "on_res_row_activated"   : self.on_select_clicked,
        "on_res_sel_changed"     : self.on_res_sel_changed,
        "on_title_entry_changed" : self.on_title_entry_changed,
        "on_help_clicked"        : self.on_help_clicked})
    # main screen items
    self.res_store = self.top.get_object("res_names_liststore")
    self.res_selection = self.top.get_object("res_selection")
    self.mainwin = self.top.get_object("main")
    return self.mainwin

  # ======================================================
  # gramplet event handlers
  # ======================================================
  def on_help_clicked(self, dummy):
      ''' Button: Display the relevant portion of GRAMPS manual'''
      pass

  def on_res_sel_changed(self, res_sel):
      """ Selecting a row in the results list """
      self.top.get_object("select_but").set_sensitive(
          res_sel.get_selected())

  def on_title_entry_changed(self, dummy):
      ''' Occurs during edits of the Title box on the main screen.
      we use this to reset the OpenStreetMap search row, as the user may be
      trying another search term.'''
      self.reset_main()

  def on_save(self, *args, **kwargs):
      CONFIG.set("preferences.web_links", self.keepweb)
      CONFIG.set("preferences.keep_enclosure", self.keep_enclosure)
      CONFIG.set("preferences.keep_lang", ' '.join(self.allowed_languages))
      CONFIG.save()

  def db_changed(self):
      self.dbstate.db.connect('place-update', self.update)
      self.main()
      if not self.dbstate.db.readonly:
          self.connect_signal('Place', self.update)

  def main(self):
      self.reset_main()
      if self.gui.get_child().get_child() == self.results_win:
          self.gui.get_child().remove(self.results_win)
          self.gui.get_child().add(self.mainwin)
      active_handle = self.get_active('Place')
      self.top.get_object("edit_but").set_sensitive(False)
      self.top.get_object("find_but").set_sensitive(False)
      self.top.get_object("title_entry").set_sensitive(False)
      if active_handle:
          self.place = self.dbstate.db.get_place_from_handle(active_handle)
          self.mainwin.hide()
          if self.place:
              self.set_has_data(True)
              title = _pd.display(self.dbstate.db, self.place)
              item = self.top.get_object("title_entry")
              item.set_text(title)
              self.top.get_object("edit_but").set_sensitive(True)
              self.top.get_object("find_but").set_sensitive(True)
              self.top.get_object("title_entry").set_sensitive(True)
          else:
              self.set_has_data(False)
          self.mainwin.show()
      else:
          self.set_has_data(False)

  def reset_main(self):
      """ Reset the main Gui to default clear """
      self.res_store.clear()
      self.res_lbl.set_text(_('\nNeniu kongruo\ntrovita'))
      self.find_but.set_label(_("Trovi"))
      self.start_row = 0
      self.osm_stage = False
      self.top.get_object("select_but").set_sensitive(False)

  def on_find_clicked(self, dummy):
      """ find a matching place.  First try in the db, then try in the
      OpenStreetMap. """
      self.res_store.clear()
      self.top.get_object("select_but").set_sensitive(False)
      if self.osm_stage:
          self.search_osm()
      else:
          self.osm_stage = True
          item = self.top.get_object("title_entry")
          title = item.get_text()
          self.places = self.lookup_places_by_name(title)
          for index, place in enumerate(self.places):
              # make sure the place found isn't self, or a place
              # enclosed by the working place
              if place.handle != self.place.handle and not located_in(
                      self.dbstate.db, place.handle, self.place.handle):
                  title = _pd.display(self.dbstate.db, place)
                  self.res_store.append(row=(index, title,
                                             str(place.place_type)))
          if len(self.res_store) > 0:
              self.res_lbl.set_text(_('%s\nLokaj\nkongruecoj') %
                                    len(self.res_store))
              self.top.get_object("select_but").set_label(_("Kunfandi"))
              self.find_but.set_label(_("Serĉi en OpenStreetMap"))
          else:
              self.search_osm()

  def search_osm(self):
      """ find a matching place in the osmnames, if possible """
      self.res_store.clear()
      # lets get a preferred language
      fmt = config.get('preferences.place-format')
      placef = _pd.get_formats()[fmt]
      self.lang = placef.language
      if len(self.lang) != 2:
          self.lang = 'fr'
      if self.lang not in self.allowed_languages:
          self.allowed_languages.append(self.lang)
      # now lets search for a place in OpenStreetMap
      item = self.top.get_object("title_entry")
      title = quote(item.get_text())
      osm_url = ('https://nominatim.openstreetmap.org/search?format=jsonv2&q='+title)
      rezultoj = self.get_osm_data(osm_url)

      if not rezultoj or len(rezultoj)==0 :
          WarningDialog(_('Neniuj kongruoj estis trovitaj'),
                        msg2=_('Provu ŝanĝi la titolon aŭ uzu la butonon "Redakti"'
                               ' por permane kompletigi ĉi tiun nivelon.'),
                        parent=self.uistate.window)
          return
      # let's check the total results; if too many, warn user and set up for
      # another pass through the search.
      nbRez = len(rezultoj)
      if nbRez:
          self.res_lbl.set_text(_("\n%s\nOpenStreetMap\nKongruecoj") % nbRez)
          self.top.get_object("select_but").set_label(_("Elekti"))
          if nbRez > 10:
              self.start_row += 10
              if self.matches_warn:
                  self.matches_warn = False
                  WarningDialog(
                      _('%s kongruoj trovitaj') % nbRez,
                      msg2=_('Nur 10 kongruecoj estas montritaj.\n'
                             'Por vidi pliajn rezultojn, premu la'
                             ' serĉbutonon denove.\n'
                             'Aŭ provu ŝanĝi la Titolo kun pli'
                             ' da detaloj, kiel lando.'),
                      parent=self.uistate.window)
      index = 0
      self.places = []
      for g_name in rezultoj:
          osm_tipo = g_name['osm_type']
          osm_id = g_name['osm_id']
          nomo = g_name['display_name']
          bad=False
          h_name_list = [nomo]
          h_osmid_list = [osm_id]
          row = (index, nomo, osm_tipo+':'+g_name['type']+':'+g_name['addresstype']+':'+str(g_name['place_rank']))
          self.res_store.append(row=row)
          self.places.append( (osm_tipo, osm_id, g_name, bad) )
          index += 1
          while Gtk.events_pending():
              Gtk.main_iteration()

  def get_osm_data(self, osm_url, osm_datoj=None):
      """ Get OpenStreetMap data from web with error checking """
      try:
          with urlopen(osm_url,data=osm_datoj, timeout=20) as response:
              data = response.read()
              res=json.loads(data)
      except URLError as err:
          try:
              txt = err.read().decode('utf-8')
          except:
              txt = ''
          ErrorDialog(_('Problemo akiri datumojn de retejo'),
                      msg2=str(err) +'\n' + txt,
                      parent=self.uistate.window)
          return None
      except socket.timeout:
          ErrorDialog(_('Problemo akiri datumojn de retejo'),
                      msg2=_('TTT-peto elĉerpita, vi povas provi denove…'),
                      parent=self.uistate.window)
          return None

      return res

  def on_next_clicked(self, dummy):
      """ find a incomplete place in the db, if possible """
      self.reset_main()
      place = self.find_an_incomplete_place()
      if place:
          self.set_active('Place', place.handle)

  def on_select_clicked(self, *dummy):
      """ If the selected place is mergable, merge it, otherwise Open
      completion screen """
      model, _iter = self.res_selection.get_selected()
      if not _iter:
          return
      (index, ) = model.get(_iter, 0)
      place = self.places[index]
      if not isinstance(place, Place):
          # we have a osmname_id
          if place[3]:
              return
          # check if we might already have it in db
          t_place = self.dbstate.db.get_place_from_gramps_id(place[0])
          if not t_place or t_place.handle == self.place.handle:
              # need to process the OpenStreetMap ID for result
              self.gui.get_child().remove(self.mainwin)
              self.gui.get_child().add(self.results_win)
              if not self.osmparse(*place):
                  return
              self.res_gui()
              return
          else:
              # turns out we already have this place, under different name!
              place = t_place
      # we have a Gramps Place, need to merge
      if place.handle == self.place.handle:
          # found self, nothing to do.
          return
      if(located_in(self.dbstate.db, place.handle, self.place.handle) or
         located_in(self.dbstate.db, self.place.handle, place.handle)):
          # attempting to create a place loop, not good!
          ErrorDialog(_('Lokciklo detektita'),
                      msg2=_("Unu el la lokoj, kiujn vi kunfandas, enfermas la alian!\n"
                             "Bonvolu elekti alian lokon."),
                      parent=self.uistate.window)
          return
      # lets clean up the place name
      self.place.name.value = self.place.name.value.split(',')[0].strip()
      place_merge = MergePlaceQuery(self.dbstate, place, self.place)
      place_merge.execute()
      # after merge we should select merged result
      self.set_active('Place', place.handle)

  def osmparse(self, osm_tipo, osm_id, json_datoj, *dummy):
      """ get data for place and parse out g_name dom structure into the
      NewPlace structure """
      self.newplace = NewPlace(json_datoj['display_name'])
      self.newplace.osmid = 'Osm_'+osm_tipo+"_"+str(osm_id)
      self.newplace.gramps_id = 'Osm_'+osm_tipo+"_"+str(osm_id)
      self.newplace.lat = json_datoj['lat']
      self.newplace.long = json_datoj['lon']
      url = Url()
      url.set_path('https://www.openstreetmap.org/'+osm_tipo+'/'+str(osm_id))
      url.set_description('openstreetmap '+osm_tipo+' '+str(osm_id))
      url.set_type(UrlType('openstreetmap'))
      self.newplace.links.append(url)
      new_place = PlaceName()
      new_place.set_value(json_datoj['name'])
      new_place.set_language("")
      # make sure we have the topname in the names list and default to
      # primary
      self.newplace.add_name(new_place)
      self.newplace.name = new_place
      self.newplace.place_type = None
      value = json_datoj['addresstype']
      if json_datoj['display_name'].endswith('France') :
        if value == 'state' :
          self.newplace.place_type = PlaceType(PlaceType.REGION)
        elif value == 'county' :
          self.newplace.place_type = PlaceType(PlaceType.DEPARTMENT)
        elif value == 'city' :
          self.newplace.place_type = PlaceType(PlaceType.MUNICIPALITY)
        elif value == 'village' :
          self.newplace.place_type = PlaceType(PlaceType.MUNICIPALITY)
        elif value == 'town' :
          self.newplace.place_type = PlaceType(PlaceType.MUNICIPALITY)
        elif value == 'suburb' :
          self.newplace.place_type = PlaceType(PlaceType.BOROUGH)
      if not self.newplace.place_type :
        if value == 'country' :
          self.newplace.place_type = PlaceType(PlaceType.COUNTRY)
        elif value == 'state' :
          self.newplace.place_type = PlaceType(PlaceType.STATE)
        elif value == 'county' :
          self.newplace.place_type = PlaceType(PlaceType.COUNTY)
        elif value == 'city' :
          self.newplace.place_type = PlaceType(PlaceType.CITY)
        elif value == 'municipality' :
          self.newplace.place_type = PlaceType(PlaceType.MUNICIPALITY)
        elif value == 'village' :
          self.newplace.place_type = PlaceType(PlaceType.VILLAGE)
        elif value == 'town' :
          self.newplace.place_type = PlaceType(PlaceType.TOWN)
        elif value == 'region' :
          self.newplace.place_type = PlaceType(PlaceType.REGION)
        elif value == 'hamlet' :
          self.newplace.place_type = PlaceType(PlaceType.HAMLET)
      # obtenir plus d'informations :
      osm_url = ('https://overpass-api.de/api/interpreter')
      if osm_tipo == 'relation' :
        osm_datoj= 'data='+quote('[out:json][timeout:25];rel('+str(osm_id)+');out center tags;')
      elif osm_tipo == 'way' :
        osm_datoj= 'data='+quote('[out:json][timeout:25];way('+str(osm_id)+');out center tags;')
      elif osm_tipo == 'node' :
        osm_datoj= 'data='+quote('[out:json][timeout:25];node('+str(osm_id)+');out center tags;')
      res = self.get_osm_data(osm_url,bytes(osm_datoj,'utf-8'))
      self.newplace.code = ''
      rezultoj = None
      if res and len(res) :
        rezultoj=res.get("elements")
        for lingvo in self.allowed_languages :
          ling_nomo = rezultoj[0]["tags"].get("name:"+lingvo)
          if ling_nomo :
            new_place = PlaceName()
            new_place.set_language(lingvo)
            new_place.set_value(ling_nomo)
            self.newplace.add_name(new_place)
        # 
        admin_level = rezultoj[0]["tags"].get("admin_level")
        if not self.newplace.place_type :
          match admin_level :
            case "2" :
              self.newplace.place_type = PlaceType(PlaceType.COUNTRY)
            case "3" :
              self.newplace.place_type = PlaceType(PlaceType.STATE)
            case "4" :
              self.newplace.place_type = PlaceType(PlaceType.REGION)
            case "5" :
              self.newplace.place_type = PlaceType(PlaceType.COUNTY)
            case "6" :
              self.newplace.place_type = PlaceType(PlaceType.DEPARTMENT)
            case "7" :
              self.newplace.place_type = PlaceType(PlaceType.BOROUGH)
            case "8" :
              self.newplace.place_type = PlaceType(PlaceType.MUNICIPALITY)
            case _ :
              self.newplace.place_type = PlaceType(PlaceType.UNKNOWN)
        code = rezultoj[0]["tags"].get("ref:INSEE")
        if code :
          self.postal_lbl.set_text(_("INSEE Kodo"))
          if admin_level == 8 :
            self.newplace.gramps_id = 'FrCogCom'+str(code)
          elif admin_level == 6 :
            self.newplace.gramps_id = 'FrCogDep'+str(code)
          elif admin_level == 4 :
            self.newplace.gramps_id = 'FrCogReg'+str(code)
        else :
          self.postal_lbl.set_text(_("Poŝtkodo"))
          code = rezultoj[0]["tags"].get("postal_code")
        if admin_level == "2" :
          code = rezultoj[0]["tags"].get("ISO3166-1:alpha3")
        self.newplace.code = code
      # FARINDAĴO
      # obtenir tous les parents administratifs :
      # 'is_in(46.6121074,0.5541073)->.a;relation["admin_level"~"8|7|6|5|4|3|2"](pivot.a);out tags center;'
      if rezultoj :
        admin_level = int( rezultoj[0]["tags"].get("admin_level") or "9")
        res = None
        while admin_level>1 and not res :
          if json_datoj['display_name'].endswith('France') :
            # en France, on saute les arrondissements et la France Métropolitaine :
            if admin_level==8 or admin_level == 4 :
              admin_level = admin_level - 1
          osm_datoj= '[timeout:10][out:json];is_in('+str(self.newplace.lat)+','+str(self.newplace.long)+')->.a;relation["admin_level"="'+str(admin_level-1)+'"](pivot.a);out tags center;'
          osm_url = ('https://overpass-api.de/api/interpreter')
          res = self.get_osm_data(osm_url,bytes(osm_datoj,'utf-8'))
          if not res or not len(res) :
            return True
          if res and len(res) and not res.get("elements") :
            admin_level = admin_level - 1
            res = None
            continue;
          rezultoj=res.get("elements")
          if len(rezultoj)==0 :
            admin_level = admin_level - 1
            res = None
            continue;
          nomoj=list()
          nomoj.append(rezultoj[0]["tags"].get("name"))
          self.newplace.parent_names = nomoj
          datoj=dict()
          datoj["display_name"]= json_datoj['display_name'].replace(json_datoj['name'],'').strip(" ,")
          datoj["name"]=rezultoj[0]["tags"].get("name")
          datoj["addresstype"]=""
          admin_level = int (rezultoj[0]["tags"].get("admin_level") or "9")
          datoj["admin_level"]=admin_level
          datoj["lat"]=str(rezultoj[0]["center"]["lat"])
          datoj["lon"]=str(rezultoj[0]["center"]["lon"])
          self.newplace.parent_datoj = datoj
          self.newplace.parent_tipo = rezultoj[0]["type"]
          self.newplace.parent_osmid = rezultoj[0]["id"]
          osm_idj=list()
          osm_id = 'Osm_'+ rezultoj[0]["type"] +"_"+ str(rezultoj[0]["id"])
          if json_datoj['display_name'].endswith('France') :
            code = rezultoj[0]["tags"].get("ref:INSEE")
            if code and admin_level == 8 :
              osm_id  = 'FrCogCom'+str(code)
            elif code and admin_level == 6 :
              osm_id = 'FrCogDep'+str(code)
            elif code and admin_level == 4 :
              osm_id = 'FrCogReg'+str(code)
          osm_idj.append(osm_id)
          self.newplace.parent_ids = osm_idj
      # obtenir les parents directs :
      # '[timeout:10][out:json]; rel(7377); rel(br); out tags center;
      #
      #      self.newplace.parent_names = h_name_list[1:]
      #      self.newplace.parent_ids = h_geoid_list[1:]
      return True

  def on_edit_clicked(self, dummy):
      """User wants to jump directly to the results view to finish off
      the place, possibly because a place was not found"""
#         if ',' in self.place.name.value:
#             name = self.place.name.value
#         else:
      name = self.place.name.value
      self.newplace = NewPlace(name)
      names = name.split(',')
      names = [name.strip() for name in names]
      self.newplace.name = PlaceName()
      self.newplace.name.value = names[0]
      self.newplace.gramps_id = self.place.gramps_id
      self.newplace.lat = self.place.lat
      self.newplace.long = self.place.long
      self.newplace.code = self.place.code
      if self.place.place_type == PlaceType.UNKNOWN:
          self.newplace.place_type = PlaceType(PlaceType.UNKNOWN)
          if any(i.isdigit() for i in self.newplace.name.value):
              self.newplace.place_type = PlaceType(PlaceType.STREET)
          ptype = PlaceType()
          for tname in self.newplace.name.value.split(' '):
              # see if it is an English PlaceType
              ptype.set_from_xml_str(tname.capitalize())
              if ptype != PlaceType.CUSTOM:
                  self.newplace.place_type = ptype
                  break
              # see if it is a translated PlaceType
              ptype.set(tname.capitalize())
              if ptype != PlaceType.CUSTOM:
                  self.newplace.place_type = ptype
                  break
              # see if it is an already added custom type
              cust_types = self.dbstate.db.get_place_types()
              if tname.capitalize() in cust_types:
                  self.newplace.place_type = ptype
      else:
          self.newplace.place_type = self.place.place_type
      self.newplace.add_name(self.newplace.name)
      self.newplace.add_name(self.place.name)
      self.newplace.add_names(self.place.alt_names)
      if self.place.placeref_list:
          # If we already have an enclosing place, use it.
          parent = self.dbstate.db.get_place_from_handle(
              self.place.placeref_list[0].ref)
          self.newplace.parent_ids = [parent.gramps_id]
      elif len(names) > 1:
          # we have an enclosing place, according to the name string
          self.newplace.parent_names = names[1:]
      self.gui.get_child().remove(self.mainwin)
      self.gui.get_child().add(self.results_win)
      self.res_gui()

# Results view

  def res_gui(self):
      """ Fill in the results display with values from new place."""
      self.alt_store.clear()
      # Setup sort on 'Inc" column so Primary is a top with checks next
      self.alt_store.set_sort_func(0, inc_sort, None)
      self.alt_store.set_sort_column_id(0, 0)
      # Merge old name and alt names into new set
      self.newplace.add_name(self.place.name)
      self.newplace.add_names(self.place.alt_names)
      # Fill in ohter fields
      self.top.get_object('res_title').set_text(self.newplace.title)
      self.top.get_object('primary').set_text(self.newplace.name.value)
      self.on_idcheck()
      self.on_latloncheck()
      self.on_postalcheck()
      self.on_typecheck()
      # Fill in names list
      for index, name in enumerate(self.newplace.names):
          if self.newplace.name == name:
              inc = 'P'
          elif name.lang in self.allowed_languages or (
                  name.lang == 'abbr' or name.lang == 'en' or not name.lang):
              inc = '\u2714'  # Check mark
          else:
              inc = ''
          row = (inc, name.value, name.lang, get_date(name), index)
          self.alt_store.append(row=row)

# Results dialog items

  def on_res_ok_clicked(self, dummy):
      """ Accept changes displayed and commit to place.
      Also find or create a new enclosing place from parent. """
      # do the names
      namelist = []
      for row in self.alt_store:
          if row[0] == 'P':
              self.place.name = self.newplace.names[row[4]]
          elif row[0] == '\u2714':
              namelist.append(self.newplace.names[row[4]])
      self.place.alt_names = namelist
      # Lat/lon/ID/code/type
      self.place.lat = self.top.get_object('latitude').get_text()
      self.place.long = self.top.get_object('longitude').get_text()
      self.place.gramps_id = self.top.get_object('grampsid').get_text()
      self.place.code = self.top.get_object('postal').get_text()
      self.place.place_type.set(self.type_combo.get_values())
      # Add in URLs if wanted
      if self.keepweb:
        self.place._merge_url_list(self.newplace)
          #for url in self.newplace.links:
          #    self.place.add_url(url)
      # Enclose in the next level place
      next_place = False
      parent = None
      if not self.keep_enclosure or not self.place.placeref_list:
        if self.newplace.parent_ids:
          # we might have a parent with geo id 'GEO12345'
          parent = self.dbstate.db.get_place_from_gramps_id(
              self.newplace.parent_ids[0])
        if not parent and self.newplace.parent_names:
          # make one, will have to be examined/cleaned later
          parent = Place()
          parent.title = ', '.join(self.newplace.parent_names)
          name = PlaceName()
          name.value = parent.title
          parent.name = name
          if self.newplace.parent_ids:
                    parent.gramps_id = self.newplace.parent_ids[0]
          with DbTxn(_("Add Place (%s)") % parent.title,
                           self.dbstate.db) as trans:
                    self.dbstate.db.add_place(parent, trans)
                    next_place = True
        if parent:
          if located_in(self.dbstate.db, parent.handle,
                              self.place.handle):
              # attempting to create a place loop, not good!
              ErrorDialog(_('Place cycle detected'),
                                msg2=_("The place you chose is enclosed in the"
                                       " place you are workin on!\n"
                                       "Please cancel and choose another "
                                       "place."),
                                parent=self.uistate.window)
              return
          # check to see if we already have the enclosing place
          already_there = False
          for pref in self.place.placeref_list:
                    if parent.handle == pref.ref:
                        already_there = True
                        break
          if not already_there:
                    placeref = PlaceRef()
                    placeref.set_reference_handle(parent.handle)
                    self.place.set_placeref_list([placeref])

      # We're finally ready to commit the updated place
      with DbTxn(_("Redakti Lokon (%s)") % self.place.title,
                 self.dbstate.db) as trans:
          self.dbstate.db.commit_place(self.place, trans)
      # Jump to enclosing place to clean it if necessary
      if next_place:
          self.set_active('Place', parent.handle)
          self.place = parent
          # if osmparse fails, leave us at main view
          if self.newplace.parent_ids and \
              self.osmparse(self.newplace.parent_tipo,
                            self.newplace.parent_osmid,
                            self.newplace.parent_datoj,
                            None):
              # osmparse worked, lets put up the results view
              self.gui.get_child().remove(self.mainwin)
              self.gui.get_child().add(self.results_win)
              self.res_gui()
              return
      self.reset_main()
      if self.gui.get_child().get_child() == self.results_win:
          self.gui.get_child().remove(self.results_win)
          self.gui.get_child().add(self.mainwin)

  def on_res_cancel_clicked(self, dummy):
      """ Cancel operations on this place. """
      self.gui.get_child().remove(self.results_win)
      self.gui.get_child().add(self.mainwin)

  def on_keep_clicked(self, dummy):
      """ Keep button clicked.  Mark selected names rows to keep. """
      model, rows = self.alt_selection.get_selected_rows()
      for row in rows:
          if model[row][0] == 'P':
              continue
          model[row][0] = '\u2714'

  def on_prim_clicked(self, dummy):
      """ Primary button clicked.  Mark first row in selection as Primary
      name, any previous primary as keep """
      model, rows = self.alt_selection.get_selected_rows()
      if not rows:
          return
      # Clear prior primary
      for row in model:
          if row[0] == 'P':
              row[0] = '\u2714'
      # mark new one.
      self.top.get_object('primary').set_text(model[rows[0]][1])
      model[rows[0]][0] = 'P'

  def on_disc_clicked(self, dummy):
      """ Discard button clicked.  Unmark selected rows. """
      model, rows = self.alt_selection.get_selected_rows()
      for row in rows:
          if model[row][0] == 'P':
              continue
          model[row][0] = ''

  def on_alt_row_activated(self, *dummy):
      """ Toggle keep status for selected row.  Seems this only works for
      last selected row."""
      model, rows = self.alt_selection.get_selected_rows()
      for row in rows:
          if model[row][0] == 'P':
              continue
          if model[row][0] == '':
              model[row][0] = '\u2714'
          else:
              model[row][0] = ''

  def on_latloncheck(self, *dummy):
      """ Check toggled; if active, load lat/lon from original place, else
      use lat/lon from gazetteer """
      obj = self.top.get_object("latloncheck")
      if not dummy:
          # inititlization
          obj.set_sensitive(True)
          obj.set_active(False)
      place = self.newplace
      if self.place.lat and self.place.long:
          if obj.get_active():
              place = self.place
      else:
          obj.set_sensitive(False)
      self.top.get_object('latitude').set_text(place.lat)
      self.top.get_object('longitude').set_text(place.long)

  def on_postalcheck(self, *dummy):
      """ Check toggled; if active, load postal from original place, else
      use postal from gazetteer """
      obj = self.top.get_object("postalcheck")
      if not dummy:
          # inititlization
          obj.set_sensitive(True)
          obj.set_active(False)
      place = self.newplace
      if self.place.code:
          if obj.get_active():
              place = self.place
          obj.set_sensitive(True)
      else:
          obj.set_sensitive(False)
      if place.code :
        self.top.get_object('postal').set_text(place.code)
      else :
        self.top.get_object('postal').set_text('')

  def on_typecheck(self, *dummy):
      """ Check toggled; if active, load type from original place, else
      use type from gazetteer """
      obj = self.top.get_object("typecheck")
      combo = self.top.get_object('place_type')
      additional = sorted(self.dbstate.db.get_place_types(),
                          key=lambda s: s.lower())
      self.type_combo = StandardCustomSelector(PlaceType().get_map(), combo,
                                               PlaceType.CUSTOM,
                                               PlaceType.UNKNOWN,
                                               additional)
      if not dummy:
          # inititlization
          obj.set_sensitive(True)
          obj.set_active(False)
      place = self.newplace
      if(self.place.place_type and
         self.place.place_type != PlaceType.UNKNOWN):
          if obj.get_active():
              place = self.place
      else:
          obj.set_sensitive(False)
      self.type_combo.set_values((int(place.place_type),
                                  str(place.place_type)))

  def on_idcheck(self, *dummy):
      """ Check toggled; if active, load gramps_id from original place, else
      use osmnamesid from gazetteer """
      obj = self.top.get_object("idcheck")
      if not dummy:
          # inititlization
          obj.set_sensitive(True)
          obj.set_active(False)
      place = self.newplace
      if self.place.gramps_id:
          if obj.get_active():
              place = self.place
      else:
          obj.set_sensitive(False)
      self.top.get_object('grampsid').set_text(place.gramps_id)

# Preferences dialog items

  def on_prefs_clicked(self, dummy):
      """ Button: display preference dialog """
      top = self.top.get_object("pref_dialog")
      top.set_transient_for(self.uistate.window)
      parent_modal = self.uistate.window.get_modal()
      if parent_modal:
        self.uistate.window.set_modal(False)
      keepweb = self.top.get_object("keepweb")
      keepweb.set_active(self.keepweb)
      # for some reason you can only set the radiobutton to True
      self.top.get_object(
          "enc_radio_but_keep" if self.keep_enclosure
          else "enc_radio_but_repl").set_active(True)
      keepalt = self.top.get_object("keep_alt_entry")
      keepalt.set_text(' '.join(self.allowed_languages))
      top.show()
      top.run()
      if self.uistate.window and parent_modal:
          self.uistate.window.set_modal(True)
      self.keepweb = keepweb.get_active()
      self.keep_enclosure = self.top.get_object(
            "enc_radio_but_keep").get_active()
      self.allowed_languages = keepalt.get_text().split()
      top.hide()

  def on_pref_help_clicked(self, dummy):
      pass

  def lookup_places_by_name(self, search_name):
      """ In local db.  Only completed places are matched.
      We may want to try some better matching algorithms, possibly
      something from difflib"""
      search_name = search_name.lower().split(',')
      places = []
      for place in self.dbstate.db.iter_places():
          if (place.get_type() != PlaceType.UNKNOWN and
              (place.get_type() == PlaceType.COUNTRY or
               (place.get_type() != PlaceType.COUNTRY and
                place.get_placeref_list()))):
              # valid place, get all its names
              for name in place.get_all_names():
                  if name.get_value().lower() == search_name[0]:
                      places.append(place)
                      break
      return places

  def find_an_incomplete_place(self):
      """ in our db.  Will return with a place (and active set to place)
      or None if no incomplete places, in which case active will be the same.
      Will also find unused places, and offer to delete."""
      p_hndls = self.dbstate.db.get_place_handles()
      if not p_hndls:
          return None  # in case there aren't any
      # keep handles in an order to avoid inconsistant
      # results when db returns them in different orders.
      p_hndls.sort()
      # try to find the handle after the previously scanned handle in the
      # list.
      found = False
      for indx, hndl in enumerate(p_hndls):
          if hndl > self.incomp_hndl:
              found = True
              break
      if not found:
          indx = 0
      # now, starting from previous place, look for incomplete place
      start = indx
      while True:
          hndl = p_hndls[indx]
          place_data = self.dbstate.db.get_raw_place_data(hndl)
          p_type = place_data[8][0]  # place_type
          refs = list(self.dbstate.db.find_backlink_handles(hndl))
          if(p_type == PlaceType.UNKNOWN or
             not refs or
             p_type != PlaceType.COUNTRY and
             not place_data[5]):  # placeref_list
              # need to get view to this place...
              self.set_active("Place", hndl)
              self.incomp_hndl = hndl
              if not refs:
                  WarningDialog(
                      _('Ĉi tiu Loko ne estas uzata!'),
                      msg2=_('Vi devus forigi ĝin aŭ, se ĝi enhavas utilajn'
                             ' notojn aŭ aliajn datumojn, uzu serĉon por '
                             'kunfandi ĝin kun valida loko.'),
                      parent=self.uistate.window)
              return self.dbstate.db.get_place_from_handle(hndl)
          indx += 1
          if indx == len(p_hndls):
              indx = 0
          if indx == start:
              break
      return None


class NewPlace():
  """ structure to store data about a found place"""
  def __init__(self, title):
      self.title = title
      self.gramps_id = ''
      self.lat = ''
      self.long = ''
      self.code = ''
      self.place_type = None
      self.names = []  # all names, including alternate, acts like a set
      self.name = PlaceName()
      self.links = []
      self.osmid = ''
      self.parent_ids = []   # list of gramps_ids in hierarchical order
      self.parent_names = [] # list of names in hierarchical order

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
  def get_url_list(self):
      return self.links

#------------------------------------------------------------------------
#
# Functions
#
#------------------------------------------------------------------------


def linkst(text, url):
  """ Return text as link styled text
  """
  tags = [StyledTextTag(StyledTextTagType.LINK, url, [(0, len(text))])]
  return StyledText(text, tags)


def inc_sort(model, row1, row2, user_data):
  value1 = model.get_value(row1, 0)
  value2 = model.get_value(row2, 0)
  if value1 == value2:
      return 0
  if value1 == 'P':
      return -1
  if value2 == 'P':
      return 1
  if value2 > value1:
      return 1
  else:
      return -1
