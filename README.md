Prototype Tool Software for Estimation of the Clearance of the Radio Path Between two Antennas of SigFox
===================================

**Version: 1.0**
**Supported QGIS version: >= 3.6**
**Licence: GNU GPLv3**
**Author: Edward Oswaldo Navarro Astudillo

Introduction:
-------------

This tool draws profile lines from raster layers or polygons vector layer with cadastral information of buildings. 
The tracing of the profile allows estimating the clearance of the radio path between two antennas (SigFox BS and an IoT device).


Installation:
-------------
The plugin must be installed manually:

First you need to locate your QGIS plugins folder. On Windows it would be 'C:\users\username\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins' (do a file search for 'QGIS3' ...)

Plugin code can then be extracted in a new folder inside the plugins folder (you should name the folder sigfoxprofiletool). Take care that the code is not inside a subfolder - the folder structure should be like this:  

+ QGIS3\profiles\default\python\__plugins__
    + [some QGIS plugin folders...] 
    + sigfoxprofiletool   
        + profileplugin.py
        + [other files and folders...]  

Dependencies:
-------------
The plugin its operation has been tested in QGIS 3.6.0, is coded in Python 3.7.0 and does not require any additional libraries than those provided by standard QGIS installation. These libraries include *numpy* and *gdal* for manipulating raster data, and *PyQt5* and *QGIS core libraries* for integration with QGIS.


**SigFox Profile Tool license:**

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
