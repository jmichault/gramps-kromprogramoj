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
"""
"  gramplet PersonGN : fonctions de comparaison
"""

from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.display.place import displayer as _pd
from gramps.gen.lib import Date, EventRoleType, EventType, Person
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.datehandler import LANG_TO_PARSER

from gn_constants import GN_GRAMPS_FAKTOJ, _
import utilaGN
import geneanet

parserEn = LANG_TO_PARSER['en']()

# j'utilise _trans.gettext pour les chaînes existantes dans gramps
# ce qui évite de les avoir dans le fichier po
_trans = glocale.translation

def _SeksoKomp(gr_persono, ext_persono):
  """ comparaison du sexe """
  if gr_persono.get_gender() == Person.MALE:
    grSekso = _trans.gettext("male")
  elif gr_persono.get_gender() == Person.FEMALE:
    grSekso = _trans.gettext("female")
  else:
    grSekso = _trans.gettext("unknown")
  extSekso = _trans.gettext("unknown")
  if 'person' in ext_persono:
    s = ext_persono['person'].get('sex')
    if s == 'MALE':
      extSekso = _trans.gettext("male")
    elif s == 'FEMALE':
      extSekso = _trans.gettext("female")
  koloro = "red"
  if grSekso == extSekso:
    koloro = "green"
  return [koloro, _('Sekso:')
          , '', grSekso
          , '', extSekso, ''
          , False, 'sekso', None, None, None, None
         ]


def _NomojKomp(gr_persono, ext_persono):
  """ comparaison des noms """
  grNomo = gr_persono.primary_name
  extNomo = ext_persono['person'].get('lastname')
  extANomo = ext_persono['person'].get('firstname')
  koloro = "red"
  if ((grNomo.get_surname().upper() == extNomo.upper()) and
      (grNomo.first_name.upper() == extANomo.upper())):
    koloro = "green"
  res = []
  res.append([
      koloro,
      _trans.gettext('Name'), '',
      grNomo.get_surname() + ', ' + grNomo.first_name, '', extNomo + ', ' + extANomo, '', False,
      'nomo1',
      str(grNomo), None,
      grNomo.get_surname(), grNomo.first_name
  ])
  return res


def _FaktoKomp(db, gr_persono, ext_persono, gr_event, ext_fakto_tipo):
  grFakto = utilaGN.getGrevent(db, gr_persono, EventType(gr_event))
  grFaktoHandle = None
  titolo = str(EventType(gr_event))
  if grFakto :
    grFaktoHandle = grFakto.handle
    grFaktoDato = utilaGN.grdatoAlFormal(grFakto.date)
    if grFakto.place :
      place = db.get_place_from_handle(grFakto.place)
      #grFaktoLoko = place.name.value
      grFaktoLoko = _pd.display(db, place)
    else:
      grFaktoLoko = ''
  else:
    grFaktoDato = ''
    grFaktoLoko = ''
  extFakto = ''
  x = ext_persono['person'].get('events')
  if x:
    for e in (x.get('elements') or []) :
      if e['type'] == 'EPERS_' + ext_fakto_tipo.upper():
        extFakto = e
        break
  extFaktoDato = utilaGN.extdatoAlFormal(ext_persono['person'].get(ext_fakto_tipo + 'Date'))
  extFaktoLoko = ext_persono['person'].get(ext_fakto_tipo + 'Place')
  if grFakto is None and extFaktoDato == '' and extFaktoLoko is None:
    return None
  if grFaktoDato == '' and grFaktoLoko == '' and extFaktoDato == '' and extFaktoLoko == '':
    return None
  koloro = "white"
  if grFakto is None and extFakto != '':
    koloro = "orange"
  if grFaktoDato != '' and (grFaktoDato == extFaktoDato):
    koloro = "green"
  if (extFaktoDato not in ('', grFaktoDato)
      or (extFaktoLoko != '' and grFaktoLoko == '')):
    koloro = "red"
  return (koloro, titolo, grFaktoDato, grFaktoLoko, extFaktoDato, extFaktoLoko, '', False, 'fakto',
          grFaktoHandle, str(extFakto), None, None)


