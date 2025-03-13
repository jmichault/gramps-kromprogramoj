"""  modulo ebliganta vin instali dependecojn per pip 
  pylint options :
         --indent-string "  " 
         --function-naming-style 'camelCase' 
         --const-naming-style='PascalCase'
"""

try:
  from importlib.metadata import version
  from packaging.version import parse
  import pip
  HavPip=True
except ImportError:
  HavPip=False

def instDep(modulo,versio):
  """ instDep provas instali dependecon kiel argumenton """
  if not HavPip:
    return
  try:
    v_0 = version(modulo)
  except Exception:
    v_0="0.0.0"
  if parse(v_0) < parse(versio) :
    print (f'dependeco {modulo} ne trovita aŭ < {versio}')
    pip.main(['install', '--user', '--upgrade', '--break-system-packages', modulo])
    pip.main(['install', '--user', '--upgrade', '--break-system-packages', modulo,'--only-binary',':all:'])
  #else:
  #  print( "dependeco %s trovita, versio %s" % (modulo , v))
