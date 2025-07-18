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
"""
" Genanet Gramplet : gestion des notes : conversion du html en styled
"""

#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
import re
from html import _charref as html_charref , _replace_charref as html_replace_charref

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.lib import (StyledText, StyledTextTag, StyledTextTagType)

#-------------------------------------------------------------------------
#
#
#-------------------------------------------------------------------------

token_specification = [
    # Italics: must not be nested, any tag terminates
    ('ITALIC',  r'<i>.*?(?=<)'),
    # bolds: must not be nested, any tag terminates
    ('BOLD',    r'<b>.*?(?=<)'),
    # Underlines: must not be nested, any tag terminates
    ('UNDER',   r'<u>.*?(?=<)'),
    # Table Header Begin (start Bold)
    ('TBLHDRB', r'<tr><th>'),
    # Table Header End (end Bold and \n)
    ('TBLHDRE', r'</th></tr>'),
    # Table Header Cell (repl with ': ')
    ('TBLHDRC', r'(<\th>)?<th>'),
    # Table Cell break (repl with ':  ')
    ('TBLCELL', r'</td><td>'),
    # Table
    ('TABLE',   r'</?table.*?>'),
    # Href start to end
    ('HREF',    r'<+a .*?href=["\' ]*(?P<HREFL>.*?)'\
                r'["\' ].*?>(?P<HREFT>.*?)</a>+'),
    # HTTP start to end (have to rstrip(' .:') for link)
    ('HTTP',    r'https?:.*?(\s|$)'),
    # Paragraph end
    ('PARAEND', r'</p>|</li>|<tr>|<br>|<br />'),
    # Skip over these tags
    ('SKIP',    r'<ul>|</ul>|<li>|<p>|</tr>|<td>|</td>|<th>|'\
                r'</a>|</i>|</b>|</u>|<a>'),
    # Unimplemented HTTP tags
    ('UNKNWN',  r'<[^<]*?>'), ]
TokRegex = '|'.join(f'(?P<{pair[0]}>{pair[1]})' for pair in token_specification)

def _convertPart1(data):
  prev = chunkpos = 0
  chunks = []
  styText = StyledText(data)
  for mo in re.finditer(html_charref, styText.get_string()):
    out = html_replace_charref(mo)
    inStart = mo.start()
    inEnd = mo.end()
    styText.set_string(styText.get_string()[:inStart] + out +
                        styText.get_string()[(inStart + len(out)):])
    if prev != inStart + len(out):
      chunks.append(styText.get_string()[prev:(inStart + len(out))])
      chunkpos += (inStart - prev + len(out))
    prev = inEnd
  chunks.append(styText.get_string()[prev:])
  styText = StyledText().join(chunks)
  return styText

