#Qt import
from qgis.PyQt import uic, QtCore, QtGui
try:
    from qgis.PyQt.QtGui import QDockWidget
except:
    from qgis.PyQt.QtWidgets import QDockWidget, QMessageBox
#qgis import
from qgis.core import *
from qgis.gui import *
#other
import platform
import os
#plugin import
from ..tools.plottingtool import *
from ..tools.tableviewtool import TableViewTool
try:
    from PyQt4.Qwt5 import *
    Qwt5_loaded = True
except ImportError:
    Qwt5_loaded = False
try:
    from matplotlib import *
    import matplotlib
    matplotlib_loaded = True
except ImportError:
    matplotlib_loaded = False


uiFilePath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'profiletool.ui')) #direccion donde esta almacenado el widget
FormClass = uic.loadUiType(uiFilePath)[0]

class PTDockWidget(QDockWidget, FormClass):

    TITLE = " WND Profile Tool"
    TYPE = None
    closed = QtCore.pyqtSignal()

    def __init__(self, iface1, profiletoolcore, parent=None):


        self.models={"0":{"id":0,"name":"Free Space"},
                     "1":{"id":1,"name":"Egli"},
                     "2":{"id":2,"name": "Lee", "scenario":"Free Space"},
                     "3":{"id":3,"name":"Okumura Hata", "scenario":"Urban", "city":"Middle City"},
                     "4":{"id":4,"name":"Erceg Sui", "category":"C"},
                     "5":{"id":5,"name":"Ecc-33", "city": "Middle City"},
                     "6":{"id":6,"name":"Ericcson", "scenario":"Sub Urban"},
                     "7":{"id":7,"name":"Walfish Ikegami", "city":"Middle City"},
                     "8":{"id":8,"name":"Xia Bertoni"}
                    }

        #Configuracion inicial
        self.config = {"frequency": 920.8, "height_BS": 20, "Ptx_BS":32, "G_BS": 5, "cable_Loss_BS":2, "sensitivity_BS":-134,
                       "height_device": 1.5,   "Ptx_device":20,  "G_device":2, "cable_Loss_device":2,
                        "deltaFrequencyDL":1.5, "K":1.333, "Indoor_Loss":15, "Miscelaneous_loss":0, "Urban_res":10, "heigth_floor":2.5, "Model": self.models["0"], "link":"UL"}
        QDockWidget.__init__(self, parent)
        self.setupUi(self)
        self.profiletoolcore = profiletoolcore
        self.iface = iface1
        #Apariencia del widget
        self.location = QtCore.Qt.BottomDockWidgetArea  #Fija el dockwidget en la parte inferior de la pantalla
        minsize = self.minimumSize()
        maxsize = self.maximumSize()
        self.setMinimumSize(minsize)                    #Crea el tamaño minimo del dockwidget automaticamente/ se puede cambiar aqui
        self.setMaximumSize(maxsize)                    #Crea el tamaño maximo del dockwidget automaticamente/ se puede cambiar aqui
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        #Inicializa las escalas donde se grafica el perfil
        self.sbMaxVal.setValue(0)
        self.sbMinVal.setValue(0)
        self.sbMaxVal.setEnabled(False)
        self.sbMinVal.setEnabled(False)

        #Configuracion inicial
        self.height_BS.setValue(self.config["height_BS"])
        self.height_device.setValue(self.config["height_device"])
        self.Ptxdevice.setValue(self.config["Ptx_device"])
        self.frequency.setValue(self.config["frequency"])
        self.PtxBS.setValue(self.config["Ptx_BS"])
        self.G_BS.setValue(self.config["G_BS"])
        self.cableLossBs.setValue(self.config["cable_Loss_BS"])
        self.sensivityBS.setValue(self.config["sensitivity_BS"])
        self.G_device.setValue(self.config["G_device"])
        self.Cable_Loss_device.setValue(self.config["cable_Loss_device"])
        self.indoorLoss.setValue(self.config["Indoor_Loss"])
        self.Urbanres.setValue(self.config["Urban_res"])
        self.HeightbyFloor.setValue(self.config["heigth_floor"])
        self.deltaFrequencyDL.setValue(self.config["deltaFrequencyDL"])
        self.Kfactor.setValue(self.config["K"])
        self.miscellaneousLoss.setValue(self.config["Miscelaneous_loss"])

        self.modelPropagation.addItems(["Free Space Model", "Egli Model", "Lee Model",
                                        "Okumura Hata Model", "Erceg SUI Model", "ECC 33 Model",
                                        "Ericcson Model", "Walfish Ikegami Model", "Xia Bertoni Model"])

        self.LeecomboBox.addItems(["Free Space", "Open Space", "Sub Urban", "Filadelfia", "Newark", "Tokyo"])
        self.HatacomboBox.setEnabled(True)
        self.HatacomboBox.addItems(["Middle City", "Big City"])
        self.E33comboBox.addItems(["Middle City", "Big City"])
        self.WalfikegcomboBox.addItems(["Middle City", "Big City"])

        #Caracteristicas de la tabla donde se cargan las capas
        self.mdl = QStandardItemModel(0, 6)             #crea el modelo de la tabla con 6 columnas
        self.tableView.setModel(self.mdl)               #agrega el modelo al dockwidget
        self.tableView.setColumnWidth(0, 20)            #ancho de la primera columna
        self.tableView.setColumnWidth(1, 20)            #ancho de la segunda columna
        hh = self.tableView.horizontalHeader()
        hh.setStretchLastSection(True)
        self.tableView.setColumnHidden(5 , True)
        self.mdl.setHorizontalHeaderLabels(["","","Layer","Band/Field","Search buffer"]) #nombres de las columnas de la tabla
        self.tableViewTool = TableViewTool()            #se emite cuando se agrega una nueva capa dandole caracteristicas a la tabla y a la polilinea que se dibuja en el mapa

        #otras variables
        self.selectionmethod = 0
        self.plotlibrary = "PyQtGraph"
        self.showcursor = True

        #señales necesarias para interactuar con el docwidget
        self.butSaveAs.clicked.connect(self.saveAs)
        self.tableView.clicked.connect(self._onClick)
        self.mdl.itemChanged.connect(self._onChange)
        self.pushButton_2.clicked.connect(self.addLayer)
        self.pushButton.clicked.connect(self.removeLayer)
        self.tableViewTool.layerAddedOrRemoved.connect(self.refreshPlot)
        self.pushButton_reinitview.clicked.connect(self.reScalePlot)
        self.saveconfButton.clicked.connect(self.setConfig)
        self.UhataradioButton.toggled.connect(self.hataCombobox)
        self.height_BS.valueChanged.connect(self.changehBS)
        self.height_device.valueChanged.connect(self.changehDevice)
        self.frequency.valueChanged.connect(self.changeFrequency)
        self.Ptxdevice.valueChanged.connect(self.changePtxdevice)
        self.ULradioButton.toggled.connect(self.changeLink)


    def changeLink(self):
        if self.ULradioButton.isChecked():
            self.config["link"]="UL"
        else:
            self.config["link"] = "DL"
        self.profiletoolcore.updateProfil(self.profiletoolcore.pointstoDraw[::-1], False, True) #invierte el perfil

    def changePtxdevice(self):
        self.config["Ptx_device"] = np.round(self.Ptxdevice.value(), 2)
        self.profiletoolcore.plotProfil()

    def changeFrequency(self):
        self.config["frequency"] = np.round(self.frequency.value(), 2)
        self.profiletoolcore.plotProfil()

    def changehDevice(self):
        self.config["height_device"] = np.round(self.height_device.value(), 2)
        self.profiletoolcore.plotProfil()

    def changehBS(self):
        self.config["height_BS"] = np.round(self.height_BS.value(), 2)
        self.profiletoolcore.plotProfil()

    def setConfig(self):

        self.config["Ptx_BS"] = np.round (self.PtxBS.value(), 2)
        self.config["G_BS"] = np.round(self.G_BS.value(), 2)
        self.config["cable_Loss_BS"] = np.round(self.cableLossBs.value(), 2)
        self.config["sensitivity_BS"] = np.round(self.sensivityBS.value(),2)
        self.config["G_device"] = np.round(self.G_device.value(), 2)
        self.config["cable_Loss_device"] = np.round(self.Cable_Loss_device.value(), 2)
        self.config["Indoor_Loss"] = np.round(self.indoorLoss.value(),2)
        self.config["Urban_res"] = self.Urbanres.value()
        self.config["heigth_floor"] = np.round(self.HeightbyFloor.value(), 2)
        self.config["deltaFrequencyDL"] = np.round(self.deltaFrequencyDL.value(), 2)
        self.config["K"] = np.round(self.Kfactor.value(), 3)
        self.config["Miscelaneous_loss"] = np.round(self.miscellaneousLoss.value(),2)
        index=self.modelPropagation.currentIndex()
        self.config["Model"] = self.models[str(index)]
        self.chooseModel(index)
        QMessageBox.about(self, "Message", "The changes have been saved successfully")
        if self.config["Urban_res"]!=5:
            self.refreshPlot()
        else:
            self.profiletoolcore.plotProfil()

    def chooseModel(self, index):
        dic={}
        if index == 2:
            dic=self.models["2"]
            dic["scenario"]=self.LeecomboBox.currentText()
        elif index ==3:
            dic=self.models["3"]
            if self.UhataradioButton.isChecked():
                dic["scenario"]="Urban"
                dic["city"]=self.HatacomboBox.currentText()
            elif self.SUhataradioButton.isChecked():
                dic["scenario"] = "Sub Urban"
            else:
                dic["scenario"] = "Rural"
        elif index == 4:
            dic=self.models["4"]
            if self.AercegradioButton.isChecked():
                dic["category"]="A"
            elif self.BercegradioButton.isChecked():
                dic["category"] = "B"
            elif self.CercegradioButton.isChecked():
                dic["category"] = "C"
        elif index == 5:
            dic = self.models["5"]
            dic["city"] = self.E33comboBox.currentText()
        elif index == 6:
            dic = self.models["6"]
            if self.UericsonradioButton.isChecked():
                dic["scenario"]="Urban"
            elif self.SUericsonradioButton.isChecked():
                dic["scenario"] = "Sub Urban"
            else:
                dic["scenario"] = "Rural"
        elif index == 7:
            dic = self.models["7"]
            dic["city"] = self.WalfikegcomboBox.currentText()
        else:
            pass

    def hataCombobox(self):
        if self.UhataradioButton.isChecked():
            self.HatacomboBox.setEnabled(True)
        else:
            self.HatacomboBox.setEnabled(False)

    #la libreria para dibujar
    def changePlotLibrary(self):
        self.addPlotWidget(self.plotlibrary)                #agrega el estilo de libreria al widget
        self.profiletoolcore.activateMouseTracking(2)


    def addPlotWidget(self, library): #le da un estilo a la caja donde se va a dibujar el perfil
        layout = self.frame_for_plot.layout() #la cajita donde se grafica el perfil

        while layout.count():
                        child = layout.takeAt(0)
                        child.widget().deleteLater()

        if library == "PyQtGraph":

            self.plotWdg = PlottingTool().changePlotWidget("PyQtGraph", self.frame_for_plot) #darle un estilo a la grilla el cursor etc
            layout.addWidget(self.plotWdg)  #agrega el estilo a la caja
            self.TYPE = "PyQtGraph"
            self.cbxSaveAs.clear()
            self.cbxSaveAs.addItems(['Graph - PNG','Graph - SVG','3D line - DXF']) #agrega al combobox de guardar los labels correspondientes


    def connectYSpinbox(self):
        self.sbMinVal.valueChanged.connect(self.reScalePlot)
        self.sbMaxVal.valueChanged.connect(self.reScalePlot)

    def disconnectYSpinbox(self):
        try:
            self.sbMinVal.valueChanged.disconnect(self.reScalePlot)
            self.sbMaxVal.valueChanged.disconnect(self.reScalePlot)
        except:
            pass

    def connectPlotRangechanged(self):
        self.plotWdg.getViewBox().sigRangeChanged.connect(self.plotRangechanged)

    def disconnectPlotRangechanged(self):
        try:
            self.plotWdg.getViewBox().sigRangeChanged.disconnect(self.plotRangechanged)
        except:
            pass

    def plotRangechanged(self, param = None):                         # se llama cuando se cambia la vista de pyqtgraph
        PlottingTool().plotRangechanged(self, self.plotlibrary)


    def reScalePlot(self, param):                         #se llama cuando se reescala la grafica

        if type(param) == bool: #comes from button
            PlottingTool().reScalePlot(self, self.profiletoolcore.profiles, self.plotlibrary, True)

        else:   #spinboxchanged

            if self.sbMinVal.value() == self.sbMaxVal.value() == 0: # Al iniciar el plugin las variables estan en 0 y esta funcion no se ejecuta
                pass
            else:
                PlottingTool().reScalePlot(self, self.profiletoolcore.profiles, self.plotlibrary)


    #********************************************************************************
    #tablebiew things ****************************************************************
    #********************************************************************************

    def addLayer(self, layer1 = None):

        if isinstance(layer1,bool): #comes from click
            layer1 = self.iface.activeLayer()
        self.tableViewTool.addLayer(self.iface, self.mdl, layer1)
        self.profiletoolcore.updateProfil(self.profiletoolcore.pointstoDraw,False)
        layer1.dataChanged.connect(self.refreshPlot)


    def removeLayer(self, index=None):
        if isinstance(index,bool):  #come from button
            index = self.tableViewTool.chooseLayerForRemoval(self.iface, self.mdl)

        if index is not None:
            layer = self.mdl.index(index, 4).data()
            try:
                layer.dataChanged.disconnect(self.refreshPlot)
            except:
                pass
            self.tableViewTool.removeLayer(self.mdl, index)
        self.profiletoolcore.updateProfil(self.profiletoolcore.pointstoDraw,False, True)

    def refreshPlot(self):

        #Actualiza la grafica sin requerir que el usuario vuelva a dibujar la poli línea en el mapa
        self.profiletoolcore.updateProfil(self.profiletoolcore.pointstoDraw, False, True)

    def _onClick(self,index1):                    #accion cuando se clickea en la tabla
        self.tableViewTool.onClick(self.iface, self, self.mdl, self.plotlibrary, index1)

    def _onChange(self,item):
        if (not self.mdl.item(item.row(),5) is None
                and item.column() == 4
                and self.mdl.item(item.row(),5).data(QtCore.Qt.EditRole).type() == qgis.core.QgsMapLayer.VectorLayer):

            self.profiletoolcore.plotProfil()

    #********************************************************************************
    #other things ****************************************************************
    #********************************************************************************

    def closeEvent(self, event):
        self.closed.emit()

    #accion que se ejecuta cuando se hace click en el boton guardar
    def saveAs(self):

        idx = self.cbxSaveAs.currentText()
        if idx == 'Graph - PDF':
                self.outPDF()
        elif idx == 'Graph - PNG':
                self.outPNG()
        elif idx == 'Graph - SVG':
                self.outSVG()
        elif idx == 'Graph - print (PS)':
                self.outPrint()
        elif idx == '3D line - DXF':
                self.outDXF()
        else:
            print('plottingtool: invalid index '+str(idx))

    def outPrint(self):
        PlottingTool().outPrint(self.iface, self, self.mdl, self.plotlibrary)

    def outPDF(self):
        PlottingTool().outPDF(self.iface, self, self.mdl, self.plotlibrary)

    def outSVG(self):
        PlottingTool().outSVG(self.iface, self, self.mdl, self.plotlibrary) #funciona

    def outPNG(self):
        PlottingTool().outPNG(self.iface, self, self.mdl, self.plotlibrary) #funciona

    def outDXF(self):                                                       #No funciona
        PlottingTool().outDXF(self.iface, self, self.mdl, self.plotlibrary, self.profiletoolcore.profiles)
