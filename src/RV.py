'''
Created on 19 ott 2019

@author: Matteo
'''
from kivy.app import App
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.gridlayout import GridLayout
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
import socket


class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''


Builder.load_string('''
<SelectableLabel>:
    # Draw a background to indicate selection
    canvas.before:
        Color:
            rgba: (.0, 0.9, .1, .3) if self.selected else (0, 0, 0, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    shname: 'sh Name'
    ico: ''
    sel: False
    pos: self.pos
    size: self.size
    CheckBox:
        id: id_selected
        active: root.selected
        on_active:
            root.apply_selection(root.parent.parent,root.index,self.active)
    Image:
        id: id_icon
        source: root.ico
    Button:
        id: id_shname
        text: root.shname
        on_release: root.send_sh()

<RV>:
    viewclass: 'SelectableLabel'
    SelectableRecycleBoxLayout:
        default_size: None, dp(56)
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: 'vertical'
        multiselect: True
        touch_multiselect: True
''')


class SelectableLabel(RecycleDataViewBehavior, GridLayout):
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)
    cols = 3

    def send_sh(self):
        datahere = self.parent.parent.data[self.index]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        Logger.info("udp://"+datahere['host']+':'+str(datahere['udpport'])+'/'+datahere['msg'])
        sock.sendto(bytes(datahere['msg'], "utf-8"), (datahere['host'], datahere['udpport']))

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        self.shname = data['name']
        self.ico = data['ico']
        self.selected = data['sel']
        self.apply_selection(rv, index, self.selected)
        return super(SelectableLabel, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(SelectableLabel, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        rv.data[index]["sel"] = is_selected
        if is_selected:
            print("selection changed to {0}".format(rv.data[index]))
        else:
            print("selection removed for {0}".format(rv.data[index]))


class RV(RecycleView):
    pass


class TestApp(App):
    def build(self):
        return RV()


if __name__ == '__main__':
    TestApp().run()
