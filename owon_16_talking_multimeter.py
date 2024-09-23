# -*- coding: utf-8 -*-

"""

   AIDE TECHNIQUE BASSE-VISION POUR ACCES AU MULTIMETRE OWON 16 AVEC NVDA 

ce code crée  une IHM accessible sur un PC pour permettre d'accéder aux mesures fournies par 
un multimetre  OWON 16 via sa liaison sans fil BLE

ce script a été développé par Sébastien de l'atelier partagé, FABLAB de Betton (France 35830)
ce projet a été mené en partenariat avec My Human Kit, FABLAB de Rennes (France).

cet outil est compatible du lecteur d'écran NVDA. 

il donne accès aux mesures du multimetre au moyen de la synthèse vocale.

ce projet est publié en opensource (libre et gratuit) sous licence libre CECIL.
http://cecill.info/licences/Licence_CeCILL_V1-fr.html 

"""

import wx
import asyncio
import wxasync
from bleak import BleakClient,  BleakGATTCharacteristic, BleakScanner, BleakError
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import time
import pyttsx3
import json

# file information 
__date__ = "2024_09_23" 
__version__ = "1.0" 

# OWON 16
MODEL_NAME="BDM"
MODEL_ADDR="A6:C0:80:90:2D:DB"
CHAR_NBR_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"

# window application configuration dictionary
config_default  = {"windows_width": 1400,
          "windows_height": 800,
          "color_foreground":(255,255,0),
          "color_background":(0,0,0),
          "font":u'Consolas',
          "font_size":70,
          "const_selecteur_decompte":3,}

config = {}

"""
# backup config file
# Serializing json
json_object = json.dumps(config, indent = 4)
print(json_object)

# Using a JSON string
with open('config.json', 'w') as outfile:
    outfile.write(json_object)
"""
# dictionnaire des états
status_dict = {"DISCON":"en attente de connexion",
               "FOUND":"Client trouvé",
               "CONN":"Connecté, en attente de données",
    }

def load_config (config_default):
    """Loading application configuration json file in dictionary

    :param config_default: a dictionary containing default value to use incase there is missing parameter in config file
    """
    config=config_default.copy()
    try:
        with open('config.json') as json_file:
            cfg = json.load(json_file)
            print(type(config))
            config.update (cfg)
    except:
        print("unable to load config file")
    return config

def parle (chaine):
    """text to speach, the string text provides the text

    :param chaine: string text
    """
    engine.say(chaine)
    engine.runAndWait()


# dictionnary containing all type sent by Owon 16.
#      => code sent by OWON 16 (data[0]) 
#      => Text to display and to speach when this type is selected,
#      => parameter to match the value send by OWON to exact value read on Owon
dict = {"25": ("milli Volts DC",10),
        "89": ("milli Volts AC",10),
        "35": ("Volts DC",1000),
        "33": ("Ohm",10),
        "55": ("Circuit ouvert",10),
        "50": ("Mega Ohm",10),
        "43": ("Kilo Ohm",10),
        "51": ("Mega Ohm",1000),
        "74": ("nanoFarad",10),
        "163": ("Hertz",10),
        "32": ("°C",1),
        "96": ("NCV",10),
        "145": ("micro Ampere DC",10),
        "209": ("micro Ampere AC",10),
        "154": ("milli Ampere DC",100),
        "218": ("milli Ampere AC",100),
        "162": ("Ampère DC",100),
        "226": ("Ampère AC",100),
        "225": ("Continuité",100),
        "231": ("Continuité",100),}


