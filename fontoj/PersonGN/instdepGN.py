"""  modulo ebliganta vin instali dependecojn per pip 
  pylint options :
         --indent-string "  " 
         --function-naming-style 'camelCase' 
         --const-naming-style='PascalCase'
"""

try:
  from importlib.metadata import version
  from importlib import invalidate_caches
  import pip
  HavPip=True
except ImportError:
  HavPip=False
try :
  from packaging.version import parse
except ImportError:
  def parse(versio) :
    x = versio.split('.')
    res = 0
    if len(x)>=1 :
      res += int(x[0])*1000000
    if len(x)>=2 :
      res += int(x[1])*1000
    if len(x)>=3 :
      res += int(x[2])
    return res

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


from gramps.gen.const import LIB_PATH

def instDep(modulo,versio):
  """ instDep provas instali dependecon kiel argumenton """
  #print( "Sercxi %s , versio %s" % (modulo , versio))
  if not HavPip:
    print( _("PersonGN : pip ne trovita."))
    return False
  if parse(pip.__version__) >= parse('23.1') :
    pipHavBreak = True
  else :
    pipHavBreak = False
  try:
    v_0 = version(modulo)
  except Exception:
    v_0="0.0.0"
  if parse(v_0) < parse(versio) :
    print (f'dependeco {modulo} ne trovita aŭ < {versio}')
    if pipHavBreak :
      pip.main(['install', '--target', LIB_PATH, '--upgrade', '--break-system-packages', modulo])
      invalidate_caches()
      v = version(modulo)
      if parse(v) < parse(versio) :
        pip.main(['install', '--target', LIB_PATH, '--upgrade', '--break-system-packages', modulo,'--only-binary',':all:'])
        invalidate_caches()
    else :
      pip.main(['install', '--target', LIB_PATH, '--upgrade', modulo])
      invalidate_caches()
      v = version(modulo)
      if parse(v) < parse(versio) :
        pip.main(['install', '--target', LIB_PATH, '--upgrade', modulo,'--only-binary',':all:'])
        invalidate_caches()
    v = version(modulo)
    if parse(v) < parse(versio) :
      print( _("dependeco %s ne trovita") % modulo )
      return False
    else :
      print( _("dependeco %s instalita, versio %s") % (modulo , v))
      return True
  else:
    #print( _("dependeco %s trovita, versio %s") % (modulo , v_0))
    return True
