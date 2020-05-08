from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *

from qgis.core import *
from qgis.gui import *
import qgis

from .selectlinetool import SelectLineTool

class ProfiletoolMapToolRenderer():

    def __init__(self, profiletool):
        self.profiletool = profiletool
        self.iface = self.profiletool.iface
        self.canvas = self.profiletool.iface.mapCanvas()
        self.tool = ProfiletoolMapTool(self.canvas,self.profiletool.plugincore.action)        #escucha acciones del raton sobre el canvas
        self.pointstoDraw = []
        self.dblclktemp = None                                                                #permite distinguir entre click izquierdo y dobleclick
        #the rubberband
        self.polygon = False
        self.rubberband =QgsRubberBand(self.iface.mapCanvas(), self.polygon) #Una clase para dibujar una linea transitoria en el mapa.
        self.rubberband.setWidth(3)                                          #tamaño de la linea
        self.rubberband.setColor(QColor(Qt.blue))                            #color de la linea

        self.rubberbandpoint = QgsVertexMarker(self.iface.mapCanvas())  #clase para dibujar un marcador sobre la polilinea "rubberband" en el canvas o mapa
        self.rubberbandpoint.setColor(QColor(Qt.magenta))               #color del marcador
        self.rubberbandpoint.setIconSize(5)                             #tamaño del marcador
        self.rubberbandpoint.setIconType(QgsVertexMarker.ICON_BOX)      #la forma del marcador "ICON_CROSS, ICON_X"
        self.rubberbandpoint.setPenWidth(3)

        self.rubberbandbuf = QgsRubberBand(self.iface.mapCanvas())      #se crea un espacio de memoria temporal
        self.rubberbandbuf.setWidth(1)
        self.rubberbandbuf.setColor(QColor(Qt.blue))
        self.textquit0 = "Left click for polyline and right click to cancel then quit"
        self.selectionmethod = 0    #la herramienta es solo para propositos de visualizacion "temporary line"
        self.cleaning()             #metodo para limpiar todas las variables


    def resetRubberBand(self): #reinicia la linea transitoria
        try:    #qgis2
            if QGis.QGIS_VERSION_INT >= 10900:
                self.rubberband.reset(QGis.Line)
            else:
                self.rubberband.reset(self.polygon)
        except: #qgis3
            self.rubberband.reset(qgis.core.QgsWkbTypes.LineGeometry)

