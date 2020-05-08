import qgis
from qgis.PyQt import QtCore

def isProfilable(layer):
    """
        Devuelve True si la capa esta dentro de los formatos adimitidos para las diferentes versiones de QGIS, de lo contrario devuelve False
    """
    if int(QtCore.QT_VERSION_STR[0]) == 4 :    #qgis2
        if int(qgis.utils.QGis.QGIS_VERSION.split('.')[0]) == 2 and int(qgis.utils.QGis.QGIS_VERSION.split('.')[1]) < 18 :
            return    (layer.type() == layer.RasterLayer) or \
                    (layer.type() == layer.PluginLayer and layer.LAYER_TYPE == 'crayfish_viewer') or \
                    (layer.type() == layer.PluginLayer and layer.LAYER_TYPE == 'selafin_viewer') 
        elif int(qgis.utils.QGis.QGIS_VERSION.split('.')[0]) == 2 and int(qgis.utils.QGis.QGIS_VERSION.split('.')[1]) >= 18 :
            return    (layer.type() == layer.RasterLayer) or \
                    (layer.type() == layer.PluginLayer and layer.LAYER_TYPE == 'crayfish_viewer') or \
                    (layer.type() == layer.PluginLayer and layer.LAYER_TYPE == 'selafin_viewer') or \
                    (layer.type() == layer.VectorLayer and layer.geometryType() == qgis.core.QGis.Point)
    elif int(QtCore.QT_VERSION_STR[0]) == 5 :    #qgis3
        #en Qgis 3 admite capas vectoriales, capas del tipo plugin y capas del tipo geometrico como puntos o plilineas
        return    (layer.type() == layer.RasterLayer) or \
                (layer.type() == layer.PluginLayer and layer.LAYER_TYPE == 'crayfish_viewer') or \
                (layer.type() == layer.PluginLayer and layer.LAYER_TYPE == 'selafin_viewer') or \
                (layer.type() == layer.VectorLayer and layer.geometryType() ==  qgis.core.QgsWkbTypes.PointGeometry) or \
                (layer.type() == layer.VectorLayer and layer.geometryType() == qgis.core.QgsWkbTypes.PolygonGeometry)