class MyFrame(wx.Frame):
    """Class defining the appli frame 

    :param inherit wx.Frame
    """
    def __init__(self):
        """Class constructor
        """
        super().__init__(None, title='Talky Multimeter for Owon 16', size=(config["windows_width"], config["windows_height"]))
        
       # Obtenir les dimensions de l'écran
        screen_width, screen_height = wx.GetDisplaySize()
        
        # factor for main window size from screen size  
        WINDOW_SCREEN_FACTOR = 0.85 

        # Calculer les nouvelles dimensions de la fenêtre (85% des dimensions de l'écran)
        window_width = int(screen_width * WINDOW_SCREEN_FACTOR)
        window_height = int(screen_height * WINDOW_SCREEN_FACTOR)
        
        # Définir la taille et la position de la fenêtre
        self.SetSize(window_width, window_height)
                
        # cree la fenetre au centre de l'ecran
        self.Centre()
        
        # ajout status bar
        self.statusbar=self.CreateStatusBar()
        # self.statusbar.SetFieldsCount(2,[50,50])
        # initialisation du texte de la statusbar 
        self.statusbar.SetStatusText("En attente de connexion,",0)
        
        # ajout panel
        self.panel = wx.Panel(self)
        
        # couleur et taille
        self.font = wx.Font(config["font_size"], wx.MODERN, wx.NORMAL, wx.NORMAL, False, config["font"])
        self.panel.SetForegroundColour(config["color_foreground"])
        self.panel.SetBackgroundColour(config["color_background"])
        self.panel.SetFont(self.font)
        
        # ajout static label box 
        self.mesure_label = wx.StaticText(self.panel,label="")
        # ajout mesure value box 
        self.mesure_valeur = wx.StaticText(self.panel, style=wx.ALIGN_CENTRE_HORIZONTAL|wx.ST_NO_AUTORESIZE,label="")
        
        # self.text_ctrl = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.mesure_label, 0, wx.EXPAND, 5)
        self.sizer.Add(self.mesure_valeur, 1, wx.EXPAND, 5)
        
        # self.sizer.Add(self.text_ctrl, 1, wx.EXPAND)
        self.panel.SetSizer(self.sizer)
        
         # add binding event
        self.Bind (wx.EVT_CLOSE, self.on_close)
        self.Bind (wx.EVT_CHAR_HOOK, self.on_key)
        #self.Bind (wx.EVT_KEY_DOWN, self.on_key)
        
        # timer
        self.timer = wx.Timer (self)
        # timer event each 1000ms
        self.timer.Start (1000)
        self.Bind (wx.EVT_TIMER, self.on_timer)
        
        # set initial status 
        self.status="DISCON"
        self.status_timer=0
        self.closure_request = False
        
        self.selecteur = "none"
        self.selecteur_transitoire = "none"
        self.selecteur_transitoire_count = config["const_selecteur_decompte"]
        # initialisation de la valeur de la mesure 
        self.value = 0
        
        
        self.connected=False
    
    # copy to clipboard function
    def copy_to_clipboard(self, event):
        """Copie la valeur de la mesure dans le presse-papier."""
        text_to_copy = str(self.value)  # Récupérer la valeur de la mesure
        # print("copy : ", str(self.value))
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text_to_copy))  # Copier le texte
            wx.TheClipboard.Flush()  # Forcer la persistance des données dans le presse-papier
            wx.TheClipboard.Close()
            # wx.MessageBox("Texte copié dans le presse-papier", "Info", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox("Impossible d'ouvrir le presse-papier", "Erreur", wx.OK | wx.ICON_ERROR)    
    
    # waiting for key stroke
    def on_key (self, event):
        """on key event to capture key stroke

        :param Standard
        """
        key = event.GetKeyCode()
        
        # Alt + F4 : tell closing and close main window 
        if key == wx.WXK_F4 and event.AltDown():
            parle("Closing main window") 
            self.Close()  # Fermer la fenêtre principale
            return  # Arrêter l'exécution de la fonction ici

        # Autres raccourcis clavier
        if key == wx.WXK_F10:
            for task in asyncio.all_tasks():
                print(task)
            print ('F10')
        # F4 : tell BLE link status between computer and OWON 16 multimeter 
        if key == wx.WXK_F4:
            parle (status_dict[self.status])
            # print ('F4 key pressed')
        # F5 : tell current measure 
        if key == wx.WXK_F5:
            # parle (str(self.value)+" "+self.selecteur)
            parle (str(self.value))
            # print(f"=> {str(self.value)}")
        # F8 : copy value to clipboard  
        if key == wx.WXK_F8:
            parle ("Copy value to clipboard.")
            self.copy_to_clipboard(None)
            # print("copy to clipboard.")        
        
        event.Skip()
        
            
    # waiting for timer event
    def on_timer (self, event):
        """timer event handling (each second, to detect connection issue to owon
            workaround to async with BleakClient(self.device, disconnected_callback=handle_disconnect) as client: function
            that is sometime blocking... waitong better fix..

        :param Standard
        """
        if self.status == "FOUND":
            # print (bluetooth_task)
            # for task in asyncio.all_tasks():
                # print(task)
            self.status_timer+=1
            if self.status_timer > 5:
                print(f"on timer disconnecting")
                bluetooth_task.cancel()
                loop = asyncio.get_event_loop()
                bluetooth_task=loop.create_task(frame.main_loop(),name="bluetooth")
                #self.client.disconnect()
            
    
    # Windows closing handler
    # correction de la methode on_close 
    def on_close(self, event):
        """Catch frame close event, to force bluetooth disconnection and avoid waiting for Owon timeout 

        :param Standard
        """
        print("on close event called")
        
        # Si pas connecté, on peut fermer immédiatement
        if not self.connected:
            self.Destroy()  # Ferme immédiatement la fenêtre
            return

        # Si connecté, demande de fermeture propre
        self.closure_request = True
        
        # Si le statut est 'FOUND' (indiquant qu'une connexion est en attente ou en cours)
        if self.status == "FOUND":
            try:
                task = asyncio.get_task("bluetooth")
                task.cancel()  # Annule la tâche Bluetooth en cours
            except Exception as e:
                print(f"Erreur lors de l'annulation de la tâche : {e}")
        
        # Déconnecte proprement le client s'il est connecté
        if self.status == "CONN":
            try:
                asyncio.create_task(self.client.disconnect())  # Déconnexion Bluetooth
            except Exception as e:
                print(f"Erreur lors de la déconnexion : {e}")
        
        # Ferme la fenêtre après avoir effectué les actions nécessaires
        self.Destroy()
       
    async def main_loop(self):
        """main waiting event loop 

        :param Standard
        """
       
        # Disconnect Handler
        async def handle_disconnect(_: BleakClient):
            """handle bluetooth disconnect -> do nothing can be removed, except logging prupose.

            :param Standard
            """
            print("Device was disconnected, goodbye.")

            
        def decode_value (data: bytearray):
            """decode data byte array send by Owon 16, 
               according to type and factor value (see dict dictionnary)

            :param data: data byte array received from Owon 16 (6 bytes) 
            
            return : selector function and measure 
            """
            print(f"{data[0]}",f"{data[1]}",f"{data[2]}",f"{data[3]}",f"{data[4]}",f"{data[5]}")
            
            selecteur,facteur=dict[str(data[0])]
            
            # extract measurement from sent data 
            if data[5] < 128:
                value = str(((data[5]*256 + data[4])/facteur) )
            else:
                value = "-"+str(((((data[5]-128)*256 + data[4])/facteur)))
                
            return (f"{selecteur}", f"{value} {selecteur}")
          
    
        # Receiving data from Bluetooth Handler
        def handle_rx(_: BleakGATTCharacteristic, data: bytearray):
            """data receive handler from OWON, ready to be decoded

            :param data: data byte array received from Owon
            """
            # print("received:", data.decode())
            # self.mesure_label.SetLabel("Selecteur: Volts")
            # self.mesure_valeur.SetLabel(data.decode())
            if data is not None:
                print("received:", decode_value(data))
                selecteur,value=decode_value(data)
                
                #chnagement de selecteur
                if selecteur != self.selecteur:
                    if selecteur == self.selecteur_transitoire:
                        #on a une
                        self.selecteur_transitoire_count -= 1
                        if self.selecteur_transitoire_count == 0:
                            #c'ets valide on a un nouveau selecteur
                            self.mesure_label.SetLabel("Selecteur: "+selecteur)
                            self.selecteur = selecteur
                            parle (selecteur)
                    else:
                        #nouvelle prpospition de selcteur
                        self.selecteur_transitoire = selecteur
                        self.selecteur_transitoire_count = config["const_selecteur_decompte"]
                    
                self.mesure_valeur.SetLabel(value)
                # rafraichissement de l'affichage de la valeur de la mesure 
                self.value = value
             
              
        # wait for connexion
        # Working loop, managing OWON connection and disconnexion
        while True:
            # at starting 
            self.device = None
            self.mesure_valeur.SetLabel("Connecting.\nPress bottom right button until you hear a beep.")
            parle ("En attente de connexion,  activer le bluetooth sur le multimètre Owon 16")
            parle("Pressez le bouton en bas à droite sous l'écran jusqu'à l'émission d'un bip sonore.") 
            self.status="DISCON"
            self.statusbar.SetStatusText("En attente de connexion...",0)
            while self.device is None:
                # self.mesure_valeur.AppendText(".")
                # self.device = await BleakScanner.find_device_by_filter(filter_bluetooth_device)
                self.device = await BleakScanner.find_device_by_name(MODEL_NAME)

            # Device connected
            self.mesure_valeur.SetLabel("Client trouvé")
            parle("Multimètre Owon 16 détecté.")
            self.statusbar.SetStatusText("Multimètre détecté",0)
            print ('device found')
            self.status="FOUND"
            self.status_timer = 0
            
            # Waiting for data loop
            try:
                async with BleakClient(self.device, disconnected_callback=handle_disconnect) as client:
                    self.mesure_valeur.SetLabel("En attente de données")
                    parle("En attente de données")
                    self.status="CONN"
                    self.closure_request = False
                    # print ('start notify')
                    # wxasync.AsyncBind(wx.EVT_CLOSE, on_close)
                    await client.start_notify(CHAR_NBR_UUID, handle_rx)
                    self.connected = await client.is_connected()
                    while self.connected and not self.closure_request:
                        await asyncio.sleep(1.0)
                        self.connected = await client.is_connected()
                        # await client.stop_notify(CHAR_NBR_UUID)
                        # print ('end notify')
            # except:
            except Exception as err:
                # Récupération des informations de l'exception
                print(f"Type de l'exception: {type(err).__name__}")
                print(f"Message de l'exception: {err}") 
                # annonce vocale de l'exception 
                parle("Exception")
                parle(f"Type de l'exception: {type(err).__name__}")
                parle(f"Message de l'exception: {err}") 
                print ("Exception raised .....")
                
            # closure of application was requeted
            if self.closure_request:
                print ('end of application')
                quit(0)
                
            parle("Multimètre Owon 16 déconnecté   ")                    
            print ('sortie de boucle')
            
        
        """
        # bloc mis en commentaire 
        await asyncio.gather(
            self.read_from_ble(),
            wxasync.AsyncBind(wx.EVT_CLOSE, self.on_close),
        )
        """


# main code 
if __name__ == '__main__':
    engine = pyttsx3.init()
    engine.setProperty("rate", 178)
    
    config = load_config (config_default)
    # print(config)
    
    app = wxasync.WxAsyncApp()
    frame = MyFrame()
    frame.Show()
    loop = asyncio.get_event_loop()
    loop.create_task(frame.main_loop())
    loop.run_until_complete(app.MainLoop())