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

#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
import io
import re
import html

#-------------------------------------------------------------------------
#
# Gtk modules
#
#-------------------------------------------------------------------------
if __name__ == '__main__':
  import gi
  gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gui.managedwindow import ManagedWindow
from gramps.gui.utils import ProgressMeter
from gramps.gen.db import DbTxn
from gramps.gui.dialog import WarningDialog
from gramps.gui.display import display_url
from gramps.gui.editors import EditNote
from gramps.gen.lib import Note
from gramps.gen.errors import WindowActiveError
from gramps.gen.lib import (StyledText, StyledTextTag, StyledTextTagType)
from gramps.gui.widgets.styledtexteditor import StyledTextEditor


#------------------------------------------------------------------------
#
# Internationalisation
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


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
tok_regex = '|'.join('(?P<%s>%s)' % pair for
                     pair in token_specification)

def convert_to_styled(data):
    """
    This scans incoming notes for possible html.  It converts a select few
    tags into StyledText and removes the rest of the tags.  Notes of this
    type occur in data from FTM and ancestry.com.  Result is a much
    cleaner note.

    @param data: a string of text possibly containg html
    @type data: str

    """
    prev = 0
    chunkpos = 0
    chunks = []
    italics = []
    bolds = []
    unders = []
    links = []
    reds = []
    bldpos = -1
    styText = StyledText(data)
    for mo in re.finditer(html._charref, styText._string):
        out = html._replace_charref(mo)
        in_start = mo.start()
        in_end = mo.end()
        styText._string = (styText._string[:in_start] + out +
                        styText._string[(in_start + len(out)):])
        if prev != in_start + len(out):
            chunks.append(styText._string[prev:(in_start + len(out))])
            chunkpos += (in_start - prev + len(out))
        prev = in_end
    chunks.append(styText._string[prev:])

    styText = StyledText().join(chunks)
    prev = 0
    chunkpos = 0
    chunks = []
    for mo in re.finditer(tok_regex, styText._string,
                          flags=(re.DOTALL | re.I)):
        kind = mo.lastgroup
        st_txt = mo.group(kind)
        in_start = mo.start()
        in_end = mo.end()
        if kind == 'SKIP' or kind == 'TABLE':
            if prev != in_start:
                chunks.append(styText._string[prev:in_start])
                chunkpos += (in_start - prev)
        elif kind == 'PARAEND':
            chunks.append(styText._string[prev:in_start] + '\n')
            chunkpos += (in_start - prev + 1)
        elif kind == 'ITALIC':
            chunks.append(styText._string[prev:in_start] +
                          styText._string[(in_start + 3):in_end])
            newpos = chunkpos - prev + in_end - 3
            italics.append((chunkpos + in_start - prev, newpos))
            chunkpos = newpos
        elif kind == 'BOLD':
            chunks.append(styText._string[prev:in_start] +
                          styText._string[(in_start + 3):in_end])
            newpos = chunkpos - prev + in_end - 3
            bolds.append((chunkpos + in_start - prev, newpos))
            chunkpos = newpos
        elif kind == 'UNDER':
            chunks.append(styText._string[prev:in_start] +
                          styText._string[(in_start + 3):in_end])
            newpos = chunkpos - prev + in_end - 3
            unders.append((chunkpos + in_start - prev, newpos))
            chunkpos = newpos
        elif kind == 'HTTP':      # HTTP found
            st_txt = mo.group('HTTP')
            oldpos = chunkpos + in_start - prev
            chunks.append(styText._string[prev:in_start] + st_txt)
            chunkpos += (in_start - prev + len(st_txt))
            st_txt = st_txt.rstrip(' .:)')
            newpos = oldpos + len(st_txt)
            links.append((st_txt, oldpos, newpos))
        elif kind == 'HREF':      # HREF found
            st_txt = mo.group('HREFT')
            lk_txt = mo.group('HREFL')
            # fix up relative links emmitted by ancestry.com
            if(lk_txt.startswith("/search/dbextra") or
               lk_txt.startswith("/handler/domain")):
                lk_txt = "http://search.ancestry.com" + lk_txt
            oldpos = chunkpos + in_start - prev
            # if tag (minus any trailing '.') is substring of link
            if st_txt[0:-1] in lk_txt:
                st_txt = lk_txt   # just use the link
            else:                 # use link and tag
                st_txt = " " + lk_txt + " (" + st_txt + ")"
            newpos = oldpos + len(st_txt)
            chunks.append(styText._string[prev:in_start] + st_txt)
            chunkpos += (in_start - prev + len(st_txt))
            links.append((lk_txt, oldpos, newpos))
        elif kind == 'TBLCELL' or kind == 'TBLHDRC':     # Table cell break
            chunks.append(styText._string[prev:in_start] + ':  ')
            chunkpos += (in_start - prev + 3)
        elif kind == 'TBLHDRB':      # header start
            if prev != in_start:
                chunks.append(styText._string[prev:in_start])
                chunkpos += (in_start - prev)
            bldpos = chunkpos
        elif kind == 'TBLHDRE':      # Header end
            if bldpos == -1:
                if prev != in_start:
                    chunks.append(styText._string[prev:in_end])
                    newpos = chunkpos - prev + in_end
                    reds.append((chunkpos + in_start - prev, newpos))
                    chunkpos = newpos
                print('Invalid table header, no start tag found')
            else:
                if prev != in_start:
                    chunks.append(styText._string[prev:in_start])
                    chunkpos += (in_start - prev)
                bolds.append((bldpos, chunkpos))
                bldpos = -1
        elif kind == 'UNKNWN':
            chunks.append(styText._string[prev:in_end])
            newpos = chunkpos - prev + in_end
            reds.append((chunkpos + in_start - prev, newpos))
            chunkpos = newpos
            print('Unexpected or unimplemented HTML tag', st_txt)
        else:
            print("shouldn't get here")

        prev = in_end
    chunks.append(styText._string[prev:])

    result = StyledText().join(chunks)
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
    return StyledText(result._string, tag_merge(result._tags, tags))


