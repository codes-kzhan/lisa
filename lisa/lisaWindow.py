# /usr/bin/env python
# -*- coding: utf-8 -*-
"""
Modul is used for GUI of Lisa
"""
import logging
logger = logging.getLogger(__name__)

import sys
import os
import numpy as np
import subprocess

import datetime
import functools

from io3d import datareader
# import segmentation
from seg2mesh import gen_mesh_from_voxels, mesh2vtk, smooth_mesh
import virtual_resection

try:
    from viewer import QVTKViewer
    viewer3D_available = True

except ImportError:
    viewer3D_available = False

path_to_script = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(path_to_script, "../extern/pysegbase/src"))

from PyQt4.QtGui import QApplication, QMainWindow, QWidget,\
    QGridLayout, QLabel, QPushButton, QFrame, \
    QFont, QPixmap, QFileDialog, QStyle
from PyQt4 import QtGui
from PyQt4.Qt import QString
try:
    from pysegbase.seed_editor_qt import QTSeedEditor
except:
    logger.warning("Deprecated of pyseg_base as submodule")
    try:
        from pysegbase.seed_editor_qt import QTSeedEditor
    except:
        logger.warning("Deprecated of pyseg_base as submodule")
        from seed_editor_qt import QTSeedEditor

import sed3
import loginWindow

def find_logo():
    import wget
    logopath = os.path.join(path_to_script, "./icons/LISA256.png")
    if os.path.exists(logopath):
        return logopath
    # lisa runtime directory
    logopath = os.path.expanduser("~/lisa_data/.lisa/LISA256.png")
    if not os.path.exists(logopath):
        try:
            wget.download(
                "https://raw.githubusercontent.com/mjirik/lisa/master/lisa/icons/LISA256.png",
                out=logopath
            )
        except:
            logger.warning('logo download failed')
            pass
    if os.path.exists(logopath):
        return logopath

    pass

