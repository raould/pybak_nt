import kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
import os
import socket
import threading
import client
import visit_core
import kivy_cancel

Builder.load_string("""
<MyWidget>:
    orientation: 'vertical'
    id: my_widget
    Label:
        size_hint: (1, 0.1)
        text: "Welcome to Pybak"
    Label:
        size_hint: (1, 0.1)
        text: "Navigate below to desired directory."
    Button
        size_hint: (1, 0.1)
        text: "[Press Me to Backup Current Directory]"
        on_release: my_widget.onOpen(filechooser.path, filechooser.selection)
    Label:
        size_hint: (1, 0.1)
        text: my_widget.getLabelName(filechooser.path, filechooser.selection)
    FileChooserListView:
        id: filechooser
        path: "/home/superman/Media/20160306"
""")

class CrawlingThread( object ):
    def __init__( self, path ):
        self.path = path
    def start( self ):
        thread = threading.Thread( target=self.run, args=() )
        thread.start()
    def run( self ):
        print( "!!! crawl: %s" % self.path )
        pybak_client = client.Client( socket.gethostname() )
        print( pybak_client )
        ip = "192.168.123.65"
        port = "6969"
        def visit_pre_dir( dirpath, max_depth, cur_depth, data ):
            return client.visit_pre_dir_c( dirpath, max_depth, cur_depth, data, ip, port, "dryrunmissing", pybak_client )
        #f = visit_core.visit( self.path, None, client.visit_file, visit_pre_dir, {'max_bytes':None} )
        cancel = kivy_cancel.CancelPopup()
        cancel.bind(on_cancel=lambda x: self.stop())
        cancel.open()
    def stop( self ):
        print( "!!! stop" )

class MyWidget( BoxLayout ):
    def is_dir( self, path, filename ):
        return os.path.isdir(os.path.join(path, filename))
    def startCrawlingThread( self, path ):
        crawlingThread = CrawlingThread( path )
        crawlingThread.start()
    def onOpen( self, path, filename ):
        print( "onOpen %s %s" % (path, filename) )
        if path != None:
            self.startCrawlingThread( path )
    def getLabelName( self, path, filename ):
        if len(filename) > 0:
            return os.path.join(path, filename[0])
        else:
            return path

class PybakApp( App ):
    def build( self ):
        return MyWidget()

def setupScreenSize():
    platform = kivy.utils.platform()
    if platform == 'android' or platform == 'ios':
        Window.fullscreen = True
    else:
        Window.fullscreen = False

if __name__ == '__main__':
    setupScreenSize()
    PybakApp().run()
