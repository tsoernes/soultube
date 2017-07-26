#! /usr/bin/env python

# Soulseek batch downloader
#
# forked from daelstorm <daelstorm@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

import sys
import urllib
import os
import select
import getopt
import ConfigParser
from time import sleep

try:
    from museek import messages, driver
except:
    print """WARNING: The Museek Message-Parsing modules, messages.py and/or
     driver.py were not found. Please install them into your
     '/usr/lib/python2.X/site-packages/museek' directory, or place them in
     a 'museek' subdirectory of the directory that contains the
     museekcontrol python scipt."""

Version = "0.1.0"


def output(s):
    print s
    sys.stdout.flush()


def safe_get(l, idx, default):
    try:
        return l[idx]
    except IndexError:
        return default


parser = ConfigParser.ConfigParser()

config_dir = str(os.path.expanduser("~/.museekd/"))
config_file = config_dir + "museekcontrol.config"
interface = None
password = None
log_dir = None


def usage():
    print(
        """MuseekControl is a command-line script for Museek, the P2P Soulseek Daemon
Author: daelstorm
Version: %s
    Default options: none
    -c, --config <file>     (Use a different config file)

    SEARCHING:
    --gs, --gsearch <query>     (Globally search for <query> & show results)
    --ad, --autodownload <query>     (Globally search for <query> & \
            autoselect a file for downloading)

    TRANSFERS:
    -t, --transfers         (Display all current up- and downloads)
    --mt, --mtransfers      (Monitor transfers)
    --download  slsk://user/path (Add file or dir to the download queue)
    --abortdown slsk://user/path (Abort Download)
    --removedown    slsk://user/path (Remove Download from queue)
    --retrydown slsk://user/path (Retry Download)

    SERVER:
    --connect   (Connect to Serverl; Disconnect if already connected)
    --disconnect    (Disconnect from Server; Do not try to reconnect)

    SHARES:
    --reloadshares          (Reload Shares Databases)

    MUSEEK DAEMON LOGIN:
    -i, --interface <host:port|/socket.path> (Use a different interface)
    -p, --password <pass>   (Use a different password (saved) )
    -v, --version       (Display version and quit)
    -h, --help          (Display this help and exit)
    """ % Version)
    sys.exit(2)


try:
    opts, args = getopt.getopt(sys.argv[1:], "hc:vi:p:j:l:p:m:b:tar", [
        "help", "config=", "interface=", "password=", "transfers",
        "monitor-transfers", "gs=", "gsearch=", "version", "log=",
        "autodownload", "download=", "mt", "mtransfers", "abortdown=",
        "retrydown=", "removedown=", "reloadshares", "disconnect",
        "connect"
    ])
except getopt.GetoptError:
    usage()
    sys.exit(2)
if len(opts) == 0:
    usage()
    sys.exit(2)
else:
    user = None
    want = None
    reason = None
    query = None
    search_results = dict()


def checkUrl(args):
    url = str(args)
    if url[:7] == "slsk://":
        try:
            user, ufile = urllib.url2pathname(url[7:]).split("/", 1)
            return user, ufile
        except Exception, e:
            print e
    else:
        print "Invalid soulseek url: %s. \
              Use the slsk://username//path format" % url
        sys.exit()


def handleDownload(args):
    user, ufile = checkUrl(args)
    if ufile[-1] != "/":
        want = "download"
        ufile = ufile.replace("/", "\\")
        print "Attempting to \
                download file: %s from %s" % (ufile, user)
    else:
        want = "downfolder"
        ufile = ufile.replace("/", "\\")
        print "Attempting to \
                download folder contents: %s from %s" % (ufile, user)
    return user, ufile, want


for opts, args in opts:
    if opts in ("-h", "--help"):
        usage()
        sys.exit()
    elif opts in ("-c", "--config"):
        config_file = str(os.path.expanduser(args))
    elif opts in ("-i", "--interface"):
        interface = str(os.path.expanduser(args))
    elif opts in ("-p", "--password"):
        password = str(os.path.expanduser(args))
    elif opts in ("-v", "--version"):
        print "Mulog version: %s" % Version
        sys.exit(2)
    elif opts == "--minfo":
        want = "info"
    elif opts == "-t" or opts == "--transfers":
        want = "transfers"
    elif opts == "--mt" or opts == "--mtransfers":
        want = "mtransfers"
    elif opts in ("--gs", "--gsearch"):
        want = "gsearch"
        query = str(args)
    elif opts in ("--ad", "--autodownload"):
        want = "autodownload"
        query = str(args)
    elif opts in ("--download"):
        user, ufile, want = handleDownload(args)
    elif opts in ("--connect", "--disconnect", "--reloadshares"):
        want = opts[2:]
    elif opts in ("--abortdown", "--removedown", "--retrydown"):
        user, ufile = checkUrl(args)
        want = opts[2:]


