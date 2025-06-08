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

#------------------------------------------------------------------------
#
# Geneanet Gramplet
#
#------------------------------------------------------------------------
from gramps.version import major_version

register(GRAMPLET,
         id = "PersonGN",
         name = _("Geneanet Gramplet"),
         description = _("interfaco por Geneanet"),
         status = STABLE,
         fname="PersonGN.py",
         height=100,
         expand=True,
         gramplet = 'PersonGN',
         gramplet_title=_("Geneanet"),
         detached_width = 500,
         detached_height = 500,
         version = 'beta 0.1.3',
         gramps_target_version= major_version,
         navtypes=["Person"],
         )

