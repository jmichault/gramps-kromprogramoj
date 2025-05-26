#!/usr/bin/env python
# coding: utf-8
# 
# Gramplet - PersonGN (interfaco por geneanet)
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

from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.display.place import displayer as _pd
from gramps.gen.lib import Date, EventType, Person
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.datehandler import parser
from gramps.gen.datehandler import LANG_TO_PARSER
parserEn = LANG_TO_PARSER['en']()

import utilaGN
import geneanet

#from objbrowser import browse ;browse(locals())
#import pdb; pdb.set_trace()

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


def SeksoKomp(grPersono, extPersono ) :
  if grPersono.get_gender() == Person.MALE :
    grSekso = _trans.gettext("male")
  elif grPersono.get_gender() == Person.FEMALE :
    grSekso = _trans.gettext("female")
  else :
    grSekso = _trans.gettext("unknown")
  extSekso = _trans.gettext("unknown")
  if 'person' in extPersono :
    s = extPersono['person'].get('sex')
    if s == 'MALE' :
      extSekso = _trans.gettext("male")
    elif s == 'FEMALE' :
      extSekso = _trans.gettext("female") 
  koloro = "red"
  if (grSekso == extSekso) :
    koloro = "green"
  return [ koloro , _('Sekso:')
        , '', grSekso
        , '', extSekso, ''
        , False, 'sekso', None, None, None, None
        ]

def NomojKomp(grPersono, extPersono ) :
    grNomo = grPersono.primary_name
    extNomo = extPersono['person'].get('lastname')
    extANomo = extPersono['person'].get('firstname')
    koloro = "red"
    if (grNomo.get_surname().upper() == extNomo.upper()) and (grNomo.first_name.upper() == extANomo.upper()) :
      koloro = "green"
    res = list()
    res.append ( [ koloro , _trans.gettext('Name')
        , '', grNomo.get_surname() + ', ' + grNomo.first_name
        , '', extNomo +  ', ' + extANomo , ''
        , False, 'nomo1', str(grNomo), None, grNomo.get_surname(), grNomo.first_name
        ])
    return res

def FaktoKomp(db, grPersono, extPerso, grEvent , extFact ) :
  grFakto = utilaGN.get_grevent(db, grPersono, EventType(grEvent))
  grFakto_handle = None
  titolo = str(EventType(grEvent))
  if grFakto is not None :
    grFakto_handle = grFakto.handle
    grFaktoDato = utilaGN.grdato_al_formal(grFakto.date)
    if grFakto.place and grFakto.place != None :
      place = db.get_place_from_handle(grFakto.place)
      #grFaktoLoko = place.name.value
      grFaktoLoko = _pd.display(db,place)
    else :
      grFaktoLoko = ''
  else :
    grFaktoDato = ''
    grFaktoLoko = ''
  extFaktoDato = utilaGN.extdato_al_formal(extPerso['person'].get(extFact+'Date'))
  extFaktoLoko = extPerso['person'].get(extFact+'Place')
  if grFakto is None and extFaktoDato == '' and extFaktoLoko is None :
    return None
  if grEvent == EventType.BIRTH or grEvent == EventType.DEATH :
    koloro = "red"
  else:
    koloro = "orange"
  if (grFaktoDato == extFaktoDato) :
    koloro = "green"
  if grFaktoDato == '' and grFaktoLoko == '' and extFaktoDato == '' and extFaktoLoko == '' :
    return None
  if extFaktoDato == '' and grFaktoDato != '':
    koloro = "yellow"
  if grFaktoDato == '' and extFaktoDato != '':
    koloro = "yellow3"
  return ( koloro , titolo
        , grFaktoDato , grFaktoLoko
        , extFaktoDato , extFaktoLoko , ''
        , False, 'fakto', grFakto_handle, None
        )

