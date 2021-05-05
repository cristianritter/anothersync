import time
import logging
import shutil
import parse_config
import os
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from datetime import date, datetime
from pyzabbix import ZabbixMetric, ZabbixSender
from threading import Thread
import wx.adv
import wx
try:    
    print('Carregando configurações...')
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) # This is your Project Root
    configuration = parse_config.ConfPacket()
    configs = configuration.load_config('SYNC_FOLDERS, LOG_FOLDER, SYNC_TIMES, SYNC_EXTENSIONS, ZABBIX, SYNC_NAME')
    sleep_time = int(configs['SYNC_TIMES']['sync_with_no_events_time'])
    TRAY_TOOLTIP = 'FolderSync - ' + configs['SYNC_NAME']['name']
    icon_file = os.path.join(ROOT_DIR, 'icon.png')
    sincronizando = False
    evento_acontecendo = False
    metric_value = 0
    
    print("Definindo classes...")

    class TaskBarIcon(wx.adv.TaskBarIcon):
        def __init__(self, frame):
            self.frame = frame
            super(TaskBarIcon, self).__init__()
            self.set_icon(icon_file)
            self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

        def create_menu_item(self, menu, label, func):
                item = wx.MenuItem(menu, -1, label)
                menu.Bind(wx.EVT_MENU, func, id=item.GetId())
                menu.Append(item)
                return item

        def CreatePopupMenu(self):
            menu = wx.Menu()
            self.create_menu_item(menu, 'Abrir log', self.on_left_down)
            menu.AppendSeparator()
            self.create_menu_item(menu, 'Exit', self.on_exit)
            return menu

        def set_icon(self, path):
            icon = wx.Icon(path)
            self.SetIcon(icon, TRAY_TOOLTIP)

        def on_left_down(self, event):      
            frame.Show()
            
        def on_exit(self, event):
            wx.CallAfter(self.Destroy)
            self.frame.Close()
            

    class MyFrame(wx.Frame):    
        def __init__(self):
            title_ = 'FolderSync by EngNSC - ' + configs['SYNC_NAME']['name']
            super().__init__(parent=None, title=title_, style=wx.CAPTION, pos=(5, 5), size=(1080, 600))        
            panel = wx.Panel(self)
            coluna = wx.BoxSizer(wx.VERTICAL) 
            font = wx.Font(18, wx.DEFAULT, wx.NORMAL, wx.BOLD)
            self.title_txt = wx.StaticText(panel, label='FolderSync')
            self.title_txt.SetFont(font)
            font = wx.Font(9, wx.DEFAULT, wx.NORMAL, wx.BOLD, underline=True)
            self.subtitle_txt = wx.StaticText(panel, label='- Log de eventos -')
            self.subtitle_txt.SetFont(font)
            linha_titulo = wx.BoxSizer(wx.HORIZONTAL)
            linha_titulo.Add(self.title_txt, 0, wx.TOP, 20)
            linha_titulo.AddSpacer(30)
            linha_titulo.Add(self.subtitle_txt, 0, wx.TOP, 30)
            self.led1 =  wx.StaticText(panel, wx.ID_ANY, label='', size=(20,15))
            self.ld1txt = wx.StaticText(panel, label='Event in progress')
            self.led2 =  wx.StaticText(panel, wx.ID_ANY, "", size=(20,15))
            self.ld2txt = wx.StaticText(panel, label='All Sync in progress')
            self.led3 =  wx.StaticText(panel, wx.ID_ANY, "", size=(20,15))
            self.ld3txt = wx.StaticText(panel, label='Error detected')
            self.led1.SetBackgroundColour('gray')
            self.led2.SetBackgroundColour('gray')
            self.led3.SetBackgroundColour('gray')
            self.clear_btn = wx.StaticText(panel, label='(Limpar Erros)')
            self.clear_btn.Bind(wx.EVT_LEFT_DOWN, self.on_clean)
            font = wx.Font(7, wx.DEFAULT, wx.FONTSTYLE_ITALIC, wx.BOLD, underline=True)
            self.clear_btn.SetFont(font)
            self.cb1 = wx.CheckBox(panel, label='Events View')
            self.cb1.SetValue(True)
            self.cb1.Bind(wx.EVT_CHECKBOX, self.check_events, self.cb1)
            self.logpanel = wx.TextCtrl(panel, value='Ainda não existe um log disponível este mês.', style=wx.TE_MULTILINE | wx.TE_READONLY, size=(50,400))
            coluna.Add(linha_titulo, 0, wx.CENTER)
            coluna.AddSpacer(10)
            coluna.Add(self.logpanel, 0, wx.ALL | wx.EXPAND, 2) 
            linha_filter = wx.BoxSizer(wx.HORIZONTAL)
            linha_filter.Add(self.cb1, 0, wx.TOP, 5)
            linha_led = wx.BoxSizer(wx.HORIZONTAL)
            linha_led.Add(self.led1, 0, wx.TOP, 5)
            linha_led.AddSpacer(10)
            linha_led.Add(self.ld1txt, 0, wx.TOP, 5)
            linha_led.AddSpacer(20)
            linha_led.Add(self.led2, 0, wx.TOP, 5)
            linha_led.AddSpacer(10)
            linha_led.Add(self.ld2txt, 0, wx.TOP, 5)
            linha_led.AddSpacer(20)
            linha_led.Add(self.led3, 0, wx.TOP, 5)
            linha_led.AddSpacer(10)
            linha_led.Add(self.ld3txt, 0, wx.TOP, 5)
            linha_led.AddSpacer(20)
            linha_led.Add(self.clear_btn, 0, wx.TOP, 10)
            hide_button = wx.Button(panel, label='Fechar')
            hide_button.Bind(wx.EVT_BUTTON, self.on_press)            
            coluna.Add(linha_filter, 0, wx.CENTER) 
            coluna.Add(linha_led, 0, wx.CENTER) 
            coluna.Add(hide_button, 0, wx.TOP | wx.CENTER, 30)
            panel.SetSizer(coluna)
            self.Show()

        def check_events(self, event):
            update_logs()
           
        def on_press(self, event):
            frame.Hide()
        
        def on_clean(self, event):
            frame.led3.SetBackgroundColour('gray')
            frame.Refresh()

        def set_error_led(self):
            frame.led3.SetBackgroundColour('Red')
            frame.Refresh()


    class Event(LoggingEventHandler):
        try:
            def dispatch(self, event): 
                LoggingEventHandler()
                adiciona_linha_log(str(event))
                path_event = str(event.src_path)
                filenamesize = (len(getfilename(path_event)))
                sliceposition = len(path_event)- (filenamesize)
                path_event_dir = os.path.join(path_event[0:sliceposition],'')
                for sync in configs['SYNC_FOLDERS']:
                    paths = (configs['SYNC_FOLDERS'][sync]).split(', ')
                    if os.path.join(paths[0], '') == path_event_dir:
                        event_operations(path_event, paths[1], sync, event)
                
        except Exception as err:
            adiciona_linha_log("Logging event handler erro - "+str(err))

    print('Definindo funções...')

    def send_status_metric():
        while 1:
            time.sleep(int(configs['ZABBIX']['send_metrics_interval']))
            global metric_value
            global frame
            value = metric_value
            if (value != 0):
                frame.set_error_led()

            '''
            Envia metricas para zabbix:
                ---Em caso de erro de sinc -> envia str com caminho do diretório que ocorreu o erro [strlen > 1]
                ---Em caso de sucesso nas rotinas -> envia flag str com '0' [strlen == 1]
                ---Após sincronizar todas as pastas da lista envia flag str com '1' [strlen == 1]
            '''
            try:
                packet = [
                    ZabbixMetric(configs['ZABBIX']['hostname'], configs['ZABBIX']['key'], value)
                ]
                ZabbixSender(zabbix_server=configs['ZABBIX']['zabbix_server'], zabbix_port=int(configs['ZABBIX']['port'])).send(packet)
            except Exception as err:
                adiciona_linha_log("Falha de conexão com o Zabbix - "+str(err))


    def adiciona_linha_log(texto):
        dataFormatada = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        mes_ano = datetime.now().strftime('_%Y%m')
        print(dataFormatada, texto)
        try:
            log_file = configs['LOG_FOLDER']['log_folder']+'log'+mes_ano+'.txt'
            f = open(log_file, "a")
            f.write(dataFormatada + ' ' + texto +"\n")
            f.close()
        except Exception as err:
            print(dataFormatada, err)
            global frame
            frame.set_error_led()
        update_logs()
            
    def getfilename(filepath):
        try:
            pathlist = filepath.split('\\')
            filename = (pathlist[len(pathlist)-1]).lower()
            return (filename)
        except Exception as Err:
            adiciona_linha_log(str(Err)+'Getfilename')
            global frame
            frame.set_error_led()

    def awkward_filename(filename):
        awkward_name = filename[0:8]+filename[-4:]
        return awkward_name

    def filetree(source, dest, sync_name):
        files_destination_md5=dict()
        files_source_md5=dict()
        try: 
            sync_ext = configs['SYNC_EXTENSIONS'][sync_name].lower().split(", ")
        except:
            sync_ext = []

        try:
            debug = 'scan dest'
            for e in os.scandir(dest):
                if e.is_file():
                    if (not os.path.splitext(e.name)[1][1:].lower() in sync_ext) & (len(sync_ext) > 0):
                        continue
                    files_destination_md5[e.name.lower()]=e.stat().st_mtime
                
            debug = 'scan source'
            for e in os.scandir(source):
                if e.is_file():
                    if (not os.path.splitext(e.name)[1][1:].lower() in sync_ext) & (len(sync_ext) > 0):
                        continue
                    files_source_md5[e.name.lower()]=e.stat().st_mtime
                
            files_to_remove=[]

            debug = 'remove files'
            for file in files_destination_md5:
                path_dest = os.path.join(dest, file)
                if file not in files_source_md5:
                    try:
                        os.remove(path_dest)
                        adiciona_linha_log("Removido: " + str(path_dest))
                        files_to_remove.append(file)
                    except Exception as ERR:
                        adiciona_linha_log("Erro ao remover arquivo." + str(ERR))
                        frame.set_error_led()

            debug = 'destination.pop'  
            for item in files_to_remove:
                files_destination_md5.pop(item)

            debug = 'copy files'
            thistime=round(time.time())
            for file in files_source_md5:
                path_source = os.path.join(source, file)
                path_dest = os.path.join(dest, awkward_filename(file))
                if file not in files_destination_md5:
                    aguarda_liberar_arquivo(path_source) #testar
                    shutil.copy2(path_source, path_dest)                
                    adiciona_linha_log("Copiado: " + str(path_source) + "[" + str(os.path.getsize( str(path_source) )) + "]" + " to " + str(path_dest) + "[" + str(os.path.getsize(str(path_dest) )) + "]")
                else:            
                    if files_source_md5[file] != files_destination_md5[file]:
                        aguarda_liberar_arquivo(path_source) #testar
                        shutil.copy2(path_source, path_dest)
                        adiciona_linha_log("Sobrescrito: " + str(path_source) + "[" + str(os.path.getsize( str(path_source) )) + "]" + " to " + str(path_dest) + "[" + str(os.path.getsize( str(path_dest) )) + "]")
                if (round(time.time()) > ( thistime + 120) ):
                    return 0   
            return 0

        except Exception as err:
            global metric_value
            metric_value = str(source) 
            adiciona_linha_log(str(err)+debug)
            return 1

    def aguarda_liberar_arquivo(filepath_source):
        thistime2=round(time.time())
        in_file = None
        source_size1 = 0
        source_size2 = -1
        while in_file == None or source_size1 != source_size2:
            source_size1 = os.path.getsize( str(filepath_source) )
            time.sleep(0.02)
            source_size2 = os.path.getsize( str(filepath_source) )
            try:
                in_file = open(filepath_source, "rb") # opening for [r]eading as [b]inary
            except:
                pass
            if (round(time.time()) > ( thistime2 + 120) ):
                adiciona_linha_log("Arquivo protegido contra gravacao por mais de 120 segundos, não permitindo a cópia.")
                frame.set_error_led()
                break
        try:
            in_file.close()            
        except:
            pass

    def event_operations(filepath_source, path_dest, sync_name, event):
        global frame
        global evento_acontecendo
        evento_acontecendo = True     
        global sincronizando
        while sincronizando == True:
            frame.led1.SetBackgroundColour('Yellow')
            frame.Refresh()
            time.sleep(0.1) 
        frame.led1.SetBackgroundColour('Red')
        frame.Refresh()
        try: 
            sync_ext = configs['SYNC_EXTENSIONS'][sync_name].lower().split(", ")
        except:
            sync_ext = []
        try:
            filename = getfilename(filepath_source).upper()
            filepath_dest = os.path.join(path_dest, awkward_filename(filename))
            if os.path.isfile(filepath_source) or os.path.isfile(filepath_dest):
                if (os.path.splitext(filename)[1][1:].lower() in sync_ext) or (len(sync_ext) == 0):    
                    if not os.path.exists(filepath_source):
                        try:
                            os.remove(filepath_dest)
                            adiciona_linha_log("Removido: " + str(filepath_dest))
                        except Exception as err:
                            adiciona_linha_log(str(err) + "Erro ao remover arquivo. " + str(filepath_dest))
                            frame.set_error_led()       
                    elif not os.path.exists(filepath_dest):
                        aguarda_liberar_arquivo(filepath_source)
                        shutil.copy2(filepath_source, filepath_dest)
                        origem_size = os.path.getsize( str(filepath_source) )
                        destino_size = os.path.getsize( str(filepath_dest) )
                        adiciona_linha_log("Copiado: " + str(filepath_source) + "[" + str(origem_size) + "]" + " to " + str(filepath_dest) + "[" + str(destino_size) + "]")  
                        if (origem_size != destino_size):
                            os.remove(filepath_dest)
                            adiciona_linha_log('Cópia corrompida. Será copiado novamente no próximo sync.' + str(filepath_source))
                            frame.set_error_led()
                    else:
                        source_mtime = os.stat(filepath_source).st_mtime
                        dest_mtime = os.stat(filepath_dest).st_mtime
                        if source_mtime != dest_mtime:
                            aguarda_liberar_arquivo(filepath_source)
                            shutil.copy2(filepath_source, filepath_dest)
                            origem_size = os.path.getsize( str(filepath_source) )
                            destino_size = os.path.getsize( str(filepath_dest) )
                            adiciona_linha_log("Sobrescrito: " + str(filepath_source) + "[" + str(origem_size) + "]" + " to " + str(filepath_dest) + "[" + str(destino_size) + "]")
                            if (origem_size != destino_size):
                                os.remove(filepath_dest)
                                adiciona_linha_log('Cópia corrompida. Será copiado novamente no próximo sync' + str(filepath_source)) 
                                frame.set_error_led()

            frame.led1.SetBackgroundColour('gray')
            frame.Refresh()
        except Exception as Err:
            adiciona_linha_log(str(Err)) 
            global metric_value
            metric_value = str(filepath_source)
        evento_acontecendo = False

    def sync_all_folders():
        try:
            error_counter = 0
            for item in configs['SYNC_FOLDERS']:
                time.sleep(0.1)
                path = (configs['SYNC_FOLDERS'][item]).split(', ')
                error_counter += filetree(path[0], path[1], item)
                time.sleep(0.1)
            if error_counter == 0:
                global metric_value
                metric_value = 0
        except Exception as err:
            adiciona_linha_log("Falha durante execução da função sync_all_folders - "+str(err))
            global frame
            frame.set_error_led()

    def update_logs():
        global frame
        mes_ano = datetime.now().strftime('_%Y%m')
        log_file = configs['LOG_FOLDER']['log_folder']+'log'+mes_ano+'.txt'
        if not os.path.exists(log_file):
            return
        f = open(log_file, "r")
        linhas = f.readlines(20000000)
        linhas.reverse()
        remover=[]
        if (frame.cb1.GetValue() == False):
            for item in linhas:
                if ('<' in item):
                    remover.append(item)
            for item in remover:
                linhas.remove(item)
        frame.logpanel.SetValue(''.join(linhas))
    
    def syncs_thread():
        while sleep_time > 0:
            global frame
            frame.led2.SetBackgroundColour('yellow')
            frame.Refresh()
            global sincronizando
            sincronizando = True
            global evento_acontecendo
            if evento_acontecendo == True:
                sincronizando = False
                time.sleep(1)
                continue
            frame.led2.SetBackgroundColour('Red')
            frame.Refresh()
            sync_all_folders()
            sincronizando = False
            frame.led2.SetBackgroundColour('gray')
            frame.Refresh()
            time.sleep(sleep_time)
            
    if __name__ == "__main__":
        
        print("Inicializando sistema de logging..")

        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S') 
        event_handler = Event()
        observer = Observer() 
        for item in configs['SYNC_FOLDERS']:
            try:
                host = (configs['SYNC_FOLDERS'][item]).split(', ')
                observer.schedule(event_handler, host[0], recursive=False)
            except Exception as err:
                adiciona_linha_log(str(err)+host[0])
                global frame
                frame.set_error_led()

        observer.start() 

        print('Iniciando janela wx...')  
          
        try:      
            app = wx.App()
            frame = MyFrame()
            frame.SetIcon(wx.Icon(icon_file))
            TaskBarIcon(frame)
            t = Thread(target=syncs_thread, daemon=True)
            u = Thread(target=send_status_metric, daemon=True)
            t.start()
            u.start()
            update_logs()
            app.MainLoop()

        except Exception as Err:
            adiciona_linha_log(str(Err))
            #observer.stop()   
            frame.set_error_led()

        #observer.join()
        
except Exception as ERR:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) # This is your Project Root
    dire = os.path.join(ROOT_DIR, 'ERRO.TXT')
    f = open(dire, "a")
    f.write(str(ERR))
    f.close()
   


