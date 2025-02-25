import metadata
import visit_core
import os
import os.path
import sys

# based on python docs.
gOS2Encoding = {
    MAC: 'utf-8',
    LINUX: None,
    WINDOWS: 'mbcs'
}

# based on what we've crawled to date.
# todo: frighteningly suspiciously missing windows machines!
gHost2OS = {
'Computer-Maru.local': MAC
'Duffs-MacBook-Pro.local': MAC
'G4-2.local': MAC
'catriona-logans-computer-2.local': MAC
'catriona-logans-computer-3.local': MAC
'computer-maru': MAC
'mx.monad.com': LINUX
'openvz.monad.com': LINUX
'superlap': LINUX
'superlap2': LINUX
'superlap4300': LINUX
'superlap4730': LINUX
'superman-laptop': LINUX
'superpet': LINUX
'unicycle': WINDOWS
'unknownb88d12207a7a': MAC
'www.monad.com/ ': LINUX
}

def pythonEncodingForHost( host ):
    encoding = None
    if host in gHost2OS:
        os = gHost2OS[host]
        if os in gOS2Encoding:
            encoding = gOS2Encoding[os]
    return encoding
