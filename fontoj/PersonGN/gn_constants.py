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
"""  module avec diverses constantes utiles pour geneanet
"""

from gramps.gen.lib import EventType
from gramps.gen.const import GRAMPS_LOCALE as glocale

#------------------------------------------------------------------------
#
# Internationalisation
#
#------------------------------------------------------------------------
try:
  _trans = glocale.get_addon_translator(__file__)
except ValueError:
  _trans = glocale.translation
_ = _trans.gettext

GN_GRAMPS_FAKTOJ = {
    # traduction des types d'évènements vers les types prédéfinis dans gramps
    "EFAM_ANNULATION": EventType.ANNULMENT,
    "EFAM_CUSTOM": EventType.CUSTOM,
    "EFAM_DIVORCE": EventType.DIVORCE,
    "EFAM_ENGAGE": EventType.ENGAGEMENT,
    "EFAM_MARRIAGE": EventType.MARRIAGE,
    "EFAM_MARRIAGE_BANN": EventType.MARR_BANNS,
    "EFAM_MARRIAGE_CONTRACT": EventType.MARR_CONTR,
    "EFAM_MARRIAGE_LICENSE": EventType.MARR_LIC,
    #  "EFAM_NO_MARRIAGE": EventType. ,
    #  "EFAM_NO_MENTION": EventType. ,
    "EFAM_PACS": EventType.MARR_ALT,
    "EFAM_RESIDENCE": EventType.RESIDENCE,
    #  "EFAM_SEPARATED": EventType. ,
    #  "EPERS_ACCOMPLISHMENT": EventType. ,
    #  "EPERS_ACQUISITION": EventType. ,
    #  "EPERS_ADHESION": EventType. ,
    "EPERS_ADOPTION": EventType.ADOPT,
    "EPERS_ADULTCHRISTENING": EventType.ADULT_CHRISTEN,
    "EPERS_ANNULMENT": EventType.ANNULMENT,
    "EPERS_BAPTISM": EventType.BAPTISM,
    #  "EPERS_BAPTISMLDS": EventType. ,
    "EPERS_BARMITZVAH": EventType.BAR_MITZVAH,
    "EPERS_BATMITZVAH": EventType.BAS_MITZVAH,
    #  "EPERS_BENEDICTION": EventType. ,
    "EPERS_BIRTH": EventType.BIRTH,
    "EPERS_BLESSING": EventType.BLESS,
    "EPERS_BURIAL": EventType.BURIAL,
    "EPERS_CENSUS": EventType.CENSUS,
    #  "EPERS_CHANGENAME": EventType. ,
    "EPERS_CHRISTENING": EventType.CHRISTEN,
    #  "EPERS_CIRCUMCISION": EventType. ,
    "EPERS_COMMONLAWMARRIAGE": EventType.MARR_ALT,
    #  "EPERS_CONFIRMATIONLDS": EventType. ,
    "EPERS_CONFIRMATION": EventType.CONFIRMATION,
    "EPERS_CREMATION": EventType.CREMATION,
    "EPERS_CUSTOM": EventType.CUSTOM,
    "EPERS_DEATH": EventType.DEATH,
    #  "EPERS_DECORATION": EventType. ,
    #  "EPERS_DEMOBILISATIONMILITAIRE": EventType. ,
    #  "EPERS_DIPLOMA": EventType. ,
    #  "EPERS_DISTINCTION": EventType. ,
    "EPERS_DIVORCE": EventType.DIVORCE,
    "EPERS_DIVORCEFILING": EventType.DIV_FILING,
    #  "EPERS_DOTATION": EventType. ,
    #  "EPERS_DOTATIONLDS": EventType. ,
    "EPERS_EDUCATION": EventType.EDUCATION,
    "EPERS_ELECTION": EventType.ELECTED,
    "EPERS_EMIGRATION": EventType.EMIGRATION,
    "EPERS_ENGAGEMENT": EventType.ENGAGEMENT,
    #  "EPERS_EXCOMMUNICATION": EventType. ,
    #  "EPERS_FAMILYLINKLDS": EventType. ,
    "EPERS_FIRSTCOMMUNION": EventType.FIRST_COMMUN,
    #  "EPERS_FUNERAL": EventType. ,
    "EPERS_GRADUATE": EventType.GRADUATION,
    "EPERS_GRADUATION": EventType.GRADUATION,
    #  "EPERS_HOSPITALISATION": EventType. ,
    #  "EPERS_ILLNESS": EventType. ,
    "EPERS_IMMIGRATION": EventType.IMMIGRATION,
    #  "EPERS_LISTEPASSENGER": EventType. ,
    "EPERS_MARRIAGEBANNS": EventType.MARR_BANNS,
    "EPERS_MARRIAGECONTRACT": EventType.MARR_CONTR,
    "EPERS_MARRIAGELICENSE": EventType.MARR_LIC,
    "EPERS_MEDICAL": EventType.MED_INFO,
    #  "EPERS_MILITARYDISTINCTION": EventType. ,
    #  "EPERS_MILITARYPROMOTION": EventType. ,
    "EPERS_MILITARYSERVICE": EventType.MILITARY_SERV,
    #  "EPERS_MOBILISATIONMILITAIRE": EventType. ,
    "EPERS_NATURALIZATION": EventType.NATURALIZATION,
    "EPERS_NUMBEROFMARRIAGES": EventType.NUM_MARRIAGES,
    "EPERS_OCCUPATION": EventType.OCCUPATION,
    "EPERS_ORDINATION": EventType.ORDINATION,
    "EPERS_PROBATE": EventType.PROBATE,
    "EPERS_PROPERTY": EventType.PROPERTY,
    "EPERS_RECENSEMENT": EventType.CENSUS,
    "EPERS_RELIGION": EventType.RELIGION,
    "EPERS_RESIDENCE": EventType.RESIDENCE,
    #  "EPERS_RETIRED": EventType. ,
    "EPERS_RETIREMENT": EventType.RETIREMENT,
    #  "EPERS_SCELLENTCHILDLDS": EventType. ,
    #  "EPERS_SCELLENTPARENTLDS": EventType. ,
    #  "EPERS_SCELLENTSPOUSELDS": EventType. ,
    "EPERS_STILLBIRTH": EventType.STILLBIRTH,
    "EPERS_TITLEOFNOBILITY": EventType.NOB_TITLE,
    #  "EPERS_VENTEBIEN": EventType. ,
    "EPERS_WILL": EventType.WILL,
    # traductions sans types prédéfinis correspondants": EventType. ,
    #  "EFAM_NO_MARRIAGE": EventType. ,
    #  "EFAM_NO_MENTION": EventType. ,
    #  "EFAM_SEPARATED": EventType. ,
    #  "EPERS_ACCOMPLISHMENT": EventType. ,
    #  "EPERS_ACQUISITION": EventType. ,
    #  "EPERS_ADHESION": EventType. ,
    #  "EPERS_BAPTISMLDS": EventType. ,
    #  "EPERS_BENEDICTION": EventType. ,
    #  "EPERS_CHANGENAME": EventType. ,
    #  "EPERS_CIRCUMCISION": EventType. ,
    #  "EPERS_CONFIRMATIONLDS": EventType. ,
    #  "EPERS_DECORATION": EventType. ,
    #  "EPERS_DEMOBILISATIONMILITAIRE": EventType. ,
    #  "EPERS_DIPLOMA": EventType. ,
    #  "EPERS_DISTINCTION": EventType. ,
    #  "EPERS_DOTATION": EventType. ,
    #  "EPERS_DOTATIONLDS": EventType. ,
    #  "EPERS_EXCOMMUNICATION": EventType. ,
    #  "EPERS_FAMILYLINKLDS": EventType. ,
    #  "EPERS_FUNERAL": EventType. ,
    #  "EPERS_HOSPITALISATION": EventType. ,
    #  "EPERS_ILLNESS": EventType. ,
    #  "EPERS_LISTEPASSENGER": EventType. ,
    #  "EPERS_MILITARYDISTINCTION": EventType. ,
    #  "EPERS_MILITARYPROMOTION": EventType. ,
    #  "EPERS_MOBILISATIONMILITAIRE": EventType. ,
    #  "EPERS_RETIRED": EventType. ,
    #  "EPERS_SCELLENTCHILDLDS": EventType. ,
    #  "EPERS_SCELLENTPARENTLDS": EventType. ,
    #  "EPERS_SCELLENTSPOUSELDS": EventType. ,
    #  "EPERS_VENTEBIEN": EventType. ,
}
