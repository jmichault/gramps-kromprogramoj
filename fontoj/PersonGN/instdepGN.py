"""  modulo ebliganta vin instali dependecojn per pip 
  pylint options :
         --indent-string "  " 
         --function-naming-style 'camelCase' 
         --const-naming-style='PascalCase'
"""

try:
  from importlib.metadata import version, invalidate_caches
  from packaging.version import parse
  import pip
  HavPip=True
except ImportError:
  HavPip=False

from gramps.gen.const import LIB_PATH

def instDep(modulo,versio):
  """ instDep provas instali dependecon kiel argumenton """
  if not HavPip:
    return
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
      pip.main(['install', '--target', LIB_PATH, '--upgrade', '--break-system-packages', modulo,'--only-binary',':all:'])
    else :
      pip.main(['install', '--target', LIB_PATH, '--upgrade', modulo])
      pip.main(['install', '--target', LIB_PATH, '--upgrade', modulo,'--only-binary',':all:'])
  invalidate_caches()
  #else:
  #  print( "dependeco %s trovita, versio %s" % (modulo , v))
