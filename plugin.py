###########################################################################
__version__             = "0.1.0"
###########################################################################

from Screens.Screen import Screen
from Components.Label import Label
from Components.ActionMap import ActionMap
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
from Components.ProgressBar import ProgressBar
from Tools.Downloader import downloadWithProgress
from enigma import eTimer

import sys
import logging
import os
import io
import re
import unicodedata
import json
import urllib2
import ast
import threading
import time
import uuid
import urllib
import re
from subprocess import call
import time
# import gc

__bouquetGroup__        = ["bouquets.radio", "bouquets.tv"]
__e2dir__               = "/etc/enigma2/"
__lambedbFile__         = __e2dir__ + 'lamedb5'
__ignoreChannels__      = ['SID 0x']
__localPiconDirectory__ = "/usr/share/enigma2/picon/"
__urlPicons__           = "https://hk319yfwbl.execute-api.sa-east-1.amazonaws.com/prod"
__updateurl__           = "https://raw.githubusercontent.com/josemoraes99/enigma2-plugin-extensions-canaispixel/master/plugin.py"
__checkupdate__         = True

###########################################################################

class BufferThread():
    def __init__(self):
        self.progress = 0
        self.downloading = False
        self.error = ""
        self.download = None
        self.qtdDownloading = 0
        self.qtdFinished = 0
        self.dlConcurrent = 0
        self.dlQueue = []
        self.fname = ""

    def startDownloading(self, url, file):
        self.progress = 0
        self.downloading = True
        self.error = ""
        self.fname = file
        self.qtdDownloading += 1
        self.dlQueue.append([url, file])

    def processQueue(self):
        while self.dlConcurrent < 7 and len( self.dlQueue ) > 0:
            url = self.dlQueue[0][0]
            file = self.dlQueue[0][1]
            self.download = downloadWithProgress(url, file)
            self.download.addProgress(self.httpProgress)
            self.download.start().addCallback(self.httpFinished).addErrback(self.httpFailed)
            self.dlConcurrent += 1
            self.dlQueue.pop(0)

    def httpProgress(self, recvbytes, totalbytes):
        self.progress = int(100 * recvbytes / float(totalbytes))

    def httpFinished(self, string=""):
        print("Download Finished " + self.fname)
        self.qtdFinished += 1
        self.dlConcurrent -= 1

        self.downloading = False
        if string is not None:
            self.error = str(string)
        else:
            self.error = ""

    def httpFailed(self, failure_instance=None, error_message=""):
        self.downloading = False
        if error_message == "" and failure_instance is not None:
            error_message = failure_instance.getErrorMessage()
            self.error = str(error_message)

    def stop(self):
        self.progress = 0
        self.downloading = False
        self.error = ""
        self.download.stop()

bufferThread = BufferThread()

###########################################################################

class HalloWorldScreen(Screen): 
    skin = """<screen position="130,150" size="920,450" title="Canais Pixel - Picons" >
            <widget name="myLabel" position="10,50" size="900,300" font="Regular;20"/>
            <widget name="progress" position="260,370" size="400,14" pixmap="skin_default/progress_big.png" borderWidth="2" borderColor="#cccccc" />
        </screen>"""
        # backgroundColor="green"
    mensagemLabel = ""

    def __init__(self, session, args = None): 
        self.session = session
        self.time = time
        Screen.__init__(self, session)

        self["myLabel"] = Label( ("Pressione OK para iniciar o download ou EXIT para sair.") )
        self["myActionMap"] = ActionMap(["SetupActions"],
        {
            "ok": self.myMsg,
            "cancel": self.cancel
        }, -1)
        self["progress"] = ProgressBar()
        self["progress"].setValue(0)

        self.infoTimer = eTimer()
        self.infoTimer.timeout.get().append(self.updateInfo)
        self.downloading = False
        self.dlFinished = False

    def myMsg(self):
        print ("\n[HalloWorldMsg] OK pressed \n")
        if self.dlFinished == True:
            self.close(False,self.session)
        else:
            if self.downloading == False:
                self.replaceLabel( "Obtendo lista de canais" )
                self.downloading = True
                fileList = iniciaDownloadPicons(self)
                self.processList(fileList)

    def cancel(self):
        print ("\n[HalloWorldMsg] cancel\n")
        if self.downloading == False:
            self.close(False,self.session)

    def replaceLabel(self, msg):
        if self.mensagemLabel == "":
            self.mensagemLabel = msg
        else:
            self.mensagemLabel += "\n" + msg
        self["myLabel"].setText( self.mensagemLabel )

    def processList(self,f):
        piconsList = []

        for file in f:
            if file[1].strip() != "":
                piconsList.append(file[1])

        uuidOne = uuid.getnode()
        piconsList = list(dict.fromkeys(piconsList))
        data = {'src': 'e2','node': uuidOne,'listChannel': piconsList}
        data = json.dumps( data )
        print(data)
        req = urllib2.Request(__urlPicons__, data, {'Content-Type': 'application/json'})
        fil = urllib2.urlopen(req)
        response = json.load(fil)
        fil.close()
        listURL = ast.literal_eval(response)  # procurar alternativa

        self["progress"].setValue(0)
        for file in f:
            for l in listURL:
                if file[1] == l[0]:
                    print("download " + file[0])
                    bufferThread.startDownloading(l[1], __localPiconDirectory__ + file[0])

        self.replaceLabel( "Iniciando download" )
        self.infoTimer.start(300, False)

    def updateInfo(self):
        bufferThread.processQueue()
        downloading = bufferThread.qtdDownloading
        finished = bufferThread.qtdFinished
        prog = int ( round( (float(finished) / float(downloading)) * 100 ) )
        self["progress"].setValue(prog)

        print( "dl --> " + str( bufferThread.qtdDownloading ) + ", finished --> " + str( bufferThread.qtdFinished ) + ", " + str (prog) + "%")
        if downloading > 0 and downloading == finished:
            self.infoTimer.stop()
            self.downloading = False
            self.dlFinished = True
            self.replaceLabel( "Concluido" )
            self.replaceLabel( "Pressione OK para sair" )

