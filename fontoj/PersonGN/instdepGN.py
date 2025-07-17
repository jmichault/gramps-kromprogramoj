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
"""  modulo ebliganta vin instali dependecojn per pip 
"""

try:
  from importlib.metadata import version,PackageNotFoundError
  from importlib import invalidate_caches
  import pip
  HavPip=True
except ImportError:
  HavPip=False
try :
  from packaging.version import parse
except ImportError:
  def parse(versio) :
    """ alternative simple parse function """
    x = versio.split('.')
    res = 0
    if len(x)>=1 :
      res += int(x[0])*1000000
    if len(x)>=2 :
      res += int(x[1])*1000
    if len(x)>=3 :
      res += int(x[2])
    return res

from gramps.gen.const import LIB_PATH
from gn_constants import _

def instDep(modulo,versio):
  """ instDep provas instali dependecon kiel argumenton """
  #print( "Sercxi %s , versio %s" % (modulo , versio))
  if not HavPip:
    print( _("PersonGN : pip ne trovita."))
    return False
  pipHavBreak = bool(parse(pip.__version__) >= parse('23.1'))
  try:
    v0 = version(modulo)
  except (ValueError,PackageNotFoundError):
    v0="0.0.0"
  if parse(v0) < parse(versio) :
    print (f'dependeco {modulo} ne trovita aŭ < {versio}')
    if pipHavBreak :
      pip.main(['install', '--target', LIB_PATH, '--upgrade', '--break-system-packages', modulo])
      invalidate_caches()
      try:
        v = version(modulo)
      except (ValueError,PackageNotFoundError):
        v="0.0.0"
      if parse(v) < parse(versio) :
        pip.main(['install', '--target', LIB_PATH, '--upgrade'
                 , '--break-system-packages', modulo,'--only-binary',':all:'])
        invalidate_caches()
    else :
      pip.main(['install', '--target', LIB_PATH, '--upgrade', modulo])
      invalidate_caches()
      try:
        v = version(modulo)
      except (ValueError,PackageNotFoundError):
        v="0.0.0"
      if parse(v) < parse(versio) :
        pip.main(['install', '--target', LIB_PATH, '--upgrade', modulo,'--only-binary',':all:'])
        invalidate_caches()
    try:
      v = version(modulo)
    except (ValueError,PackageNotFoundError):
      v="0.0.0"
    if parse(v) < parse(versio) :
      print( _("dependeco %s ne trovita") % modulo )
      return False
    print( _("dependeco %s instalita, versio %s") % (modulo , v))
    return True
  #print( _("dependeco %s trovita, versio %s") % (modulo , v0))
  return True