museekcontrol_config = {
    "connection": {
        "interface": 'localhost:2240',
        "password": None
    },
    "museekcontrol": {
        "log_dir": "~/.museekd/logs/"
    }
}


def create_config():
    parser.read([config_file])
    museekcontrol_config_file = file(config_file, 'w')
    for i in museekcontrol_config.keys():
        if not parser.has_section(i):
            parser.add_section(i)
        for j in museekcontrol_config[i].keys():
            if j not in ["nonexisting", "hated", "options"]:
                parser.set(i, j, museekcontrol_config[i][j])
            else:
                parser.remove_option(i, j)
    parser.write(museekcontrol_config_file)
    museekcontrol_config_file.close()


def read_config():
    parser.read([config_file])
    for i in parser.sections():
        for j in parser.options(i):
            val = parser.get(i, j, raw=1)
            if j in ['login', 'password', 'interface', "log_dir"]:
                museekcontrol_config[i][j] = val
            else:
                try:
                    museekcontrol_config[i][j] = eval(val, {})
                except:
                    museekcontrol_config[i][j] = None


def update_config():
    museekcontrol_config_file = file(config_file, 'w')
    for i in museekcontrol_config.keys():
        if not parser.has_section(i):
            parser.add_section(i)
        for j in museekcontrol_config[i].keys():
            if j not in ["evilness"]:
                parser.set(i, j, museekcontrol_config[i][j])
            else:
                parser.remove_option(i, j)
    parser.write(museekcontrol_config_file)
    museekcontrol_config_file.close()


def check_path():
    if os.path.exists(config_dir):
        if os.path.exists(config_file) and os.stat(config_file)[6] > 0:
            read_config()
        else:
            create_config()
    else:
        os.mkdir(config_dir, 0700)
        create_config()


check_path()

if log_dir is not None:
    museekcontrol_config["museekcontrol"]["log_dir"] = log_dir
if password is not None:
    museekcontrol_config["connection"]["password"] = password
if interface is not None:
    museekcontrol_config["connection"]["interface"] = interface

update_config()


