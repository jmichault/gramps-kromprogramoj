#
# Gramplet - PlaceFrCog (Place : France : Code Officiel Géographique)
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
PlaceFrCog Gramplet.
"""

#------------------------------------------------------------------------
#
# Python modules
#
#------------------------------------------------------------------------
import requests
from requests.exceptions import HTTPError

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
from gramps.gen.plug import Gramplet
from gramps.gen.db import DbTxn
from gramps.gen.lib import Place, PlaceName, PlaceType, PlaceRef, Url, UrlType
from gramps.gen.datehandler import parser
from gramps.gen.config import config
from gramps.gen.display.place import displayer as _pd
from gramps.gui.dialog import (DBErrorDialog, ErrorDialog, QuestionDialog2, 
                            WarningDialog)


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

#------------------------------------------------------------------------
#
# PlaceFrCog class
#
#------------------------------------------------------------------------
class PlaceFrCog(Gramplet):
  """
  Gramplet por akiri lokojn el la datumbazo Insee.
  """
  def init(self):
    """
    Komencu la gramplet.
    """
    root = self.__krei_gui()
    self.gui.get_container_widget().remove(self.gui.textview)
    self.gui.get_container_widget().add_with_viewport(root)
    root.show_all()


  def __krei_gui(self):
    """
    Krei la komponentoj de la grampleto.
    """
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    vbox.set_spacing(4)

    label = Gtk.Label(_('Enigu la INSEE-numeron de la komunumo: (aŭ plurajn nombrojn apartigitajn per spacoj)'))
    label.set_halign(Gtk.Align.START)
    self.entry = Gtk.Entry()
    button_box = Gtk.ButtonBox()
    button_box.set_layout(Gtk.ButtonBoxStyle.START)
    get = Gtk.Button(label=_('Ŝargi per kodo'))
    get.connect("clicked", self.__get_places)
    button_box.add(get)
    vbox.pack_start(label, False, True, 0)
    vbox.pack_start(self.entry, False, True, 0)
    vbox.pack_start(button_box, False, True, 0)

    label2 = Gtk.Label(_('Enigu la nomon de la komunumo:'))
    label2.set_halign(Gtk.Align.START)
    self.entry2 = Gtk.Entry()
    button_box2 = Gtk.ButtonBox()
    button_box2.set_layout(Gtk.ButtonBoxStyle.START)
    get2 = Gtk.Button(label=_('Ŝarĝi per nomo'))
    get2.connect("clicked", self.__get_places2)
    button_box2.add(get2)
    vbox.pack_start(label2, False, True, 0)
    vbox.pack_start(self.entry2, False, True, 0)
    vbox.pack_start(button_box2, False, True, 0)

    return vbox

  def main(self):
    """
    Called to update the display.
    """
    pass

  def __get_places2(self, obj):
    lokonomo = self.entry2.get_text()
    #place = self.dbstate.db.get_place_from_gramps_id('FrCogCom'+insee_id)
    geo_url = 'http://geo.api.gouv.fr/communes?fields=nom,code,centre,codeDepartement,codeRegion&format=json&geometry=centre&nom=' + lokonomo

    response = requests.get(geo_url)
    response.raise_for_status()
    json = response.json()
    if json == []:
      WarningDialog(_("Nekonato nomo"), _("Ĉi tiu nomo ne estis trovita en la INSEE-datumbazo: ")+lokonomo, parent=self.uistate.window)
      return 
    codDep = json[0]['codeDepartement']
    insee_id = json[0]['code']
    nb = len(json)
    if nb >1 :
      d = QuestionDialog2(_("%d rezultoj") % (nb), _("Unua rezulto :\n\t%s ; kodo=%s. \n\n\t\tImporti ?\n") % ( json[0]['nom'] , insee_id )
                 ,_("Ies, Importi"),_("Ne, dankon")
                 , parent=self.uistate.window)
      res = d.run()
      if not res :
        return

    with DbTxn(_('Aldono de loko kun INSEE-id %s') % insee_id, self.dbstate.db) as trans:
      place = self.dbstate.db.get_place_from_gramps_id('FrCogCom'+insee_id)
      if place is None:
        dep = self.__get_dep(codDep , trans)
        place = Place()
        place.gramps_id = 'FrCogCom' + insee_id
        place_name = PlaceName()
        place_name.set_value( json[0]['nom'])
        place.set_name(place_name)
        place.set_code(insee_id)
        place.set_title(json[0]['nom'])
        place.set_longitude(str(json[0]['centre']['coordinates'][0]))
        place.set_latitude(str(json[0]['centre']['coordinates'][1]))
        place_type = PlaceType(14)
        place.set_type(place_type)
        placeref = PlaceRef()
        placeref.ref = dep.handle
        place.add_placeref(placeref)
        self.dbstate.db.add_place(place, trans)

  def __get_places(self, obj):
    insee_id = self.entry.get_text()
    to_do = insee_id.split()
    try:
      preferred_lang = config.get('preferences.place-lang')
    except AttributeError:
      fmt = config.get('preferences.place-format')
      pf = _pd.get_formats()[fmt]
      preferred_lang = pf.language
    if len(preferred_lang) != 2:
      preferred_lang = 'fr'

    with DbTxn(_('Aldono de loko %s') % insee_id, self.dbstate.db) as trans:
      #print("traitement insee_id : "+insee_id)
      while to_do:
        insee_id = to_do.pop()
        place = self.dbstate.db.get_place_from_gramps_id('FrCogCom'+insee_id)
        if place is None:
          self.__get_commune(insee_id , trans)

  def __get_fra(self, trans):

    fra = self.dbstate.db.get_place_from_gramps_id('FRA')
    if fra is not None:
      return fra

    place = Place()
    place.gramps_id = 'FRA'
    place_name = PlaceName()
    place_name.set_value( 'France')
    place.set_name(place_name)
    place.set_code('FRA')
    place.set_title('France')
    place_type = PlaceType(1)
    place.set_type(place_type)
    self.dbstate.db.add_place(place, trans)
    return place

  def __get_reg(self, insee_id , trans):
    reg = self.dbstate.db.get_place_from_gramps_id('FrCogReg'+insee_id)
    if reg is not None:
      return reg

    geo_url = 'http://geo.api.gouv.fr/regions?fields=nom,code&format=json&code=' + insee_id

    response = requests.get(geo_url)
    response.raise_for_status()
    json = response.json()

    place = Place()
    place.gramps_id = 'FrCogReg' + insee_id
    place_name = PlaceName()
    place_name.set_value( json[0]['nom'])
    place.set_name(place_name)
    place.set_code(insee_id)
    place.set_title(json[0]['nom'])
    place_type = PlaceType(9)
    place.set_type(place_type)
    placeref = PlaceRef()
    fra = self.__get_fra( trans)
    placeref.ref = fra.handle
    place.add_placeref(placeref)
    self.dbstate.db.add_place(place, trans)
    return place

  def __get_dep(self, insee_id , trans):
    dep = self.dbstate.db.get_place_from_gramps_id('FrCogDep'+insee_id)
    if dep is not None:
      return dep

    geo_url = 'http://geo.api.gouv.fr/departements?fields=nom,code,codeRegion&format=json&code=' + insee_id

    response = requests.get(geo_url)
    response.raise_for_status()
    json = response.json()
    codReg = json[0]['codeRegion']
    reg = self.__get_reg(codReg , trans)

    place = Place()
    place.gramps_id = 'FrCogDep' + insee_id
    place_name = PlaceName()
    place_name.set_value( json[0]['nom'])
    place.set_name(place_name)
    place.set_code(insee_id)
    place.set_title(json[0]['nom'])
    place_type = PlaceType(10)
    place.set_type(place_type)
    placeref = PlaceRef()
    placeref.ref = reg.handle
    place.add_placeref(placeref)
    self.dbstate.db.add_place(place, trans)
    return place

  def __get_commune(self, insee_id , trans):
    geo_url = 'http://geo.api.gouv.fr/communes?fields=nom,code,centre,codeDepartement,codeRegion&format=json&geometry=centre&code=' + insee_id

    response = requests.get(geo_url)
    response.raise_for_status()
    json = response.json()
    if json == []:
      WarningDialog(_("Nekonata kodo"), _("Ĉi tiu kodo ne estis trovita en la INSEE-datumbazo: ")+insee_id, parent=self.uistate.window)
      return 
    codDep = json[0]['codeDepartement']
    dep = self.__get_dep(codDep , trans)

    place = Place()
    place.gramps_id = 'FrCogCom' + insee_id
    place_name = PlaceName()
    place_name.set_value( json[0]['nom'])
    place.set_name(place_name)
    place.set_code(insee_id)
    place.set_title(json[0]['nom'])
    place.set_longitude(str(json[0]['centre']['coordinates'][0]))
    place.set_latitude(str(json[0]['centre']['coordinates'][1]))
    place_type = PlaceType(14)
    place.set_type(place_type)
    placeref = PlaceRef()
    placeref.ref = dep.handle
    place.add_placeref(placeref)
    self.dbstate.db.add_place(place, trans)
    return place