def grperso_datoj (db, grPersono) :
  if not grPersono:
    return ''
  grBirth = utilaGN.get_grevent(db, grPersono, EventType(EventType.BIRTH))
  if grBirth :
    if grBirth.date.modifier == Date.MOD_ABOUT :
      res = '~'
    elif grBirth.date.modifier == Date.MOD_BEFORE:
      res = '/'
    else :
      res = ' '
    val = "%04d" % ( grBirth.date.dateval[Date._POS_YR] )
    if val == '0000' :
      val = '....'
    if grBirth.date.modifier == Date.MOD_AFTER:
      res = res + val + '/-'
    else :
      res = res + val + '-'
  else :
    res = ' ....-'
  grDeath = utilaGN.get_grevent(db, grPersono, EventType(EventType.DEATH))
  if grDeath :
    if grDeath.date.modifier == Date.MOD_ABOUT :
      res = res + '~'
    elif grDeath.date.modifier == Date.MOD_BEFORE:
      res = res + '/'
    val = "%04d" % ( grDeath.date.dateval[Date._POS_YR] )
    if val == '0000' :
      val = '....'
    if grDeath.date.modifier == Date.MOD_AFTER:
      res = res + val + '/'
    else :
      res = res + val
  else :
    res = res + '....'
  return res

def extperso_datoj(extPersono) :
  res=''
  if extPersono is None :
    return res
  dato = extPersono.get('birthDateConv')
  if dato is None : dato = extPersono.get('birthShortDate')
  grBirth = None
  if dato :
    grBirth = parserEn.parse(dato)
  if grBirth :
    if grBirth.modifier == Date.MOD_ABOUT :
      res = '~'
    elif grBirth.modifier == Date.MOD_BEFORE:
      res = '/'
    else :
      res = ' '
    val = "%04d" % ( grBirth.dateval[Date._POS_YR] )
    if val == '0000' :
      val = '....'
    if grBirth.modifier == Date.MOD_AFTER:
      res = res + val + '/-'
    else :
      res = res + val + '-'
  else :
    res = ' ....-'
  dato = extPersono.get('deathDateConv')
  if dato is None : dato = extPersono.get('deathShortDate')
  grDeath = None
  if dato :
    grDeath = parserEn.parse(dato)
  if grDeath :
    if grDeath.modifier == Date.MOD_ABOUT :
      res = res + '~'
    elif grDeath.modifier == Date.MOD_BEFORE:
      res = res + '/'
    val = "%04d" % ( grDeath.dateval[Date._POS_YR] )
    if val == '0000' :
      val = '....'
    if grDeath.modifier == Date.MOD_AFTER:
      res = res + val + '/'
    else :
      res = res + val
  else :
    res = res + '....'
  return res


def GepKomp(db, grPersono, extPersono ) :
  """
  " aldonas gepatran komparon
  """
  family_handle = grPersono.get_main_parents_family_handle()
  father = None
  father_handle = None
  father_name = ''
  mother = None
  mother_handle = None
  mother_name = ''
  res = list()
  if family_handle:
    family = db.get_family_from_handle(family_handle)
    father_handle = family.get_father_handle()
    if father_handle:
      father = db.get_person_from_handle(father_handle)
      father_name = name_displayer.display(father)
    mother_handle = family.get_mother_handle()
    if mother_handle:
      mother = db.get_person_from_handle(mother_handle)
      mother_name = name_displayer.display(mother)
  extFather = extPersono['person'].get('father')
  ext_patro_nomo = extPatUrl = ''
  if extFather :
    ext_patro_nomo = extFather.get('lastname')+', '+extFather.get('firstname')
    extPatUrl = geneanet.id2url(extFather)
  koloro = "orange"
  if father_name.upper() == ext_patro_nomo.upper() :
    koloro = "green"
  if father is not None or extFather is not None :
    res.append ( [ koloro , _trans.gettext('Father')
        , grperso_datoj(db, father) , ' ' + father_name 
        , extperso_datoj( extFather) , ext_patro_nomo , ''
        , False, 'patro', father_handle , extPatUrl, None, None
        ] )
  extMother = extPersono['person'].get('mother')
  ext_patrino_nomo = extMatUrl = ''
  if extMother :
    ext_patrino_nomo = extMother.get('lastname')+', '+extMother.get('firstname')
    extMatUrl = geneanet.id2url(extMother)
  koloro = "orange"
  if mother_name.upper() == ext_patrino_nomo.upper() :
    koloro = "green"
  if mother is not None or extMother is not None :
    res.append ( [ koloro , _trans.gettext('Mother')
        , grperso_datoj(db, mother) , ' ' + mother_name 
        , extperso_datoj( extMother) , ext_patrino_nomo , ''
        , False, 'patrino', mother_handle ,extMatUrl, None, None
        ] )
  return res