class museekcontrol(driver.Driver):
    def __init__(self):
        driver.Driver.__init__(self)
        self.s_query = {}
        self.search_number = 0
        self.connected = 0
        self.count = 0
        self.states = {
            0: "Finished",
            1: "Transferring",
            2: "Negotiating",
            3: "Waiting",
            4: "Establishing",
            5: "Initiating",
            6: "Connecting",
            7: "Queued",
            8: "Address",
            9: "Status",
            10: "Offline",
            11: "Closed",
            12: "Can't Connect",
            13: "Aborted",
            14: "Not Shared"
        }

    def disconnect(self):
        driver.Driver.close(self)

    def connect(self):
        try:
            driver.Driver.connect(
                self, museekcontrol_config["connection"]["interface"],
                museekcontrol_config["connection"]["password"],
                messages.EM_CHAT | messages.EM_USERINFO | messages.EM_PRIVATE
                | messages.EM_TRANSFERS | messages.EM_USERSHARES
                | messages.EM_CONFIG)
        except Exception, e:
            print e

    def process(self):
        d = 0
        r, w, x = select.select([self.socket, sys.stdin], [], [self.socket], d)
        if self.socket in r:
            driver.Driver.process(self)
        if self.connected == 1:
            if want is None or want == "":
                print "Nothing to be done, exiting"
                sys.exit()
            elif want == "stats":
                if user is not None:
                    self.send(messages.PeerStats(user))
            elif want == "connect":
                self.send(messages.ConnectServer())
                sys.exit()
            elif want == "disconnect":
                self.send(messages.DisconnectServer())
                sys.exit()
            elif want == "download":
                if user != '':
                    self.send(messages.DownloadFile(user, ufile))
                sys.exit()
            elif want == "autodownload":
                self.send(messages.Search(0, query))
                # TODO wait for a set time,
                # then find best result and download it
                # user, ufile = handleDownload(url)
                if user != '':
                    self.send(messages.DownloadFile(user, ufile))
            elif want == "downfolder":
                if user != '':
                    s = ufile[:-1]
                    self.send(messages.GetFolderContents(user, s))
                sys.exit()
            elif want == "gsearch":
                if self.count == 0:
                    self.send(messages.Search(0, query))
                    self.count += 1
            elif want == "abortdown":
                self.send(messages.TransferAbort(0, user, ufile))
                sleep(1)
                sys.exit()
            elif want == "removedown":
                self.send(messages.TransferRemove(0, user, ufile))
                sleep(1)
                sys.exit()
            elif want == "retrydown":
                self.send(messages.DownloadFile(user, ufile))
                sleep(1)
                sys.exit()
            else:
                print "Got unhandled want:" + want
        sleep(0.001)

    def cb_search_ticket(self, query, ticket):
        self.s_query[ticket] = query

    def status_check(self, status):
        if status == 0:
            stat = "Offline"
        elif status == 1:
            stat = "Away"
        elif status == 2:
            stat = "Online"
        return stat

    def cb_search_results(self, ticket, user, free, speed, queue, results):
        if want in ("gsearch", "autodownload"):
            output("---------\nSearch: " + str(self.s_query[ticket]) +
                   " Results [%s-%s] from user: %s"
                   % (str(self.search_number),
                      str(self.search_number+len(results)), user))
            str(self.search_number)
            # this should be top level as the callback is called
            # once per user with results
            # user_results = []
            for result in results:
                # user, free, speed, queue,
                # path, size, filetype, [bitrate, length]
                # result_info = user, free, speed, queue, \
                #        result[0], result[1], result[2], result[3]
                # if free:
                    # user_results += result_info
                # TODO Cant we get out more useful info here?
                # Count Search Result
                # Display Search Result

                path = result[0]
                size_kb = result[1] / 1024
                if size_kb > 1000:
                    size = str(size_kb / 1024) + 'MB'
                else:
                    size = str(size_kb) + 'KB'

                bitrate = "None"
                length = "0"
                if len(result) > 3:
                    if len(result[3]) > 0:
                        bitrate = result[3][0]
                        if len(result[3]) > 1:
                            length = result[3][1]

                length = int(length)
                if length < 10 and bitrate is not "None" and size_kb > 0:
                    length = size_kb / int(bitrate) * 8
                minutes = length / 60
                seconds = str(length - (60 * minutes))
                if len(seconds) < 2:
                    seconds = '0' + seconds + 's'

                if free:
                    free = 'Y'
                else:
                    free = 'N'
                output("slsk://%s/%s" % (user, path.replace("\\", "/")))
                output("Size: " + str(size) + " Bitrate: " + str(bitrate) +
                       " Length: " + str(minutes) + ":" + seconds +
                       " Queue: " + str(queue) + " Speed: " + str(speed) +
                       " Free: " + free)
                output(" ")

                # Example:
                # Search: anahera Results from: User: Rtyom
                # [50] slsk://Rtyom/@@scipc/Music/SoulSeek/complete/Beatport Trance Top 100 August 2015/05. Ferry Corsten Pres. Gouryella - Anahera (Original Mix).mp3
                # Size: 17952KB Bitrate: 320 Length: 0:00 Queue: 7 Speed: 104793 Free: Y filetype: mp3
                #
                # [51] slsk://Rtyom/@@scipc/Music/SoulSeek/complete/Beatport Trance Top 100 August 2015/Ferry Corsten Pres. Gouryella - Anahera (Original Mix).mp3
                # Size: 18009KB Bitrate: 320 Length: 0:00 Queue: 7 Speed: 104793 Free: Y filetype: mp3
            # search_results[ticket] += user_results

    def cb_disconnected(self):
        self.connected = 0
        print "--- Disconnected from the Museek Daemon ---"
        sys.exit()

    def cb_login_error(self, reason):
        self.connected = 0
        if reason == "INVPASS":
            self.invalidpass = 1
            print "couldn't log in: Invalid Password"
            self.connect()
        else:
            self.invalidpass = 0
            print "couldn't log in: " + reason

    def cb_login_ok(self):
        self.connected = 1
        self.invalidpass = 0
        print "Logging in"

    def cb_server_state(self, state, username):
        if state:
            output("Connected to server, username: " + username)
        else:
            output("Not connected to server")

    def cb_transfer_state(self, downloads, uploads):
        if want in ("mtransfers", "transfers"):
            for transfer in uploads:
                self.cb_transfer_update(transfer)
            for transfer in downloads:
                self.cb_transfer_update(transfer)
        if want == "transfers":
            sys.exit()

    def cb_transfer_update(self, transfer):
        if want in ("mtransfers", "transfers"):
            if transfer.is_upload:
                print "Upload:",
            else:
                print "Download:",

            print " slsk://%s/%s\nSize: %s Pos:\
                    %s Rate: %s State: %s %s" % (
                transfer.user, transfer.path, transfer.filesize,
                transfer.filepos, transfer.rate,
                self.states[int(transfer.state)], transfer.error)
            print "- - - - - - - - - - - - - - - -"


if museekcontrol_config["connection"]["password"] is None:
    output("No password set")
    sys.exit()
c = museekcontrol()


def start():
    try:
        while 1:
            if c.socket is None:
                c.connect()
            c.process()
    except Exception, e:
        print e


start()
