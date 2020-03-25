#
# QUTI Status Check
#
# Checks status of openVPN tunnel, UFW, QBT and QUTI services
# Should be an hourly job
# 0 */1 * * * /home/<svcaccount>/venvs/QUTI/healthcheck.sh >>/home/<svcaccount>/quticron.log 2>&1
# Requires changes to sudoers.d to allow unprivileged user to restart these services
#
# Variable initialization
msgGreeting="Starting QUTI Environment Healthcheck at `date +'%D %T'`\r\n"
today=`date +"%Y%m%d"`
# Overall status is never reset to true, just switched to false if something fails
statusgood=true
# Individual status messages are changed to "UP" when good, used in final log file message
statusFirewall="DOWN"
statusTunnel="DOWN"
statusQBT="DOWN"
statusQUTI="DOWN"
# Restart statuses are used in log file message, set appropriately if restart is attempted
statusVPNRestart=""
statusQBTRestart=""
statusQUTIRestart=""
#
# Main Script
#
echo $msgGreeting
# Check for presence of tunnel interface (change tun0 to reflect the name you expect)
tunnelup=$(/sbin/ifconfig | grep tun0)
# Check if traffic can actually get out (this assumes UFW rules only allow external traffic over tun0)
# There may be cases where tun0 adapter is present but not working correctly.
tunnelworking=$(ping 8.8.8.8 -w1 | grep 'icmp_seq=1 ttl=')
# If tunnel is down or not working, restart OpenVPN
# It's assumed you've modified sudoers.d with an allowance for unpriv'd user to run the reset
# e.g. <regularuser> <machinename> = NOPASSWD: /bin/systemctl restart openvpn
if [ -z "$tunnelup" ] || [ -z "$tunnelworking" ]
then 
    echo "VPN IS DOWN!"
    statusVPNRestart="(Attempted Restart)"
    # if tunnel is down, restart the openvpn service
    echo "Restarting OpenVPN..."
    sudo systemctl restart openvpn
    # wait a few seconds before retesting...
    sleep 3
    # Checking for tunnel up again
    tunnelup=$(ifconfig | grep tun0)
    tunnelworking=$(ping 8.8.8.8 -w1 | grep 'icmp_seq=1 ttl=')
    if [ -z "$tunnelup" ] || [ -z "$tunnelworking" ]
    then
        echo "VPN is still down, restart failed"
        statusgood=false
    else
        # Fixed it, so resetting status
        statusVPNRestart="(Had to Restart)"
        statusTunnel="UP"
        echo "OpenVPN restarted successfully"
    fi
else
    echo "VPN is Up!"
    statusTunnel="UP"
fi
# Check status of firewall
# This assumes you've modified sodoers.d as above to include /usr/sbin/ufw status verbose
# You can make this check as precise as you want it. I'm only confirming that ufw is running
# and the default action is still set to deny traffic. I think you could lay in the whole
# ruleset as a check (basically a differ) to make sure config is static since it shouldn't
# change very often.
ufwup=$(sudo ufw status verbose | grep 'Default: deny (incoming), deny (outgoing)')
if [ -z "$ufwup" ]
then
    # What should you do if firewall isn't working? I say shut it all down
    # stop qbt service
    echo "FIREWALL IS DOWN!"
    statusgood=false
else
    # Firewall is up
    echo "Firewall is up!"
    statusFirewall="UP"
fi
# Check status of QBT
qbtup=$(systemctl status qbittorrent.service | grep 'Active: active (running)')
if [ -z "$qbtup" ]
then
    # QBT is down
    echo "QBT IS DOWN!"
    statusQBTRestart="(Attempted Restart)"
    sudo systemctl restart qbittorrent.service
    # give it a few seconds
    sleep 3
    qbtup=$(systemctl status qbittorrent.service | grep 'Active: active (running)')
    if [ -z "$qbtup" ]
    then
        statusQBT="DOWN"
        echo "QBT is still down, restart failed"
        statusgood=false
    else
        statusQBT="UP"
        echo "QBT restarted successfully"
        statusQBTRestart="(Had to Restart)"
    fi
else
    echo "QBT is up!"
    statusQBT="UP"
fi

# Check status of QUTI
qutiup=$(systemctl status quti.service | grep 'Active: active (running)')
if [ -z "$qutiup" ]
then
    echo "QUTI IS DOWN!"
    statusQUTIRestart="(Attempted Restart)"
    # restart QUTI service if it's not active
    sudo systemctl restart quti.service
    # give it a few seconds...
    sleep 3
    qutiup=$(systemctl status quti.service | grep 'Active: active (running)')
    if [ -z "$qutiup" ]
    then
        statusQUTI="DOWN"
        echo "QUTI is still down, restart failed"
        statusgood=false
    else
        statusQUTI="UP"
        echo "QBT restarted successfully"
        statusQUTIRestart="(Had to Restart)"
    fi
else
    echo "QUTI is up!"
    statusQUTI="UP"
fi
if [ $statusgood = true ]
then
    line1="      __\r\n"
    line2="     / /   Firewall is   $statusFirewall\r\n"
    line3="__  / /    Tunnel is     $statusTunnel $statusVPNRestart\r\n"
    line4="\\ \\/ /     QB is         $statusQBT $statusQBTRestart\r\n"
    line5=" \__/      API Facade is $statusQUTI $statusQUTIRestart\r\n"
else
    line1="__    __\r\n"
    line2="\ \  / /   Firewall is   $statusFirewall\r\n"
    line3=" \ \/ /    Tunnel is     $statusTunnel $statusVPNRestart\r\n"
    line4=" / /\ \    QB is         $statusQBT $statusQBTRestart\r\n"
    line5="/_/  \_\   API Facade is $statusQUTI $statusQUTIRestart\r\n"
fi
msgStatus=$line1$line2$line3$line4$line5
msgSalutation='Healthcheck complete!\r\n'
echo -e "$msgGreeting$msgStatus$msgSalutation" >> "/home/qbtuser/qbtimmigrationd/statusQUTI-$today.log"