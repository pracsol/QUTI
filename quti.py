"""Present a facade of the uTorrent API and call equivalent QBT methods."""
import json
import time
from flask import Flask, request, Response
from flask_jsonpify import jsonify
from flask_restful import Resource, Api
from qbittorrent import Client

APP_QUT = Flask(__name__)
API_QUT = Api(APP_QUT)
APP_QUT.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# QBITTORRENT Constants
# This is the address of QBT's API
# It's the "Backend"
# Include port number and suffix with '/'
# as in 'http://x.x.x.x:yyyy/'
QB_URI = 'http://192.168.1.120:8080/'
# UID and PWD or QBT's WebUI/API
# TODO: switch this over to use the UT creds passed from MCM
QB_UID = 'admin'
QB_PWD = 'adminadmin'
# UTORRENT Constants
# These are the settings you'll be using
# within MCM. It's the "Frontend"
# UT_URI is the address for the API facade
# to listen on. By default Flask only listens
# on localhosts, and specifying '0.0.0.0' 
# means all interfaces but you can specify 
# a specific IP if it matters to you.
UT_URI = '0.0.0.0'
# Note that port is an integer, unlike URI
UT_PORT = 8081
# FLASK Debug Mode
FLASK_DEBUG = False
# Path for saving temporary files
QB_TEMPPATH = "/home/qbtuser/qbtimmigrationd/"

class GUI(Resource):
    """Define API for uTorrent"""
    def get(self):
        """Handle all GET requests and return response"""
        param_action = request.args.get('action')
        if param_action == 'add-url':
            # Add a magnet link to the queue
            uri = request.args.get('s')
            result = add_url(uri)
            result = Response('{"build":44332}', status=200, mimetype='text/plain')
            # Why am I manually building a response?
            # For whatever reason, uTorrent sends back
            # JSON data with a plaintext mime type, and
            # for whatever reason, MCM wants to see this
            # to confirm the add was successful. The add
            # fails if the mime-type is changed. The MCM
            # error handling doesn't give much detail as
            # I think it's dropping into a generic msg
            # about the target directory not being cfg'd
            # correctly.
        elif param_action == 'start':
            # Force start a torrent
            torrent = request.args.get('hash')
            torrent = torrent.strip()
            result = force_start(torrent)
        elif param_action == 'stop':
            # Stop a torrent
            # I don't think QBT really knows how to 'stop' a torrent
            # so my theory is the only time you'd call this from MCM
            # is to cancel a torrent, so I'm treating this as a call
            # to QBT to delete the torrent and any downloaded data
            # or deletePerm
            torrent = request.args.get('hash')
            torrent = torrent.strip()
            result = stop(torrent)
        elif param_action == 'remove':
            torrent = request.args.get('hash')
            # TODO: MCM is passing in the hash with leading NL and spaces
            # I think this is because we're returning formatted json
            # which has a NL and same number of leading spaces in the list
            # I think workaround is to disable prettyprint in flask
            torrent = torrent.strip()
            result = delete(torrent)
        elif param_action == 'pause':
            torrent = request.args.get('hash')
            torrent = torrent.strip()
            result = pause(torrent)
        elif param_action == 'unpause':
            torrent = request.args.get('hash')
            torrent = torrent.strip()
            result = unpause(torrent)
        else:
            # Check for a list request
            param_list = request.args.get('list')
            if param_list == '1':
                # Get list of active torrents
                result = json.loads(get_list())
            else:
                # If request doesn't conform to supported
                # methods, just let the caller know we're
                # listening
                result = "Yes, I'm up. Try asking for something meaningful."
        # Send a response back
        return result
    def post(self):
        """Handle all POST requests and return response"""
        # I think the only POST request that uTorrent's API
        # supports is for putting up a torrent file
        # so no need for if/elif/else stuff here
        # TODO: Needs integration testing
        # It's getting tough to find .torrent files for
        # anything MCM cares about, so this hasn't been
        # through integration testing. It works from
        # Postman, but if it doesn't work from MCM
        # it's probably something like the mime-type
        # header as seen with the add_url method
        dummy = request.form
        # Have to read the form data from a POST request
        # to succeed
        file = request.files['torrent_file']
        result = add_file(file)
        return jsonify(result)
# The following methods make the calls to the QBT API
# TODO: consider logging off the session or doing static connection mgr
def add_url(uri):
    """Call QB method to add magnet link"""
    qb_client = initiate_qb()
    return qb_client.download_from_link(uri, savepath=QB_TEMPPATH)

def add_file(file):
    """"Call QB method to add file"""
    qb_client = initiate_qb()
    return qb_client.download_from_file(file, savepath=QB_TEMPPATH)

def force_start(torrent):
    """Call QB method to force start the torrent"""
    qb_client = initiate_qb()
    return qb_client.force_start(torrent)

def stop(torrent):
    """Call QB method to stop the torrent"""
    qb_client = initiate_qb()
    return qb_client.delete_permanently(torrent)

