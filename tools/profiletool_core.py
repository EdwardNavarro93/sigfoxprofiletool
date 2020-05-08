#Qt import
from qgis.PyQt import uic, QtCore, QtGui
try:
    from qgis.PyQt.QtGui import QWidget
except:
    from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.QtSvg import *
#qgis import
import qgis
from qgis.core import *
from qgis.gui import *
#other
import platform
import sys
from math import sqrt
import numpy as np
#plugin import
from .dataReaderTool import DataReaderTool
from .plottingtool import PlottingTool
from .ptmaptool import ProfiletoolMapTool, ProfiletoolMapToolRenderer
from ..ui.ptdockwidget import PTDockWidget
from . import profilers

class ProfileToolCore(QWidget):

    def __init__(self, iface,plugincore, parent = None):
        QWidget.__init__(self, parent)
        self.iface = iface
        self.plugincore = plugincore
        if QtCore.QSettings().value("sigfoxprofiletool/lastdirectory") != '':                 #recordar repositorio para guardar
            self.loaddirectory = QtCore.QSettings().value("sigfoxprofiletool/lastdirectory")
        else:
            self.loaddirectory = ''
        self.doTracking = False         #variable necesaria para el seguimiento del mouse
        self.profiles = None            #diccionario donde se guardan los datos de trazado del perfil
        self.pointstoDraw = []          #variable donde se almacena las coordenadas proyectadas en m del Tx y Rx
        self.toolrenderer = None        #renderizador para la polilínea temporal.
        self.saveTool = None            #guarda las herramientas del mapa
        self.previousLayerId = None
        self.x_cursor = None            #Mantiene un registro de la última posición x del cursor
        #the dockwidget
        self.dockwidget = PTDockWidget(self.iface,self) #proporciona un widget general que se puede acoplar dentro de la pantalla principal del mapa de Qgis
        self.dockwidget.changePlotLibrary()


    """funcion que activa las herramientas de perfil"""
    def activateProfileMapTool(self):
        self.saveTool = self.iface.mapCanvas().mapTool()
        #acciones del mouse
        self.toolrenderer = ProfiletoolMapToolRenderer(self)        #inicializa la herramienta en el mapa y espera acciones sobre el
        self.toolrenderer.connectTool()                             #conecta la acciones sobre el mapa
        self.toolrenderer.setSelectionMethod()
        self.iface.mapCanvas().setMapTool(self.toolrenderer.tool)

    # ******************************************************************************************
    # **************************** function part *************************************************
    # ******************************************************************************************

    def clearProfil(self):
        self.updateProfilFromFeatures(None, [])

    def updateProfilFromFeatures(self, layer, features, plotProfil=True):

        pointstoDraw = []
        previousLayer = QgsProject.instance().mapLayer(self.previousLayerId)

        if previousLayer:
            previousLayer.removeSelection()

        if layer:
            self.previousLayerId = layer.id()
        else:
            self.previousLayerId = None

        if layer:
            layer.removeSelection()
            layer.select([f.id() for f in features])
            first_segment = True
            for feature in features:
                if first_segment:
                    k = 0
                    first_segment = False
                else:
                    k = 1
                while not feature.geometry().vertexAt(k) == QgsPoint(0,0):
                    point2 = self.toolrenderer.tool.toMapCoordinates( layer, QgsPointXY(feature.geometry().vertexAt(k)))
                    pointstoDraw += [[point2.x(),point2.y()]]
                    k += 1
        self.updateProfil(pointstoDraw, False, plotProfil)

    """Funcion que permite obtener los datos topograficos de las capas cargadas para graficar el perfil del terreno"""
    def updateProfil(self, points1, removeSelection=True, plotProfil=True):

        if removeSelection:
            previousLayer = QgsProject.instance().mapLayer(self.previousLayerId)
            if previousLayer:
                previousLayer.removeSelection()

        self.config=self.dockwidget.config
        self.pointstoDraw = points1                         #coordenadas del Tx y Rx
        self.profiles = []                                  #variable que almacena el perfil
        #calculo del perfil topografico
        self.cont= self.dockwidget.mdl.rowCount()           #verifica cuantas capas hay cargadas en la tabla
        res_urban= self.config["Urban_res"]                 #resolucion en metros con la que se toman muestras del perfil urbano

        for i in range(0, self.cont):                       #crea un perfil para cada fila de la tabla donde se cargan las capas

            self.profiles.append({"layer": self.dockwidget.mdl.item(i, 5).data(QtCore.Qt.EditRole)})
            self.profiles[i]["band"] = self.dockwidget.mdl.item(i, 3).data(QtCore.Qt.EditRole)

            if self.dockwidget.mdl.item(i, 5).data(QtCore.Qt.EditRole).type() == qgis.core.QgsMapLayer.RasterLayer:     # verifica si es una capa raster valida
                res = self.profiles[i]["layer"].rasterUnitsPerPixelX()                                                  #si solo se tiene la capa raster la toma de muestras es del mismo tamaño de las celdas de la capa
                if self.cont>=2:
                    res=res_urban                                                                                       #si se agrega la capa vectorial la resolucion sera la ingresada por el usuario
                self.profiles[i] = DataReaderTool().dataReader(self.iface, self.toolrenderer.tool, self.profiles[i],self.pointstoDraw, res)  # realiza el calculo del perfil
            elif self.dockwidget.mdl.item(i, 5).data(QtCore.Qt.EditRole).type() == qgis.core.QgsMapLayer.VectorLayer:
                res = res_urban
                self.profiles[i] = DataReaderTool().dataReader(self.iface, self.toolrenderer.tool, self.profiles[i],self.pointstoDraw, res)
        if plotProfil:
            self.plotProfil()

    """funcion que permite graficar el perfil del terreno"""
    def plotProfil(self):

        if self.profiles == None:
            return

        self.disableMouseCoordonates()
        self.clearLabels()
        self.removeClosedLayers(self.dockwidget.mdl)
        PlottingTool().clearData(self.dockwidget, self.profiles, self.dockwidget.plotlibrary)
        PlottingTool().attachCurves(self.dockwidget, self.profiles, self.dockwidget.mdl, self.cont,self.config)  #crea las graficas de perfil
        PlottingTool().reScalePlot(self.dockwidget, self.profiles, self.dockwidget.plotlibrary)                  #escala automaticamente la grafica
        #Mouse tracking
        self.updateCursorOnMap(self.x_cursor)
        self.enableMouseCoordonates(self.dockwidget.plotlibrary)

    def updateCursorOnMap(self, x):
        self.x_cursor = x
        if self.pointstoDraw:
            if x is not None:
                points = [QgsPointXY(*p) for p in self.pointstoDraw]
                geom =  qgis.core.QgsGeometry.fromPolylineXY(points)
                try:
                    if len(points) > 1:
                        try:
                            pointprojected = geom.interpolate(x).asPoint()
                        except:
                            pointprojected = None
                    else:
                        pointprojected = points[0]
                except (IndexError, AttributeError):
                    pointprojected = None
                
                if pointprojected:
                    self.toolrenderer.rubberbandpoint.setCenter(
                        pointprojected)
            self.toolrenderer.rubberbandpoint.show()
        else:
            self.toolrenderer.rubberbandpoint.hide()

    # remove layers which were removed from QGIS
    def removeClosedLayers(self, model1):
        qgisLayerNames = []
        if int(QtCore.QT_VERSION_STR[0]) == 4 :    #qgis2
            qgisLayerNames = [  layer.name()    for layer in self.iface.legendInterface().layers()]

        elif int(QtCore.QT_VERSION_STR[0]) == 5 :    #qgis3
            qgisLayerNames = [  layer.name()    for layer in qgis.core.QgsProject.instance().mapLayers().values()]

        for i in range(0 , model1.rowCount()):
            layerName = model1.item(i,2).data(QtCore.Qt.EditRole)
            if not layerName in qgisLayerNames:
                self.dockwidget.removeLayer(i)
                self.removeClosedLayers(model1)
                break

    def cleaning(self):
        self.clearProfil()
        if self.toolrenderer:
            self.toolrenderer.cleaning()

    def clearLabels(self):
        self.dockwidget.lossPropagationlabel.clear()
        self.dockwidget.Obstaculeslabel.clear()
        self.dockwidget.Difractionlabel.clear()
        self.dockwidget.receptionLosslabel.clear()
        self.dockwidget.linkBudgetText.clear()
        self.dockwidget.indoorlabel.clear()

    #******************************************************************************************
    #**************************** mouse interaction *******************************************
    #******************************************************************************************

    def activateMouseTracking(self,int1):
        if self.dockwidget.TYPE == 'PyQtGraph':

            if int1 == 2 :
                self.doTracking = True
            elif int1 == 0 :
                self.doTracking = False

    def enableMouseCoordonates(self,library):
        if library == "PyQtGraph":
            self.dockwidget.plotWdg.scene().sigMouseMoved.connect(self.mouseMovedPyQtGraph)
            self.dockwidget.plotWdg.getViewBox().autoRange( items=self.dockwidget.plotWdg.getPlotItem().listDataItems())
            #self.dockwidget.plotWdg.getViewBox().sigRangeChanged.connect(self.dockwidget.plotRangechanged)
            self.dockwidget.connectPlotRangechanged()

    def disableMouseCoordonates(self):
        try:
            self.dockwidget.plotWdg.scene().sigMouseMoved.disconnect(self.mouseMovedPyQtGraph)
        except:
            pass

        self.dockwidget.disconnectPlotRangechanged()


    def mouseMovedPyQtGraph(self, pos): # si connexion directe du signal "mouseMoved" : la fonction reçoit le point courant
            roundvalue = 3

            if self.dockwidget.plotWdg.sceneBoundingRect().contains(pos): # si le point est dans la zone courante

                if self.dockwidget.showcursor :
                    range = self.dockwidget.plotWdg.getViewBox().viewRange()
                    mousePoint = self.dockwidget.plotWdg.getViewBox().mapSceneToView(pos) # récupère le point souris à partir ViewBox

                    datas = []
                    pitems = self.dockwidget.plotWdg.getPlotItem()
                    ytoplot = None
                    xtoplot = None

                    if len(pitems.listDataItems())>0:
                        #get data and nearest xy from cursor
                        compt = 0
                        try:
                            for  item in pitems.listDataItems():
                                if item.isVisible() :
                                    x,y = item.getData()
                                    nearestindex = np.argmin( abs(np.array(x)-mousePoint.x()) )
                                    if compt == 0:
                                        xtoplot = np.array(x)[nearestindex]
                                        ytoplot = np.array(y)[nearestindex]
                                    else:
                                        if abs( np.array(y)[nearestindex] - mousePoint.y() ) < abs( ytoplot -  mousePoint.y() ):
                                            ytoplot = np.array(y)[nearestindex]
                                            xtoplot = np.array(x)[nearestindex]
                                    compt += 1
                        except ValueError:
                            ytoplot = None
                            xtoplot = None
                        #plot xy label and cursor
                        if not xtoplot is None and not ytoplot is None:
                            for item in self.dockwidget.plotWdg.allChildItems():
                                if str(type(item)) == "<class 'sigfoxprofiletool.pyqtgraph.graphicsItems.InfiniteLine.InfiniteLine'>":
                                    if item.name() == 'cross_vertical':
                                        item.show()
                                        item.setPos(xtoplot)
                                    elif item.name() == 'cross_horizontal':
                                        item.show()
                                        item.setPos(ytoplot)
                                elif str(type(item)) == "<class 'sigfoxprofiletool.pyqtgraph.graphicsItems.TextItem.TextItem'>":
                                    if item.textItem.toPlainText()[0] == 'X':
                                        item.show()
                                        item.setText('X : '+str(round(xtoplot,roundvalue)))
                                        item.setPos(xtoplot,range[1][0] )
                                    elif item.textItem.toPlainText()[0] == 'Y':
                                        item.show()
                                        item.setText('Y : '+str(round(ytoplot,roundvalue)))
                                        item.setPos(range[0][0],ytoplot )
                    #tracking part
                    self.updateCursorOnMap(xtoplot)