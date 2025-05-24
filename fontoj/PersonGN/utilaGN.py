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

from gramps.gen.db import DbTxn
from gramps.gen.lib import Attribute, EventRoleType, Date, SrcAttribute
from gramps.gen.lib.date import gregorian
from gramps.gui.dialog import WarningDialog, QuestionDialog2

from gramps.gen.const import GRAMPS_LOCALE as glocale

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


def get_fsftid(grObj) :
  if not grObj :
    return ''
  for attr in grObj.get_attribute_list():
    if attr.get_type() == '_FSFTID':
      return attr.get_value()
  return ''

def get_url(grObj) :
  if not grObj :
    return None
  for attr in grObj.get_attribute_list():
    if attr.get_type() == _('Internet Address'):
      return attr.get_value()
  return None

def get_grevent(db, person, event_type):
  """
  " Liveras la unuan gramps eventon de la donita tipo.
  """
  if not person:
    return None
  for event_ref in person.get_event_ref_list():
    if int(event_ref.get_role()) == EventRoleType.PRIMARY:
      event = db.get_event_from_handle(event_ref.ref)
      if event.get_type() == event_type:
        return event
  return None

def grdato_al_formal( dato) :
  """
  " konvertas gramps-daton al «formal» dato
  "   «formal» dato : <https://github.com/FamilySearch/gedcomx/blob/master/specifications/date-format-specification.md>
  """
  if dato is None :
    return None;
  res=''
  gdato = gregorian(dato)
  if gdato.modifier == Date.MOD_ABOUT :
    res = 'A'
  elif gdato.modifier == Date.MOD_BEFORE:
    res = '/'
  if gdato.dateval[Date._POS_YR] < 0 :
    res = res + '-'
  else :
    res = res + '+'
  if gdato.dateval[Date._POS_DAY] > 0 :
    val = "%04d-%02d-%02d" % (
                gdato.dateval[Date._POS_YR], gdato.dateval[Date._POS_MON],
                gdato.dateval[Date._POS_DAY])
  elif gdato.dateval[Date._POS_MON] > 0 :
    val = "%04d-%02d" % (
                gdato.dateval[Date._POS_YR], gdato.dateval[Date._POS_MON])
  elif gdato.dateval[Date._POS_YR] > 0 :
    val = "%04d" % ( gdato.dateval[Date._POS_YR] )
  else :
    res = gdato.text
    val=''
  res = res+val
  if gdato.modifier == Date.MOD_AFTER:
    res = res + '/'
  if gdato.modifier == Date.MOD_RANGE:
    res = res + '/'
    if gdato.dateval[Date._POS_RYR] < 0 :
      res = res + '-'
    else :
      res = res + '+'
    if gdato.dateval[Date._POS_RDAY] > 0 :
      val = "%04d-%02d-%02d" % (
                gdato.dateval[Date._POS_RYR], gdato.dateval[Date._POS_RMON],
                gdato.dateval[Date._POS_RDAY])
    elif gdato.dateval[Date._POS_RMON] > 0 :
      val = "%04d-%02d" % (
                gdato.dateval[Date._POS_RYR], gdato.dateval[Date._POS_RMON])
    elif gdato.dateval[Date._POS_RYR] > 0 :
      val = "%04d" % ( gdato.dateval[Date._POS_RYR] )
    else:
      val = ''
    res = res+val
  # FARINDAĴOJ : range ?  estimate ? calculate ? heure ?
  
  return res

def extdato_al_formal(dato) :
  if dato is None:
    return ''
  splt = dato.split(' ')
  if len(splt) == 3 :
    res = '+'+splt[2]
    match splt[1]:
     case 'Jan.':
      res += '-01'
     case 'Feb.':
      res += '-02'
     case 'Mar.':
      res += '-03'
     case 'Apr.':
      res += '-04'
     case 'May.':
      res += '-05'
     case 'Jun.':
      res += '-06'
     case 'Jul.':
      res += '-07'
     case 'Aug.':
      res += '-08'
     case 'Sep.':
      res += '-09'
     case 'Oct.':
      res += '-10'
     case 'Nov.':
      res += '-11'
     case 'Dec.':
      res += '-12'
     case _:
      res += '-'+splt[2]
    res += '-'+splt[0]
    return res
  else:
    return dato