def delete(torrent):
    """Call QB method to delete a torrent with downloaded data"""
    qb_client = initiate_qb()
    return qb_client.delete(torrent)

def pause(torrent):
    """Call QB method to pause a torrent"""
    qb_client = initiate_qb()
    return qb_client.pause(torrent)

def unpause(torrent):
    """Call QB method to unpause a torrent"""
    qb_client = initiate_qb()
    return qb_client.resume(torrent)

def get_list():
    """Call QB method to get list of torrents"""
    qb_client = initiate_qb()
    torrent_list = qb_client.torrents()
    utlist = build_utlist(torrent_list, qb_client)
    return utlist

def initiate_qb():
    """Instantiate and return an authenticated QBT client"""
    qb_client = Client(QB_URI)
    qb_client.login(QB_UID, QB_PWD)
    return qb_client

def build_utlist(qbtlist, client):
    """take a qbt list of torrent details, build and return a string in UT format"""
    utlist = ''
    # Initiate UT list with header
    utlist = '{"build":443322, "label":[["notsupported",' + str(len(qbtlist)) + ']],"torrents":['
    # Initiate UT torrent list with header
    # Loop through torrent details and build a UT-formatted list
    torrents_list = []
    torrent_list = []
    start = time.clock()
    for torrent in qbtlist:
        torrent_detail = client.get_torrent(torrent['hash'])
        utstatuscode = convert_torrent_status(torrent['state'], torrent['force_start'])
        # Add the hash, status
        # Experiment with list join rather than complete concatenation
        torrent_list.append('["' + torrent['hash'] + '"')
        torrent_list.append(utstatuscode)
        torrent_list.append('"' + torrent['name'] + '"')
        torrent_list.append(str(torrent['size']))
        torrent_list.append(str((float(torrent['progress'] * 1000))))
        torrent_list.append(str(torrent_detail['total_downloaded']))
        torrent_list.append(str(torrent_detail['total_uploaded']))
        torrent_list.append(str(torrent['ratio'] / 10))
        torrent_list.append(str(torrent['upspeed']))
        torrent_list.append(str(torrent['dlspeed']))
        torrent_list.append(str(torrent['eta']))
        torrent_list.append('"' + torrent['category'] + '"')
        torrent_list.append(str(torrent_detail['peers']))
        torrent_list.append(str(torrent_detail['peers_total']))
        torrent_list.append(str(torrent_detail['seeds']))
        torrent_list.append(str(torrent_detail['seeds_total']))
        torrent_list.append('0')
        torrent_list.append(str(torrent['priority']))
        torrent_list.append(str(torrent['size'] - torrent['progress'] * torrent['size']) + ']')
        # Join all the elements of torrent_list into master list
        torrents_list.append(','.join(torrent_list))
        torrent_list.clear()

    # add the torrent list to the UT list
    utlist += ','.join(torrents_list)
    end = time.clock()
    # add a footer to the UT list
    # MCM doesn't care about the UT list cache ID
    # so am using this to clock the performance of list grabs
    utlist += '],"time":' + str(end - start) + '}'
    #utlist += '],"torrentc":"9999"}'
    return utlist

def convert_torrent_status(qbtstatus, qbtforce=False):
    """Take in qbt state and convert to utorrent status"""
    utstatus = ''
    # DL in progress (percent progress < 1000)
    if qbtstatus == 'error':
        utstatus = '152'
    elif qbtstatus == 'pausedUP':
        # I think this is the closest thing QBT has to
        # the UT status of 'finished'. If you set your
        # config to pause completed torrents after hitting a share
        # ratio, this is the status, which UT would call finished.
        # MCM reads this as 'stopped'
        utstatus = '136'
    elif qbtstatus == 'pausedDL' and qbtforce is True:
        utstatus = '169'
    elif qbtstatus == 'pausedDL' and qbtforce is False:
        utstatus = '233'
    elif qbtstatus == 'queuedUP':
        utstatus = '200'
    elif qbtstatus == 'queuedDL':
        utstatus = '200'
    elif qbtstatus == 'uploading':
        utstatus = '201'
    elif qbtstatus == 'stalledUP':
        utstatus = '201'
    elif qbtstatus == 'checkingUP':
        utstatus = '130'
    elif qbtstatus == 'checkingDL':
        utstatus = '130'
    elif qbtstatus == 'downloading' and qbtforce is True:
        utstatus = '137'
    elif qbtstatus == 'downloading' and qbtforce is False:
        utstatus = '201'
    elif qbtstatus == 'stalledDL':
        utstatus = '201'
    elif qbtstatus == 'metaDL':
        utstatus = '201'
    else:
        # Just set the default to 201
        utstatus = '201'
    return utstatus

# NOTE: flask is case-sensitive, and mcm
# is using lower case uri.
API_QUT.add_resource(GUI, '/gui/')

if __name__ == '__main__':
    # Runs flask to listen on specified port
    # and interface/IP addy
    APP_QUT.run(host=UT_URI, port=UT_PORT, debug=FLASK_DEBUG)
