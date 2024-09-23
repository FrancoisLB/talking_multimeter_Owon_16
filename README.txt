# Talking multimeter project 
This application enables a visually impaired or blind person to use an Owon 16 multimeter using their PC and the NVDA screen reader.

The PC connects to the multimeter's BLE link to acquire measurements.

## Functionalities 
This application allows to :
* display the measured values on the screen in large characters and adapted contrast (font color and background)
* verbally announce the measured values and units

## keyboard shortcuts 
Following shortcuts are defined :
    * Alt + F4 : close the main application window 
    * F4 : indicates the status of the BLE link (connected or not) 
    * F5 : announces the value of the measurement
	* F8 : copy measure to clipboard 

Two internal dictionnaries are used :
* for protocol data exchange (measurements, data type and units, and gain)
* tool configuration (background and dont colors, font size, etc) 

## Accessibility 
this tool is fully accessible with the NVDA screen reader (free and open source published by NV Access fundation).

## Source code 
This application has been developed in python 3. 
The GUI is based on the WX python library to ensure its accessibility.

Folowing modules are used :
* pyttsx3 : voice générator
* WXpython : graphical interface
* wxasync: thread managment 
* asyncio : async managment 

see requirements.txt file 

## License 
This tool is developed under CC by SA-NC license. 
it is free and open source.
any modification of the code have to be published in the same terms.
 
## Developers
This tool has been developped by 2 members of "l'atelier partagé" FABLAB located in Betton (Bretagne France), with the support of "My Human Kit" (MHK), FABLAB located in Rennes (Bretagne France).
* Developper : Sebastien B.
* user : François LB

