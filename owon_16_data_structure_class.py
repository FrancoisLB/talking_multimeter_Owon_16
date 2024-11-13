
"""
    définition d'une classe pour la structure des données du multimetre OWON 16 (séquence de 6 bytes)
    
    voir la description de la strucure dans le docstring de la classe 

"""
__version__ = "4.0"
__date__ = "2024/10/15" 

# Dictionnaire de description des fonctions du multimètre, type de mesure (Unité), et mode (AC/DC) 
# valeurs codées sur 13 bits selon le protocole d'écahgne des 6 bytes de données 
OWON_FUNCTION = {
    'MILLIVOLT_DC': 7683, 
    'MILLIVOLT_AC': 7691, 
    'VOLT_DC': 7684, 
    'VOLT_AC': 7692, 
    'DIODE_TEST': 7764, 
    'MICROAMPERE_DC': 7698, 
    'MICROAMPERE_AC': 7706, 
    'MILLIAMPERE_AC': 7707, 
    'AMPERE_DC': 7700, 
    'AMPERE_AC': 7708, 
    'OHM_NORMAL': 7716, 
    'OHM_CONTINUITY_TEST': 7772, 
    'KILOOHM': 7717, 
    'MEGAOHM': 7718, 
    'NANOFARAD': 7721, 
    'MICROFARAD': 7722, 
    'MILLIFARAD': 7723, 
    'FARAD': 7724, 
    'HERTZ': 7732, 
    'PERCENT': 7740, 
    'CELSIUS': 7748, 
    'FAHRENHEIT': 7756, 
    'NEARFIELD': 7788
}

# Class definition to describe OWON datastructure (6 bytes)
class Owon_MultimeterData:
    def __init__(self, raw_data):
        """Definition of data structure of Owon 16 multimeter :
        
        6 Bytes structured as follow :
        
                           Field_name  start_bit  Length_bit
        0      decimal_places          0            2
        1            overflow          2            1
        2   function_selector          3            13
        3      data_hold_mode         16            1
        4       relative_mode         17            1
        5        auto_ranging         18            1
        6         low_battery         19            1
        7          not_used_1         20            4
        8          not_used_2         24            8
        9               value         32            15
        10               sign         47            1
        
        Attributs de la classe : 
            * raw_data : bloc de 6 octets 
            * decimal_places : position de la décimale pour l'affichage de la mesure (valeurs 0, 1, 2 ou 3)
            * overflow : flag pour overflow (0 ou 1) 
            * unit : unité de la mesure (str voir dictionnaire ci-dessus)
            * data_hold_mode : flag pour data_hold_mode (0 ou 1) 
            * relative_mode : flag pour relative_mode (0 ou 1) 
            * auto_ranging : flag pour auto_ranging (0 ou 1) 
            * low_battery : flag pour low_battery (0 ou 1) 
            * value : valeur de la mesure 
            * sign : signe de la mesure (flag 0 : positif ou 1 : négatif)  
        
        """

        if len(raw_data) != 6:
            raise ValueError("Expected 6 bytes of data. Received : ", len(raw_data))
        
        self.raw_data = raw_data
        self._transform_and_decode_data()

    def _transform_and_decode_data(self):
        """method to decode OWON raw data (6 bytes in Little Endian) to detailled data fileds of structure. see structure description in class definition.""" 
        # class private data 
        # unit and decimal in 2 first bytes : data[0] and data[1] 
        unit_and_decimal = (self.raw_data[1] << 8) | self.raw_data[0]
        # flags in byte 3 in data[2]
        flags = self.raw_data[2]
        # not used byte 4 in data[3]
        unused = self.raw_data[3]
        
        # measured value 
        #  data received in Little EndIan mode 
        # in bytes 5 and 6 corresponding to data[4] and data[5] 
        value_and_sign = (self.raw_data[5] << 8) | self.raw_data[4]
        
        # class attributs definition  
        self.decimal_places = unit_and_decimal & 0b11  # Les deux premiers bits 0 et 1 
        self.overflow = (unit_and_decimal >> 2) & 0b1  # Bit 2 (Overflow)
        self.unit = unit_and_decimal >> 3  # 13 Bits 3-15 
        
        # unit name in str type 
        self.unit_name = self.get_unit_from_value(self.unit)
        
        # flags extraction 
        self.data_hold_mode = flags & 0b1  # Bit 0
        self.relative_mode = (flags >> 1) & 0b1  # Bit 1
        self.auto_ranging = (flags >> 2) & 0b1  # Bit 2
        self.low_battery = (flags >> 3) & 0b1  # Bit 3

        # mesured value extraction 
        self.value = value_and_sign & 0b11111111111111  # Les 14 bits inférieurs
        self.sign = (value_and_sign >> 15) & 0b1  # Bit 15

        # measured value determination 
        if self.sign:
            self.value = -self.value
        
        # apply scale factor 
        scale_factor = pow(10, self.decimal_places)
        self.value = self.value / scale_factor

    # get unit name from unit code 
    def get_unit_from_value(self, value):
        """Get function name as str (unit and AC/DC mode) from unit code int value (13 bits field).
           
           value : int 
           
           return : str unit name
        """
        for key, val in OWON_FUNCTION.items():
            if val == value:
                return key.replace("_", " ")
        return "unknown value"

    def flag_status_to_string(self, flag_value):
        """Return status as string : On or Off 
        
        param : flag value int 0 or 1 
        """
        status_string = {0: "Off", 1: "On"}.get(flag_value, "Unknown falg value.")
        return status_string 

    def __repr__(self):
        """Print multimeter data fields values"""
        return (f"Multimeter Data:\n"
                f"  Decimal Places: {self.decimal_places}\n"
                f"  Overflow: {self.flag_status_to_string(self.overflow)}\n"
                f"  Unit: {self.unit}\n"
                f"  Unit name: {self.unit_name}\n" 
                f"  Data Hold Mode: {self.flag_status_to_string(self.data_hold_mode)}\n"
                f"  Relative Mode: {self.flag_status_to_string(self.relative_mode)}\n"
                f"  Auto Ranging: {self.flag_status_to_string(self.auto_ranging)}\n"
                f"  Low Battery: {self.low_battery}\n"
                f"  Value: {self.value}")
 
