from gramps.gen.db import DbTxn
from gramps.gen.lib import Attribute, EventRoleType, Date, SrcAttribute
from gramps.gen.lib.date import gregorian
from gramps.gui.dialog import WarningDialog, QuestionDialog2

from gramps.gen.const import GRAMPS_LOCALE as glocale

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


fs_gr = None
fs_gr_lokoj = None

def konstrui_fs_gr(vokanto,progress,nbPas) :
  global fs_gr
  global fs_gr_lokoj
  dupAverto = True
  fs_gr = dict()
  progress.set_pass(_('Konstrui FSID listo (1/'+str(nbPas)+')'), vokanto.dbstate.db.get_number_of_people())
  for person_handle in vokanto.dbstate.db.get_person_handles() :
    progress.step()
    person = vokanto.dbstate.db.get_person_from_handle(person_handle)
    fsid = get_fsftid(person)
    if fs_gr.get(fsid) :
      print(_('«FamilySearch» duplikata ID : %s ')%(fsid))
      if dupAverto :
        qd = QuestionDialog2(
              _('Duplikata FSFTID')
            , _('«FamilySearch» duplikata ID : %s ')%(fsid)
            , _('_Daŭru averton'), _('_Ĉesu averton')
            , parent=vokanto.uistate.window)
        if not qd.run():
          dupAverto = False

    elif fsid != '' :
      fs_gr[fsid] = person_handle
  progress.set_pass(_('Konstrui FSID listo por lokoj (2/'+str(nbPas)+')'), vokanto.dbstate.db.get_number_of_places())
  fs_gr_lokoj = dict()
  for place_handle in vokanto.dbstate.db.get_place_handles() :
    progress.step()
    place = vokanto.dbstate.db.get_place_from_handle(place_handle)
    for url in place.urls :
      if str(url.type) == 'FamilySearch' :
        fs_gr_lokoj[url.path] = place_handle

def fsdato_al_gr( fsDato) :
  if fsDato:
    grDato = Date()
    grDato.set_calendar(Date.CAL_GREGORIAN)
    jaro=monato=tago= 0
    if fsDato.formal :
      if fsDato.formal.unuaDato and fsDato.formal.unuaDato.jaro:
        jaro = fsDato.formal.unuaDato.jaro
        monato = fsDato.formal.unuaDato.monato
        tago = fsDato.formal.unuaDato.tago
      elif fsDato.formal.finalaDato and fsDato.formal.finalaDato.jaro:
        jaro = fsDato.formal.finalaDato.jaro
        monato = fsDato.formal.finalaDato.monato
        tago = fsDato.formal.finalaDato.tago
      if fsDato.formal.proksimuma :
        grDato.set_modifier(Date.MOD_ABOUT)
      if fsDato.formal.gamo :
        if not fsDato.formal.unuaDato or not fsDato.formal.unuaDato.jaro :
          grDato.set_modifier(Date.MOD_BEFORE)
        elif not fsDato.formal.finalaDato or not fsDato.formal.finalaDato.jaro :
          grDato.set_modifier(Date.MOD_AFTER)
        else :
          grDato.set_modifier(Date.MOD_RANGE)
          if fsDato.formal.finalaDato and fsDato.formal.finalaDato.jaro :
            jaro2 = fsDato.formal.finalaDato.jaro
            monato2 = fsDato.formal.finalaDato.monato
            tago2 = fsDato.formal.finalaDato.tago
    if jaro == 0 and monato == 0 and tago == 0 :
      return None
    if grDato.modifier == Date.MOD_RANGE :
      grDato.set(value=(tago, monato, jaro, 0, tago2, monato2, jaro2, 0),text=fsDato.original or '',newyear=Date.NEWYEAR_JAN1)
    else : 
      grDato.set(value=(tago, monato, jaro, 0),text=fsDato.original or '',newyear=Date.NEWYEAR_JAN1)
  else : grDato = None
  return grDato

