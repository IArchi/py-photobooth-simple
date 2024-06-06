# Simple PhotoBooth

I wanted to create a very simple to use photobooth without unecessary features.
This project is easy to edit and has been tested on 3 to 5 years old child to ensure it was easy to understand the way to use it.

## State machine
It relies on a state machine to display screens.
![State Machine](doc/state_machine.png)

## Screens
![Waiting screen](doc/waiting.png)
![Select format](doc/select_format.png)
![Print screen](doc/print.png)

## Cameras
The application is compatible with piCamera, DSLR and CV2 devices.
By default, it will try to use the best available quality:
 - If piCamera is connected, it will be used for preview ;
 - If DSLR is connected, it will be used for capture ;

If one of these is not available, it will use the first available one.

## Compatibility
Tested on MacOs Sonoma and RaspberryPi 5 8GB with Arducam 64MB.

## Installation
To install dependencies:
```
pip3 install -r requirements.txt
```

To start the application:
```
python3 photoboothapp.py
```

## Customization
To customize collages, you can edit `logo.png`. As a PNG file, you can use transparency.

You can also edit `photoboothapp.py` to change some parameters such as:
 - LOCALES = Locales.get_EN (To select language to use)
 - FULLSCREEN = False (If set to True, the window fill take all available space)
 - COUNTDOWN = 3 (Countdown before the photo is taken)
 - ROOT_DIRECTORY = './DCIM' (Directory in which the photos and collages are stored)
 - PRINTER = 'truc' (The printer's name in CUPS)

## USB dump
A dedicated thread will handle USB dongles and automatically dump the whole content of the `ROOT_DIRECTORY` to the device.
Application will not be usable during the copy process but will display a message.

## TODO
 - Test with gphoto2 and piCamera2
