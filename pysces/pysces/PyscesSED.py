"""
PySCeS - Python Simulator for Cellular Systems (http://pysces.sourceforge.net)

Copyright (C) 2004-2013 B.G. Olivier, J.M. Rohwer, J.-H.S Hofmeyr all rights reserved,

Brett G. Olivier (bgoli@users.sourceforge.net)
Triple-J Group for Molecular Cell Physiology
Stellenbosch University, South Africa.

Permission to use, modify, and distribute this software is given under the
terms of the PySceS (BSD style) license. See LICENSE.txt that came with
this distribution for specifics.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
Brett G. Olivier
"""

import os, time, numpy, itertools, cStringIO, subprocess, zipfile, cPickle
import pysces

class SBWSEDMLWebApps:
    """
    Class that holds useful methods for using SBW Webapps via a SUDS provided soap client

    """

    Kclient = None
    SBWSEDMLURI = "http://sysbioapps.dyndns.org/SED-ML%20Web%20Tools/Services/SedMLService.asmx?WSDL"
    HAVE_SUDS = False
    _SED_CURRENT_ = False


    def __init__(self, url=None):
        """
        Attempt to create a connector if SUDS is install

        - *url* the url to the SBW SED-ML SOAP web services only set if the default doesn't work

        """
        if url == None:
            url = self.SBWSEDMLURI

        try:
            import suds
            self.HAVE_SUDS = True
        except:
            print('\nERROR: SUDS import error please install from http://pypi.python.org/pypi/suds (or easy_install suds)\n')
            self.HAVE_SUDS = False
        try:
            self.Kclient = suds.client.Client(url)
            self.SBWSEDMLURI = url
        except:
            print('\nERROR: Error connecting to SBW SED-ML web-services \"{}\" please check your internet connection\n'.format(url))
            self.HAVE_SUDS = False

    def GetVersion(self):
        """
        The ubiquitous connection test, returns the webservices version

        """
        if not self.HAVE_SUDS or self.Kclient == None:
            print('\nERROR: No suds client or connection, cannot comply with your request\n')
            return None
        try:
            print('Connecting ...')
            g = self.Kclient.service.GetVersion()
            print('done.')
        except Exception, ex:
            print('\nERROR: GetVersion() exception\n')
            print ex
        return g

    def ConvertScriptToSedML(self, sedscript):
        """
        Attempts to convert a string containing a sedml script into SEDML.
        See http://libsedml.sourceforge.net/libSedML/SedMLScript.html for more information on SedML script

         - *sedscript* A string containing a sedml script

        """
        if not self.HAVE_SUDS or self.Kclient == None:
            print('\nERROR: No suds client or connection, cannot comply with your request\n')
            return None
        try:
            print('Connecting ...')
            g = self.Kclient.service.ConvertScriptToSedML(sedscript)
            print('done.')
        except Exception, ex:
            print('\nERROR: ConvertScriptToSedML() exception\n')
            print ex
        return g

