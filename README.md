# QUTI (Qbittorrent-to-UTorrent Integration)
uTorrent API facade for QBittorrent

## DESCRIPTION  

uTorrent offers a REST api with which other programs integrate, such as Media Center Master (MCM). This script runs an interface that mimics the uTorrent API but translates it to QBitTorrent, enabling drop-in replacement of uTorrent with QBT, if preferred. 

It supports the following methods:
add-url
start/stop
remove
pause/unpause
list

## TABLE OF CONTENTS

1. Installation  
    1.1 Preparing the Base Environment (including QBT)  
    1.2 Setting up the QUTI service  
    1.3 Configuring QUTI  
2. Recommended Supplements  
3. License  

## Installation  

Since this has been built specifically to front-end QBT, it will also include background on setting up your QBT environment. 

### Preparing the Base Environment  
This script has primarily been tested on Ubuntu 16+, and using Python 3.6+ with Python-venv for the virtual environment.

So create your server, install Python3.x along with python-venv and create an unprivileged user that will function as the service account for this script. (e.g. qbtuser)

In that service account's home directory, create two folders - one for downloaded files and one for incomplete files (e.g. qbtimmigrationd and wishlistd). You can use one folder if you want to comingle your in-process and completed files. 

If you need access to these folders from a Windows machine, you can either map these directories to shares on a Windows computer, or share the directories themselves (using Samba, for instance). If you're running this script and QBT on a lightweight linux VM, it probably makes more sense to map your storage to Windows folders rather than share folders from the linux machine. This keeps your VM clean and replacable. 

Install headless qbittorrent (qbittorrent-nox).

To ensure qbittorrent is running as a daemon, confirm your /etc/systemd/system/qbittorrent.service file includes the service account as the user (e.g. User=qbtuser). Your [Service] section may look like the following:  
[Service]  
User=qbtuser  
ExecStart=/usr/bin/qbittorrent-nox  
ExecStop=/usr/bin/killall -w qbittorrent-nox  

In QBT's web interface, designate the two directories you created above in the Options. If you're using two folders, you'll want to tell QBT to run a program after torrent completion, to copy the file from one directory to the other. 

Make note of QBT's port number (e.g. 8080).

### Setting up the QUTI service  
Clone the repo to some folder in the service account's home directory, e.g. venvs. 

Create your virtual environment in that folder (e.g. python3 -m venv /home/<serviceaccount>/venvs/QUTI/.venv)

Activate the environment and install dependencies (e.g. source ./.venv/bin/activate; python3 -m pip install -r requirements.txt)

Create a .service file in /etc/systemd/system for QUTI named quti.service. It may look like the following if you've used the example naming conventions above:  
[Unit]  
Description=qbittorrent API Facade Service  
After=syslog.target network.target  
  
[Service]  
User=qbtuser  
ExecStart=/bin/bash -c "source /home/qbtuser/venvs/QUTI/.venv/bin/activate; python /home/qbtuser/venvs/QUTI/quti.py"  
WorkingDirectory=/home/qbtuser/venvs/QUTI/  
Restart=on-failure  
RemainAfterExit=yes  

[Install]  
WantedBy=multi-user.target  

### Configure QUTI  
Open the quti.py file and verify some of the environment variables at the top of the script. You want to make sure the port numbers match what QBT is running on (e.g. 8080) and what your other applications are expecting to find uTorrent on (e.g. 8081). Change these accordingly along with your server IP and the working directory path in the script.

## Recommended Supplements

It's wise to also install some sort of VPN on the server you're using for QBT, and that's a bit outside of the scope of these instructions, but installing a VPN with a kill switch (so Internet traffic can't occur without the tunnel being up) is advisable. 

This repo includes a shell script that can be run hourly to test for a working openVPN tunnel, and whether UFW, QBT and QUTI services are all running. This script creates a daily log file in one of the working folders per the naming conventions above. It does require modification of the sudoers.d content to ensure your service account can restart the openVPN service, etc. If your VPN tunnel has a habit of timing out, this can be very helpful. 

## License  
This script uses the MIT license, as outlined in the License file