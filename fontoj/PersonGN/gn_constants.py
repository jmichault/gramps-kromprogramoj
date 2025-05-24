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


from gramps.gen.lib import EventType

GN_GRAMPS_FAKTOJ = {
# traduction des types d'évènements vers les types prédéfinis dans gramps
  "EPERS_ADOPTION": EventType.ADOPT,
  "EPERS_ADULTcHRISTENING": EventType.ADULT_CHRISTEN,
  "EPERS_ANNULMENT": EventType.ANNULMENT,
  "EPERS_BAPTISM": EventType.BAPTISM,
  "EPERS_BARMITZVAH": EventType.BAR_MITZVAH,
  "EPERS_BATMITZVAH": EventType.BAS_MITZVAH,
  "EPERS_BIRTH": EventType.BIRTH,
  "EPERS_BLESSING": EventType.BLESS,
  "EPERS_BURIAL": EventType.BURIAL,
  "EPERS_CENSUS": EventType.CENSUS,
  "EPERS_CHRISTENING": EventType.CHRISTEN,
  "EPERS_COMMONLAWMARRIAGE": EventType.MARR_ALT,
  "EPERS_CONFIRMATION": EventType.CONFIRMATION,
  "EPERS_CREMATION": EventType.CREMATION,
  "EPERS_DEATH": EventType.DEATH,
  "EPERS_DIVORCE": EventType.DIVORCE,
  "EPERS_DIVORCEFILING": EventType.DIV_FILING,
  "EPERS_EDUCATION": EventType.EDUCATION,
  "EPERS_EMIGRATION": EventType.EMIGRATION,
  "EPERS_ENGAGEMENT": EventType.ENGAGEMENT,
  "EPERS_FIRSTCOMMUNION": EventType.FIRST_COMMUN,
  "EPERS_GRADUATION": EventType.GRADUATION,
  "EPERS_IMMIGRATION": EventType.IMMIGRATION,
  "EPERS_MILITARYSERVICE": EventType.MILITARY_SERV,
  "EFAM_MARRIAGE": EventType.MARRIAGE,
  "EPERS_MARRIAGEBANNS": EventType.MARR_BANNS,
  "EPERS_MARRIAGECONTRACT": EventType.MARR_CONTR,
  "EPERS_MARRIAGELICENSE": EventType.MARR_LIC,
  "EPERS_MEDICAL": EventType.MED_INFO,
  "EPERS_NATURALIZATION": EventType.NATURALIZATION,
  "EPERS_NUMBEROFMARRIAGES": EventType.NUM_MARRIAGES,
  "EPERS_OCCUPATION": EventType.OCCUPATION,
  "EPERS_ORDINATION": EventType.ORDINATION,
  "EPERS_PROBATE": EventType.PROBATE,
  "EPERS_PROPERTY": EventType.PROPERTY,
  "EPERS_RELIGION": EventType.RELIGION,
  "EPERS_RESIDENCE": EventType.RESIDENCE,
  "EPERS_RETIREMENT": EventType.RETIREMENT,
  "EPERS_STILLBIRTH": EventType.STILLBIRTH,
  "EPERS_WILL": EventType.WILL,
  "EPERS_TITLEOFNOBILITY": EventType.NOB_TITLE,
# traductions sans types prédéfinis correspondants
}
