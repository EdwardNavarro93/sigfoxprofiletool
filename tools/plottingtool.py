import os
from qgis.core import *
from qgis.gui import *
import qgis
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtSvg import *
try:
    from qgis.PyQt.QtWidgets import *
except:
    pass
import platform
import numpy as np
from math import atan2, log10, exp, atan, pi, sqrt, cos, sin, acos
from cmath import phase
from shapely.geometry import Point, LineString, Polygon
from shapely.affinity import scale, rotate
from .. import pyqtgraph as pg
from ..pyqtgraph import exporters
pg.setConfigOption('background', 'w')
from .. import dxfwrite
from ..dxfwrite import DXFEngine as dxf
has_qwt = False
has_mpl = False
try:
    from PyQt4.Qwt5 import *
    has_qwt = True
    import itertools # only needed for Qwt plot
except:
    pass
try:
    from matplotlib import *
    import matplotlib
    has_mpl = True
except:
    pass

from .radioplanningtool import RadioPlanningTool

class PlottingTool:

    """define la libreria a utilizar para el grafico y sus atributos"""
    def changePlotWidget(self, library, frame_for_plot):

        if library == "PyQtGraph":
            plotWdg = pg.PlotWidget() #usa la libreria para mejorar visualmente el widget para graficar los perfiles
            plotWdg.showGrid(True,True,0.9) #muestra la grilla al iniciar el plugin
            datavline = pg.InfiniteLine(0, angle=90 ,pen=pg.mkPen('r',  width=1) , name = 'cross_vertical' ) # crea una lina amarilla vertical al iniciar el plugin
            datahline = pg.InfiniteLine(0, angle=0 , pen=pg.mkPen('r',  width=1) , name = 'cross_horizontal') #crea una lina azul horizontal al iniciar el plugin
            plotWdg.addItem(datavline) #agrega las lineas
            plotWdg.addItem(datahline)
            # caracteristicas del cursor
            xtextitem = pg.TextItem('X : /', color = (0,0,0), border = pg.mkPen(color=(0, 0, 0),  width=1), fill=pg.mkBrush('w'), anchor=(0,1))
            ytextitem = pg.TextItem('Y : / ', color = (0,0,0) , border = pg.mkPen(color=(0, 0, 0),  width=1), fill=pg.mkBrush('w'), anchor=(0,0))
            plotWdg.addItem(xtextitem)
            plotWdg.addItem(ytextitem)
            # el rango y color del borde del widget
            plotWdg.getViewBox().autoRange( items=[])
            plotWdg.getViewBox().disableAutoRange()
            plotWdg.getViewBox().border = pg.mkPen(color=(0, 0, 0),  width=1)
            return plotWdg

    def drawVertLine(self,wdg, pointstoDraw, library):
        if library == "PyQtGraph":
            pass

    """grafica el perfil"""
    def attachCurves(self, wdg, profiles, model1, contador, conf):
        alt_pis = conf["heigth_floor"]                          #altura asignada para cada piso en metros
        k = conf["K"]                                           #factor k para los calculos
        h_device = conf["height_device"]                        #altura del Tx sobre la cota
        h_antenna_BS = conf["height_BS"]                        #altura del RX sobre la cota
        L_indoor = conf["Indoor_Loss"]                          #perdidas indoor
        Lm = conf["Miscelaneous_loss"]                          #perdidas miscelaneas
        link = conf["link"]                                     #modo de calculo UL/DL
        model = conf["Model"]["id"]                             #el modelo de propagacion escogido
        radioPlanningTool = RadioPlanningTool(conf)
        #Er=15 y sigma=0.012 para tierra seca
        #pol=1               #polarizacion: 1 pol vertical, 2 pol horizontal

        if len(profiles)>0:
            x = np.array(profiles[0]["l"])                                              # convierte en array los valores de x para usar la libreria numpy

            if len(x) > 0:
                if contador == 1:
                    y = np.array(profiles[0]["z"], dtype=np.float)                      # convierte en array los valores de y para usar la libreria numpy
                    if profiles[0]["layer"].type() == qgis.core.QgsMapLayer.RasterLayer:

                        color = (9, 138, 5)  # grafica el perfil del terreno con color verde
                        L_indoor = 0
                        h = 0
                        h_BS = h_antenna_BS  # en el caaso rural la altura de la BS  es la misma altura de la antena

                        if link == "UL":
                            A = Point(x[0], y[0] + h_device)
                            B= Point(x[-1], y[-1]+ h_antenna_BS)
                        else:
                            A = Point(x[0], y[0] + h_antenna_BS)
                            B = Point(x[-1], y[-1] +h_device)

                    elif profiles[0]["layer"].type() == qgis.core.QgsMapLayer.VectorLayer:
                        y = y * alt_pis
                        color=(25, 9, 165)                                          # grafica perfil de edificios con color azul
                        h = np.average(y[np.where(y > 0)])                          # calcula la altura promedio de edificios

                        if link == "UL":
                            A = Point(x[0], h_device)
                            B = Point(x[-1], y[-1] + h_antenna_BS)
                            if y[0] == 0:
                                L_indoor = 0
                            y[0] = 0  # elimina el primer edificio
                            h_BS = y[-1] + h_antenna_BS  # altura de la antena mas la altura del edificio
                        else:
                            A = Point(x[0], y[0] + h_antenna_BS)
                            B = Point(x[-1], h_device)
                            if y[-1] == 0:
                                L_indoor = 0
                            y[-1] = 0  # elimina el ultimo edificio
                            h_BS = y[0] + h_antenna_BS  # altura de la antena mas la altura del edificio

                    flecha = radioPlanningTool.protuber_of_Earth(B, x, k)           # calculo de la protuberancia de la tierra
                    y = flecha + y                                                  # correccion de alturas de obstaculos
                    wdg.plotWdg.plot(x, y, pen=pg.mkPen(color=color, width=3))      # calculo de perfil para una sola capa cargada

                elif contador == 2:
                    if profiles[0]["layer"].type() == qgis.core.QgsMapLayer.RasterLayer:
                        yraster = np.array(profiles[0]["z"], dtype=np.float)                    # altura del terreno
                        yvector = np.array(profiles[1]["z"], dtype=np.float) * alt_pis          # altura de edificios
                    elif profiles[0]["layer"].type() == qgis.core.QgsMapLayer.VectorLayer:
                        yvector = np.array(profiles[0]["z"], dtype=np.float) * alt_pis          # altura de edificios
                        yraster = np.array(profiles[1]["z"], dtype=np.float)                    # altura del terreno

                    h = np.average(yvector[np.where(yvector > 0)])  # altura promedio de edificios
                    y = yraster + yvector  # suma de alturas

                    if link == "UL":
                        A = Point(x[0], yraster[0] + h_device)
                        B = Point(x[-1], y[-1] + h_antenna_BS)
                        if yvector[0] == 0:
                            L_indoor = 0
                        yvector[0] = 0  # elimina el ultimo edificio
                        h_BS = yvector[-1] + h_antenna_BS  # altura de la antena mas la altura del edificio

                    else:
                        A = Point(x[0], y[0] + h_antenna_BS)                            # punto inicial del perfil donde se encuentra la BS
                        B = Point(x[-1], yraster[-1] + h_device)                        # punto final del perfil donde se encuentra el dispositivo
                        if yvector[-1] == 0:
                            L_indoor = 0
                        yvector[-1] = 0  # elimina el ultimo edificio
                        h_BS = yvector[0] + h_antenna_BS  # altura de la antena mas la altura del edificio

                    flecha = radioPlanningTool.protuber_of_Earth(B, x, k)           # calculo de la protuberancia de la tierra
                    yraster= yraster + flecha                                       # correccion de alturas de obstaculos
                    y = yraster + yvector
                    wdg.plotWdg.plot(x, y, pen=pg.mkPen(color=(25, 9, 165), width=2.5))       # grafica el perfil de terreno mas edificios color azul
                    wdg.plotWdg.plot(x, yraster, pen=pg.mkPen(color=(9, 138, 5), width=3))    # grafica el perfil de terreno color verde

                # Lb = self.reflexionLoss(Er,sigma, height_Tx, height_Rx, (B.x) / 1000, flecha, k,pol)  # metodo de dos rayos para tierra plana y curva
                Dkm = (radioPlanningTool.distanceBetweenPoint(A, B))/1000                   # distancia entre Tx y Rx en Km
                f_x, f_y = radioPlanningTool.fresnelZone(A, B)                              # 60% de la zona fresnel
                Los = radioPlanningTool.straightBetweenTwoPoints(A, B, x)                   # LOS entre la BS y el dispositivo
                Ldifr, numobstacules = radioPlanningTool.difractionLoss(A, B, x, y, Los)    # calcula las perdidas por difraccion a lo largo del radioenlace
                wdg.plotWdg.plot(f_x, f_y, pen=pg.mkPen('r', width=2))                      # grafica la elipse de fresnel (rojo)
                wdg.plotWdg.plot(x, Los, pen=pg.mkPen('k', width=2))                        # grafica LOS (negro)

                L, L_model_difr = radioPlanningTool.chooseModel(h_BS, Dkm, Ldifr, h)       #perdidas basicas de propagacion segun el modelo

                if model ==7 or model == 8:                                          #para wwalfish ikegami y xia beroni la difraccion es diferente
                    Ldifr = L_model_difr
                L_total = L+Ldifr + L_indoor + Lm                                    #perdidas totales de propagacion
                Prx = radioPlanningTool.linkBudget(L_total)                          #potencia recibida en la BS
                self.printLabels(wdg, Prx, L, numobstacules, Ldifr, L_indoor, conf)
                self.commonResults(wdg, Dkm, numobstacules, Ldifr, L_indoor, conf)
                if link == "UL":
                    self.printULResults(wdg, L, L_total, Prx, conf)
                else:
                    self.printDLResults(wdg, L, L_total, Prx, conf)
        else:
            pass

    """imprime los resultados obtenidos en un widget de texto"""
    def commonResults(self, wdg, Dkm, numobstacules, Ldifr, L_indoor, conf):
        plainTxt = "Radio Link Information: \n \n" \
                   "Distance between BS and the IoT Device: {0} Km. \n" \
                   "Propagation loss model: {1}. \n".format(str(np.round(Dkm, 2)), conf["Model"]["name"])
        try:
            plainTxt= plainTxt + "Model escenario: {0} {1}. \n".format(conf["Model"]["name"], conf["Model"]["scenario"])

        except:
            pass

        try:
            plainTxt= plainTxt + "Model category: {0} {1}. \n".format(conf["Model"]["name"], conf["Model"]["category"])
        except:
            pass

        try:
            if conf["Model"]["id"]==3 and conf["Model"]["scenario"]=="Rural": #Okumura hata escenario urbano
                pass
            elif conf["Model"]["id"]==3 and conf["Model"]["scenario"]=="Sub Urban":
                pass
            else:
                plainTxt = plainTxt + "Model city: {0} {1}. \n".format(conf["Model"]["name"], conf["Model"]["city"])
        except:
            pass

        plainTxt= plainTxt + "Number of obstacles in the Radio Link: {0}. \n" \
                             "Difraction Loss: {1} dB.\n" \
                             "Indoor Loss: {2} dB.\n" \
                             "Miscellaneous loss: {3} dB.\n \n".format(str(numobstacules), str(np.round(Ldifr, 2)), str(np.round(L_indoor,2)), conf["Miscelaneous_loss"])
        wdg.linkBudgetText.insertPlainText(plainTxt)

    """imprime los resultados mas importantes en los labels principales del docwidget"""
    def printLabels(self, wdg, Prx, L, numobstacules, Ldifr, L_indoor, conf):

        wdg.receptionLosslabel.setText("Received Power: " + str(np.round(Prx, 2))+" dBm")
        wdg.lossPropagationlabel.setText(conf["Model"]["name"] + " Loss: " + str(np.round(L, 2))+" dB")
        wdg.Obstaculeslabel.setText("Number of Obstacles: " + str(numobstacules))
        wdg.Difractionlabel.setText("Difraction Loss: " + str(np.round(Ldifr, 2)) +" dB")
        wdg.indoorlabel.setText("Indoor Loss: " + str(np.round(L_indoor,2)) + " dB")

    """imprime resultados del enlace ascendente UL"""
    def printULResults(self, wdg, L, L_total, Prx, conf):

        EIRP= str(np.round((conf["Ptx_device"] + conf["G_device"] - conf["cable_Loss_device"]), 2))
        gain= str(np.round((conf["G_BS"] - conf["cable_Loss_BS"]), 2))
        pathloss= str(np.round(L, 2))
        ltotal=str(np.round(L_total, 2))
        Prx=str(np.round(Prx, 2))
        plainTxt= "UpLink Information: \n \n" \
                  "Frequency: {0} MHz.\n" \
                  "Power of Transmission of the IoT Device: {1} dBm.\n" \
                  "EIRP: {2} dBm.\n"\
                  "Reception Gain: {3} dB.\n"\
                  "Path Loss: {4} dB.\n"\
                  "Total Loss: {5} dB.\n"\
                  "Power of Recepcion in BS: {6} dBm.\n \n".format(str(conf["frequency"]), str(np.round(conf["Ptx_device"], 2)), EIRP, gain,
                                                                 pathloss, ltotal, Prx)
        wdg.linkBudgetText.insertPlainText(plainTxt)

    """imprime resultados del enlace descendente DL"""
    def printDLResults(self,wdg, L, L_total, Prx, conf):

        frequency = str(np.round((conf["frequency"] + conf["deltaFrequencyDL"]), 2))
        EIRP = str(np.round((conf["Ptx_BS"] + conf["G_BS"] - conf["cable_Loss_BS"]), 2))
        gain = str(np.round((conf["G_device"] - conf["cable_Loss_device"]), 2))
        pathloss = str(np.round(L, 2))
        ltotal = str(np.round(L_total, 2))
        Prx = str(np.round(Prx, 2))

        plainTxt = "DownLink Information: \n \n" \
                   "Frequency: {0} MHz.\n" \
                   "Power of Transmission of the BS: {1} dBm.\n" \
                   "EIRP: {2} dBm.\n" \
                   "Reception Gain: {3} dB.\n" \
                   "Path Loss: {4} dB.\n" \
                   "Total Loss: {5} dB.\n" \
                   "Power of Recepcion in IoT Device: {6} dBm.\n".format(frequency, str(np.round(conf["Ptx_BS"], 2)), EIRP, gain,
                                                                  pathloss, ltotal, Prx)
        wdg.linkBudgetText.insertPlainText(plainTxt)

    def findMin(self, values):
        minVal = min( z for z in values if z is not None )
        return minVal

    def findMax(self, values):
        maxVal = max( z for z in values if z is not None )
        return maxVal

    def plotRangechanged(self, wdg, library):

        if library == "PyQtGraph":
            range = wdg.plotWdg.getViewBox().viewRange()
            wdg.disconnectYSpinbox()
            wdg.sbMaxVal.setValue(range[1][1])
            wdg.sbMinVal.setValue(range[1][0])
            wdg.connectYSpinbox()

    """escala automaticamente la grafica"""
    def reScalePlot(self, wdg, profiles, library,auto = False):                         # called when spinbox value changed
        if profiles == None:
            return
        minimumValue = wdg.sbMinVal.value()
        maximumValue = wdg.sbMaxVal.value()

        y_vals = [p["z"] for p in profiles]

        if minimumValue == maximumValue:
            # Automatic mode
            minimumValue = 1000000000
            maximumValue = -1000000000
            for i in range(0,len(y_vals)):
                if profiles[i]["layer"] != None and len([z for z in y_vals[i] if z is not None]) > 0:
                    minimumValue = min(self.findMin(y_vals[i]), minimumValue)
                    maximumValue = max(self.findMax(y_vals[i]) + 1,
                                       maximumValue)
                    wdg.sbMaxVal.setValue(maximumValue)
                    wdg.sbMinVal.setValue(minimumValue)
                    wdg.sbMaxVal.setEnabled(True)
                    wdg.sbMinVal.setEnabled(True)

        if minimumValue < maximumValue:
            if library == "PyQtGraph":
                wdg.disconnectPlotRangechanged()
                if auto:
                    wdg.plotWdg.getViewBox().autoRange( items=wdg.plotWdg.getPlotItem().listDataItems())
                    wdg.plotRangechanged()
                else:
                    wdg.plotWdg.getViewBox().setYRange( minimumValue,maximumValue , padding = 0 )
                wdg.connectPlotRangechanged()


    def clearData(self, wdg, profiles, library):                             # erase one of profiles
        if not profiles:
            return

        if library == "PyQtGraph":
            pitems = wdg.plotWdg.getPlotItem().listDataItems()
            for item in pitems:
                wdg.plotWdg.removeItem(item)
            try:
                wdg.plotWdg.scene().sigMouseMoved.disconnect(self.mouseMoved)
            except:
                pass
        wdg.sbMaxVal.setEnabled(False)
        wdg.sbMinVal.setEnabled(False)
        wdg.sbMaxVal.setValue(0)
        wdg.sbMinVal.setValue(0)

    ### no esta implementado
    def changeColor(self,wdg, library, color1, name):                    #Action when clicking the tableview - color

        if library == "PyQtGraph":
            pitems = wdg.plotWdg.getPlotItem()
            for i, item in enumerate(pitems.listDataItems()):
                if item.name() == name:
                    item.setPen( color1,  width=2)

    def changeAttachCurve(self, wdg, library, bool, name):                #Action when clicking the tableview - checkstate
        if library == "PyQtGraph":
            pitems = wdg.plotWdg.getPlotItem()
            for i, item in enumerate(pitems.listDataItems()):
                if item.name() == name:
                    if bool:
                        item.setVisible(True)
                    else:
                        item.setVisible(False)

    def manageMatplotlibAxe(self, axe1):
        axe1.grid()
        axe1.tick_params(axis = "both", which = "major", direction= "out", length=10, width=1, bottom = True, top = False, left = True, right = False)
        axe1.minorticks_on()
        axe1.tick_params(axis = "both", which = "minor", direction= "out", length=5, width=1, bottom = True, top = False, left = True, right = False)


    def outPrint(self, iface, wdg, mdl, library): # Postscript file rendering doesn't work properly yet.
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i,0).data(Qt.CheckStateRole):
                name = str(mdl.item(i,2).data(Qt.EditRole))
                #return
        fileName = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As","Profile of " + name + ".ps","PostScript Format (*.ps)")
        if fileName:
            if library == "Qwt5" and has_qwt:
                printer = QPrinter()
                printer.setCreator("QGIS Profile Plugin")
                printer.setDocName("QGIS Profile")
                printer.setOutputFileName(fileName)
                printer.setColorMode(QPrinter.Color)
                printer.setOrientation(QPrinter.Portrait)
                dialog = QPrintDialog(printer)
                if dialog.exec_():
                    wdg.plotWdg.print_(printer)
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))


    def outPDF(self, iface, wdg, mdl, library):
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i,0).data(Qt.CheckStateRole):
                name = str(mdl.item(i,2).data(Qt.EditRole))
                break
        fileName = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As","Profile of " + name + ".pdf","Portable Document Format (*.pdf)")
        if fileName:
            if library == "Qwt5" and has_qwt:
                printer = QPrinter()
                printer.setCreator('QGIS Profile Plugin')
                printer.setOutputFileName(fileName)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOrientation(QPrinter.Landscape)
                wdg.plotWdg.print_(printer)
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))


    def outSVG(self, iface, wdg, mdl, library):
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i,0).data(Qt.CheckStateRole):
                name = str(mdl.item(i,2).data(Qt.EditRole))
                #return
        fileName = QFileDialog.getSaveFileName(parent = iface.mainWindow(),
                                               caption = "Save As",
                                               directory = wdg.profiletoolcore.loaddirectory,
                                               #filter = "Profile of " + name + ".png",
                                               filter = "Scalable Vector Graphics (*.svg)")


        if fileName:
            if isinstance(fileName,tuple):  #pyqt5 case
                fileName = fileName[0]

            wdg.profiletoolcore.loaddirectory = os.path.dirname(fileName)
            qgis.PyQt.QtCore.QSettings().setValue("sigfoxprofiletool/lastdirectory", wdg.profiletoolcore.loaddirectory)

            if library == "PyQtGraph":
                exporter = exporters.SVGExporter(wdg.plotWdg.getPlotItem().scene())
                #exporter =  pg.exporters.ImageExporter(wdg.plotWdg.getPlotItem()
                exporter.export(fileName = fileName)

            elif library == "Qwt5" and has_qwt:
                printer = QSvgGenerator()
                printer.setFileName(fileName)
                printer.setSize(QSize(800, 400))
                wdg.plotWdg.print_(printer)
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))

    def outPNG(self, iface, wdg, mdl, library):
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i,0).data(Qt.CheckStateRole):
                name = str(mdl.item(i,2).data(Qt.EditRole))
                #return
        fileName = QFileDialog.getSaveFileName(parent = iface.mainWindow(),
                                               caption = "Save As",
                                               directory = wdg.profiletoolcore.loaddirectory,
                                               #filter = "Profile of " + name + ".png",
                                               filter = "Portable Network Graphics (*.png)")

        if fileName:

            if isinstance(fileName,tuple):  #pyqt5 case
                fileName = fileName[0]

            wdg.profiletoolcore.loaddirectory = os.path.dirname(fileName)
            qgis.PyQt.QtCore.QSettings().setValue("sigfoxprofiletool/lastdirectory", wdg.profiletoolcore.loaddirectory)

            if library == "PyQtGraph":
                exporter =  exporters.ImageExporter(wdg.plotWdg.getPlotItem())
                exporter.export(fileName)
            elif library == "Qwt5" and has_qwt:
                QPixmap.grabWidget(wdg.plotWdg).save(fileName, "PNG")
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))

    def outDXF(self, iface, wdg, mdl, library, profiles):

        for i in range (0,mdl.rowCount()):
            if  mdl.item(i,0).data(Qt.CheckStateRole):
                name = str(mdl.item(i,2).data(Qt.EditRole))
                #return
        #fileName = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As",wdg.profiletoolcore.loaddirectory,"Profile of " + name + ".dxf","dxf (*.dxf)")
        fileName = QFileDialog.getSaveFileName(parent = iface.mainWindow(),
                                               caption = "Save As",
                                               directory = wdg.profiletoolcore.loaddirectory,
                                               #filter = "Profile of " + name + ".png",
                                               filter = "dxf (*.dxf)")
        if fileName:
            if isinstance(fileName,tuple):  #pyqt5 case
                fileName = fileName[0]

            wdg.profiletoolcore.loaddirectory = os.path.dirname(fileName)
            qgis.PyQt.QtCore.QSettings().setValue("sigfoxprofiletool/lastdirectory", wdg.profiletoolcore.loaddirectory)

            drawing = dxf.drawing(fileName)
            for profile in profiles:
                name = profile['layer'].name()
                drawing.add_layer(name)
                points = [(profile['x'][i], profile['y'][i],profile['z'][i]) for i in range(len(profile['l']))]
                drawing.add(dxf.polyline(points, color=7, layer=name))
            drawing.save()