# GUI
class OrganSegmentationWindow(QMainWindow):

    def __init__(self, oseg=None):

        self.oseg = oseg

        QMainWindow.__init__(self)
        self._initUI()
        self._initMenu()

        if oseg is not None:
            if oseg.data3d is not None:
                self.setLabelText(self.text_dcm_dir, self.oseg.datapath)
                self.setLabelText(self.text_dcm_data, self.getDcmInfo())

        self.statusBar().showMessage('Ready')


    def _initMenu(self):
        menubar = self.menuBar()

        ###### FILE MENU ######
        fileMenu = menubar.addMenu('&File')
        loadSubmenu = fileMenu.addMenu('&Load')
        # load dir
        loadDirAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Directory', self)
        loadDirAction.setStatusTip('Load data from directory (DICOM, jpg, png...)')
        loadDirAction.triggered.connect(self.loadDataDir)
        loadSubmenu.addAction(loadDirAction)
        # load file
        loadFileAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&File', self)
        loadFileAction.setStatusTip('Load data from file (pkl, 3D Dicom, tiff...)')
        loadFileAction.triggered.connect(self.loadDataFile)
        loadSubmenu.addAction(loadFileAction) 
        
        saveSubmenu = fileMenu.addMenu('&Save')
        # save file
        saveFileAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&File', self)
        saveFileAction.setStatusTip('Save data with segmentation')
        saveFileAction.triggered.connect(self.saveOut)
        saveSubmenu.addAction(saveFileAction)   
        # save dicom
        saveDicomAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&DICOM', self)
        saveDicomAction.setStatusTip('Save DICOM data')
        saveDicomAction.triggered.connect(self.btnSaveOutDcm)
        saveSubmenu.addAction(saveDicomAction)
        # save dicom overlay
        saveDicomOverlayAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&DICOM overlay', self)
        saveDicomOverlayAction.setStatusTip('Save overlay DICOM data')
        saveDicomOverlayAction.triggered.connect(self.btnSaveOutDcmOverlay)
        saveSubmenu.addAction(saveDicomOverlayAction)     
        # save PV tree
        savePVAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&PV tree', self)
        savePVAction.setStatusTip('Save Portal Vein 1D model')
        savePVAction.triggered.connect(self.btnSavePortalVeinTree)
        saveSubmenu.addAction(savePVAction)     
        # save HV tree
        saveHVAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&HV tree', self)
        saveHVAction.setStatusTip('Save Hepatic Veins 1D model')
        saveHVAction.triggered.connect(self.btnSaveHepaticVeinsTree)
        saveSubmenu.addAction(saveHVAction)     

        separator = fileMenu.addAction("")
        separator.setSeparator(True)

        autoSeedsAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Automatic liver seeds', self)
        autoSeedsAction.setStatusTip('Automatic liver seeds')
        autoSeedsAction.triggered.connect(self.btnAutomaticLiverSeeds)
        fileMenu.addAction(autoSeedsAction)

        autoSegAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Automatic segmentation', self)
        autoSegAction.setStatusTip('Automatic segmentation')
        autoSegAction.triggered.connect(self.autoSeg)
        fileMenu.addAction(autoSegAction)

        cropAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Crop', self)
        cropAction.setStatusTip('')
        cropAction.triggered.connect(self.cropDcm)
        fileMenu.addAction(cropAction)

        maskAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Mask region', self)
        maskAction.setStatusTip('')
        maskAction.triggered.connect(self.maskRegion)
        fileMenu.addAction(maskAction)

        view3DAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&View 3D', self)
        view3DAction.setStatusTip('View segmentation in 3D model')
        view3DAction.triggered.connect(self.view3D)
        fileMenu.addAction(view3DAction)

        separator = fileMenu.addAction("")
        separator.setSeparator(True)

        exitAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(QtGui.qApp.quit)
        fileMenu.addAction(exitAction)


        ###### IMAGE MENU ######
        imageMenu = menubar.addMenu('&Image')

        randomRotateAction= QtGui.QAction(QtGui.QIcon('exit.png'), '&Random Rotate', self)
        # autoSeedsAction.setShortcut('Ctrl+Q')
        randomRotateAction.setStatusTip('Random rotation')
        randomRotateAction.triggered.connect(self.btnRandomRotate)
        imageMenu.addAction(randomRotateAction)

        mirrorZAxisAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Mirror Z-axis', self)
        mirrorZAxisAction.setStatusTip('Mirror Z-axis')
        mirrorZAxisAction.triggered.connect(self.oseg.mirror_z_axis)
        imageMenu.addAction(mirrorZAxisAction)


        ###### OPTION MENU ######
        optionMenu = menubar.addMenu('&Option')
        
        configAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Configuration', self)
        configAction.setStatusTip('Config settings')
        configAction.triggered.connect(self.btnConfig)
        optionMenu.addAction(configAction)

        logAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Log', self)
        logAction.setStatusTip('See log file')
        logAction.triggered.connect(self.btnLog)
        optionMenu.addAction(logAction)

        syncAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Sync', self)
        syncAction.setStatusTip('Synchronize files from the server')
        syncAction.triggered.connect(self.sync_lisa_data)
        optionMenu.addAction(syncAction)        

        updateAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Update', self)
        updateAction.setStatusTip('Check new update')
        updateAction.triggered.connect(self.btnUpdate)
        optionMenu.addAction(updateAction)


        ###### CONFIG MENU ######
        configMenu = menubar.addMenu('&Config')
        # combo = QtGui.QComboBox(self)
        for text in self.oseg.segmentation_alternative_params.keys():
            iAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&' + text, self)
            iAction.setStatusTip('Use predefined config "%s"' % (text))
            # something like lambda
            fn = functools.partial(self.onAlternativeSegmentationParams, text)
            iAction.triggered.connect(fn)

            configMenu.addAction(iAction)
        # combo.activated[str].connect(self.onAlternativeSegmentationParams)
        # grid.addWidget(combo, 4, 1)

    def _add_button(
            self,
            text,
            callback,
            uiw_label=None,
            tooltip=None,
            icon=None
                    ):
        if uiw_label is None:
            uiw_label = text
        btn = QPushButton(text, self)
        btn.clicked.connect(callback)
        if icon is not None:
            btn.setIcon(btn.style().standardIcon(icon))
        self.uiw[uiw_label] = btn
        if tooltip is not None:
            btn.setToolTip(tooltip)

        return btn


    def _initUI(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        grid = QGridLayout()
        grid.setSpacing(10)

        self.uiw = {}

        # status bar
        self.statusBar().showMessage('Ready')

        ## menubar
        #self._initMenu()

        font_label = QFont()
        font_label.setBold(True)
        font_info = QFont()
        font_info.setItalic(True)
        font_info.setPixelSize(10)
        
        # # # # # # #
        # #  LISA logo
        # font_title = QFont()
        # font_title.setBold(True)
        # font_title.setSize(24)

        #lisa_title = QLabel('Liver Surgery Analyser')
        #info = QLabel('Developed by:\n' +
        #              'University of West Bohemia\n' +
        #              'Faculty of Applied Sciences\n' +
        #              QString.fromUtf8('M. Jiřík, V. Lukeš - 2013') +
        #              '\n\nVersion: ' + self.oseg.version
        #              )
        #info.setFont(font_info)
        #lisa_title.setFont(font_label)
        #grid.addWidget(lisa_title, 0, 1)
        #grid.addWidget(info, 1, 1)

        lisa_logo = QLabel()
        logopath = find_logo()
        logo = QPixmap(logopath)
        lisa_logo.setPixmap(logo)  # scaledToWidth(128))
        grid.addWidget(lisa_logo, 0, 2, 5, 2)

        ##### MAIN MENU #####
        btnLoad = QPushButton("Load", self)
        btnLoad.clicked.connect(self.btnLoad)
        grid.addWidget(btnLoad, 5, 2)

        btnSave = QPushButton("Save", self)
        btnSave.clicked.connect(self.btnSave)
        grid.addWidget(btnSave, 6, 2)

        btnSegmentation = QPushButton("Segmentation", self)
        btnSegmentation.clicked.connect(self.btnSegmentation)
        grid.addWidget(btnSegmentation, 7, 2)

        btnCompare = QPushButton("Compare", self)
        btnCompare.clicked.connect(self.compareSegmentationWithFile)
        grid.addWidget(btnCompare, 8, 2)

        btnQuit = QPushButton("Quit", self)
        btnQuit.clicked.connect(self.quit)
        grid.addWidget(btnQuit, 9, 2)


        ##### LOAD MENU #####
        loadWidget = QWidget()
        loadGrid = QGridLayout()
        loadGrid.setSpacing(10)
        lisa_logo = QLabel()
        lisa_logo.setPixmap(logo)
        loadGrid.addWidget(lisa_logo, 0, 2, 5, 2)

        btnLoadFile = QPushButton("File", self)
        btnLoadFile.clicked.connect(self.loadDataFile)
        loadGrid.addWidget(btnLoadFile, 5, 2)

        btnLoadDir = QPushButton("Directory", self)
        btnLoadDir.clicked.connect(self.loadDataDir)
        loadGrid.addWidget(btnLoadDir, 6, 2)

        btnMainMenu = QPushButton("Back", self)
        btnMainMenu.clicked.connect(self.btnMainMenu)
        loadGrid.addWidget(btnMainMenu, 7, 2)


        ##### SAVE MENU #####
        saveWidget = QWidget()
        saveGrid = QGridLayout()
        saveGrid.setSpacing(10)
        lisa_logo = QLabel()
        lisa_logo.setPixmap(logo)
        saveGrid.addWidget(lisa_logo, 0, 2, 5, 2)

        btnSaveFile = QPushButton("File", self)
        btnSaveFile.clicked.connect(self.saveOut)
        saveGrid.addWidget(btnSaveFile, 5, 2)

        btnSaveDcm = QPushButton("Dicom", self)
        btnSaveDcm.clicked.connect(self.btnSaveOutDcm)
        saveGrid.addWidget(btnSaveDcm, 6, 2)

        btnSaveDcmOverlay = QPushButton("Dicom overlay", self)
        btnSaveDcmOverlay.clicked.connect(self.btnSaveOutDcmOverlay)
        saveGrid.addWidget(btnSaveDcmOverlay, 6, 3)

        btnSavePV = QPushButton("PV tree", self)
        btnSavePV.clicked.connect(self.btnSavePortalVeinTree)
        saveGrid.addWidget(btnSavePV, 7, 2)

        btnSaveHV = QPushButton("HV tree", self)
        btnSaveHV.clicked.connect(self.btnSaveHepaticVeinsTree)
        saveGrid.addWidget(btnSaveHV, 8, 2)

        btnMainMenu = QPushButton("Back", self)
        btnMainMenu.clicked.connect(self.btnMainMenu)
        saveGrid.addWidget(btnMainMenu, 9, 2)


        ##### SEGMENTATION MENU #####
        segWidget = QWidget()
        segGrid = QGridLayout()
        segGrid.setSpacing(10)
        lisa_logo = QLabel()
        lisa_logo.setPixmap(logo)
        segGrid.addWidget(lisa_logo, 0, 2, 5, 2)

        btnSegManual = QPushButton("Manual", self)
        btnSegManual.clicked.connect(self.liverSeg)
        segGrid.addWidget(btnSegManual, 5, 2)

        btnSegMask = QPushButton("Mask", self)
        btnSegMask.clicked.connect(self.maskRegion)
        segGrid.addWidget(btnSegMask, 6, 2)

        btnSegPV = QPushButton("Portal Vein", self)
        btnSegPV.clicked.connect(self.btnPortalVeinSegmentation)
        segGrid.addWidget(btnSegPV, 7, 2)

        btnSegHV = QPushButton("Hepatic Vein", self)
        btnSegHV.clicked.connect(self.btnHepaticVeinsSegmentation)
        segGrid.addWidget(btnSegHV, 8, 2)

        btnMainMenu = QPushButton("Back", self)
        btnMainMenu.clicked.connect(self.btnMainMenu)
        segGrid.addWidget(btnMainMenu, 9, 2)

        if self.oseg.debug_mode:
            btn_debug = QPushButton("Debug", self)
            btn_debug.clicked.connect(self.run_debug)
            grid.addWidget(btn_debug, rstart - 2, 4)

        cw.setLayout(grid)
        self.cw = cw
        self.grid = grid
        
        loadWidget.setLayout(loadGrid)
        self.loadWidget = loadWidget
        self.loadGrid = loadGrid
        self.loadWidget.hide()

        saveWidget.setLayout(saveGrid)
        self.saveWidget = saveWidget
        self.saveGrid = saveGrid
        self.saveWidget.hide()

        segWidget.setLayout(segGrid)
        self.segWidget = segWidget
        self.segGrid = segGrid
        self.segWidget.hide()

        self.setWindowTitle('LISA')

        self.show()


    def btnLoad(self, event):
        self.cw.hide()
        self.setCentralWidget(self.loadWidget)
        self.loadWidget.show()

    def btnSave(self, event):
        self.cw.hide()
        self.setCentralWidget(self.saveWidget)
        self.saveWidget.show()

    def btnSegmentation(self, event):
        self.cw.hide()
        self.setCentralWidget(self.segWidget)
        self.segWidget.show()

    def btnMainMenu(self, event):
        self._initUI()

    def quit(self, event):
        return self.close()

    def run_debug(self, event):
        """
        Stop processing and start debugger in console. Function started by
        pressing "Debug" button wich is availeble after starting Lisa with
        -d parameter.
        """
        logger.debug('== Starting debug mode, leave it with command "c" =')
        from PyQt4.QtCore import pyqtRemoveInputHook
        pyqtRemoveInputHook()
        import ipdb; ipdb.set_trace()  # noqa BREAKPOINT

    def changeVoxelSize(self, val):
        self.scaling_mode = str(val)

    def setLabelText(self, obj, text):
        dlab = str(obj.text())
        obj.setText(dlab[:dlab.find(':')] + ': %s' % text)

    def getDcmInfo(self):
        vx_size = self.oseg.voxelsize_mm
        vsize = tuple([float(ii) for ii in vx_size])
        ret = ' %dx%dx%d,  %fx%fx%f mm' % (self.oseg.data3d.shape + vsize)

        return ret

    # def setVoxelVolume(self, vxs):
    #     self.voxel_volume = np.prod(vxs)

    def __get_datafile(self, app=False, directory=''):
        """
        Draw a dialog for directory selection.
        """

        from PyQt4.QtGui import QFileDialog
        if app:
            dcmdir = QFileDialog.getOpenFileName(
                caption='Select Data File',
                directory=directory
                # ptions=QFileDialog.ShowDirsOnly,
            )
        else:
            app = QApplication(sys.argv)
            dcmdir = QFileDialog.getOpenFileName(
                caption='Select DICOM Folder',
                # ptions=QFileDialog.ShowDirsOnly,
                directory=directory
            )
            # pp.exec_()
            app.exit(0)
        if len(dcmdir) > 0:

            dcmdir = "%s" % (dcmdir)
            dcmdir = dcmdir.encode("utf8")
        else:
            dcmdir = None
        return dcmdir

    def __get_datadir(self, app=False, directory=''):
        """
        Draw a dialog for directory selection.
        """

        from PyQt4.QtGui import QFileDialog
        if app:
            dcmdir = QFileDialog.getExistingDirectory(
                caption='Select DICOM Folder',
                options=QFileDialog.ShowDirsOnly,
                directory=directory
            )
        else:
            app = QApplication(sys.argv)
            dcmdir = QFileDialog.getExistingDirectory(
                caption='Select DICOM Folder',
                options=QFileDialog.ShowDirsOnly,
                directory=directory
            )
            # pp.exec_()
            app.exit(0)
        if len(dcmdir) > 0:

            dcmdir = "%s" % (dcmdir)
            dcmdir = dcmdir.encode("utf8")
        else:
            dcmdir = None
        return dcmdir

    def loadDataFile(self):
        self.statusBar().showMessage('Reading data file...')
        QApplication.processEvents()

        oseg = self.oseg
        # f oseg.datapath is None:
        #     seg.datapath = dcmreader.get_dcmdir_qt(
        #        app=True,
        #        directory=self.oseg.input_datapath_start
        if 'loadfiledir' in self.oseg.cache.data.keys():
            directory = self.oseg.cache.get('loadfiledir')
        else:
            directory = self.oseg.input_datapath_start
        #
        oseg.datapath = self.__get_datafile(
            app=True,
            directory=directory
        )

        if oseg.datapath is None:
            self.statusBar().showMessage('No data path specified!')
            return
        head, teil = os.path.split(oseg.datapath)
        self.oseg.cache.update('loadfiledir', head)

        self.importDataWithGui()

    def sync_lisa_data(self):
        """
        set sftp_username and sftp_password in ~/lisa_data/organ_segmentation.config
        """
        self.statusBar().showMessage('Sync in progress...')
        login = loginWindow.Login(checkLoginFcn=self.__loginCheckFcn)
        login.exec_()
        # print repr(self.oseg.sftp_username)
        # print repr(self.oseg.sftp_password)
        try:
            self.oseg.sync_lisa_data(self.oseg.sftp_username, self.oseg.sftp_password, callback=self._print_sync_progress)
        except:
            import traceback
            traceback.print_exc()
            logger.error(traceback.format_exc())

            QtGui.QMessageBox.warning(
                self, 'Error', 'Sync error')

        self.oseg.sftp_username = ''
        self.oseg.sftp_password = ''
        self.statusBar().showMessage('Sync finished')

    def __loginCheckFcn(self, textname, textpass):
        self.oseg.sftp_username = textname
        self.oseg.sftp_password = textpass
        return True

    def _print_sync_progress(self, transferred, toBeTransferred):
        self.statusBar().showMessage('Sync of current file {0} % '.format((100.0 * transferred) / toBeTransferred ))

        # print "Transferred: {0}\tOut of: {1}".format(transferred, toBeTransferred)

    def loadDataDir(self):
        self.statusBar().showMessage('Reading DICOM directory...')
        QApplication.processEvents()

        oseg = self.oseg
        if 'loaddir' in self.oseg.cache.data.keys():
            directory = self.oseg.cache.get('loaddir')
        else:
            directory = self.oseg.input_datapath_start

        oseg.datapath = self.__get_datadir(
            app=True,
            directory=directory
        )

        if oseg.datapath is None:
            self.statusBar().showMessage('No DICOM directory specified!')
            return
        # head, teil = os.path.split(oseg.datapath)
        self.oseg.cache.update('loaddir', oseg.datapath)

        self.importDataWithGui()

    def importDataWithGui(self):
        oseg = self.oseg

        reader = datareader.DataReader()

        # seg.data3d, metadata =
        datap = reader.Get3DData(oseg.datapath, dataplus_format=True)
        # rint datap.keys()
        # self.iparams['series_number'] = self.metadata['series_number']
        # self.iparams['datapath'] = self.datapath
        oseg.import_dataplus(datap)
        self.setLabelText(self.text_dcm_dir, oseg.datapath)
        self.setLabelText(self.text_dcm_data, self.getDcmInfo())
        self.statusBar().showMessage('Ready')

    def cropDcm(self):
        oseg = self.oseg

        if oseg.data3d is None:
            self.statusBar().showMessage('No DICOM data!')
            return

        self.statusBar().showMessage('Cropping DICOM data...')
        QApplication.processEvents()

        pyed = QTSeedEditor(oseg.data3d, mode='crop',
                            voxelSize=oseg.voxelsize_mm)
        # @TODO
        mx = self.oseg.viewermax
        mn = self.oseg.viewermin
        width = mx - mn
        # enter = (float(mx)-float(mn))
        center = np.average([mx, mn])
        logger.debug("window params max %f min %f width, %f center %f" %
                     (mx, mn, width, center))
        pyed.changeC(center)
        pyed.changeW(width)
        pyed.exec_()

        crinfo = pyed.getROI()
        if crinfo is not None:
            tmpcrinfo = []
            for ii in crinfo:
                tmpcrinfo.append([ii.start, ii.stop])

            # seg.data3d = qmisc.crop(oseg.data3d, oseg.crinfo)
            oseg.crop(tmpcrinfo)

        self.setLabelText(self.text_dcm_data, self.getDcmInfo())
        self.statusBar().showMessage('Ready')

    def maskRegion(self):
        if self.oseg.data3d is None:
            self.statusBar().showMessage('No DICOM data!')
            return

        self.statusBar().showMessage('Mask region...')
        QApplication.processEvents()

        pyed = QTSeedEditor(
                self.oseg.data3d, mode='mask',
                voxelSize=self.oseg.voxelsize_mm,
                contours=((self.oseg.segmentation == 0).astype(np.int8)*2)
                )

        pyed.contours_old = pyed.contours.copy()
        # initial mask set
        # pyed.masked = np.ones(self.oseg.data3d.shape, np.int8)
        # pyed.masked = (self.oseg.segmentation == 0).astype(np.int8)

        mx = self.oseg.viewermax
        mn = self.oseg.viewermin
        width = mx - mn
        # enter = (float(mx)-float(mn))
        center = np.average([mx, mn])
        logger.debug("window params max %f min %f width, %f center %f" %
                     (mx, mn, width, center))
        pyed.changeC(center)
        pyed.changeW(width)
        pyed.exec_()

        self.statusBar().showMessage('Ready')

    def loadSegmentationFromFile(self):
        """
        Function make GUI for reading segmentaion file and calls
        organ_segmentation function to do the work.
        """
        self.statusBar().showMessage('Reading segmentation from file ...')
        QApplication.processEvents()
        logger.debug("import segmentation from file")
        logger.debug(str(self.oseg.crinfo))
        logger.debug(str(self.oseg.data3d.shape))
        logger.debug(str(self.oseg.segmentation.shape))
        seg_path = self.__get_datafile(
            app=True,
            directory=self.oseg.input_datapath_start
        )
        if seg_path is None:
            self.statusBar().showMessage('No data path specified!')
            return
        self.oseg.import_segmentation_from_file(seg_path)
        self.statusBar().showMessage('Ready')

    def __evaluation_to_text(self, evaluation):
        overall_score = evaluation['sliver_overall_pts']
        # \
        #     volumetry_evaluation.sliver_overall_score_for_one_couple(
        #         score
        #     )

        logger.info('overall score: ' + str(overall_score))
        return "Sliver score: " + str(overall_score)

    def compareSegmentationWithFile(self):
        """
        Function make GUI for reading segmentaion file to compare it with
        actual segmentation using Sliver methodics. It calls
        organ_segmentation function to do the work.
        """
        self.statusBar().showMessage('Reading segmentation from file ...')
        QApplication.processEvents()
        logger.debug("import segmentation from file to compare by sliver")
        logger.debug(str(self.oseg.crinfo))
        logger.debug(str(self.oseg.data3d.shape))
        logger.debug(str(self.oseg.segmentation.shape))
        if 'loadcomparedir' in self.oseg.cache.data.keys():
            directory = self.oseg.cache.get('loadcomparedir')
        else:
            directory = self.oseg.input_datapath_start
        #
        seg_path = self.__get_datafile(
            app=True,
            directory=directory
        )
        if seg_path is None:
            self.statusBar().showMessage('No data path specified!')
            return
        evaluation, segdiff = \
            self.oseg.sliver_compare_with_other_volume_from_file(seg_path)
        print 'Evaluation: ', evaluation
        # print 'Score: ', score

        text = self.__evaluation_to_text(evaluation)

        segdiff[segdiff == -1] = 2
        logger.debug('segdif unique ' + str(np.unique(segdiff)))

        QApplication.processEvents()
        try:

            ed = sed3.sed3qt(
                self.oseg.data3d,
                seeds=segdiff,
                # contour=(self.oseg.segmentation == self.oseg.slab['liver'])
                contour=self.oseg.segmentation
            )
            ed.exec_()
        except:
            ed = sed3.sed3(
                self.oseg.data3d,
                seeds=segdiff,
                contour=(self.oseg.segmentation == self.oseg.slab['liver'])
            )
            ed.show()

        head, teil = os.path.split(seg_path)
        self.oseg.cache.update('loadcomparedir', head)
        # self.setLabelText(self.text_seg_data, text)
        self.statusBar().showMessage('Ready')

    def liverSeg(self):
        self.statusBar().showMessage('Performing liver segmentation ...')
        if self.oseg.data3d is None:
            self.statusBar().showMessage('No DICOM data!')
            return

        self.oseg.interactivity(
            min_val=self.oseg.viewermin,
            max_val=self.oseg.viewermax)
        self.checkSegData('auto. seg., ')
        self.statusBar().showMessage('Ready')

    def autoSeg(self):
        self.statusBar().showMessage('Performing automatic segmentation...')
        QApplication.processEvents()
        if self.oseg.data3d is None:
            self.statusBar().showMessage('No DICOM data!')
            return

        self.oseg.run_sss()
        self.statusBar().showMessage('Automatic segmentation finished')

    def manualSeg(self):
        oseg = self.oseg
        # rint 'ms d3d ', oseg.data3d.shape
        # rint 'ms seg ', oseg.segmentation.shape
        # rint 'crinfo ', oseg.crinfo
        if oseg.data3d is None:
            self.statusBar().showMessage('No DICOM data!')
            return
        sgm = oseg.segmentation.astype(np.uint8)

        pyed = QTSeedEditor(oseg.data3d,
                            seeds=sgm,
                            mode='draw',
                            voxelSize=oseg.voxelsize_mm, volume_unit='ml')
        pyed.exec_()

        oseg.segmentation = pyed.getSeeds()
        self.oseg.processing_time = \
            datetime.datetime.now() - self.oseg.time_start
        self.checkSegData('manual seg., ')

    def checkSegData(self, msg):
        oseg = self.oseg
        if oseg.segmentation is None:
            self.statusBar().showMessage('No segmentation!')
            return

        nzs = oseg.segmentation.nonzero()
        nn = nzs[0].shape[0]
        if nn > 0:
            voxelvolume_mm3 = np.prod(oseg.voxelsize_mm)
            tim = self.oseg.processing_time

            if self.oseg.volume_unit == 'ml':
                # import datetime
                # timstr = str(datetime.timedelta(seconds=round(tim)))
                timstr = str(tim)
                # logger.debug('tim = ' + str(tim))
                aux = 'volume = %.2f [ml] , time = %s' %\
                      (nn * voxelvolume_mm3 / 1000, timstr)
            else:
                aux = 'volume = %.6e mm3' % (nn * voxelvolume_mm3, )
            self.setLabelText(self.text_seg_data, msg + aux)
            self.statusBar().showMessage('Ready')

        else:
            self.statusBar().showMessage('No segmentation!')

    def saveOut(self, event=None, filename=None):
        """
        Open dialog for selecting file output filename. Uniqe name is as
        suggested.
        """
        if self.oseg.segmentation is not None:
            self.statusBar().showMessage('Saving segmentation data...')
            QApplication.processEvents()
            ofilename = self.oseg.get_standard_ouptut_filename()
            filename = str(QFileDialog.getSaveFileName(
                self,
                "Save file",
                ofilename,
                filter="*.pklz"))

            logger.info('Data saved to: ' + ofilename)

            self.oseg.save_outputs(filename)
            self.statusBar().showMessage('Ready')

        else:
            self.statusBar().showMessage('No segmentation data!')

    def btnUpdate(self, event=None):

        self.statusBar().showMessage('Checking for update ...')
        self.oseg.update()
        self.statusBar().showMessage('Update finished. Please restart Lisa')

    def btnAutomaticLiverSeeds(self, event=None):
        self.statusBar().showMessage('Automatic liver seeds...')
        self.oseg.automatic_liver_seeds()
        self.statusBar().showMessage('Ready')

    def btnSaveSegmentation(self, event=None):
        """
        Not fully implemented yet
        :param event:
        :return:
        """
        import dictGUI
        slab_selection = {}
        for label, value in  self.oseg.slab.iteritems():
            slab_selection[label] = True

        slab_selection = dictGUI.dictGui(slab_selection)
        # TODO use some function from oseg to store

    def btnConfig(self, event=None):
        import config
        import organ_segmentation as los
        import lisaConfigGui as lcg
        d = los.lisa_config_init()

        newconf = lcg.configGui(d)

        if newconf is None:
# reset config
            os.remove(
                os.path.join(
                    d['output_datapath'],
                    'organ_segmentation.config')
            )
        else:
            config.save_config(
                newconf,
                os.path.join(
                    newconf['output_datapath'],
                    'organ_segmentation.config')
            )
        
        self.quit(event)

    def btnSaveOutDcmOverlay(self, event=None, filename=None):
        if self.oseg.segmentation is not None:
            self.statusBar().showMessage('Saving segmentation data...')
            QApplication.processEvents()

            self.oseg.save_outputs_dcm_overlay()
            self.statusBar().showMessage('Ready')

        else:
            self.statusBar().showMessage('No segmentation data!')

    def btnSaveOutDcm(self, event=None, filename=None):
        logger.info('Pressed button "Save Dicom"')
        self.statusBar().showMessage('Saving input data...')
        QApplication.processEvents()
        ofilename = self.oseg.get_standard_ouptut_filename(filetype='dcm')
        filename = str(QFileDialog.getSaveFileName(
            self,
            "Save file",
            ofilename,
            filter="*.*"))

        self.oseg.save_input_dcm(filename)
        logger.info('Input data saved to: ' + filename)
        self.statusBar().showMessage('Ready')
        if self.oseg.segmentation is not None:
            self.statusBar().showMessage('Saving segmentation data...')
            QApplication.processEvents()
            filename = filename[:-4] + '-seg' + filename[-4:]
            logger.debug('saving to file: ' + filename)
            # osfilename = self.oseg.get_standard_ouptut_filename(
            #     filetype='dcm')
            self.oseg.save_outputs_dcm(filename)

            self.statusBar().showMessage('Ready')
        else:
            self.statusBar().showMessage('No segmentation data!')

    def btnVirtualResectionPV(self):
        self._virtual_resection('PV')

    def btnVirtualResectionPlanar(self):
        self._virtual_resection('planar')

    def _virtual_resection(self, method='planar'):
        # mport vessel_cut

        self.statusBar().showMessage('Performing virtual resection ...')
        data = {'data3d': self.oseg.data3d,
                'segmentation': self.oseg.segmentation,
                'slab': self.oseg.slab,
                'voxelsize_mm': self.oseg.voxelsize_mm
                }
        cut = virtual_resection.resection(data, method=method)
        self.oseg.segmentation = cut['segmentation']
        self.oseg.slab = cut['slab']

        # rint

        voxelvolume_mm3 = np.prod(self.oseg.voxelsize_mm)
        v1 = np.sum(cut['segmentation'] == self.oseg.slab['liver'])
        v2 = np.sum(cut['segmentation'] == self.oseg.slab['resected_liver'])
        v1 = (v1) * voxelvolume_mm3
        v2 = (v2) * voxelvolume_mm3
        aux = "volume = %.4g l, %.4g/%.4g (%.3g/%.3g %% )" % (
            (v1 + v2) * 1e-6,
            (v1) * 1e-6,
            (v2) * 1e-6,
            100 * v1 / (v1 + v2),
            100 * v2 / (v1 + v2)
        )
        self.setLabelText(self.text_seg_data, aux)


    def btnLesionLocalization(self):
        self.oseg.lesionsLocalization()

    def btnPortalVeinSegmentation(self):
        """
        Function calls segmentation.vesselSegmentation function.
        """

        self.statusBar().showMessage('Vessel segmentation ...')
        self.oseg.portalVeinSegmentation()
        self.statusBar().showMessage('Ready')

    def btnSavePortalVeinTree(self):
        self.statusBar().showMessage('Saving vessel tree ...')
        QApplication.processEvents()
        self.oseg.saveVesselTree('porta')
        self.statusBar().showMessage('Ready')

    def btnSaveHepaticVeinsTree(self):
        self.statusBar().showMessage('Saving vessel tree ...')
        QApplication.processEvents()
        self.oseg.saveVesselTree('hepatic_veins')
        self.statusBar().showMessage('Ready')

    def btnHepaticVeinsSegmentation(self):
        """
        Function calls segmentation.vesselSegmentation function.
        """
        self.statusBar().showMessage('Vessel segmentation ...')
        self.oseg.hepaticVeinsSegmentation()
        self.statusBar().showMessage('Ready')

    def btnLog(self):
        import logWindow
        import os.path as op
        fn = op.expanduser("~/lisa_data/lisa.log")
        form = logWindow.LogViewerForm(fn) #, qapp=self.app)
        form.show()
        form.exec_()

    def btnRandomRotate(self):
        self.oseg.random_rotate()

    def btnRotateZ(self):
        pass


    def onAlternativeSegmentationParams(self, text):
        self.oseg.update_parameters_based_on_label(str(text))

    def view3D(self):
        # rom seg2mesh import gen_mesh_from_voxels, mesh2vtk, smooth_mesh
        # rom viewer import QVTKViewer
        oseg = self.oseg
        if oseg.segmentation is not None:
            pts, els, et = gen_mesh_from_voxels(oseg.segmentation,
                                                oseg.voxelsize_mm,
                                                etype='q', mtype='s')
            pts = smooth_mesh(pts, els, et,
                              n_iter=10)
            vtkdata = mesh2vtk(pts, els, et)
            view = QVTKViewer(vtk_data=vtkdata)
            view.exec_()

        else:
            self.statusBar().showMessage('No segmentation data!')