###########################################################################
def main(session, **kwargs):
    print ("\n[Hallo World] start\n")
    if __checkupdate__:
        print("check for update")
        updateReturn = update(__updateurl__)
        if updateReturn:
            print("updgraded")
            # logging.info( "Reiniciando script" )
            # python = sys.executable
            # os.execl(python, python, *sys.argv)
    session.open(HalloWorldScreen)
###########################################################################
def Plugins(**kwargs):
    return PluginDescriptor(
        name="Canais Pixel",
        description="Download de picons " + __version__,
        where = PluginDescriptor.WHERE_PLUGINMENU,
        icon="icon.png",
        fnc=main)

def lerBouquetGroup( g ):
    bResult = []
    for b in g:
        bResult = bResult + lerArquivoBouquet( b )

    listChan = []
    for f in bResult:
        listChan = listChan + lerArquivoUserBouquet( f )

    listChClean = []
    for l in listChan:
        if l not in listChClean:
            listChClean.append(l)

    return listChClean

def lerArquivoBouquet( f ):
    fileR = __e2dir__ + f
    # logging.info( "Lendo arquivo " + fileR )
    # cl.replaceLabel( "Lendo arquivo " + fileR )
    if os.path.isfile( fileR ):
        with io.open( fileR , encoding='utf-8', errors='ignore') as f:
            resp = []
            for line in f:
                if line.startswith( "#SERVICE" ):
                    resp.append( line.split('BOUQUET "')[1].split('" ')[0] )
            return resp

    else:
        # logging.info( "Arquivo nao encontrado" )
        exit()

def lerArquivoUserBouquet( f ):
    excludeBouquets=["1:0:CA","1:320:0"] # tres primeiros
    fileR = __e2dir__ + f
    channels = []
    # logging.info( "Lendo arquivo " + fileR )
    # cl.replaceLabel( "Lendo arquivo " + fileR )
    if os.path.isfile( fileR ):
        with io.open( fileR , encoding='utf-8', errors='ignore') as f:
            resp = []
            for line in f:
                if line.startswith( "#SERVICE" ):
                    lineSpl = line.split('#SERVICE ')[1]
                    srvc = ":".join(lineSpl.split(":", 10)[:10])
                    strSrvc = ":".join(srvc.split(":", 3)[:3])
                    if not strSrvc in excludeBouquets:
                        channels.append(srvc)
            return channels

def lerLameDb(f):
    # logging.info( "Lendo arquivo " + f )
    if os.path.isfile(f):
        with io.open(f, encoding='utf-8', errors='ignore') as f:
            lDb = []
            for line in f:
                if line.startswith( "s:" ):
                    chName = line.split(",")[1].strip().strip('"')
                    if chName != '':
                        lDb.append(line.strip())
            return lDb
    else:
        # logging.info( "Arquivo nao encontrado" )
        exit()

def gerarLista(c,l,ign):
    # logging.info( "Processando lista" )
    chan =[]
    for item in c:
        for lis in l:
            lt = lis.split(",")[0].upper()
            if item.split(":")[3] == lt.split(":")[1].lstrip("0") and item.split(":")[5] == lt.split(":")[4].lstrip("0"):
                nomeCanal = lis.split(",")[1].lstrip('""').rstrip('""')
                for i in ign:
                    if i not in nomeCanal:
                        canalclean = re.sub(re.compile('\W'), '', ''.join(c.lower() for c in unicodedata.normalize('NFKD', lis.split(",")[1].replace("+", "mais")).encode('ascii', 'ignore') if not c.isspace()))
                        # canalFinal = 'canal' + canalclean + '.png'

                        filenameE2 = item.replace(":", "_").upper() + '.png'
                        chan.append([filenameE2,canalclean])
    return chan