def grdato_al_formal( dato) :
  """
  " konvertas gramps-daton al «formal» dato
  "   «formal» dato : <https://github.com/FamilySearch/gedcomx/blob/master/specifications/date-format-specification.md>
  """
  if dato is None :
    return None;
  res=''
  gdato = gregorian(dato)
  if gdato.modifier == Date.MOD_ABOUT :
    res = 'A'
  elif gdato.modifier == Date.MOD_BEFORE:
    res = '/'
  if gdato.dateval[Date._POS_YR] < 0 :
    res = res + '-'
  else :
    res = res + '+'
  if gdato.dateval[Date._POS_DAY] > 0 :
    val = "%04d-%02d-%02d" % (
                gdato.dateval[Date._POS_YR], gdato.dateval[Date._POS_MON],
                gdato.dateval[Date._POS_DAY])
  elif gdato.dateval[Date._POS_MON] > 0 :
    val = "%04d-%02d" % (
                gdato.dateval[Date._POS_YR], gdato.dateval[Date._POS_MON])
  elif gdato.dateval[Date._POS_YR] > 0 :
    val = "%04d" % ( gdato.dateval[Date._POS_YR] )
  else :
    res = gdato.text
    val=''
  res = res+val
  if gdato.modifier == Date.MOD_AFTER:
    res = res + '/'
  if gdato.modifier == Date.MOD_RANGE:
    res = res + '/'
    if gdato.dateval[Date._POS_RYR] < 0 :
      res = res + '-'
    else :
      res = res + '+'
    if gdato.dateval[Date._POS_RDAY] > 0 :
      val = "%04d-%02d-%02d" % (
                gdato.dateval[Date._POS_RYR], gdato.dateval[Date._POS_RMON],
                gdato.dateval[Date._POS_RDAY])
    elif gdato.dateval[Date._POS_RMON] > 0 :
      val = "%04d-%02d" % (
                gdato.dateval[Date._POS_RYR], gdato.dateval[Date._POS_RMON])
    elif gdato.dateval[Date._POS_RYR] > 0 :
      val = "%04d" % ( gdato.dateval[Date._POS_RYR] )
    else:
      val = ''
    res = res+val
  # FARINDAĴOJ : range ?  estimate ? calculate ? heure ?
  
  return res

def get_fsftid(grObj) :
  if not grObj :
    return ''
  for attr in grObj.get_attribute_list():
    if attr.get_type() == '_FSFTID':
      return attr.get_value()
  return ''

def get_url(grObj) :
  if not grObj :
    return None
  for attr in grObj.get_attribute_list():
    if attr.get_type() == _('Internet Address'):
      return attr.get_value()
  return None

def get_fsfact(person, fact_tipo):
  """
  " Liveras la unuan familysearch fakton de la donita tipo.
  """
  for fact in person.facts :
    if fact.type == fact_tipo :
      return fact
  return None

def get_grevent(db, person, event_type):
  """
  " Liveras la unuan gramps eventon de la donita tipo.
  """
  if not person:
    return None
  for event_ref in person.get_event_ref_list():
    if int(event_ref.get_role()) == EventRoleType.PRIMARY:
      event = db.get_event_from_handle(event_ref.ref)
      if event.get_type() == event_type:
        return event
  return None

def ligi_gr_fs(db,grObjekto,fsid):
  global fs_gr
  global fs_gr_lokoj
  attr = None
  if db.transaction :
    intr = True
    txn=db.transaction
  else :
    intr = False
    txn = DbTxn(_("FamilySearch etikedoj"), db)
  attr = None
  for x in grObjekto.get_attribute_list():
      if x.get_type() == '_FSFTID':
        attr = x
        if fsid != x.get_value() :
          x.set_value(fsid)
        break
  if not attr :
   if  grObjekto.__class__.__name__ == 'Citation' :
     attr = SrcAttribute()
   else :
     attr = Attribute()
   attr.set_type('_FSFTID')
   attr.set_value(fsid)
   grObjekto.add_attribute(attr)
  match  grObjekto.__class__.__name__ :
    case 'Person' :
      db.commit_person(grObjekto,txn)
      if fs_gr :
        fs_gr[fsid] = grObjekto.get_handle()
    case 'Event' :
      db.commit_event(grObjekto,txn)
    case 'Citation' :
      db.commit_citation(grObjekto,txn)
    case _ :
      print ("utila.ligi_gr_fs : klaso ne trakta : " + grObjekto.__class__.__name__)
  if not intr :
    db.transaction_commit(txn)
    del txn
