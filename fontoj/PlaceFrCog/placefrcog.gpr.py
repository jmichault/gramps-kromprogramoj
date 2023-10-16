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

#------------------------------------------------------------------------
#
# PlaceFrCog Gramplet
#
#------------------------------------------------------------------------

register(GRAMPLET,
         id = "PlaceFrCog Gramplet",
         name = _("Lokoj : Franca Oficiala Geografia Kodo"),
         description = _("Gramplet por preni municipojn de la datumbazo Insee"),
         status = STABLE,
         version = '1.0.18',
         gramps_target_version = '5.1',
         fname = "placefrcog.py",
         gramplet = 'PlaceFrCog',
         height = 375,
         detached_width = 510,
         detached_height = 480,
         expand = True,
         gramplet_title = _("Fr COG"),
         include_in_listing = True,
        )
