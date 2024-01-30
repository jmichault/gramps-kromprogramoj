#
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


"""
Lokpurigado Gramplet.
"""

register(
    GRAMPLET,
    id = "Lokpurigado",
    name = _("Lokpurigado"),
    description = _("Lokpurigado helpas kompletigi lokojn uzante OpenStreetMap."),
    status = STABLE,
    version = '1.0.19',
    gramps_target_version = '5.1',
    fname = "lokpurigado.py",
    gramplet = 'Lokpurigado',
    navtypes=["Place"],
    height = 375,
    detached_width = 510,
    detached_height = 480,
    expand = True,
    gramplet_title = _("Lokpurigado"),
    help_url="Addon:Lokpurigado",
    include_in_listing = True,
    )