class SED(object):
    script = None
    xml = None
    cntr = None
    sedpath = None
    models = None
    sims = None
    id = None
    tasks = None
    datagens = None
    plots2d = None
    libSEDMLpath = None
    __sedscript__ = None
    __sedxml__ = None
    __sedarchive__ = None
    omex_description = 'Created with PySCeS (http://pysces.sf.net)'
    HAVE_LIBSEDML = False
    HAVE_SBWSEDSOAP = False
    _SED_CURRENT_ = False
    _SED_XML_ = None
    sbwsedclient = None

    def __init__(self, id, sedpath, libSEDMLpath=None, sbwsedmluri=None):
        """
        Try to establish whether we have access to libSEDML locally installed or the SBW SEDML webservices

         - *libSEDMLpath* [default=None] uses the default path to "SedMLConsole.exe" unless specified
         - *sbwsedmluri* [default=None] uses the default uri for the SBW webservices unless specified

        """
        if libSEDMLpath == None:
            self.libSEDMLpath = "\"C:\\Program Files (x86)\\SED-ML Script Editor\\SedMLConsole.exe\""
        else:
            self.libSEDMLpath = libSEDMLpath

        if os.path.exists(self.libSEDMLpath):
            self.HAVE_LIBSEDML = True
        self.sbwsedclient = SBWSEDMLWebApps(sbwsedmluri)
        if self.sbwsedclient.HAVE_SUDS:
            self.HAVE_SBWSEDSOAP = True

        if not self.HAVE_LIBSEDML and not self.HAVE_SBWSEDSOAP:
            print('\nNo connection to libSEDML or SEDML webservices.')

        #self.sed = {}
        self.models = {}
        self.sims = {}
        self.tasks = {}
        self.datagens = {}
        self.plots2d = {}
        self.id = id
        self.sedpath = os.path.join(sedpath, id)
        self.cntr = itertools.count()

    def addModel(self, id, model):
        try:
            if not self.models.has_key(id):
                self.models[id] = model.clone()
            else:
                self.models[id] = model.clone()
        except:
            print('\nWARNING: model clone failed, using more than one model per SED is not recomended!\n')
            self.models[id] = model

    def addModelAlt(self, id, model):
        mid = str(time.time()).split('.')[0]
        storeObj(model, os.path.join(self.sedpath, mid))
        del model
        model = loadObj(os.path.join(self.sedpath, mid)+'.dat')
        if not self.models.has_key(id):
            self.models[id] = model
        else:
            self.models[id] = model
        os.remove(os.path.join(self.sedpath, mid)+'.dat')

    def addSimulation(self, id, start, end, steps, output, initial=None, algorithm='KISAO:0000019'):
        if initial == None:
            initial = start
        S = {'start' : start,
             'initial' : initial,
             'end' : end,
             'steps' : steps,
             'algorithm' : algorithm,
             'output' : output}
        self.sims[id] = S

    def addTask(self, id, sim_id, model_id):
        assert self.sims.has_key(sim_id), '\nBad simId'
        assert self.models.has_key(model_id), '\nBad modelId'
        self.tasks[id] = {'sim' : sim_id, 'model' : model_id}

    def addDataGenerator(self, var, task_id):
        if var.lower() == 'time':
            var = 'time'
        dgId = 'dg_%s_%s' % (task_id, var)
        # dgId = '%s' % (var)
        varId = '%s_%s' % (var, self.cntr.next())
        self.datagens[dgId] = {'varId' : varId, 'taskId' : task_id, 'var' : var}

    def addTaskDataGenerators(self, taskId):
        assert self.tasks.has_key(taskId), '\nBad taskId'
        print self.tasks
        for o_ in self.sims[self.tasks[taskId]['sim']]['output']:
            self.addDataGenerator(o_, taskId)

    def addPlot(self, plotId, plotName, listOfCurves):
        self.plots2d[plotId] = {'name' : plotName,
                                'curves' : listOfCurves}

    def addTaskPlot(self, taskId):
        plotId = '%s_plot' % taskId
        name = 'Plot generated for Task: %s' % taskId
        curves = []
        for o_ in self.sims[self.tasks[taskId]['sim']]['output']:
            if o_ not in ['Time','TIME', 'time']:

                curves.append(('dg_%s_time' % (taskId), 'dg_%s_%s' % (taskId, o_)))
        self.addPlot(plotId, name, curves)

    def writeSedScript(self, sedx=False):
        sedscr = cStringIO.StringIO()
        if not os.path.exists(self.sedpath):
            os.makedirs(self.sedpath)
        for m_ in self.models:
            if not sedx:
                mf = os.path.join(self.sedpath, '%s-%s.xml' % (self.id, m_))
                tmp = (m_, str(os.path.join(self.sedpath,'%s-%s.xml' % (self.id, m_))))
            else:
                if not os.path.exists(os.path.join(self.sedpath, 'sedxtmp')):
                    os.makedirs(os.path.join(self.sedpath, 'sedxtmp'))
                mf = os.path.join(self.sedpath, 'sedxtmp', '%s-%s.xml' % (self.id, m_))
                tmp = (m_, str('%s-%s.xml' % (self.id, m_)))
            pysces.interface.writeMod2SBML(self.models[m_], mf)
            sedscr.write("AddModel('%s', r'%s', 'urn:sedml:language:sbml')\n" % tmp)
        sedscr.write('\n')

        for s_ in self.sims:
            S = self.sims[s_]
            sedscr.write("AddTimeCourseSimulation('%s', '%s', %s, %s, %s, %s)\n" %  (s_,\
                    S['algorithm'], S['start'], S['initial'], S['end'], S['steps']))
        sedscr.write('\n')

        for t_ in self.tasks:
            T = self.tasks[t_]
            sedscr.write("AddTask(\'%s\', \'%s\', \'%s\')\n" % (t_, T['sim'], T['model']))
        sedscr.write('\n')

        for dg_ in self.datagens:
            D = self.datagens[dg_]
            sedscr.write("AddColumn('%s', [['%s', '%s', '%s']])\n" % (dg_, D['varId'], D['taskId'], D['var']))
        sedscr.write('\n')

        for p_ in self.plots2d:
            P = self.plots2d[p_]
            sedscr.write("AddPlot('%s', '%s', [" % (p_, P['name']))
            cstr = ''
            for c_ in P['curves']:
                cstr += "['%s', '%s']," % (c_[0], c_[1])
            sedscr.write(cstr[:-1])
            sedscr.write("])\n")
        sedscr.write('\n')

        print '\nThe SED\n++++++\n'
        sedscr.seek(0)
        print sedscr.read()
        sedscr.seek(0)
        if not sedx:
            sf = os.path.join(self.sedpath, '%s.txt' % (self.id))
        else:
            sf = os.path.join(self.sedpath, 'sedxtmp', '%s.txt' % (self.id))
        F = file(sf, 'w')
        F.write(sedscr.read())
        F.flush()
        F.close()
        self.__sedscript__ = sf
        print '\nSED-ML script files written to:', sf

    def writeSedXML(self, sedx=False):
        sedname = '%s.sed.xml' % (self.id)
        self.writeSedScript(sedx=sedx)
        if not sedx:
            sf = os.path.join(self.sedpath, sedname)
        else:
            sf = os.path.join(self.sedpath, 'sedxtmp', sedname)

        if self._SED_CURRENT_:
            print '\nBypass active: SED-ML files written to: %s' % self.sedpath
        elif self.HAVE_LIBSEDML:
            assert os.path.exists(self.libSEDMLpath)
            #sedname = '%s.sed.xml' % (self.id)
            #self.writeSedScript(sedx=sedx)
            #if not sedx:
                #sf = os.path.join(self.sedpath, sedname)
            #else:
                #sf = os.path.join(self.sedpath, 'sedxtmp', sedname)
            cmd = ['%s' % str(self.libSEDMLpath), '--fromScript', '%s' % str(self.__sedscript__), '%s' % str(sf)]
            print cmd
            try:
                a = subprocess.call(cmd)
            except Exception, ex:
                print '\nOops no SED: %s' % ex
            self.__sedxml__ = sf
            F = file(sf, 'r')
            self._SED_XML_ = F.read()
            F.close()
            del F
            print 'SED-ML files written to: %s' % self.sedpath
            self.__sedarchive__ = None
        elif self.HAVE_SBWSEDSOAP:
            print('\nINFO: PySCeS will now try to connect via internet to: http://sysbioapps.dyndns.org ...\n(press <ctrl>+<c> to abort)')
            time.sleep(5)
            #sedname = '%s.sed.xml' % (self.id)
            #self.writeSedScript(sedx=sedx)
            #if not sedx:
                #sf = os.path.join(self.sedpath, sedname)
            #else:
                #sf = os.path.join(self.sedpath, 'sedxtmp', sedname)

            F = file(self.__sedscript__, 'r')
            sedscr = F.read()
            F.close()
            self._SED_XML_ = self.sbwsedclient.ConvertScriptToSedML(sedscr)
            F = file(sf, 'w')
            F.write(self._SED_XML_)
            F.flush()
            F.close()

            self.__sedxml__ = sf
            print 'SED-ML files written to: %s' % self.sedpath
            self.__sedarchive__ = None
        else:
            raise RuntimeError, '\n'
        if self._SED_CURRENT_:
            F = file(self.__sedxml__, 'w')
            F.write(self._SED_XML_)
            F.flush()
            F.close()

    def writeSedXArchive(self):
        self.writeSedXML(sedx=True)
        sedxname = '%s.sed.sedx' % (self.id)
        #sedxname = '%s.sed.sedx.zip' % (self.id)
        ptmp = os.path.join(self.sedpath, 'sedxtmp')
        sf = os.path.join(self.sedpath, sedxname)
        self.__sedarchive__ = sf
        zf = zipfile.ZipFile(sf, mode='w', compression=zipfile.ZIP_STORED)
        zf.write(self.__sedxml__, arcname=os.path.split(self.__sedxml__)[-1])
        for m_ in self.models:
            modname = '%s-%s.xml' % (self.id, m_)
            modpath = os.path.join(ptmp, modname)
            zf.write(modpath, arcname=modname)
        zf.close()

        for f_ in os.listdir(ptmp):
            os.remove(os.path.join(ptmp, f_))
        os.removedirs(ptmp)
        if not self._SED_CURRENT_:
            self.__sedxml__ = None
        self.__sedscript__ = None
        print 'SED-ML archive created: %s' % sf

    def writeCOMBINEArchive(self):
        scTime = time.strftime('%Y-%m-%dT%H:%M:%S') + '%i:00' % (time.timezone/60/60)
        self.writeSedXML(sedx=True)
        sedxname = '%s.sed.omex' % (self.id)
        #sedxname = '%s.sed.omex.zip' % (self.id)
        sf = os.path.join(self.sedpath, sedxname)
        ptmp = os.path.join(self.sedpath, 'sedxtmp')
        self.__sedarchive__ = sf
        zf = zipfile.ZipFile(sf, mode='w', compression=zipfile.ZIP_STORED)
        zf.write(self.__sedxml__, arcname=os.path.split(self.__sedxml__)[-1])

        MFstr = ''
        MDstr = ''
        MFstr += '<omexManifest xmlns="http://identifiers.org/combine.specifications/omex-manifest">\n'
        MFstr += ' <content location="./manifest.xml" format="http://identifiers.org/combine.specifications/omex-manifest"/>\n'
        MFstr += ' <content location="./%s" format="http://identifiers.org/combine.specifications/sedml"/>\n' % os.path.split(self.__sedxml__)[-1]
        for m_ in self.models:
            modname = '%s-%s.xml' % (self.id, m_)
            modpath = os.path.join(ptmp, modname)
            zf.write(modpath, arcname=modname)
            MFstr += ' <content location="./%s" format="http://identifiers.org/combine.specifications/sbml"/>\n' % modname
        MFstr += ' <content location="./metadata.rdf" format="http://identifiers.org/combine.specifications/omex-metadata"/>'

        MF = file(os.path.join(ptmp, 'manifest.xml'), 'w')
        MF.write('<?xml version="1.0" encoding="utf-8"?>\n%s\n</omexManifest>\n' % MFstr)
        MF.close()

        MD = file(os.path.join(ptmp, 'metadata.rdf'), 'w')
        MD.write('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n')
        MD.write('    xmlns:dcterms="http://purl.org/dc/terms/"\n')
        MD.write('    xmlns:vCard="http://www.w3.org/2006/vcard/ns#">\n')
        MD.write(' <rdf:Description rdf:about="./%s">\n' % os.path.split(self.__sedxml__)[-1])
        MDstr += '   <dcterms:description>\n     %s\n    </dcterms:description>\n' % self.omex_description
        MDstr += '   <dcterms:created rdf:parseType="Resource">\n'
        MDstr += '    <dcterms:W3CDTF>%s</dcterms:W3CDTF>\n' % scTime
        MDstr += '   </dcterms:created>\n'
        MDstr += '   <dcterms:modified rdf:parseType="Resource">\n'
        MDstr += '    <dcterms:W3CDTF>%s</dcterms:W3CDTF>\n' % scTime
        MDstr += '   </dcterms:modified>\n'
        MD.write('%s' % MDstr)
        MD.write(' </rdf:Description>\n')
        MD.write('</rdf:RDF> \n')
        MD.close()

        zf.write(os.path.join(ptmp, 'manifest.xml'), arcname='manifest.xml')
        zf.write(os.path.join(ptmp, 'metadata.rdf'), arcname='metadata.rdf')
        zf.close()

        for f_ in os.listdir(ptmp):
            os.remove(os.path.join(ptmp, f_))
        os.removedirs(ptmp)
        if not self._SED_CURRENT_:
            self.__sedxml__ = None
        self.__sedscript__ = None
        print 'COMBINE archive created: %s' % sf

def storeObj(obj, filename):
    """
    Stores a Python *obj* as a serialised binary object in *filename*.dat

    """
    filename = filename+'.dat'
    F = file(filename, 'wb')
    cPickle.dump(obj, F, protocol=2)
    print 'Object serialised as %s' % filename
    F.close()

def loadObj(filename):
    """
    Loads a serialised Python cPickle from *filename* returns the Python object(s)

    """
    assert os.path.exists(filename), '\nTry again mate!'
    F = file(filename, 'rb')
    obj = cPickle.load(F)
    F.close()
    return obj