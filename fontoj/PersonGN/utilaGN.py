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
"""  module avec diverses fonctions utiles
"""

from gramps.gen.lib import EventRoleType, EventType, Date
from gramps.gen.lib.date import gregorian
from gramps.gen.datehandler import LANG_TO_PARSER

from gn_constants import _

parserEn = LANG_TO_PARSER['en']()

def getUrl(gr_obj) :
  """
  " renvoie l'url geneanet de l'objet, sans le préfixe 'https://gw.geneanet.org/'
  """
  if not gr_obj :
    return None
  for attr in gr_obj.get_attribute_list() :
    if attr.get_type() == _('Internet Address') :
      url = attr.get_value()
      if url[0:24] == 'https://gw.geneanet.org/' :
        return url[24:]
  return None

def getBirth(db, person):
  """ renvoie la date de naissance, ou à défaut de baptême """
  grBirth = getGrevent(db, person, EventType(EventType.BIRTH))
  if grBirth is None or grBirth.date is None or grBirth.date.is_empty():
    grBirth = getGrevent(db, person, EventType(EventType.CHRISTEN))
  if grBirth is None or grBirth.date is None or grBirth.date.is_empty():
    grBirth = getGrevent(db, person, EventType(EventType.ADULT_CHRISTEN))
  if grBirth is None or grBirth.date is None or grBirth.date.is_empty():
    grBirth = getGrevent(db, person, EventType(EventType.BAPTISM))
  return grBirth

def getGrevent(db, person, event_type):
  """
  " Liveras la unuan gramps eventon de la donita tipo.
  """
  if not person:
    return None
  for eventRef in person.get_event_ref_list():
    if int(eventRef.get_role()) == EventRoleType.PRIMARY:
      event = db.get_event_from_handle(eventRef.ref)
      if event.get_type() == event_type:
        return event
  return None

def formatiDato(jaro,monato,tago):
  """ formate la date à YYYY-MM-DD, en ignorant le jour et/ou le mois si pas renseignés """
  if jaro < 0 :
    res = '-'
  else :
    res = '+'
  if jaro > 0 :
    res = res + f"{jaro:04d}"
    if monato > 0 :
      res = res + f"-{monato:02d}"
      if tago > 0 :
        res = res + f"-{tago:02d}"
  return res



def grdatoAlFormal( dato) :
  """
  " konvertas gramps-daton al «formal» dato
  "   «formal» dato :
  "<https://github.com/FamilySearch/gedcomx/blob/master/specifications/date-format-specification.md>
  """
  if dato is None :
    return None
  res=''
  gdato = gregorian(dato)
  if gdato.modifier == Date.MOD_ABOUT :
    res = 'A'
  if gdato.modifier == Date.MOD_BEFORE:
    res = '/'
  if gdato.get_year() != 0:
    res = res + formatiDato(gdato.get_year(),gdato.get_month(),gdato.get_day())
  else:
    res = gdato.text
  if gdato.modifier == Date.MOD_AFTER:
    res = res + '/'
  if gdato.modifier == Date.MOD_RANGE:
    res = res + '/'
    if gdato.get_stop_year() < 0 :
      res = res + '-'
    else :
      res = res + '+'
    res = res + formatiDato(gdato.get_stop_year(),gdato.get_stop_month(),gdato.get_stop_day())
  # FARINDAĴOJ : range ?  estimate ? calculate ? heure ?
  return res

def extdatoAlFormal(dato) :
  """ convertit une date externe (geneanet) en date formal(familySearch) """
  if dato is None:
    return ''
  grDato = parserEn.parse(dato)
  return grdatoAlFormal( grDato)