def iniciaDownloadPicons(cl):

    channelList = lerBouquetGroup( __bouquetGroup__ )

    lameDb = lerLameDb( __lambedbFile__ )

    listFiles = gerarLista(channelList,lameDb,__ignoreChannels__)

    return listFiles

###########################################################################

def update(dl_url, force_update=False):
    """
Attempts to download the update url in order to find if an update is needed.
If an update is needed, the current script is backed up and the update is
saved in its place.
"""
    def compare_versions(vA, vB):
        """
Compares two version number strings
@param vA: first version string to compare
@param vB: second version string to compare
@author <a href="http_stream://sebthom.de/136-comparing-version-numbers-in-jython-pytho/">Sebastian Thomschke</a>
@return negative if vA < vB, zero if vA == vB, positive if vA > vB.
"""
        if vA == vB: return 0

        def num(s):
            if s.isdigit(): return int(s)
            return s

        seqA = map(num, re.findall('\d+|\w+', vA.replace('-SNAPSHOT', '')))
        seqB = map(num, re.findall('\d+|\w+', vB.replace('-SNAPSHOT', '')))

        # this is to ensure that 1.0 == 1.0.0 in cmp(..)
        lenA, lenB = len(seqA), len(seqB)
        for i in range(lenA, lenB): seqA += (0,)
        for i in range(lenB, lenA): seqB += (0,)

        rc = cmp(seqA, seqB)

        if rc == 0:
            if vA.endswith('-SNAPSHOT'): return -1
            if vB.endswith('-SNAPSHOT'): return 1
        return rc

    # dl the first 256 bytes and parse it for version number
    try:
        http_stream = urllib.urlopen(dl_url)
        # update_file = http_stream.read(256)
        update_file = http_stream.read(300)
        http_stream.close()

    except IOError, (errno, strerror):
        logging.info( "Unable to retrieve version data" )
        logging.info( "Error %s: %s" % (errno, strerror) )
        return

    match_regex = re.search(r'__version__ *= *"(\S+)"', update_file)
    if not match_regex:
        logging.info( "No version info could be found" )
        return
    update_version = match_regex.group(1)

    if not update_version:
        logging.info( "Unable to parse version data" )
        return

    if force_update:
        logging.info( "Forcing update, downloading version %s..." % update_version )

    else:
        cmp_result = compare_versions(__version__, update_version)
        if cmp_result < 0:
            logging.info( "Newer version %s available, downloading..." % update_version )
        elif cmp_result > 0:
            logging.info( "Local version %s newer then available %s, not updating." % (__version__, update_version) )
            return
        else:
            logging.info( "You already have the latest version." )
            return

    # dl, backup, and save the updated script
    # app_path = os.path.realpath(sys.argv[0])
    # if __asModule__ == True:
    app_path = __file__

    if not os.access(app_path, os.W_OK):
        logging.info( "Cannot update -- unable to write to %s" % app_path )

    dl_path = app_path + ".new"
    backup_path = app_path + ".old"
    try:
        dl_file = open(dl_path, 'w')
        http_stream = urllib.urlopen(dl_url)
        total_size = None
        bytes_so_far = 0
        chunk_size = 8192
        try:
            total_size = int(http_stream.info().getheader('Content-Length').strip())
        except:
            # The header is improper or missing Content-Length, just download
            dl_file.write(http_stream.read())

        while total_size:
            chunk = http_stream.read(chunk_size)
            dl_file.write(chunk)
            bytes_so_far += len(chunk)

            if not chunk:
                break

            percent = float(bytes_so_far) / total_size
            percent = round(percent*100, 2)
            sys.stdout.write("Downloaded %d of %d bytes (%0.2f%%)\r" %
                (bytes_so_far, total_size, percent))

            if bytes_so_far >= total_size:
                sys.stdout.write('\n')

        http_stream.close()
        dl_file.close()
    except IOError, (errno, strerror):
        logging.info( "Download failed" )
        logging.info( "Error %s: %s" % (errno, strerror) )
        return

    try:
        os.rename(app_path, backup_path)
    except OSError, (errno, strerror):
        logging.info( "Unable to rename %s to %s: (%d) %s" % (app_path, backup_path, errno, strerror) )
        return

    try:
        os.rename(dl_path, app_path)
    except OSError, (errno, strerror):
        logging.info( "Unable to rename %s to %s: (%d) %s" % (dl_path, app_path, errno, strerror) )
        return

    try:
        import shutil
        shutil.copymode(backup_path, app_path)
    except:
        os.chmod(app_path, 0755)

    logging.info( "New version installed as %s" % app_path )
    logging.info( "(previous version backed up to %s)" % (backup_path) )
    return True
