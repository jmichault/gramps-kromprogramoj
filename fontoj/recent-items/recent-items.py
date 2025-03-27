#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2024      Kari Kujansuu
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

# Recent Items
# ------------
#
# This plugin implements a "recent items" feature in all Gramps selector dialogs.
#
# The plugin will patch the object selector code so that the selector dialogs include
# a list of recently used items. The list is stored in an JSON format file in
# the same directory where this code resides.
#
# To update the recent list the plugin must also handle the cases:
# - an object is selected using a selector dialog
# - an object is ədded using an editor dialog for a primary object
# - an object is ədded using an editor dialog for a reference to a primary objects
# These are implemented by patching the object editors
# and the object reference editors as well as the selector dialog.

# ------------------------------------------------------------------------
#
# Python modules
#
# ------------------------------------------------------------------------
#from objbrowser import browse ;browse(locals())
#import pdb; pdb.set_trace()

import json
import os
import sys
import traceback

# ------------------------------------------------------------------------
#
# GRAMPS modules
#
# ------------------------------------------------------------------------

from gi.repository import Gtk, Gdk

from gramps.gen.config import CONFIGMAN as config
from gramps.gen.errors import HandleError
from gramps.gen.lib import Source, Citation, Person

from gramps.gui.editors.editperson import EditPerson
from gramps.gui.editors.editprimary import EditPrimary
from gramps.gui.editors.editreference import EditReference
from gramps.gui.editors import EditPlaceRef
from gramps.gui.selectors.selectplace import SelectPlace
from gramps.gui.selectors.baseselector import BaseSelector
from gramps.gui.widgets import SimpleButton
from gramps.gui.widgets.persistenttreeview import PersistentTreeView

# ------------------------------------------------------------------------
#
# Internationalisation
#
# ------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

dbpath = config.get("database.path")

name = "recent-items.json"
dirname = os.path.split(__file__)[0]
fname = os.path.join(dirname, name)

MAXITEMS = 8


def load_on_reg(dbstate, uistate, plugin):
    # patch some classes
    if not hasattr(BaseSelector, "orig_init"):
        BaseSelector.orig_init = BaseSelector.__init__
    BaseSelector.__init__ = lambda self, *args, **kwargs: new_init(self, dbstate, *args, **kwargs)

    if not hasattr(BaseSelector, "orig_run"):
        BaseSelector.orig_run = BaseSelector.run
    BaseSelector.run = new_run

    if not hasattr(EditPrimary, "orig_do_close"):
        EditPrimary.orig_do_close = EditPrimary._do_close
    EditPrimary._do_close = new_do_close

    if not hasattr(EditReference, "orig_close"):
        EditReference.orig_close = EditReference.close
    EditReference.close = new_close


def update_recent_items(self, dbid, obj):
    """
    This is called to update the .json file with a new (selected or added) object
    """
    namespace = get_namespace(self)
    recent_data = get_recent_data()
    olddata = recent_data.get(dbid, {}).get(namespace, [])
    if not obj or not obj.handle:
        return # prevent null values
    value = obj.handle
    if value in olddata:
        olddata.remove(value)
    olddata.insert(0, value)
    olddata = olddata[0:MAXITEMS]
    if dbid not in recent_data:
        recent_data[dbid] = {}
    recent_data[dbid][namespace] = olddata
    if namespace == "Person":
        ns1 = None
        if obj.gender == Person.MALE:
            ns1 = "Person-M"
        if obj.gender == Person.FEMALE:
            ns1 = "Person-F"
        if ns1:
            olddata = recent_data[dbid].get(ns1, [])
            if value in olddata:
                olddata.remove(value)
            olddata.insert(0, value)
            olddata = olddata[0:MAXITEMS]
            recent_data[dbid][ns1] = olddata
    remove_deleted_databases(recent_data)
    with open(fname, "w") as f:
        print(json.dumps(recent_data, indent=4), file=f)

