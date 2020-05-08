from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
try:
    from qgis.PyQt.QtWidgets import *
except:
    pass
from .tools.profiletool_core import ProfileToolCore

class ProfilePlugin:

    def __init__(self, iface):
        self.iface = iface              #variable para acceder a la mayoría de los componentes gráficos de QGIS.
        self.canvas = iface.mapCanvas() #variable para utilizar el lienzo del mapa
        self.profiletool = None         #variable donde se almacena la herramienta del perfil
        self.dockOpened = False         #controla la apertura y el cierre del plugin

    """ initgui: funcion necesaria para la instalacion del plugin """
    def initGui(self):
        self.action = QAction(QIcon(os.path.join(os.path.dirname(__file__), "profileIcon.png")),
                              "SigFox Coverage Tool", self.iface.mainWindow())  #crea el icono del plugin y las acciones sobre el
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&SigFox Profile Tool", self.action)

    """ Unload: funcion necesaria para la desinstalacion el plugin """
    def unload(self):
        try:
            self.profiletool.dockwidget.close()
        except:
            pass
        try:
            self.canvas.mapToolSet.disconnect(self.mapToolChanged)
        except:
            pass
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&SigFox Profile Tool", self.action)

    """ Run: funcion que ejecuta todas las operaciones del plugin """
    def run(self):

        if not self.dockOpened:
            self.profiletool = ProfileToolCore(self.iface,self)             #carga el estado inical del plugin
            self.iface.addDockWidget(self.profiletool.dockwidget.location,
                                     self.profiletool.dockwidget)           #agrega las caracteristicas del plugin
            self.profiletool.dockwidget.closed.connect(self.cleaning)       #limpia todas las acciones al cerrarse el plugin
            self.dockOpened = True
            self.profiletool.activateProfileMapTool()                       #activa las herramientas de perfil
        else:
            self.profiletool.activateProfileMapTool()

    """ cleaning: funcion para limpiar las acciones realizadas por el plugin """
    def cleaning(self):
        self.dockOpened = False
        self.profiletool.cleaning()
        if self.profiletool.toolrenderer:                                   #limpia la polilinea temporal creada en el mapa
            self.canvas.unsetMapTool(self.profiletool.toolrenderer.tool)
        self.canvas.setMapTool(self.profiletool.saveTool)
        self.iface.mainWindow().statusBar().showMessage( "" )