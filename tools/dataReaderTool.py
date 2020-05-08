from qgis.core import *
import qgis
import numpy as np
import platform
from math import sqrt , log10
from .utils import isProfilable

class DataReaderTool:

    """obtiene la informacion de las capas vecoriales y las guarda en un diccionario"""
    def dataReader(self, iface1,tool1, profile1, pointstoDraw1, res):

        self.tool = tool1                   # Necesario para transformar coordenadas de puntos.
        self.profiles = profile1            # Perfil con capa y banda para calcular.
        self.pointstoDraw = pointstoDraw1   # la polilinea a computar
        self.iface = iface1
        layer = profile1["layer"]
        l = []
        z = []
        x = []
        y = []
        try:
            if len(pointstoDraw1) >= 2:
                x, y, l = self.getCoordinates(x, y, l, res)
                if layer.type() == qgis.core.QgsMapLayer.RasterLayer:
                    z = self._extractZValues(x, y)                          #extrae valores de altura del raster cargado
                elif layer.type() == qgis.core.QgsMapLayer.VectorLayer:
                    newlayer = self.createBuffer(layer, pointstoDraw1)      #crea una capa vectorial temporal para optimizar los calculos
                    z = self.extract(x, y, newlayer)                        #extrae informacion de altura de la capa vectorial de edificios
                    QgsProject.instance().removeMapLayer(newlayer)          #borra la capa
                    del newlayer
        except:
            pass

        self.profiles["l"] = l
        self.profiles["z"] = z
        self.profiles["x"] = x
        self.profiles["y"] = y
        return self.profiles

    """devuelve listas de coordenadas x,y de cada punto a lo largo de un perfil"""
    def getCoordinates(self, x,y, l, res):

        lbefore = 0
        first_segment = True
        for p_start, p_end in zip(self.pointstoDraw[:-1],self.pointstoDraw[1:]):
            x1D = float(p_start[0])
            y1D = float(p_start[1])
            x2D = float(p_end[0])
            y2D = float(p_end[1])
            # lenght between (x1,y1) and (x2,y2)
            tlC = sqrt(((x2D - x1D) * (x2D - x1D)) + ((y2D - y1D) * (y2D - y1D)))
            steps = int(tlC / res)
            steps = min(steps, 1000)
            # calculate dx, dy and dl for one step
            dxD = (x2D - x1D) / steps
            dyD = (y2D - y1D) / steps
            dlD = sqrt((dxD * dxD) + (dyD * dyD))
            # reading data
            if first_segment:
                debut = 0
                first_segment = False
            else:
                debut = 1
            for n in range(debut, steps + 1):
                xC = x1D + dxD * n
                yC = y1D + dyD * n
                lD = dlD * n + lbefore
                x.append(xC)  # valores del eje  x por cada paso
                y.append(yC)  # valores del eje  y por cada paso
                l.append(lD)  # valores de la distancia de cada paso sumado el anterior
            lbefore = l[-1]
        return x,y,l

    """crea una capa vectorial temporal con informacion filtrada de la capa vectorial cargada"""
    def createBuffer(self, layer, pointstoDraw1):
        destCrs = layer.crs()
        # sourceCrs = iface1.mapCanvas().mapSettings().destinationCrs()
        geom = qgis.core.QgsGeometry.fromPolylineXY([QgsPointXY(point[0], point[1]) for point in pointstoDraw1])
        buffergeom = geom.buffer(0.1, 1)                                                                 #crea un buffer del tamaño de la distancia entre los dos puntos
        featsPnt = list(layer.getFeatures(QgsFeatureRequest().setFilterRect(buffergeom.boundingBox())))  #lee unicamente la informacion entre los dos puntos
        #crea una nueva capa vectorial con la informacion filtrada para optimizar calculos
        fields = layer.fields()
        uri = "MultiPolygon?crs=" + destCrs.authid()
        newlayer = QgsVectorLayer(uri, "temp", "memory")
        pr = newlayer.dataProvider()
        pr.addAttributes(fields)
        newlayer.updateFields()
        pr.addFeatures(featsPnt)
        newlayer.updateExtents()
        QgsProject.instance().addMapLayer(newlayer, False)
        return newlayer

    """Funcion que obtiene informacion de altura de los edificios de la capa vectorial para cada punto a lo largo del perfil trazado"""
    def extract(self,x,y,layer):
        z=[]
        choosenBand = self.profiles["band"]
        geom = [QgsGeometry.fromPointXY(QgsPointXY(point[0], point[1])) for point in zip(x,y)]
        feats = [list(layer.getFeatures(QgsFeatureRequest().setFilterRect(geometry.boundingBox()))) for geometry in geom]
        for n in feats:
            numero_pis = 0
            if len(n) > 0:
                numero_pis = n[0].attribute(choosenBand)
            z.append(numero_pis)
        return z

    def _status_update(self, advancement_pct):
        """Send a progress message to status bar.
        advancement_pct is the advancemente in percentage (from 0 to 100).
        """
        if advancement_pct % 10 == 0:
            progress = "Creating profile: " + "|" * (advancement_pct//10)
            self.iface.mainWindow().statusBar().showMessage(progress)

    """Funcion que obtiene informacion de altura de la capa raster para cada punto a lo largo del perfil trazado"""
    def _extractZValues(self, x, y):

        layer = self.profiles["layer"]
        choosenBand = self.profiles["band"]
        z = []
        for n, coords in enumerate(zip(x, y)):
            ident = layer.dataProvider().identify(QgsPointXY(*coords), QgsRaster.IdentifyFormatValue)
            if ident is not None and (choosenBand in ident.results()):
                attr = ident.results()[choosenBand]
            else:
                attr = 0
            z.append(attr)
        return z