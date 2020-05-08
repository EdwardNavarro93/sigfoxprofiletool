#Qt import
from qgis.PyQt import uic, QtCore, QtGui
try:
    from qgis.PyQt.QtGui import QInputDialog, QMessageBox
except:
    from qgis.PyQt.QtWidgets import QInputDialog, QMessageBox
#qgis import
from qgis.core import *
from qgis.gui import *
#plugin import
from .plottingtool import *
from .utils import isProfilable

class TableViewTool(QtCore.QObject):
    
    layerAddedOrRemoved = QtCore.pyqtSignal()           #Señal emitida cuando se agrega o se elimina una nueva capa

    def addLayer(self , iface, mdl, layer1 = None):     #se activa cuando se agrega una nueva capa a la tabla dandole sus caracteristicas
        if layer1 == None:
            templist=[]
            j=0
            #Pregunta a la capa mediante un diálogo de entrada.
            for i in range(0, iface.mapCanvas().layerCount()):
                donothing = False
                layer = iface.mapCanvas().layer(i)
                if isProfilable(layer):                     #si la capa es aceptada por el plugin (capas raster, capas geometricas)
                    for j in range(0, mdl.rowCount()):
                        if str(mdl.item(j,2).data(QtCore.Qt.EditRole)) == str(layer.name()): #ingresa el nombre de la capa a la tabla
                            donothing = True
                else:
                    donothing = True
                if donothing == False:
                    templist += [[layer, layer.name()]]
                        
            if len(templist) == 0:
                QMessageBox.warning(iface.mainWindow(), "SigFox Profile tool", "No raster to add")
                return
            else:    
                testqt, ok = QInputDialog.getItem(iface.mainWindow(), "Layer selector", "Choose layer", [templist[k][1] for k in range( len(templist) )], False)
                if ok:
                    for i in range (0,len(templist)):
                        if templist[i][1] == testqt:
                            layer2 = templist[i][0]
                else:
                    return
        else : 
            if isProfilable(layer1):
                layer2 = layer1
            else:
                QMessageBox.warning(iface.mainWindow(), "SigFox Profile tool", "Active layer is not a profilable layer")
                return

        #pregunta la banda de la capa raster o el campo que se desea calcular en la capa vectorial
        if layer2.type() == layer2.PluginLayer and  isProfilable(layer2):
            self.bandoffset = 0
            typename = 'parameter'
        elif layer2.type() == layer2.RasterLayer:
            self.bandoffset = 1
            typename = 'band'
        elif layer2.type() == layer2.VectorLayer:
            self.bandoffset = 0
            typename = 'field'

            
        if layer2.type() == layer2.RasterLayer and layer2.bandCount() != 1: #si hay mas de una banda en la capa raster
            listband = []
            for i in range(0,layer2.bandCount()):
                listband.append(str(i+self.bandoffset))
            testqt, ok = QInputDialog.getItem(iface.mainWindow(), typename + " selector", "Choose the " + typename, listband, False)
            if ok :
                choosenBand = int(testqt) - self.bandoffset
            else:
                return 2
        elif layer2.type() == layer2.VectorLayer :  #elegir cual es el campo que se desea de la capa vectorial mediante una ventana de dialogo
            fieldstemp = [field.name() for field in layer2.fields()]
            if int(QtCore.QT_VERSION_STR[0]) == 4 :    #qgis2
                fields = [field.name() for field in layer2.fields() if field.type() in [2,3,4,5,6]]

            elif int(QtCore.QT_VERSION_STR[0]) == 5 :    #qgis3
                fields = [field.name() for field in layer2.fields() if field.isNumeric()]
            if len(fields)==0:
                QMessageBox.warning(iface.mainWindow(), "Profile tool", "Active layer is not a profilable layer")
                return
            elif len(fields) == 1 :
                choosenBand = fieldstemp.index(fields[0])

            else:
                testqt, ok = QInputDialog.getItem(iface.mainWindow(), typename + " selector", "Choose the " + typename, fields, False)
                if ok :
                    #choosenBand = fieldstemp.index(testqt)
                    choosenBand= testqt
                else:
                    return 2
            
        else:
            choosenBand = 0

        #Completa la tabla de layers
        row = mdl.rowCount()
        mdl.insertRow(row)
        mdl.setData( mdl.index(row, 0, QModelIndex())  ,True, QtCore.Qt.CheckStateRole)
        mdl.item(row,0).setFlags(QtCore.Qt.ItemIsSelectable)
        if layer2.type() == layer2.RasterLayer:
            lineColour = QtCore.Qt.green                #Da el color a la capa raster cargada
        elif layer2.type() == layer2.VectorLayer:
            lineColour = QtCore.Qt.blue                 #Da el color a la capa vectorial cargada
        else:
            lineColour = QtCore.Qt.blue
        mdl.setData( mdl.index(row, 1, QModelIndex())  ,QColor(lineColour) , QtCore.Qt.BackgroundRole)
        mdl.item(row,1).setFlags(QtCore.Qt.NoItemFlags) 
        mdl.setData( mdl.index(row, 2, QModelIndex())  ,layer2.name())
        mdl.item(row,2).setFlags(QtCore.Qt.NoItemFlags)

        if layer2.type() == layer2.VectorLayer :

            mdl.setData(mdl.index(row, 3, QModelIndex()), choosenBand)
            mdl.item(row, 3).setFlags(QtCore.Qt.NoItemFlags)
            mdl.setData( mdl.index(row, 4, QModelIndex())  ,100.0)
        else:

            mdl.setData(mdl.index(row, 3, QModelIndex()), choosenBand + self.bandoffset)
            mdl.item(row, 3).setFlags(QtCore.Qt.NoItemFlags)
            mdl.setData( mdl.index(row, 4, QModelIndex())  ,'')
            mdl.item(row,4).setFlags(QtCore.Qt.NoItemFlags) 

        mdl.setData( mdl.index(row, 5, QModelIndex())  ,layer2)
        mdl.item(row,5).setFlags(QtCore.Qt.NoItemFlags)
        self.layerAddedOrRemoved.emit()

    def removeLayer(self, mdl, index): #se activa cuando se elimina una capa
            try:
                mdl.removeRow(index)
                self.layerAddedOrRemoved.emit()
            except:
                return

    def chooseLayerForRemoval(self, iface, mdl): #permite elegir que capa se desea eliminar de la tabla
        
        if mdl.rowCount() < 2:
            if mdl.rowCount() == 1:
                return 0
            return None

        list1 = []
        for i in range(0,mdl.rowCount()):
            list1.append(str(i +1) + " : " + mdl.item(i,2).data(QtCore.Qt.EditRole))
        testqt, ok = QInputDialog.getItem(iface.mainWindow(), "Layer selector", "Choose the Layer", list1, False)
        if ok:
            for i in range(0,mdl.rowCount()):
                if testqt == (str(i+1) + " : " + mdl.item(i,2).data(QtCore.Qt.EditRole)):
                    return i
        return None
        
    def onClick(self, iface, wdg, mdl, plotlibrary, index1):    #accion que se ejecuta cuando se ha clickeado sobre la tabla
        temp = mdl.itemFromIndex(index1)
        if index1.column() == 1:                #permite modificar el color por defecto
            name = ("%s") % (mdl.item(index1.row(),2).data(QtCore.Qt.EditRole))
            color = QColorDialog().getColor(temp.data(QtCore.Qt.BackgroundRole))
            mdl.setData( mdl.index(temp.row(), 1, QModelIndex())  ,color , QtCore.Qt.BackgroundRole)
            PlottingTool().changeColor(wdg, plotlibrary, color, name)
        elif index1.column() == 0:               #permite activar o desactivar la capa(no esta funcionando)
            #name = mdl.item(index1.row(),2).data(Qt.EditRole)
            name = ("%s") % (mdl.item(index1.row(),2).data(QtCore.Qt.EditRole))
            booltemp = temp.data(QtCore.Qt.CheckStateRole)
            if booltemp == True:
                booltemp = False
            else:
                booltemp = True
            mdl.setData( mdl.index(temp.row(), 0, QModelIndex())  ,booltemp, QtCore.Qt.CheckStateRole)
            PlottingTool().changeAttachCurve(wdg, plotlibrary, booltemp, name)
        elif False and index1.column() == 4:
            name = mdl.item(index1.row(),4).data(QtCore.Qt.EditRole)
        else:
            return