#************************************* Mouse listener actions ***********************************************

    def moved(self,position):        #dibuja la polilinea en la capa temporal (rubberband) mientras el mouse se mueve
        if self.selectionmethod == 0:
            if len(self.pointstoDraw) > 0:
                #Get mouse coords
                mapPos = self.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
                #Draw on temp layer
                self.resetRubberBand()
                for i in range(0,len(self.pointstoDraw)):
                     self.rubberband.addPoint(QgsPointXY(self.pointstoDraw[i][0],self.pointstoDraw[i][1]))
                self.rubberband.addPoint(QgsPointXY(mapPos.x(),mapPos.y()))


    def rightClicked(self,position):  #usado para borrar la linea temporal y todos los calculos
        self.profiletool.clearProfil()
        self.cleaning()

    def leftClicked(self,position):  #agrega un punto para analizar
        mapPos = self.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"]) #obtiene la cordenada del cursor en ese punto y lo transforma en coordenadas de mapa para trabajar sobre el
        newPoints = [[mapPos.x(), mapPos.y()]] #los nuevos puntos sobre el mapa

        if self.profiletool.doTracking:
            self.rubberbandpoint.hide() #esconder el puntero mientras se dibuja la polilinea

        if self.selectionmethod == 0:
            if newPoints == self.dblclktemp:
                self.dblclktemp = None   #para distinguir entre click derecho e izqquierdo
                return
            else :
                if len(self.pointstoDraw) == 0:
                    self.resetRubberBand()          #reinicia la "rubberband"
                    self.rubberbandbuf.reset()      #reinicia la memoria
                    self.pointstoDraw += newPoints  #agrega los puntos
                    self.profiletool.updateProfil(self.pointstoDraw) #manda los puntos para actualizar la herramienta de perfil
                elif len(self.pointstoDraw) == 1:
                    self.pointstoDraw += newPoints  #agrega los puntos
                    self.profiletool.updateProfil(self.pointstoDraw)  #manda los puntos para actualizar la herramienta de perfil
                    self.pointstoDraw = []
                    # temp point to distinct leftclick and dbleclick
                    self.dblclktemp = newPoints

    def doubleClicked(self,position): #fuera de funcionamiento
        if self.selectionmethod == 0:
            #Validation of line
            mapPos = self.canvas.getCoordinateTransform().toMapCoordinates(position["x"],position["y"])
            newPoints = [[mapPos.x(), mapPos.y()]]
            self.pointstoDraw += newPoints
            #launch analyses
            self.iface.mainWindow().statusBar().showMessage(str(self.pointstoDraw))
            self.profiletool.updateProfil(self.pointstoDraw)
            #Reset
            self.pointstoDraw = []
            #temp point to distinct leftclick and dbleclick
            self.dblclktemp = newPoints
            self.iface.mainWindow().statusBar().showMessage(self.textquit0)
        if self.selectionmethod in (1, 2):
            return

    def setSelectionMethod(self):
        self.cleaning()
        self.tool.setCursor(Qt.CrossCursor)
        self.iface.mainWindow().statusBar().showMessage(self.textquit0)

    def setBufferGeometry(self, geoms):
        self.rubberbandbuf.reset()
        for g in geoms:
            self.rubberbandbuf.addGeometry(g, None)

    def cleaning(self):            #usado cuando se hace click derecho
        self.pointstoDraw = []
        self.rubberbandpoint.hide()
        self.resetRubberBand()
        self.rubberbandbuf.reset()
        self.profiletool.clearLabels()
        self.iface.mainWindow().statusBar().showMessage( "" )


    def connectTool(self):                      #conecta a las acciones sobre el mapa
        self.tool.moved.connect(self.moved)                 #cuando el cursor se mueva sobre el mapa
        self.tool.rightClicked.connect(self.rightClicked)   #cuando el cursor haga click derecho sobre el mapa
        self.tool.leftClicked.connect(self.leftClicked)     #cuando el cursor haga click izquierdo sobre el mapa
        self.tool.doubleClicked.connect(self.doubleClicked) #cuando el cursor haga doble click sobre el mapa
        self.tool.desactivate.connect(self.deactivate)      #cuando se desactive el cursor

    def deactivate(self):        #habilitar la salida limpia del plugin
        self.cleaning()
        self.tool.moved.disconnect(self.moved)
        self.tool.rightClicked.disconnect(self.rightClicked)
        self.tool.leftClicked.disconnect(self.leftClicked)
        self.tool.doubleClicked.disconnect(self.doubleClicked)
        self.tool.desactivate.disconnect(self.deactivate)
        self.canvas.unsetMapTool(self.tool)
        self.canvas.setMapTool(self.profiletool.saveTool)

class ProfiletoolMapTool(QgsMapTool):

    moved = pyqtSignal(dict)
    rightClicked = pyqtSignal(dict)
    leftClicked = pyqtSignal(dict)
    doubleClicked = pyqtSignal(dict)
    desactivate = pyqtSignal()

    def __init__(self, canvas,button):
        QgsMapTool.__init__(self,canvas)
        self.canvas = canvas
        self.cursor = QCursor(Qt.CrossCursor) #elige un cursor en forma de cruz para desplazarse sobre el canvas
        self.button = button

    def canvasMoveEvent(self,event):    #mientras se mueve sobre el canvas o mapa
        self.moved.emit({'x': event.pos().x(), 'y': event.pos().y()})


    def canvasReleaseEvent(self,event):  #cuando se hace click sobre el mapa
        if event.button() == Qt.RightButton:
            self.rightClicked.emit({'x': event.pos().x(), 'y': event.pos().y()})
        else:
            self.leftClicked.emit( {'x': event.pos().x(), 'y': event.pos().y()} )

    def canvasDoubleClickEvent(self,event):
        self.doubleClicked.emit( {'x': event.pos().x(), 'y': event.pos().y()} )

    def activate(self):
        QgsMapTool.activate(self)
        self.canvas.setCursor(self.cursor)
        self.button.setCheckable(True)
        self.button.setChecked(True)

    def deactivate(self):
        self.desactivate.emit()
        self.button.setCheckable(False)
        QgsMapTool.deactivate(self)

    def isZoomTool(self):
        return False

    def setCursor(self,cursor):
        self.cursor = QCursor(cursor)
