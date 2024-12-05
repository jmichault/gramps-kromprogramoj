

try:
  import importlib
  from importlib.metadata import version
  from packaging.version import parse
  import pip
  HavPip=True
except:
  HavPip=False
  pass

def instDep(modulo,versio):
  global HavPip
  if not HavPip:
    return
  try:
    v = version(modulo)
  except :
    v="0.0.0"
  if parse(v) < parse(versio) :
    print ('dependeco %s ne trovita aŭ < %s' % ( modulo , versio))
    pip.main(['install', '--user', '--upgrade', '--break-system-packages', modulo])
  #else:
  #  print( "dependeco %s trovita, versio %s" % (modulo , v))