# Exemple d'utilisation
if __name__ == "__main__":
    
    # première validation avec les données 
    # mesure de 3.279 en volt DC 
    values_int = [35, 240, 4, 0, 207, 12]
    
    raw_data = values_int
    
    multimeter_data = Owon_MultimeterData(raw_data)
    
    # affichage des données d'entrée :
    print("Données d'entrée : ")
    print(raw_data) 
    
    # Affichage des résultats
    print(multimeter_data)
 
    # Accéder aux champs
    # print("proprietes de la variable : multimeter_data ") 
    # print("Valeur décimale:", multimeter_data.decimal_places)
    # print("Valeur en dépassement:", multimeter_data.overflow)
    # print("Unité de mesure:", multimeter_data.unit_name)
    # print("Valeur mesurée:", multimeter_data.value)
    
    # Validation sur une série de mesures 
    # boucle sur les mesures de validation 
    print("Données de validation du code.")     
    list_cas = [
               "Millivotlts DC : -13 ",
               "Millivotlts DC : -2,6",
               "Mega Ohms : overflow oui",
               "Méga ohms : 0,839",
               "Degrés Celsius :  -1"
               ]
    list_raw_data = [
                    [25,240,4,0,130,128],
                    [25,240,1,0,26,128],
                    [55,241,4,0,255,127],
                    [51,241,5,0,71,3],
                    [32,242,2,0,1,128]
                    ]
    
    for i, raw_data in enumerate(list_raw_data):
        print(" ") 
        print(f"cas : {i+1} ")
        print(list_cas[i]) 
        
        # extraction des données 
        multimeter_data = Owon_MultimeterData(raw_data)
    
        # affichage des données d'entrée :
        print("Données d'entrée : ")
        print(raw_data) 
    
        # Affichage des résultats
        print(multimeter_data)
    
    # fin de boucle for 
    
print("Terminé") 
    