def remove_deleted_databases(recent_data):
    dbids = set(os.listdir(dbpath))
    for dbid in list(recent_data):
        if dbid not in dbids:
            del recent_data[dbid]
            
def get_recent_data():
    try:
        recent_data = json.loads(open(fname).read())
    except:
        recent_data = {}
    return recent_data


def get_namespace(self):
    """
    This function converts the self class name to namespace, e.g.
        SelectPlace     ->  Place
        EditPlace       ->  Place
        EditPlaceRef    ->  Place
    """
    clsname = self.__class__.__name__
    namespace = clsname.replace("Select", "")
    namespace = namespace.replace("Edit", "")
    namespace = namespace.replace("Ref", "")
    return namespace


# ------------------------------------------


def new_init(self, dbstate, *args, **kwargs):
    """
    This method will replace the __init__ method in BaseSelector.

    This will add the "Recent items" list in the selector dialog.

    This is done by adding a Gtk.TreeView in the UI originally loaded from the Glade file baseselector.glade.
    The other widgets are moved down to make room for the TreeView.
    """
    BaseSelector.orig_init(self, *args, **kwargs)

    # move other items down to make room for the TreeView at position 1
    vbox = self.glade.get_object("select_person_vbox")
    #    - 4 items:
    #        title
    #        scrolledwindow
    #        showall checkbox
    #        label "Loading"
    for i, c in enumerate(vbox.get_children()):
        if i > 0:
            vbox.child_set_property(c, "position", i + 1)
    recent_box = Gtk.VBox()
    vbox.add(recent_box)
    vbox.child_set_property(recent_box, "position", 1)

    maxindex = max(index for colnam, width, coltype, index in self.get_column_titles())
    numcolumns = maxindex + 1
    args = [str] * (numcolumns + 1)  # one for the handle
    model = Gtk.ListStore(*args)
    tree = PersistentTreeView(self.uistate, self.get_config_name())
    tree.set_model(model)
    #tree.set_headers_visible(False)

    BaseSelector.add_columns(self, tree)
    tree.restore_column_size()
    if hasattr(self,'filter') and self.filter :
      filterobj = self.filter[1]
    else :
      filterobj = None

    namespace = get_namespace(self)
    if namespace == "Person":
      if self.title == _("Select Mother"):
#        if isinstance(filterobj, FastFemaleFilter):
            namespace = "Person-F"
      if self.title == _("Select Father"):
#        if isinstance(filterobj, FastMaleFilter):
            namespace = "Person-M"
    dbid = self.db.get_dbid()
    recent_data = get_recent_data()
    olddata = recent_data.get(dbid, {}).get(
        namespace, []
    )  # list of handles for this database and this namespace
    
    
    for handle in olddata:
        try:
            obj = self.get_from_handle_func()(handle)
        except HandleError:
            continue  # object probably deleted, skip
        if namespace == "Person" and filterobj and not filterobj.match(handle, self.db):
            continue        
        values = [""] * numcolumns
        for colnam, width, coltype, index in self.get_column_titles():
            fmap = self.model.fmap
            if namespace == "Citation":
                if isinstance(obj, Source):
                    fmap = self.model.fmap
                if isinstance(obj, Citation):
                    fmap = self.model.fmap2

            if index == 0 and isinstance(obj, Citation):
                value = get_citation_title(self.db, obj)  # special case
            else:
                if ( 
                    fmap[index] is None
                ):  # e.g. Abbreviation column for Citations does not exist
                    value = ""
                # FIXME : pourquoi ça ne marche pas avec le nom des personnes ???
                elif namespace[0:6] == "Person" and index==0 :
                  #import pdb; pdb.set_trace()
                  #value = str(obj.primary_name)
                  primary_name = obj.get_primary_name()
                  from gramps.gen.lib import Name
                  nname = Name(primary_name)
                  nname.set_display_as(primary_name.display_as)
                  from gramps.gen.display.name import displayer as _nd
                  value = _nd.display_name(nname)
                #    value = ""
                else:
                    value = fmap[index](obj)  # normal case
            values[index] = value
        values.append(handle)
        model.append(values)

    msg = "<b>" + _("Recent items:") + "</b>"
    if len(model) == 0:  # no recent items to display
        msg += " " + _("None")
    header = Gtk.HBox()
    header.set_size_request(-1,-1)
    lbl = Gtk.Label(msg)
    lbl.set_use_markup(True)
    lbl.set_halign(Gtk.Align.START)
    but = Gtk.Button("New")
    but.connect("clicked", lambda _widget: new_item(self, dbstate))