def convertToStyled(data):
  """
  This scans incoming notes for possible html.  It converts a select few
  tags into StyledText and removes the rest of the tags.  Notes of this
  type occur in data from FTM and ancestry.com.  Result is a much
  cleaner note.

  @param data: a string of text possibly containg html
  @type data: str
  """
  tags = { 'italics': [],
           'bolds': [],
           'unders': [],
           'links': [],
           'reds': [],
         }
  bldpos = -1
  styText = _convertPart1(data)
  prev = chunkpos = 0
  chunks = []
  for mo in re.finditer(TokRegex, styText.get_string(), flags=re.DOTALL | re.I ):
    stTxt = mo.group(mo.lastgroup)
    inStart = mo.start()
    inEnd = mo.end()
    match mo.lastgroup:
      case 'SKIP' | 'TABLE':
        if prev != inStart:
          chunks.append(styText.get_string()[prev:inStart])
          chunkpos += (inStart - prev)
      case 'PARAEND':
        chunks.append(styText.get_string()[prev:inStart] + '\n')
        chunkpos += (inStart - prev + 1)
      case 'ITALIC':
        chunks.append(styText.get_string()[prev:inStart] +
                    styText.get_string()[(inStart + 3):inEnd])
        oldpos = chunkpos + inStart - prev
        chunkpos = chunkpos - prev + inEnd - 3
        tags['italics'].append((oldpos, chunkpos))
      case 'BOLD':
        chunks.append(styText.get_string()[prev:inStart] +
                    styText.get_string()[(inStart + 3):inEnd])
        oldpos = chunkpos + inStart - prev
        chunkpos = chunkpos - prev + inEnd - 3
        tags['bolds'].append((oldpos, chunkpos))
      case 'UNDER':
        chunks.append(styText.get_string()[prev:inStart] +
                    styText.get_string()[(inStart + 3):inEnd])
        oldpos = chunkpos + inStart - prev
        chunkpos = chunkpos - prev + inEnd - 3
        tags['unders'].append((oldpos, chunkpos))
      case 'HTTP':      # HTTP found
        stTxt = mo.group('HTTP')
        oldpos = chunkpos + inStart - prev
        chunks.append(styText.get_string()[prev:inStart] + stTxt)
        chunkpos += (inStart - prev + len(stTxt))
        stTxt = stTxt.rstrip(' .:)')
        tags['links'].append((stTxt, oldpos, oldpos + len(stTxt)))
      case 'HREF':      # HREF found
        stTxt = mo.group('HREFT')
        lkTxt = mo.group('HREFL')
        # fix up relative links emmitted by ancestry.com
        if(lkTxt.startswith("/search/dbextra") or
               lkTxt.startswith("/handler/domain")):
          lkTxt = "http://search.ancestry.com" + lkTxt
        oldpos = chunkpos + inStart - prev
        # if tag (minus any trailing '.') is substring of link
        if stTxt[0:-1] in lkTxt:
          stTxt = lkTxt   # just use the link
        else:                 # use link and tag
          stTxt = " " + lkTxt + " (" + stTxt + ")"
        chunks.append(styText.get_string()[prev:inStart] + stTxt)
        chunkpos += (inStart - prev + len(stTxt))
        tags['links'].append((lkTxt, oldpos, oldpos + len(stTxt)))
      case 'TBLCELL' | 'TBLHDRC':  # Table cell break
        chunks.append(styText.get_string()[prev:inStart] + ':  ')
        chunkpos += (inStart - prev + 3)
      case 'TBLHDRB':      # header start
        if prev != inStart:
          chunks.append(styText.get_string()[prev:inStart])
          chunkpos += (inStart - prev)
        bldpos = chunkpos
      case 'TBLHDRE':      # Header end
        if bldpos == -1:
          if prev != inStart:
            chunks.append(styText.get_string()[prev:inEnd])
            oldpos = chunkpos + inStart - prev
            chunkpos = chunkpos - prev + inEnd
            tags['reds'].append((oldpos, chunkpos))
          print('Invalid table header, no start tag found')
        else:
          if prev != inStart:
            chunks.append(styText.get_string()[prev:inStart])
            chunkpos += (inStart - prev)
          tags['bolds'].append((bldpos, chunkpos))
          bldpos = -1
      case 'UNKNWN':
        chunks.append(styText.get_string()[prev:inEnd])
        oldpos = chunkpos + inStart - prev
        chunkpos = chunkpos - prev + inEnd
        tags['reds'].append((oldpos, chunkpos))
        print('Unexpected or unimplemented HTML tag', stTxt)
      case _:
        print("shouldn't get here")
    prev = inEnd
  chunks.append(styText.get_string()[prev:])
  result = StyledText().join(chunks)
  return StyledText(result.get_string()
           , tagMerge(result.get_tags()
           , _concatTags(tags['links'],tags['italics'],tags['bolds'],tags['unders'],tags['reds']) ))

def _concatTags(links,italics,bolds,unders,reds):
  """ concatenate all tags """
  tags = []
  for link in links:
    tags.append(StyledTextTag(StyledTextTagType.LINK, link[0],
                                  [(link[1], link[2])]))
  if italics:
    tags.append(StyledTextTag(StyledTextTagType.ITALIC, False ,
                                  italics))
  if bolds:
    tags.append(StyledTextTag(StyledTextTagType.BOLD, False , bolds))
  if unders:
    tags.append(StyledTextTag(StyledTextTagType.UNDERLINE, False ,
                                  unders))
  if reds:
    tags.append(StyledTextTag(StyledTextTagType.HIGHLIGHT, '#FFFF00',
                                  reds))
  return tags