def kompariGrExt(grPersono,extPersono,db,model):
  # Komparo de esenca eroj
  ext_Esenco = False
  listres=list()
  res = SeksoKomp(grPersono, extPersono)
  if res:
    listres.append(res)
    if res[0] != "green" : ext_Esenco = True
  resNomoj = NomojKomp(grPersono, extPersono)
  if resNomoj :
    if resNomoj[0][0] != "green" : ext_Esenco = True
    listres.append(resNomoj.pop(0))
  res = FaktoKomp(db, grPersono, extPersono, EventType.BIRTH , "birth") 
  if res:
    listres.append(res)
    if res[0] != "green" : ext_Esenco = True
  res = FaktoKomp(db, grPersono, extPersono, EventType.BAPTISM , "baptism") 
  if res:
    listres.append(res)
    if res[0] != "green" : ext_Esenco = True
  res = FaktoKomp(db, grPersono, extPersono, EventType.DEATH , "death") 
  if res:
    listres.append(res)
    if res[0] != "green" : ext_Esenco = True
  res = FaktoKomp(db, grPersono, extPersono, EventType.BURIAL , "burial") 
  if res:
    listres.append(res)
    if res[0] != "green" : ext_Esenco = True
  if len(listres) :
    if ext_Esenco:
      esenco_nodo = model.add(['red',_('Esenco'),'==========','============================','==========','','',False,'Esenco',None,None,None,None]  )
    else:
      esenco_nodo = model.add(['green',_('Esenco'),'==========','============================','==========','','',False,'Esenco',None,None,None,None]  )
    for linio in listres:
      model.add( linio,node=esenco_nodo)
  # parents
  listres = GepKomp(db, grPersono, extPersono )
  if len(listres) :
    koloro=listres[0][0]
    if koloro == 'green' and len(listres)>1 :
      koloro=listres[1][0]
    gepatroj_nodo = model.add([koloro,_('Gepatroj'),'==========','============================','==========','','',False,'Gepatroj',None,None,None,None]  )
    for linio in listres:
      model.add( linio,node=gepatroj_nodo)
  # familles
  grFamilioj = grPersono.get_family_handle_list()
  extFamilioj = extPersono['person'].get('families').copy()
  for family_handle in grPersono.get_family_handle_list():
    family = db.get_family_from_handle(family_handle)
    if family :
      if family.mother_handle == grPersono.handle :
        edzo_handle = family.father_handle
      elif family.father_handle == grPersono.handle :
        edzo_handle = family.mother_handle
      else :
        continue
      if edzo_handle is None :
        edzo = Person()
      else :
        edzo = db.get_person_from_handle(edzo_handle)
      edzoNomo = edzo.primary_name.get_surname()
      edzoNomoj = (edzo.primary_name.get_surname() or '?') +', '+ (edzo.primary_name.first_name or '?')
      # serĉi geedziĝo
      geJaro = 0 # date du mariage
      for eventref in family.get_event_ref_list() :
        event = db.get_event_from_handle(eventref.ref)
        if event.type == EventType.MARRIAGE :
          geJaro = event.date.get_year()
      # serĉi cî familio en extFamilioj
      extEdzDato = extEdzDatoj = extEdzJaro = extEdzNomoj = ''
      extEdzUrl = extFamIndekso = None
      indekso = 0
      extFam = None
      extParoId = None
      for f in extFamilioj :
        extEdzNomo = f['spouse'].get('lastname')
        tmpEdzDato = f.get('marriageDate') or ''
        tmpDato = parserEn.parse(tmpEdzDato)
        extEdzJaro = tmpDato.get_year()
        if (geJaro>0 and geJaro == extEdzJaro) \
          or (extEdzNomo.upper() == edzoNomo.upper() ) :
          extEdzDato = f.get('marriageDate') or ''
          extEdzUrl = geneanet.id2url(f['spouse'])
          extParoId = f.get('index')
          extEdzDatoj = extperso_datoj(f['spouse'])
          extEdzNomoj = (f['spouse'].get('lastname') or '?') +', '+(f['spouse'].get('firstname') or '?')
          extFam = f
          koloro = "green"
          extFamilioj.remove(f)
          break
        indekso += 1
      # Ekrano
      koloro = "yellow"
      edzo_nodo = model.add( [ koloro , _trans.gettext('Spouse')
                , str(geJaro) , edzoNomoj+' ('+grperso_datoj(db, edzo)+')'
          , str(extEdzDato) , extEdzNomoj +' ('+extEdzDatoj+')', ''
          , False, 'edzo', edzo_handle ,str(extEdzUrl) , family.handle, str(extParoId)
           ] )
      extInfanoj = dict()
      if extFam :
        c=extFam.get('children')
        if c :
          extInfanoj=c.copy()
      for child_ref in family.get_child_ref_list():
        infano = db.get_person_from_handle(child_ref.ref)
        infanoNomo = infano.primary_name
        infanoANomo = infano.primary_name.first_name
        extInfano = extInfanoUrl = extParoId = None
        extInfDatoj = extInfNomoj = ''
        koloro = "yellow"
        for c in extInfanoj :
          tmpANomo = c.get('firstname')
          if tmpANomo.upper() == infanoANomo.upper() :
            koloro = "green"
            extInfDatoj = extperso_datoj(c)
            extInfNomoj = (c.get('lastname') or '?')+', '+(c.get('firstname') or '?')
            extInfano = c
            extInfanoj.remove(c)
        extNomo = ''
        model.add( [ koloro ,'    '+ _trans.gettext('Child')
                , grperso_datoj(db, infano) , infanoNomo.get_surname() + ', ' + infanoNomo.first_name
                , extInfDatoj, extInfNomoj , ''
          , False, 'infano', child_ref.ref  ,str(extInfanoUrl), family.handle, str(extParoId)
           ],node=edzo_nodo )
      for c in extInfanoj :
        extInfDatoj = extperso_datoj(c)
        extInfNomoj = (c.get('lastname') or '?')+', '+(c.get('firstname') or '?')
        extInfUrl = geneanet.id2url(c)
        model.add( [ koloro ,'    '+ _trans.gettext('Child')
                , '' , ''
                , extInfDatoj, extInfNomoj , ''
          , False, 'infano', None  ,str(extInfUrl), family.handle, str(extParoId)
           ] ,node=edzo_nodo)

  # Ekrano de Geneanet familioj
  extFamIndekso = 0
  for f in extFamilioj :
    koloro = "yellow"
    extEdzUrl = geneanet.id2url(f['spouse'])
    extParoId = f.get('index')
    extEdzDatoj = (f['spouse'].get('marriageDate') or '/?')+ ' - ' + (f['spouse'].get('marriageDate') or '/?')
    extEdzNomoj = (f['spouse'].get('lastname') or '?') +' '+ (f['spouse'].get('firstname') or '?')
    edzo_nodo = model.add( [ koloro , _trans.gettext('Spouse')
                , '' , ''
          , extEdzDatoj , extEdzNomoj , ''
          , False, 'edzo', None ,str(extEdzUrl) , None, str(extParoId)
           ] )
    extFamIndekso += 1
    c=f.get('children')
    if c :
      extInfanoj=c.copy()
    else :
      extInfanoj = dict()
    for c in extInfanoj :
        extInfDatoj = extInfNomoj = ''
        extInfNomoj = (c.get('lastname') or '?')+' '+(c.get('firstname') or '?')
        extInfId = c.get('index')
        extInfUrl = geneanet.id2url(c)
        model.add( [ koloro ,'    '+ _trans.gettext('Child')
                , '' , ''
                , extInfDatoj, extInfNomoj , ''
          , False, 'infano', None  ,str(extInfUrl), None, str(extParoId)
           ],node=edzo_nodo )