def tag_merge(old_tags, tag_list):
    styles = {}  # key:name  value:quad
    outstyles = {}  # key:tuple(name, value), value:list(ranges)
    tags = []
    for (prior, tags_) in enumerate((old_tags, tag_list)):
        for tag in tags_:
            if tag.name.value not in styles:
                styles[tag.name.value] = []
            out_range = outstyles.get((tag.name.value, tag.value))
            if out_range is None:
                out_range = outstyles[(tag.name.value, tag.value)] = []
            quads = styles[tag.name.value]
            for rang in tag.ranges:
                # quad: Value, priority, Start or Stop, True if Stop
                quads.append((tag.value, prior, rang[0], False))
                quads.append((tag.value, prior, rang[1], True))

    for tagname, quads in styles.items():
        quads.sort(key=lambda quad: quad[2])  # sort by start/stop index
        # start, end are current range
        start = value = prior = None
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
            else:  # we have an end
                if start is None:  # end with no start
                    continue
                if quad[0] == value:  # current finished
                    outstyles[(tagname, value)].append((start, quad[2]))
                    if openst[1]:  # high priority nested to restart
                        value = openst[1].pop()
                        prior = 1
                        start = quad[2]
                    elif openst[0]:  # low priority nested to restart
                        value = openst[0].pop()
                        prior = 0
                        start = quad[2]
                    else:  # no nest to restart, just close out
                        start = value = prior = None

                else:  # clear out overlap
                    try:
                        openst[quad[1]].remove(quad[0])
                    except ValueError:
                        pass
                    continue
        end = None
    msg = ("Bad Style range!  Do not save, "
           "if you do your db will be corrupted.")
    for ((name, value), ranges) in outstyles.items():
        new_range = []
        start = None
        for rang in ranges:
            if start is not None:
                if rang[0] == end:
                    # should merge two ranges together
                    end = rang[1]
                    continue
                else:
                    new_range.append((start, end))
                    if start is None or end is None:
                        raise ValueError(msg)
            start = rang[0]
            end = rang[1]
        new_range.append((start, end))
        if start is None or end is None:
            raise ValueError(msg)
        tags.append(StyledTextTag(name, value, new_range))
    return tags

if __name__ == '__main__':
   print(convert_to_styled('<p>\
<a href="http://archives.marne.fr/ark:/86869/a011310543788e2DmVt/1/113" target="_blank">http://archives.marne.fr/ark:/86869/a011310543788e2DmVt/1/113</a><br>\
<br>\
Stanislas, né à 03h00.<br>\
fils de Louis Charles Desbordes, boucher, signe.<br>\
et de Marie Madeleine Éléonore Brémond.\
</p>'))