def grPersonoDatoj(db, gr_persono):
  """ renvoie les dates de naissance et décès sous forme raccourcie """
  if not gr_persono:
    return ''
  grBirth = utilaGN.getGrevent(db, gr_persono, EventType(EventType.BIRTH))
  if grBirth:
    if grBirth.date.modifier == Date.MOD_ABOUT:
      res = '~'
    elif grBirth.date.modifier == Date.MOD_BEFORE:
      res = '/'
    else:
      res = ' '
    val = f"{grBirth.date.get_year():04d}"
    if val == '0000':
      val = '....'
    if grBirth.date.modifier == Date.MOD_AFTER:
      res = res + val + '/-'
    else:
      res = res + val + '-'
  else:
    res = ' ....-'
  grDeath = utilaGN.getGrevent(db, gr_persono, EventType(EventType.DEATH))
  if grDeath:
    if grDeath.date.modifier == Date.MOD_ABOUT:
      res = res + '~'
    elif grDeath.date.modifier == Date.MOD_BEFORE:
      res = res + '/'
    val = f"{grDeath.date.get_year():04d}"
    if val == '0000':
      val = '....'
    if grDeath.date.modifier == Date.MOD_AFTER:
      res = res + val + '/'
    else:
      res = res + val
  else:
    res = res + '....'
  return res


def extpersoDatoj(ext_persono):
  """ renvoie les dates de naissance et décès sous forme raccourcie """
  res = ''
  if ext_persono is None:
    return res
  dato = ext_persono.get('birthDateConv')
  if dato is None:
    dato = ext_persono.get('birthShortDate')
  grBirth = None
  if dato:
    grBirth = parserEn.parse(dato)
  if grBirth:
    if grBirth.modifier == Date.MOD_ABOUT:
      res = '~'
    elif grBirth.modifier == Date.MOD_BEFORE:
      res = '/'
    else:
      res = ' '
    val = f"{grBirth.get_year():04d}"
    if val == '0000':
      val = '....'
    if grBirth.modifier == Date.MOD_AFTER:
      res = res + val + '/-'
    else:
      res = res + val + '-'
  else:
    res = ' ....-'
  dato = ext_persono.get('deathDateConv')
  if dato is None:
    dato = ext_persono.get('deathShortDate')
  grDeath = None
  if dato:
    grDeath = parserEn.parse(dato)
  if grDeath:
    if grDeath.modifier == Date.MOD_ABOUT:
      res = res + '~'
    elif grDeath.modifier == Date.MOD_BEFORE:
      res = res + '/'
    val = f"{grDeath.get_year():04d}"
    if val == '0000':
      val = '....'
    if grDeath.modifier == Date.MOD_AFTER:
      res = res + val + '/'
    else:
      res = res + val
  else:
    res = res + '....'
  return res

def _koloroGepatro(gr_persono, gr_nomo, ext_persono,ext_nomo):
  koloro = "white"
  if gr_nomo.upper() == ext_nomo.upper():
    koloro = "green"
  if gr_persono is None and ext_persono is not None:
    koloro = "orange"
  if (gr_persono is not None and ext_persono is not None and
      gr_nomo.upper() != ext_nomo.upper()):
    koloro = "red"
  return koloro

def _resGepKomp(db, gr_handle, ext_persono, tipo):
  if gr_handle :
    grPersono = db.get_person_from_handle(gr_handle)
    grNomo = name_displayer.display(grPersono)
  else :
    grPersono = None
    grNomo = ''
  if ext_persono:
    extNomo = ext_persono.get('lastname') + ', ' + ext_persono.get('firstname')
    extUrl = geneanet.id2url(ext_persono)
  else:
    extNomo = extUrl = ''
  koloro = _koloroGepatro(grPersono, grNomo, ext_persono,extNomo)
  if grPersono is not None or ext_persono is not None:
    if tipo == 'patro':
      titolo = _trans.gettext('Father')
    else:
      titolo = _trans.gettext('Mother')
    return [
        koloro,
        titolo,
        grPersonoDatoj(db, grPersono), ' ' + grNomo,
        extpersoDatoj(ext_persono), extNomo, '', False, tipo, gr_handle, extUrl,
        None, None
      ]
  return None

def gepKomp(db, gr_persono, ext_persono):
  """
  " aldonas gepatran komparon
  """
  familyHandle = gr_persono.get_main_parents_family_handle()
  patroHandle = None
  patrinoHandle = None
  res = []
  if familyHandle:
    family = db.get_family_from_handle(familyHandle)
    patroHandle = family.get_father_handle()
    patrinoHandle = family.get_mother_handle()
  extFather = ext_persono['person'].get('father')
  res1 = _resGepKomp(db, patroHandle, extFather, 'patro')
  if res1:
    res.append(res1)
  extMother = ext_persono['person'].get('mother')
  res1 = _resGepKomp(db, patrinoHandle, extMother, 'patrino')
  if res1:
    res.append(res1)
  return res