#     but = SimpleButton('list-add',  lambda _widget: new_item(self, dbstate))
#     but.set_relief(Gtk.ReliefStyle.NORMAL)

    header.pack_start(lbl, False, True, 0)
#    header.pack_start(but, False, True, 5)
    recent_box.add(header)
    recent_box.add(tree)
    recent_box.show_all()

    # activate a row on the recent items list but do not select it yet
    tree.set_activate_on_single_click(True)
    tree.connect(
        "row-activated",
        lambda tree, path, col: row_activated(self, model, tree, path, col),
    )

    # OK button clicked -> select the item
    tree.connect(
        "button-press-event",
        lambda _tree, event: button_press(self, tree, _tree, event),
    )


def new_item(self, dbstate):
    print("new")
    p = Person()
#     class DbState: pass
#     dbstate = DbState()
#     dbstate.db = self.db 
    track = []
    EditPerson(dbstate, self.uistate, track, p, callback=callback)
    
def callback(obj):
    print("new obj",obj)
    
def get_citation_title(db, citation):
    src = db.get_source_from_handle(citation.get_reference_handle())
    return src.title + ": " + citation.page


def row_activated(self, model, tree, path, col):
    it = model.get_iter(path)
    row = model[it]
    handle = list(row)[-1]
    BaseSelector.goto_handle(self, handle)


def button_press(self, tree, _tree, event):
    # type: (Gtk.TreeView, Gtk.Event) -> bool
    model, treeiter = tree.get_selection().get_selected()
    if model is None or treeiter is None:
        return
    row = list(model[treeiter])
    handle = row[-1]
    if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
        self.window.response(Gtk.ResponseType.OK)
        return True
    return False


# ------------------------------------------------------------------


def new_run(self):
    """
    This method will replace the "run()" method in BaseSelector.

    The code is copied from BaseSelector and the call to update_recent_items is added.
    ResponseType.OK means that the user has pressed the OK button and accepts an item from the list.
    That item is added to recent items.
    """
    val = self.window.run()
    result = None
    if val == Gtk.ResponseType.OK:
        id_list = self.get_selected_ids()
        if id_list and id_list[0]:
            handle = id_list[0]
            result = self.get_from_handle_func()(handle)
            update_recent_items(self, self.db.get_dbid(), result)
        self.close()
    elif val != Gtk.ResponseType.DELETE_EVENT:
        self.close()
    return result


# ------------------------------------------------------------------


def new_do_close(self, *args):
    """
    This method will replace the "_do_close" method in EditPrimary.

    This handles the case when a new object is added through an EditPrimary subclass (EditPerson, EditPlace etc).

    The "_do_close" function is patched to call the update_recent_items function.
    """
    dbid = self.db.get_dbid()
    update_recent_items(self, dbid, self.obj)
    EditPrimary.orig_do_close(self, *args)


# ------------------------------------------------------------------


def new_close(self, *args):
    """
    This method will replace the "close" method in EditReference.

    This handles the case when a new object is added through an EditReference subclass (EditPersonRef etc), i.e. in
    cases when there is an intermediate reference object.

    The "close" function is patched to call the update_recent_items function.
    """
    dbid = self.db.get_dbid()
    update_recent_items(self, dbid, self.source)
    EditReference.orig_close(self, *args)
