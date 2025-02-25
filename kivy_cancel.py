from kivy.properties import StringProperty
from os.path import join, dirname
from kivy.lang import Builder
from kivy.uix.popup import Popup

Builder.load_file(join(dirname(__file__), 'kivy_cancel.kv'))

class CancelPopup(Popup):

    text = StringProperty('Backing up')
    cancel_text = StringProperty('cancel!')
    __events__ = ('on_ok', 'on_cancel')

    def setPath(self, path):
        self.text = "Backing up %s" % path

    def cancel(self):
        self.dispatch('on_cancel')
        self.dismiss()

    def on_ok(self):
        pass

    def on_cancel(self):
        pass


