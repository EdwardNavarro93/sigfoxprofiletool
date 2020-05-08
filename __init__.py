
from . import apicompat

def classFactory(iface):
 from .profileplugin import ProfilePlugin
 return ProfilePlugin(iface)