def kompariGrExt(gr_persono, ext_persono, db, model):
  """ Komparo de esenca eroj """
  listres = []
  res = _SeksoKomp(gr_persono, ext_persono)
  if res:
    listres.append(res)
  resNomoj = _NomojKomp(gr_persono, ext_persono)
  if resNomoj:
    listres.append(resNomoj.pop(0))
  res = _FaktoKomp(db, gr_persono, ext_persono, EventType.BIRTH, "birth")
  if res:
    listres.append(res)
  res = _FaktoKomp(db, gr_persono, ext_persono, EventType.BAPTISM, "baptism")
  if res:
    listres.append(res)
  res = _FaktoKomp(db, gr_persono, ext_persono, EventType.DEATH, "death")
  if res:
    listres.append(res)
  res = _FaktoKomp(db, gr_persono, ext_persono, EventType.BURIAL, "burial")
  if res:
    listres.append(res)
  if listres:
    koloro = 'green'
    for linio in listres:
      if linio[0] == 'red' or linio[0] == 'orange':
        koloro = 'yellow'
      elif koloro == 'green' and linio[0] != 'green':
        koloro = 'white'
    esencoNodo = model.add([koloro, _('Esenco'), '==========', '============================'
        , '==========', '', '', False, 'Esenco', None, None, None, None])
    for linio in listres:
      model.add(linio, node=esencoNodo)
  # parents
  listres = gepKomp(db, gr_persono, ext_persono)
  if len(listres) > 0:
    koloro = 'green'
    for linio in listres:
      if linio[0] == 'red' or linio[0] == 'orange':
        koloro = 'yellow'
      elif koloro == 'green' and linio[0] != 'green':
        koloro = 'white'
    gepatrojNodo = model.add([koloro, _('Gepatroj'), '==========', '============================'
        , '==========', '', '', False, 'Gepatroj', None, None, None, None])
    for linio in listres:
      model.add(linio, node=gepatrojNodo)
  # familles
  extFamilioj = ext_persono['person'].get('families').copy()
  for familyHandle in gr_persono.get_family_handle_list():
    family = db.get_family_from_handle(familyHandle)
    if family:
      edzKoloro = "white"
      if family.mother_handle == gr_persono.handle:
        edzoHandle = family.father_handle
      elif family.father_handle == gr_persono.handle:
        edzoHandle = family.mother_handle
      else:
        continue
      if edzoHandle is None:
        edzo = Person()
      else:
        edzo = db.get_person_from_handle(edzoHandle)
      edzoNomo = edzo.primary_name.get_surname()
      edzoNomoj = (edzo.primary_name.get_surname() or '?') + ', ' + (
          edzo.primary_name.first_name or '?')
      # serĉi geedziĝo
      geJaro = 0  # date du mariage
      for eventref in family.get_event_ref_list():
        event = db.get_event_from_handle(eventref.ref)
        if event.type == EventType.MARRIAGE:
          geJaro = event.date.get_year()
      # serĉi cî familio en extFamilioj
      extEdzDato = extEdzDatoj = extEdzJaro = extEdzNomoj = ''
      extEdzUrl = extFamIndekso = ''
      indekso = 0
      extFam = ''
      extParoId = ''
      for f in extFamilioj:
        extEdzNomo = f['spouse'].get('lastname')
        tmpEdzDato = f.get('marriageDate') or ''
        tmpDato = parserEn.parse(tmpEdzDato)
        extEdzJaro = tmpDato.get_year()
        if ((geJaro > 0 and geJaro == extEdzJaro) or (extEdzNomo.upper() == edzoNomo.upper()) or
            (f.get('_grEdzHandle') == edzoHandle)):
          extEdzDato = extEdzJaro
          extEdzUrl = geneanet.id2url(f['spouse'])
          extParoId = f.get('index')
          extEdzDatoj = extpersoDatoj(f['spouse'])
          extEdzNomoj = (f['spouse'].get('lastname') or '?') + ', ' + (
              f['spouse'].get('firstname') or '?')
          extFam = f
          edzKoloro = "green"
          extFamilioj.remove(f)
          break
        indekso += 1
      listres = []
      # familiaj eventoj (edziĝo, …)
      extEdzFaktoj = []
      if extEdzUrl :
        extFaktoj = ((ext_persono['person'].get('events') or {}).get('elements') or [])
        for ef in extFaktoj:
          if ((ef.get('type') or '')[:5] == 'EFAM_' and
              (ef.get('spouse') or {}).get('index') == extFam.get('spouse').get('index') and
              (ef.get('dateLong') or '') == (extFam.get('marriageDateLong') or '')):
            extEdzFaktoj.append(ef)
      for eventref in family.get_event_ref_list():
        koloro = "white"
        event = db.get_event_from_handle(eventref.ref)
        titolo = str(EventType(event.type))
        grFaktoPriskribo = event.description or ''
        grFaktoDato = utilaGN.grdatoAlFormal(event.date)
        if event.place :
          place = db.get_place_from_handle(event.place)
          grFaktoLoko = _pd.display(db, place)
        else:
          grFaktoLoko = ''
        if grFaktoLoko == '':
          grValoro = grFaktoPriskribo
        else:
          grValoro = grFaktoPriskribo + ' @ ' + grFaktoLoko
        extFaktoDato = ''
        extFakto = None
        extValoro = ''
        for ef in extEdzFaktoj:
          tipo = GN_GRAMPS_FAKTOJ.get(ef.get('type'))
          if not tipo:
            tipo = ef.get('type')
          if str(EventType(tipo)) == titolo:
            koloro = "green"
            extFakto = ef
            extFaktoDato = utilaGN.extdatoAlFormal(extFakto.get('dateLong'))
            if extFaktoDato != grFaktoDato:
              koloro = "red"
            extValoro = extFakto.get('place')
            break
        if extFakto :
          extEdzFaktoj.remove(extFakto)

        listres.append([
            koloro, '  ' + titolo, grFaktoDato, grValoro, extFaktoDato, extValoro, '', False,
            'edzoFakto', family.handle,
            str(extParoId), eventref.ref,
            str(extFakto)
        ])

      for extFakto in extEdzFaktoj:
        koloro = "orange"
        fakTipo = GN_GRAMPS_FAKTOJ.get(extFakto.get('type'))
        if not fakTipo:
          fakTipo = extFakto.get('type')
        titolo = str(EventType(fakTipo))
        extFaktoDato = utilaGN.extdatoAlFormal(extFakto.get('dateLong'))
        extValoro = extFakto.get('place')
        listres.append([
            koloro, '  ' + titolo, '', '', extFaktoDato, extValoro, '', False, 'edzoFakto',
            family.handle,
            str(extParoId), None,
            str(extFakto)
        ])
      # infanoj
      extInfanoj = {}
      if extFam:
        c = extFam.get('children')
        if c:
          extInfanoj = c.copy()
      for childRef in family.get_child_ref_list():
        koloro = "white"
        infano = db.get_person_from_handle(childRef.ref)
        infanoNomo = infano.primary_name
        infanoANomo = infano.primary_name.first_name
        extInfanoUrl = extParoId = None
        extInfDatoj = extInfNomoj = ''
        for c in extInfanoj:
          tmpANomo = c.get('firstname')
          if tmpANomo.upper() == infanoANomo.upper():
            koloro = "green"
            extInfDatoj = extpersoDatoj(c)
            extInfNomoj = (c.get('lastname') or '?') + ', ' + (c.get('firstname') or '?')
            extInfanoj.remove(c)
        listres.append([
            koloro, '    ' + _trans.gettext('Child'),
            grPersonoDatoj(db, infano),
            infanoNomo.get_surname() + ', ' + infanoNomo.first_name, extInfDatoj, extInfNomoj, '',
            False, 'infano', childRef.ref,
            str(extInfanoUrl), family.handle,
            str(extParoId)
        ])
      koloro = "orange"
      for c in extInfanoj:
        extInfDatoj = extpersoDatoj(c)
        extInfNomoj = (c.get('lastname') or '?') + ', ' + (c.get('firstname') or '?')
        extInfUrl = geneanet.id2url(c)
        listres.append([
            koloro, '    ' + _trans.gettext('Child'), '', '', extInfDatoj, extInfNomoj, '', False,
            'infano', None,
            str(extInfUrl), family.handle,
            str(extParoId)
        ])
      if edzKoloro == 'green':
        for linio in listres:
          if linio[0] == 'orange' or linio[0] == 'red':
            edzKoloro = 'yellow'
          elif edzKoloro == 'green' and linio[0] != 'green':
            edzKoloro = 'white'
      # Familia ekrano
      edzoNodo = model.add([
          edzKoloro,
          _trans.gettext('Spouse'),
          str(geJaro), edzoNomoj + ' (' + grPersonoDatoj(db, edzo) + ')',
          str(extEdzDato), extEdzNomoj + ' (' + extEdzDatoj + ')', '', False, 'edzo', edzoHandle,
          str(extEdzUrl), family.handle or '',
          str(extParoId or '')
      ])
      for linio in listres:
        model.add(linio, node=edzoNodo)

  # Ekrano de Geneanet familioj
  extFamIndekso = 0
  for f in extFamilioj:
    koloro = "orange"
    extEdzUrl = geneanet.id2url(f['spouse'])
    extParoId = f.get('index')
    extEdzDatoj = (f['spouse'].get('marriageDate') or '/?') + ' - ' + (
        f['spouse'].get('marriageDate') or '/?')
    extEdzNomoj = (f['spouse'].get('lastname') or '?') + ' ' + (f['spouse'].get('firstname') or '?')
    edzoNodo = model.add([
        koloro,
        _trans.gettext('Spouse'), '', '', extEdzDatoj, extEdzNomoj, '', False, 'edzo', '',
        str(extEdzUrl), '',
        str(extParoId or '')
    ])
    extFamIndekso += 1
    c = f.get('children')
    if c:
      extInfanoj = c.copy()
    else:
      extInfanoj = {}
    for c in extInfanoj:
      extInfDatoj = extInfNomoj = ''
      extInfNomoj = (c.get('lastname') or '?') + ' ' + (c.get('firstname') or '?')
      #extInfId = c.get('index')
      extInfUrl = geneanet.id2url(c)
      model.add([
          koloro, '    ' + _trans.gettext('Child'), '', '', extInfDatoj, extInfNomoj, '', False,
          'infano', '',
          str(extInfUrl), '',
          str(extParoId)
      ],
                node=edzoNodo)
  # Ekrano de aliaj faktoj
  res = []
  grFaktoj = gr_persono.event_ref_list
  extFaktoj = ((ext_persono['person'].get('events') or {}).get('elements') or []).copy()
  for grFaktoRef in grFaktoj:
    koloro = "white"
    if int(grFaktoRef.get_role()) != EventRoleType.PRIMARY:
      continue
    grFakto = db.get_event_from_handle(grFaktoRef.ref)
    if grFakto.type in (EventType.BIRTH, EventType.DEATH, EventType.BAPTISM, EventType.BURIAL):
      continue
    titolo = str(EventType(grFakto.type))
    grFaktoPriskribo = grFakto.description or ''
    grFaktoDato = utilaGN.grdatoAlFormal(grFakto.date)
    if grFakto.place:
      place = db.get_place_from_handle(grFakto.place)
      grFaktoLoko = _pd.display(db, place)
    else:
      grFaktoLoko = ''
    if grFaktoLoko == '':
      grValoro = grFaktoPriskribo
    else:
      grValoro = grFaktoPriskribo + ' @ ' + grFaktoLoko
    extFakto = {}
    for ef in extFaktoj:
      efDato = utilaGN.extdatoAlFormal(ef.get('dateLong'))
      efTipo = GN_GRAMPS_FAKTOJ.get(ef.get('type'))
      if not efTipo:
        efTipo = ef.get('type')
      if efTipo == grFakto.type and grFaktoDato == efDato:
        koloro = "green"
        extFakto = ef
        extFaktoj.remove(ef)
        break
    extFaktoDato = utilaGN.extdatoAlFormal(extFakto.get('dateLong'))
    extFaktoLoko = extFakto.get('place')
    res.append([
        koloro, titolo, grFaktoDato, grFaktoLoko, extFaktoDato, extFaktoLoko, '', False, 'fakto',
        grFakto.get_handle(),
        str(extFakto), None, None
    ])
  koloro = "orange"
  for extFakto in extFaktoj:
    extFakTipo = extFakto.get('type')
    if extFakTipo in ('EPERS_BIRTH', 'EPERS_DEATH', 'EPERS_BAPTISM', 'EPERS_BURIAL'):
      continue
    if extFakTipo[:5] == 'EFAM_':
      continue
    extFaktoDato = extFaktoLoko = ''
    extFaktoDato = utilaGN.extdatoAlFormal(extFakto.get('dateLong'))
    extFaktoLoko = extFakto.get('place')
    fakTipo = GN_GRAMPS_FAKTOJ.get(extFakto.get('type'))
    if not fakTipo:
      fakTipo = extFakto.get('type')
    titolo = str(EventType(fakTipo))
    res.append([
        koloro, titolo, '', '', extFaktoDato, extFaktoLoko, '', False, 'fakto', None,
        str(extFakto), None, None
    ])

  if res:
    koloro = 'green'
    for linio in res:
      if linio[0] == 'red' or linio[0] == 'orange':
        koloro = 'yellow'
      elif koloro == 'green' and linio[0] != 'green':
        koloro = 'white'
    fakNodo = model.add([koloro, _('Faktoj'), '==========', '============================'
         , '==========', '======', '', False, 'Faktoj', None, None, None, None])
    for linio in res:
      model.add(linio, node=fakNodo)
