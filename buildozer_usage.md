Requirements needed to build Android kivy App:
## UBUNTU
1. Download VirtualBox [if you don't have Linux OS] https://www.virtualbox.org/wiki/Downloads
2. Download Ubuntu Desktop image to use as OS inside VirtualBox https://www.virtualbox.org/wiki/Downloads
3. Download git [pip install git]
4. Using git, clone buildozer
   1. TERMINAL -> git clone https://github.com/kivy/buildozer.git
5. Make sure python 3.9 is installed
   1. TERMINAL -> sudo apt-get install python3.9
6. Install python3 setuptools
   1. TERMINAL -> sudo apt-get install python3-setuptools
7. Access buildozer and run following:
   1. TERMINAL -> cd buildozer
   2. TERMINAL -> sudo python3 setup.py install
8. Clone wanted repository, afterwards access it with terminal
9. Inside the project folder, type the following, which will create the spec file for the App
   1. TERMINAL -> buildozer init
10. Go to project folder and access .spec file
    1. Inside the spec folder, you'll need to specify the libraries you're using, as well as the extensions of the files you want to be packaged
    2. Search for OS [Android]
    3. Go to android.permissions
       1. Add ACCESS_COARSE_LOCATION, ACCESS_FINE_LOCATION, ACCESS_BACKGROUND_LOCATION, BLUETOOTH, BLUETOOTH_ADMIN, WAKE_LOCK
11. Go back to terminal, and type all commands to update dependencies
    1. sudo apt install -y git zip unzip openjdk-11-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev
    2. sudo apt-get install --user --upgrade cython virtualenv
       1. IF ALREADY WORKING ON A VIRTUAL ENV OMIT --user
12. Deploy App 
    1. TERMINAL -> buildozer android debug deploy run logcat.   

*_IMPORTANT:_* Some debugging may be necessary. If app doesn't deploy, check documentation. The following links are recommended:
+ buildozer.readthedocs.io/en/latest/installation.html
+ If an ERROR occurred with Cython https://github.com/kivy/buildozer/issues/1235
+ NEED TO CHECK Java file is correct: ./Gradlew
  + TERMINAL -> sudo apt-get install openjdk-version-jdk
  + The Error Message includes the version compatible with the project
+ If udev rules don't allow connection, we'll need to update them.
  + sudo usermod -aG plugdev "machine username"
  + CHECK PAGE: https://lynxbee.com/solved-no-permissions-user-in-plugdev-group-are-your-udev-rules-wrong/

-------
## ANDROID SETUP
1. Access Settings and touch 7 times the compilation info inside phone info
   1. This gives us developer rights
2. After that, developer options will appear
3. Inside developer options, enable USB Debugging and mantain active while connected to USB

_____
## CAN ALSO CHECK:
https://github.com/Android-for-Python/Android-for-Python-Users#user-permissions.
For other debugging problems that may appear
