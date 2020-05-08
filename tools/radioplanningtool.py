import os
from qgis.core import *
from qgis.gui import *
import qgis
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtSvg import *
import platform
import numpy as np
from math import atan2, log10, exp, atan, pi, sqrt, cos, sin, acos
from cmath import phase
from shapely.geometry import Point, LineString, Polygon
from shapely.affinity import scale, rotate

class RadioPlanningTool():
    def __init__(self, conf):
        self.conf=conf
        if conf["link"]=="UL":
            self.f_Mhz = conf["frequency"]              #frecuencia UL en MHz
        else:
            self.f_Mhz = conf["frequency"] + conf["deltaFrequencyDL"]
        self.lamda = 300 / self.f_Mhz               #longitud de onda en metros
        self.h_device = conf["height_device"]       #altura del dispositivo sobre el terreno
        self.model= conf["Model"]                   #modelo usado para el calculo
        self.G_BS = conf["G_BS"]                    #Ganancia de la antena de la BS (dBi)
        self.G_device= conf["G_device"]             #Ganancia de la antena del dispositivo (dBi)
        self.Ptx_device= conf["Ptx_device"]         #poencia de transmision del dispositivo (dBm)
        self.cable_Loss_BS = conf["cable_Loss_BS"]  #perdidas debidas a cables y otros elementos en la BS
        self.cable_Loss_device=conf["cable_Loss_device"] #perdidas debidas a cables y otros elementos en EL DISPOSITIVO
        self.Ptx_BS= conf["Ptx_BS"]                      #potencia de transmision de la BS
        self.Lm=conf["Miscelaneous_loss"]                #perdidas misceclaneas (dB)

    #calcula en balance del enlace
    def linkBudget(self, L):
        if self.conf["link"]=="UL": #UpLink
            Prx= self.Ptx_device + self.G_device - self.cable_Loss_device - L - self.Lm + self.G_BS - self.cable_Loss_BS
        else:                       #DownLins
            Prx = self.Ptx_BS + self.G_BS - self.cable_Loss_BS  - L - self.Lm + self.G_device - self.cable_Loss_device
        return Prx

    #protuberancia de la tierra
    def protuber_of_Earth(self,B,x,k):
        d = B.x / 1000
        x = x / 1000
        f = 0.07849 * ((x * (d - x)) / k)  # protuberancia de la tierra o flecha
        return f

    # Funcion que permite corregir las alturas de Tx y Rx a lo largo de un perfil topografico teniendo en cuenta el terreno intermedio
    # A,B puntos de Tx y Rx respectivamente, d: en Km; x,y en metros
    def calculation_h1_h2(self,A,B,d,x,y): #d en Km
        c1 = 200 * d        #20% de la distancia en metros
        c2= 800 * d         #80% de la distancia en metros
        y = y[np.where((x > c1) & (x < c2))]
        x = x[np.where((x > c1) & (x < c2))]
        m=(y[-1] - y[0]) / (x[-1]- x[0])
        y1= - (m * x[0]) + y[0]
        y2= (m * (d*1000)) - (m * x[0]) + y[0]
        h1=abs(A.y - y1)
        h2=abs(B.y - y2)
        return h1, h2

    # Funcion que calcula altura efectiva de la antena Tx sobre un terreno irregular segun recomendacion ITU.R P1546
    # A,B puntos de Tx y Rx respectivamente, d: en Km; x,y en metros
    def h_eff(self,A,d,x,y):
        if d > 15:
            y = y[np.where((x > 3000) & (x < 15000))]   #se calcula entre 3Km y 15Km seun la recomendacion
            x = (x[np.where((x > 3000) & (x < 15000))])/1000 #debe ser en Km para el calculo de la altura media del terreno
        elif 0 < d <= 15:
            c = 200 * d                # 20% de la distancia en metros
            y = y[np.where(x > c)]
            x = (x[np.where(x > c)])/1000
        b = []
        for i in range(len(x)): #calculo de la altura media del terreno
            try:
                b.append(((y[i] + y[i + 1]) / 2) * (x[i + 1] - x[i]))
            except:
                pass
        hm= sum(b)/12 #altura media del tereno
        heff= A.y - hm
        return heff

    #calculo de altura efectiva de la BS (no implementado)
    def hb_effective_Tx(self,A,d,x,y): #calcula la altura efectiva del Tx sobre el terreno completo (d en Km)
        if d > 15:
            y = y[np.where((x > 3000) & (x < 15000))]
        elif 0 < d <= 15:
            c = 200 * d #20% de la distancia en metros
            y = y[np.where(x > c)]
        h = A.y - np.average(y)
        return h

    # modelo de propagacion Erceg-SUI; d,ht,hr en metros
    def ercsg_SUI_Loss(self,d,ht,hr,cat="B"):
        if cat=="A":
            a= 4.6; b= 0.0075; c= 12.6      #a,b y c, constantes ajustadas empiricamente
            Xh = -10.8 * log10(hr / 2)      #Xh: correccion debida a la altura del Rx
            S= 10.6                         #S:  correccion debida a efecto de shadowing
        elif cat=="B":
            a = 4; b = 0.0065; c = 17.1
            Xh = -10.8 * log10(hr / 2)
            S = 9.6
        else:
            a = 3.6; b = 0.0050; c = 20
            Xh = -20 * log10(hr / 2)
            S = 8.2
        A = 20*log10((4*pi*100)/self.lamda)
        gama= a - (b*ht) + (c/ht)               #altura de la estacion base sobre el suelo 10m-80m
        Xf= 6*log10(self.f_Mhz/1900)            #correccion debido a la frecuencia
        L= A + 10*gama*np.log10(d / 100) + Xf + Xh + S
        return L

    # modelo de propagacion ECC-33 f: ajustada a MHz, d en Km, ht y hr en m
    def ECC_33_Loss(self,d,ht,hr,escenario="Middle City"):
        Lfs = self.freeSpaceLoss(d)                                                                        #perdidas de espacio libre d en km
        f=self.f_Mhz/1000
        Lbm= 20.41 + 9.83*np.log10(d)+ 7.894*log10(f) + 9.56*((log10(f))**2)   #perdidas medianas basicas del trayecto, d en Km, frecuencia en GHz
        Gb=log10(ht/200)*(13.958 + 5.8*((np.log10(d))**2))                                                 #Ganancia en la estacion base
        if escenario == "Big City":         # ciudades grandes
            Gr= 0.795*hr - 1.862                                                                           #Ganancia del terminal receptor
        else:                      #ciudades medianas
            Gr=(42.57 + 13.7*log10(f))*(log10(hr) - 0.585)
        L= Lfs+ Lbm- Gb- Gr
        return L

    # Modelo de propagacion Ericcson: solo es aplicable para escenarios urbanos y semiurbanos, d en Km, ht y hr en metros
    def ericcson_Loss(self,d,ht,hr,escenario="Sub Urban"): #solo es aplicable para escenarios urbanos y semiurbanos
        a2 = -12; a3 = 0.1
        if escenario == "Rural":
            a0 = 36.2; a1 = 30.2
        elif escenario == "Sub Urban":
            a0 = 43.2; a1 = 68.93
        elif escenario == "Urban":
            a0 = 45.96; a1 = 100.6
        Gf=44.49*log10(self.f_Mhz) - 4.78*((log10(self.f_Mhz))**2)
        L=a0+a1*np.log10(d) + a2*log10(ht) + a3*(log10(ht)*np.log10(d)) -3.2*((log10(11.75*hr))**2) + Gf
        return L

    # Modelo de Lee:  dependiente del ambiente donde se calcule, d en Km; ht,hr en metros; Gb,Gm en Dbi
    def Lee_Loss(self,d,ht,hr,escenario="Sub Urban"): #depende del ambiente donde se calcule, d en Km

        if escenario=="Free Space": #se encuentra en espacio libre
            Lo=85; gama=20
        elif escenario=="Open Space": #escenario rural
            Lo = 89; gama = 43.5
        elif escenario =="Sub Urban": #escenario suburbano
            Lo = 101.7; gama = 38.5
        #areas urbanas
        elif escenario == "Filadelfia": #filadelfia
            Lo = 110; gama = 36.8
        elif escenario == "Newark": #newwark
            Lo = 104; gama = 43.1
        elif escenario == "Tokyo": #tokyo
            Lo = 124; gama = 30.5
        F1= (ht/30.48)**2                     #Factor de corrección para la altura de la antena Tx, ht en mts
        if hr >=3:
            F3=((hr/3)**2)                    #Factor de corrección para la altura de la antena Rx, hr en mts
        else:
            F3=hr/3
        if self.f_Mhz<450:
            n=2
        else:
            n=3
        F4= (self.f_Mhz/900)**-n              #factor de ajuste de frecuencia
        Fo=F1*F3*F4
        L=Lo + gama*np.log10(d) - 10*log10(Fo)
        return L

    # perdidas por espacio libre: d en km
    def freeSpaceLoss(self, d):  #perdidas por espacio libre (d en km)
        Lfs = 32.4 + 20 * log10(self.f_Mhz) + 20 * np.log10(d)
        return Lfs

    # Perdidas modelo egli: d en Km
    def egliLoss(self,d,ht,hr):
        L= 40* np.log10(d) - 20*log10(ht) - 20*log10(hr) - 20* log10(40/self.f_Mhz)
        return L

    # Modelo Walfish bertoni: modelo usado para entornos urbanos, d en Km (no implementado)
    def wlfisbertoniLoss(self,d,ht,hr,h): ##modelo usado para entornos urbanos
        A=5*log10(((d**2)/2) + (h-hr)**2) - 9*log10(d)
        Lfs = self.freeSpaceLoss(d)
        Lex= 57.1 + A + log10(self.f_Mhz) + 18*log10(d) - 18*log10(ht-h) -18*log10(1-((d**2)/(17*(ht-h))))
        L = Lfs + Lex
        return L

    #modelo ikegami (no implementado)
    def ikegamiLoss(self):  #escenarios urbanos
        if Ldifr == 0:  # linea de vista
            L = 42.6 + 26 * log10(Dkm) + 20 * log10(self.f_Mhz)
        else:
            Ir=3.2                      #Parámetro dependiente del coeficiente de reflexión en la fachada de los edificios Ir= 2 (VHF) y Ir= 3.2 (UHF).
            L=26.25 + 30*log10(self.f_Mhz) + 20*log10(d) - 10*log10(1 + (3/(Ir**2))) - 10*log10(W) + 20*log10(H-hr) +10*log10(sin(fi))

    # modelo Walfis Ikegami: d en Km; ht y hr en metros
    def wlfishkegamiLoss(self,d,ht,hr,h,Ldifr, escenario="Middle City",gama=90, b=40): #escenarios urbanos
        w=b/2
        # modelo de walfish ikegami
        if Ldifr == 0:                  # linea de vista (lOS)
            L= 42.6 + 26*log10(d) + 20*log10(self.f_Mhz)
            Ldif_walf = 0
        else:                           # modo NLOS
            Lfs = self.freeSpaceLoss(d)
            if 0 <=gama <35:
                Lori=-10+0.35*gama
            elif 35 <= gama < 55:
                Lori= 2.5 + 0.075*(gama-35)
            elif 55 <= gama <=90:
                Lori= 4 - 0.114 * (gama - 55)
            if (ht-h)>0:
                Lbsh= -18*log10(1+(ht-h))
                kd=18
            else:
                Lbsh=0
                kd=18-15*((ht-h)/h)
            if (ht-h)>=0:
                ka=54
            elif (ht-h)<0 and d >=0.5:
                ka= 54 - 0.8*(ht-h)
            elif (ht-h)<0 and d<0.5:
                ka=54-1.6*(d*(ht-h))
            if escenario=="Middle City":    # ciudades medianas y suburbios con densidad de arboles mediana
                kf= -4 + 0.7*(self.f_Mhz/925 -1)
            elif escenario=="Big City":     #ciudades grandes
                kf= -4 + 1.5*(self.f_Mhz/925 -1)
            Lrts= -16.9 - 10* log10(w) + 10*log10(self.f_Mhz) + 20* log10(h-hr) + Lori #h altura media de los edificios
            Lmsd= Lbsh + ka + kd * log10(d) + kf*log10(self.f_Mhz)- 9* log10(b) #b en metros
            Ldif_walf= Lrts + Lmsd # perdidas por difraccion dadas por el modelo walfish ikegami
            if Ldif_walf<0:
                Ldif_walf= 0
            L = Lfs + Ldif_walf # Db
        return L, Ldif_walf

    # Modelo Xia-Bertoni: usado para escenarios urbanos, d en Km
    def xia_bertoni_Loss(self,d,ht,hr,h,b=40): #f en Mhz y d en Km
        w=b/2
        x=w/2
        fi = abs(atan2((hr - h), x))
        r = sqrt((hr - h) ** 2 + x ** 2)
        if ht-h >= 2:                           #Altura de antena Txe por encima del nivel de los tejados, ht >> h
            L=  79.6 - 0.24*(ht-h) - 18*log10(ht-h) - 9*log10(b) + 21*log10(self.f_Mhz)+ 10*log10(r) +  20*log10(fi*(2*pi + fi)) + 40*(1 - (2*(10**-3))*(ht-h))*log10(d)
        elif (ht - h) < 2 and (ht-h) > -2 :     #Altura de antena Tx muy cerca del nivel de los tejados, ht ≈ h
            L=61.67 + 10*log10(r) - 20*log10(b) + 20*log10(fi*(2*pi + fi)) + 30*log10(self.f_Mhz) + 40*log10(d)
        elif (ht-h) <= -2:
            rprima = sqrt(w**2 + (ht - h)**2)
            teta= -1*atan2((ht-h),w)
            L= 36.9 + 40*log10(self.f_Mhz) + 40*log10(d) + 10*log10(rprima) + 10*log10(r) + 20*log10(fi*(2*pi + fi)) + 20*log10(teta*(2*pi + teta))
        Lfs = self.freeSpaceLoss(d)
        Ldif_xia = L - Lfs
        if Ldif_xia < 0:
            Ldif_xia = 0
        return L, Ldif_xia

    # Modelo Okumura Hata: usado para multiples escenario, d en Km
    def hataLoss(self,d,ht,hr,escenario="Sub Urban", city="Middle City"):
        if escenario=="Urban":
            C=0
            if city=="Big City":

                if self.f_Mhz <= 300:
                    ahm = 8.29 * (log10(1.54 * hr)) ** 2 - 1.1  # f <= 300 Mhz
                else:
                    ahm = 3.2 * (log10(11.75 * hr)) ** 2 - 4.97  # f >= 300 Mhz
            else:
                ahm = (1.1 * log10(self.f_Mhz) - 0.7) * hr - (1.56 * log10(self.f_Mhz) - 0.8)
        elif escenario=="Sub Urban":              #escenario para ciudades de pequeño o mediano porte (escenario suburbano)
            ahm = (1.1 * log10(self.f_Mhz) - 0.7) * hr - (1.56 * log10(self.f_Mhz) - 0.8)
            C= - 2 * ((log10(self.f_Mhz / 28)) ** 2) - 5.4
        else:                           #escenario rural
            ahm= (1.1 * log10(self.f_Mhz) - 0.7) * hr - (1.56 * log10(self.f_Mhz) - 0.8)
            C= - 4.78 * ((log10(self.f_Mhz)) ** 2) + 18.33 * log10(self.f_Mhz) - 40.94

        A = 69.55 + 26.16 * log10(self.f_Mhz) - 13.82 * log10(ht) - ahm
        B = 44.9 - 6.55 * log10(ht)
        L = A + B * np.log10(d) + C
        return L

    #Funcion que permie escoger el modelo de propagacion para los calculos
    def chooseModel(self, h_BS, Dkm, Ldifr, h=0):
        L_model_difr= 0 #perdidas por difraccion calculada intrinsecamente por los modelos: Walfish Ikegami y Xia bertoni
        if self.model["id"] == 0:                   #Espacio Libre
            L = self.freeSpaceLoss(Dkm)
        elif self.model["id"] == 1:                 #Egli
            L = self.egliLoss(Dkm, h_BS, self.h_device)
        elif self.model["id"] == 2:                 #Lee
            L=self.Lee_Loss(Dkm,h_BS,self.h_device,self.model["scenario"])
        elif self.model["id"] == 3:                 #okumura hata
            L=self.hataLoss(Dkm,h_BS,self.h_device,self.model["scenario"],self.model["city"])
        elif self.model["id"] == 4:                 #Erceg SUI
            L= self.ercsg_SUI_Loss(Dkm*1000,h_BS,self.h_device, self.model["category"])
        elif self.model["id"] == 5:                 #ECC-33
            L=self.ECC_33_Loss(Dkm,h_BS,self.h_device,self.model["city"])
        elif self.model["id"] == 6:                 #Ericsson
            L=self.ericcson_Loss(Dkm,h_BS,self.h_device, self.model["scenario"])
        elif self.model["id"] == 7:                 #Walfish Ikegami
            L, L_model_difr =self.wlfishkegamiLoss(Dkm, h_BS, self.h_device, h , Ldifr, escenario=self.model["city"])
        elif self.model["id"] == 8:                 #Xia bertoni
            L, L_model_difr = self.xia_bertoni_Loss(Dkm, h_BS,self.h_device,h)
        return L, L_model_difr


    #funcion para calcular el elipsoide de fresnel a lo largo del radio enlace
    def fresnelZone(self, A,B):
        f=self.f_Mhz/1000                           # frecuencia en GHertz
        R = 0.6 * 8.657 * sqrt((B.x / 1000) / f)    # 60% de la primera zona de fresnel
        d = self.distanceBetweenPoint(A, B)         # distancia del enlace
        S = Point(A.x + d / 2, A.y)                 # punto medio para graficar la elipse
        # LOS = LineString([(A.x, A.y), (B.x, A.y)])
        alpha = atan2(B.y - A.y, B.x - A.x)         # obtiene el angulo de rotacion con respecto al eje x
        C = S.buffer(d / 2,resolution=16)           # Crea un círculo con centro en S pasando por A y B (a >resolution utiliza mas puntos para dibujar)
        try:
            C = scale(C, 1,R / (d / 2))             # vuelve a escalar este círculo en la dirección y de modo que el eje correspondiente, sea R unidades de longitud
            C = rotate(C, alpha, origin=A,use_radians=True)  # gira la elipse obtenida a la posición debida (ángulos positivos representan rotación en sentido antihorario)
            f_x, f_y = C.exterior.xy
            return f_x, f_y
        except ZeroDivisionError:
            pass

    #distancia entre dos puntos en metros
    def distanceBetweenPoint(self, A, B): #distancia en metros desde Tx a Rx
        d = A.distance(B)
        return d

    def straightBetweenTwoPoints(self, A, B, x):  # calculo de la recta que representa la LoS entre Tx y Rx
        m = (B.y - A.y) / (B.x - A.x)
        y = (m * x) - (m * A.x) + A.y
        return y

    def calculationParameterV(self, A, O, B, h): #calcula el parametro v para obtener perdidas por dfraccion por obstaculos (d en Km, h en m)
        d = self.distanceBetweenPoint(A, B) / 1000
        d1 = self.distanceBetweenPoint(A, O) / 1000
        d2 = self.distanceBetweenPoint(O, B) / 1000
        v = 2.58e-3 * h * sqrt((self.f_Mhz * d) / (d1 * d2))
        return v

    def lossDiffractionAcuteObstacle(self, v):  # perdidas por difraccion de un obstaculo agudo

        if v<-0.8:
            LDv= 0
        elif -0.8 <= v < 0:
            LDv = -20*log10(0.5 - 0.62*v)
        elif 0 <= v < 1:
            LDv=-20*log10(0.5*exp(-0.95*v))
        elif 1 <= v < 2.4:
            LDv=-20*log10(0.4 - sqrt(0.1184 - (0.38 - 0.1*v)**2))
        else:
            LDv=-20*log10(0.225/v)
        return LDv

    def correction2Obstacles(self, A, O1, O2, B, v1, v2, decition): #correccion para el caso de dos obstaculos
        try:
            s1 = (O1.x - A.x) / 1000
            s2 = (O2.x - O1.x) / 1000
            s3 = (B.x - O2.x) / 1000
            if decition == 1:
                alpa = atan(((s2 * (s1 + s2 + s3)) / (s1 * s3)) ** 0.5)
                Lc = (12 - 20 * log10(2 / (1 - (alpa / pi)))) * ((v2 / v1) ** (2 * v1))
            elif decition == 2:
                Lc = 10 * log10(((s1 + s2) * (s2 + s3)) / (s2 * (s1 + s2 + s3)))
        except:
            Lc=0
        return Lc


    def maximumObstacleCoordinates(self, valoresh, CoordenadasObstaculo, i): #obtiene la coordenada donde se encuentran los obstaculos

        if i >= 3:                  #para mas de 3 obstaculos
            maxhobstaculos = []
            listadepuntos = []

            for ii in range(len(valoresh)):
                maxhobstaculos.append(max(valoresh[str(ii)]))               # lista de valores maximos para cada obstaculo
                indice = valoresh[str(ii)].index(max(valoresh[str(ii)]))    #indice donde se encuentra los valores maximos
                listadepuntos.append(CoordenadasObstaculo[str(ii)][indice]) #lista con las coordenadas de los obstaculos maximos

            hmax= max(maxhobstaculos)                       #el valor maximo de todos los obstaculos
            indicemax = maxhobstaculos.index(hmax)          #indice del maximo obstaculo
            O =listadepuntos[indicemax]                     #posicion del obstaculo mas grande
            hsubvanoTx = maxhobstaculos[:indicemax]         #subvano alturas de obstaculos desde Tx hasta el maximo obstaculo
            coordsubvanoTx = listadepuntos[:indicemax]      # coordenadaas de los obstaculos Tx- O
            hsubvanoRx = maxhobstaculos[indicemax + 1:]     #subvano de alturas obstaculos desde el maximo obstaculo hasta  Rx
            coordsubvanoRx= listadepuntos[indicemax + 1:]   #coordenadas obstaculos O- RX
            resultados=[hmax,O, hsubvanoTx, coordsubvanoTx,  hsubvanoRx, coordsubvanoRx] #lista de resultados
            return resultados

        else:
            hmax=max(valoresh) #obtiene el maximo valor del parametro h del obstaculo
            indice = valoresh.index(hmax)  # obtiene la posicion donde se encuentra el maximo valor
            O=CoordenadasObstaculo[indice] #obtiene el punto con las coordenadas x e y donde se encuentra el maximo valor de h del obstaculo
            return hmax, O

    # calculo de las perdidas por difraccion multiobstaculo  a lo largo de un perfil
    def difractionLoss(self, A, B, x, y, y2):
        obstaculoprevio = False
        contador = 0
        diccionario_valoresh = {}
        CoordenadasObstaculo = {}
        valoresdeh = []
        coordenadasobstaculo = []

        for i in range(len(x)):             #para cada punto de x
            h = y[i] - y2[i]                #calculo del despejamiento
            d1 = (x[i] - A.x) / 1000        #d1 en km
            d2 = (B.x - x[i]) / 1000        #d2 en Kmn
            Rpuntoapunto = 550 * sqrt((d1 * d2) / ((d1 + d2) * self.f_Mhz)) #calculo del 60% del radio fresnel para cada punto
            if (-0.6 * Rpuntoapunto) <= h:  #si se encuentra un obstaculo dentro del 60% del radio de fresnel
                obstaculoprevio = True
                valoresdeh.append(h)                            #guarda el valor del despejamiento con el obstaculo
                coordenadasobstaculo.append(Point(x[i], y[i]))  #guarda la coordenada del obstaculo
                continue                                        #se queda en este bucle hasta que salga del radio de fresnel
            #repite este ciclo para cada obstaculos grande que encuentre
            if obstaculoprevio:                                                #cada obstaculo es un conjunto de valores de h
                diccionario_valoresh[str(contador)] = valoresdeh               #diccionario de valors de h
                CoordenadasObstaculo[str(contador)] = coordenadasobstaculo     #diccionario con las coordenadas de valores de h
                coordenadasobstaculo = []
                valoresdeh = []
                contador += 1                                                  #lleva un registro de cuantos obstaculos encuentra a lo largo del radio enlace
                obstaculoprevio = False

        numobstaculos = len(diccionario_valoresh)        #cantidad de obstaculos a lo largo de TX-RX

        if numobstaculos > 0:
            if numobstaculos == 1:    #caso para un solo obstaculo aislado

                hmax, O = self.maximumObstacleCoordinates(diccionario_valoresh[str(0)], CoordenadasObstaculo[str(0)], 0) #obtiene el despejamiento maximo para el obstaculo y su coordenada(x,y)
                v = self.calculationParameterV(A, O, B, hmax)       #calculo del parametro adimensional v
                Ldifr = self.lossDiffractionAcuteObstacle(v)            #calculo de las perdidas debido a un obstaculo aislado

            elif numobstaculos == 2: #caso para dos obstaculos aislados

                hmax1, O1 = self.maximumObstacleCoordinates(diccionario_valoresh[str(0)], CoordenadasObstaculo[str(0)],0) #obtiene el despejamiento maximo para el obstaculo y su coordenada(x,y)
                hmax2, O2 = self.maximumObstacleCoordinates(diccionario_valoresh[str(1)], CoordenadasObstaculo[str(1)],1) #obtiene el despejamiento maximo para el obstaculo y su coordenada(x,y)
                v1 = self.calculationParameterV(A, O1, B, hmax1)
                v2 = self.calculationParameterV(A, O2, B, hmax2)

                if (v1 <= 0) and (v2 <= 0):  #caso para despejamientos negativos insuficientes  Metodo EMP

                    LDv1 = self.lossDiffractionAcuteObstacle(v1)
                    LDv2 = self.lossDiffractionAcuteObstacle(v2)
                    Ldifr = LDv1 + LDv2

                elif (v1 > 0) and (v2 > 0):  #despejamientos positivos

                    if abs(v2 - v1) > 0.5:   #Método de la Rec. 526 ITU-R: Obstáculo con despejamiento positivo y claramente dominante
                        if v1 > v2:

                            LDv1 = self.lossDiffractionAcuteObstacle(v1)
                            y_2 = self.straightBetweenTwoPoints(O1, B, O2.x)
                            h2_prima = O2.y - y_2
                            v2_prima = self.calculationParameterV(O1, O2, B, h2_prima)
                            LDv2 = self.lossDiffractionAcuteObstacle(v2_prima)
                            Lc = self.correction2Obstacles(A, O1, O2, B, v1, v2, 1)     #correccion sugerida por la recomendacion
                            Ldifr = LDv1 + LDv2 - Lc

                        elif v2 > v1:

                            LDv2 = self.lossDiffractionAcuteObstacle(v2)
                            y_1 = self.straightBetweenTwoPoints(A, O2, O1.x)
                            h1_prima = O1.y - y_1
                            v1_prima = self.calculationParameterV(A, O1, O2, h1_prima)
                            LDv1 = self.lossDiffractionAcuteObstacle(v1_prima)
                            Lc = self.correction2Obstacles(A, O1, O2, B, v2, v1, 1)
                            Ldifr = LDv1 + LDv2 - Lc

                    else:                    #caso para 2 obstaculos positivos con perdidas semejantes metodo Epstein peterson
                        y_1 = self.straightBetweenTwoPoints(A, O2, O1.x)
                        h1_prima = O1.y - y_1
                        y_2 = self.straightBetweenTwoPoints(O1, B, O2.x)
                        h2_prima = O2.y - y_2
                        v1_prima = self.calculationParameterV(A, O1, O2, h1_prima)
                        v2_prima = self.calculationParameterV(O1, O2, B, h2_prima)
                        LDv1 = self.lossDiffractionAcuteObstacle(v1_prima)
                        LDv2 = self.lossDiffractionAcuteObstacle(v2_prima)
                        if (LDv1 >= 15) and (LDv2 >= 15):
                            Lc = self.correction2Obstacles(A, O1, O2, B, v2, v1, 2)
                            Ldifr = LDv1 + LDv2 + Lc
                        else:
                            Ldifr = LDv1 + LDv2

                elif (v1 <= 0) and (v2 > 0): #caso donde O1 es negativo y O2 es positivo

                    LDv1 = self.lossDiffractionAcuteObstacle(v1)
                    LDv2 = self.lossDiffractionAcuteObstacle(v2)
                    Ldifr = LDv1 + LDv2

                elif (v2 <= 0) and (v1 > 0): #caso donde O2 es negativo y O1 es positivo

                    LDv2 = self.lossDiffractionAcuteObstacle(v2)
                    LDv1 = self.lossDiffractionAcuteObstacle(v1)
                    Ldifr = LDv1 + LDv2

            elif numobstaculos >= 3:  #caso para 3 obstaculos o mas/ metodo de Deygout modificado

                hmax3 = self.maximumObstacleCoordinates(diccionario_valoresh, CoordenadasObstaculo, 3)[0] #despejamiento maximo del mayor de los obstaculos
                O3 = self.maximumObstacleCoordinates(diccionario_valoresh, CoordenadasObstaculo, 3)[1]    #coordenada (x,y) del maximo obstaculo
                vp = self.calculationParameterV(A, O3, B, hmax3)                                        #parametro v del maximo obstaculo
                LDvp = self.lossDiffractionAcuteObstacle(vp)                                              #perdidas del obstaculo maximo
                T = 1 - exp(-(LDvp / 6.0))                                                                #parametro para correccion
                C = 10 + 0.04 * (B.x / 1000)                                                              #parametro para correccion
                subvanoTx = self.maximumObstacleCoordinates(diccionario_valoresh, CoordenadasObstaculo, 3)[2]       #despejamientos maximos de los obstaculos desde Tx hasta 03
                coordsubvanoTx = self.maximumObstacleCoordinates(diccionario_valoresh, CoordenadasObstaculo, 3)[3]  #coordenadas de los maximos obstaculos desde Tx hasta O3
                subvanoRx = self.maximumObstacleCoordinates(diccionario_valoresh, CoordenadasObstaculo, 3)[4]       #despejamientos maximos de los obstaculos desde O3 hasta RX
                coordsubvanoRx = self.maximumObstacleCoordinates(diccionario_valoresh, CoordenadasObstaculo, 3)[5]  #coordenadas de los maximos obstaculos desde O3 hasta Rx

                if len(subvanoRx) == 0: #no hay obstaculos a la derecha de O3

                    hmax2, O2 = self.maximumObstacleCoordinates(subvanoTx, coordsubvanoTx, 0)
                    y_1 = self.straightBetweenTwoPoints(A, O3, O2.x)
                    h1_prima = O2.y - y_1
                    vt = self.calculationParameterV(A, O2, O3, h1_prima)
                    LDvt = self.lossDiffractionAcuteObstacle(vt)
                    LDvr = 0
                    Ldifr = LDvp + T * (LDvt + LDvr + C)

                elif len(subvanoTx) == 0: #no hay obstaculos a la izquierda de O3

                    hmax4, O4 = self.maximumObstacleCoordinates(subvanoRx, coordsubvanoRx, 0)
                    y_2 = self.straightBetweenTwoPoints(O3, B, O4.x)
                    h2_prima = O4.y - y_2
                    vr = self.calculationParameterV(O3, O4, B, h2_prima)
                    LDvr = self.lossDiffractionAcuteObstacle(vr)
                    LDvt = 0
                    Ldifr = LDvp + T * (LDvt + LDvr + C)

                else: #hay obstaculos a ambos lados de O3

                    hmax2, O2 = self.maximumObstacleCoordinates(subvanoTx, coordsubvanoTx, 0)
                    hmax4, O4 = self.maximumObstacleCoordinates(subvanoRx, coordsubvanoRx, 0)
                    y_1 = self.straightBetweenTwoPoints(A, O3, O2.x)
                    h1_prima = O2.y - y_1
                    vt = self.calculationParameterV(A, O2, O3, h1_prima)
                    LDvt = self.lossDiffractionAcuteObstacle(vt)
                    y_2 = self.straightBetweenTwoPoints(O3, B, O4.x)
                    h2_prima = O4.y - y_2
                    vr = self.calculationParameterV(O3, O4, B, h2_prima)
                    LDvr = self.lossDiffractionAcuteObstacle(vr)
                    Ldifr = LDvp + T * (LDvt + LDvr + C)
        else: #el trayecto no presenta ningun obstaculo y por lo tanto ninguna perdida por difraccion
            Ldifr=0
        return Ldifr, numobstaculos

    # Funcion que calcula la rugosidad del terreno en m
    def roughnes_of_Grnd(self,x,y,ht,hr,d): #calculo de rugosidad del terreno en m
        lamda = 0.3 / self.f_Mhz
        ht = ht / 1000 #altura Tx en Km
        hr = hr / 1000 #altura Rx en Km
        D1 = (2 * (lamda * d + (ht + hr) ** 2)) / d
        x1 = ((2 * ht * (ht + hr) + lamda * d - sqrt((lamda * d) ** 2 + 4 * ht * hr * lamda * d)) / D1)*1000 #inicio zona determinante de reflexion
        xn = ((2 * ht * (ht + hr) + lamda * d + sqrt((lamda * d) ** 2 + 4 * ht * hr * lamda * d)) / D1)*1000 #final zona determinante de reflexion
        y = y[np.where((x > x1) & (x < xn))] #valores de alturas en la zona determinante
        try:
            deltah = abs(sqrt((sum((y - (np.average(y))) ** 2)) / len(y))) #calculo de la rugosidad del terreno
        except:
            deltah=0
        return deltah

    # metodo de tierra esferica para ambientes rurales y distancias muy grandes
    def spherical_eart_Diff(self,Er,sigma,k,ht,hr,ht_prima,hr_prima,d1,d2,d,pol): #difraccion sobre tierra esferica
        R=k*6370
        Kh = 0.36 * ((R * self.f_Mhz) ** -1 / 3) * (((Er - 1) ** 2 + ((18000 * sigma) / self.f_Mhz) ** 2) ** -1 / 4)
        if pol==1: #polarizacion vertical
            K=Kh*((Er**2 + ((18000*sigma)/self.f_Mhz)**2)**0.5)
        else: #polarizacion horizontal
            K = Kh
        Dht= 3.57*(sqrt(k*ht))#distancia al horizonte Tx
        Dhr = 3.57 * (sqrt(k * hr))  # distancia al horizonte Rx
        Dv= Dht+Dhr #distancia de visibilidad radioelectrica
        if d>= Dv: #perdidas despues del horizonte
            Ld=self.diffloss_Horizon(R,K,d,ht,hr)
        else: #perdidas antes del horizonte
            h=(ht_prima*d2 +  hr_prima*d1)/d
            R1 = 550 * sqrt((d1 * d2) / ((d1 + d2) * self.f_Mhz))
            Lh = self.diffloss_Horizon(R, K, Dht, ht, hr)
            Ld= (1- (5/3)*(h/R1))*Lh
        return Ld

    def F(self,X):
        F=11+10*log10(X)-17.6*X
        return F

    def G(self,Y,K):
        if Y>2:
            G=17.6*((Y-1.1)**0.5) - 5*log10(Y-1.1) -8
        elif 10*K<Y<2:
            G=20*log10(Y+ 0.1*(Y**3))
        elif K/10<Y<10*K:
            G=2 + 20*log10(K) + 9*log10(Y/K)*(log10(Y/K) + 1)
        elif Y<K/10:
            G= 2 + 20*log10(K)
        return G

    # perdida debida a la difraccion de la tierra despues del horizonte
    def diffloss_Horizon(self,R,K,d,ht,hr): #perdida debida a la difraccion de la tierra despues del horizonte
        beta = (1 + 1.6 * (K ** 2) + 0.75 * (K ** 4)) / (1 + 4.5 * (K ** 2) + 1.35 * (K ** 4))
        X = 2.2 * beta * (self.f_Mhz ** (1 / 3)) * (R ** (-2 / 3)) * d
        Y1 = 9.6 * (10 ** -3) * beta * (self.f_Mhz ** (2 / 3)) * (R ** (-1 / 3)) * ht
        Y2 = 9.6 * (10 ** -3) * beta * (self.f_Mhz ** (2 / 3)) * (R ** (-1 / 3)) * hr
        F = self.F(X)
        G1 = self.G(Y1, K)
        G2 = self.G(Y2, K)
        Ld = -F - G1 - G2
        return Ld

    # modelo de perdidas debida a 2 rayos o reflexion en la tierra
    # d en Km, Er constante dielectrica relativa, sigma: conductividad (mhos/m), pol:  polarizacion del enlace(horizontal/vertical)
    def reflexionLoss(self,Er,sigma,ht,hr,d,flecha,k,pol): #d ditancia del enlace en Km, Er constante dielectrica relativa, sigma: conductividad (mhos/m), pol: la polarizacion del enlace
        Lfs = self.freeSpaceLoss(d) #perdidas de espacio libre d en km
        img = -60 * sigma * self.lamda
        Eo = complex(Er, img)
        if max(flecha)<=5: #modelo de tierra plana
            fi = atan2(ht + hr, d*1000)
            delta = (4 * pi * ht * hr) / (self.lamda * (d*1000))

        else: #modelo de tierra curva  se utiliza la d en Km
            ro = (2 / sqrt(3)) * sqrt(6.37 * k * (ht + hr) + (d / 2) ** 2)
            if ht>=hr:
                fi1 = acos((12.74 * k * (ht - hr) * d) / ro ** 3)
                d1 = d / 2 + ro * cos((pi + fi1) / 3)
                d2 = d - d1
            else:
                fi1 = acos((12.74 * k * (hr - ht) * d) / ro ** 3)
                d2 = d / 2 + ro * cos((pi + fi1) / 3)
                d1 = d - d2
            ht_prima = ht - (4 * (d1 ** 2)) / (51 * k)  # correccion de ht para tierra curva
            hr_prima = hr - (4 * (d2 ** 2)) / (51 * k)  # correccion de hr para tierra curva
            psi = (ht_prima + hr_prima) / d  # angulo de incidencia en miliradianes
            psi_lim = (5400 / self.f_Mhz) ** (1 / 3)  # angulo limite en miliradianes

            if psi< psi_lim:
                Lb= Lfs+ self.spherical_eart_Diff(Er,sigma,k,ht,hr,ht_prima,hr_prima,d1,d2,d,pol)
                return Lb
            else:
                D = 1 / sqrt(1 + (((d1 ** 2) * d2) / (d * ht_prima)) * (5 / (16 * k)))  # factor de divergencia
                deltal = (2 * ht_prima * hr_prima * 10 ** -3) / d  # diferencia de trayectos
                delta = (pi * self.f_Mhz * deltal) / 150  # desfazamiento
                fi = psi * (10 ** -3)  # angulo de incidencia en radianes
        if pol==1: #para polrizacion vertical
            R = (Eo * sin(fi) - ((Eo - cos(fi) ** 2)) ** 0.5) / (Eo * sin(fi) + ((Eo - cos(fi) ** 2)) ** 0.5)
        else: #para polarizacion horizontal
            R = (sin(fi) - ((Eo - cos(fi) ** 2)) ** 0.5) / (sin(fi) + ((Eo - cos(fi) ** 2)) ** 0.5)
        angle = abs(phase(R))
        if max(flecha) <= 5: #tierra plana
            mag = abs(R)
        else: #tierra curva
            mag= abs(R)*D
        Lb = Lfs - 10 * log10(1 + mag ** 2 + 2 * mag * cos(delta + angle))
        return Lb