def _tagEnumerate(old_tags, tag_list):
  """ first set for merge : enumerate all tags """
  styles = {}  # key:name  value:quad
  outstyles = {}  # key:tuple(name, value), value:list(ranges)
  tags = []
  for (prior, _tags) in enumerate((old_tags, tag_list)):
    for tag in _tags:
      if tag.name.value not in styles:
        styles[tag.name.value] = []
      outRange = outstyles.get((tag.name.value, tag.value))
      if outRange is None:
        outRange = outstyles[(tag.name.value, tag.value)] = []
      quads = styles[tag.name.value]
      for rang in tag.ranges:
        # quad: Value, priority, Start or Stop, True if Stop
        quads.append((tag.value, prior, rang[0], False))
        quads.append((tag.value, prior, rang[1], True))
  return styles,outstyles,tags

def tagMerge(old_tags, tag_list):
  """ merge tags """
  (styles,outstyles,tags) = _tagEnumerate(old_tags, tag_list)
  for tagname, quads in styles.items():
    quads.sort(key=lambda quad: quad[2])  # sort by start/stop index
    # start, end are current range
    start = value = None
    prior = 0
    # open_low; list of low priority open (nested) values
    # open_high; list of high priority open (nested) values
    openst = [[], []]
    for quad in quads:
      if not quad[3]:  # We have a start
        if start is None:  # we can start up
          value = quad[0]
          prior = quad[1]
          start = quad[2]
        elif value == quad[0]:
          # we have an overlap with same
          continue
        else:  # we have a nest or overlap with different
          openst[prior].append(value)  # save current in open
          # close out current, and start new
          outstyles[(tagname, value)].append((start, quad[2]))
          value = quad[0]
          prior = quad[1]
          start = quad[2]
        continue
      # we have a end
      if start is None:  # end with no start
        continue
      if quad[0] == value:  # current finished
        outstyles[(tagname, value)].append((start, quad[2]))
        start = value = prior = None
        if openst[1]:  # high priority nested to restart
          value = openst[1].pop()
          prior = 1
          start = quad[2]
        elif openst[0]:  # low priority nested to restart
          value = openst[0].pop()
          prior = 0
          start = quad[2]
      else:  # clear out overlap
        try:
          openst[quad[1]].remove(quad[0])
        except ValueError:
          pass
        continue
  return _doMerge(outstyles,tags)

def _doMerge(outstyles,tags):
  """ all is prepared in outstyles : do final merge """
  end = None
  msg = ("Bad Style range!  Do not save, "
         "if you do your db will be corrupted.")
  for ((name, value), ranges) in outstyles.items():
    newRange = []
    start = None
    for rang in ranges:
      if start is not None:
        if rang[0] == end:
          # should merge two ranges together
          end = rang[1]
          continue
        newRange.append((start, end))
        if start is None or end is None:
          raise ValueError(msg)
      start = rang[0]
      end = rang[1]
    newRange.append((start, end))
    if start is None or end is None:
      raise ValueError(msg)
    tags.append(StyledTextTag(name, value, newRange))
  return tags

if __name__ == '__main__':
  Html='<p>'\
       '<a href="http://archives.marne.fr/ark:/86869/a011310543788e2DmVt/1/113" target="_blank">'\
       'un_premier_lien</a><br>'\
       '<br>'\
       'Stanislas, <b>né</b> à 03h00.<br>'\
       '<a href="http://archives.marne.fr/ark:/86869/a011310543788e2DmVt/1/114" target="_blank">'\
       '<b>deuxième</b> lien</a><br>'\
       'fils de <b>Louis <i>Charles</b> Desbordes</i>, boucher, signe.<br>'\
       'et de Marie Madeleine Éléonore Brémond.'\
       '</p>'
  Converted = convertToStyled(Html)
  print(Converted)
  for t in Converted.get_tags() :
    print(t.name)
    print(t.value,t.ranges)
