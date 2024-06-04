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
Tested on MacOs Sonoma and RaspberryPi 5 8GB.

## Installation
To install dependencies:
```
pip3 install -r requirements.txt
```

To start the application:
```
python3 photoboothapp.py
```

## TODO
 - Improve print icons
 - Test with DSLR and piCamera2
