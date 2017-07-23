#! /usr/bin/env python

# museekcontrol -- command-line control of museekd
#
# Copyright (C) 2006 daelstorm <daelstorm@gmail.com>
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

Version = "0.3.0"


def output(s):
    print s
    sys.stdout.flush()


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
        "download=", "mt", "mtransfers", "abortdown=",
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


def checkUrl(args):
    url = str(args)
    if url[:7] == "slsk://":
        try:
            user, ufile = urllib.url2pathname(url[7:]).split("/", 1)
            ufile = ufile.replace("/", "\\")
            return True
        except Exception, e:
            print e
            return False
    else:
        print "Invalid soulseek url: %s. \
                    Use the slsk://username//path format" % url
        return False


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
    elif opts == "-b" or opts == "--browse":
        want = "browse"
        user = str(args)
    elif opts == "--minfo":
        want = "info"
    elif opts == "-t" or opts == "--transfers":
        want = "transfers"
    elif opts == "--mt" or opts == "--mtransfers":
        want = "mtransfers"
    elif opts in ("--gs", "--gsearch"):
        want = "gsearch"
        query = str(args)
    elif opts in ("--reloadshares"):
        want = "reloadshares"
    elif opts == "--connect":
        want = "connect"
    elif opts == "--disconnect":
        want = "disconnect"
    elif opts in ("--download"):
        url = str(args)
        if url[:7] == "slsk://":
            try:
                user, ufile = urllib.url2pathname(url[7:]).split("/", 1)
                if ufile[-1] != "/":
                    want = "download"
                    ufile = ufile.replace("/", "\\")
                    print "Attempting to \
                            Queue file: %s from %s" % (ufile, user)
                else:
                    want = "downfolder"
                    ufile = ufile.replace("/", "\\")
                    print "Attempting to \
                            get folder contents: %s from %s" % (ufile, user)
            except Exception, e:
                print e
        else:
            print "Invalid soulseek url: %s. Use the \
                    slsk://username//path format" % url
    elif opts in ("--abortdown", "--removedown", "--retrydown",):
        if checkUrl:
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
        self.count = 0
        self.connected = 0
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
                if self.count == 0:
                    if user is not None:
                        self.send(messages.PeerStats(user))
                    self.count += 1
            elif want == "browse":
                if self.count == 0:
                    if user is not None:
                        self.send(messages.UserShares(user))
                    self.count += 1
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
            elif want == "downfolder":
                if user != '':
                    s = ufile[:-1]
                    self.send(messages.GetFolderContents(user, ufile))
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
        sleep(0.001)

    def cb_search_ticket(self, query, ticket):
        self.s_query[ticket] = query

    def cb_search_results(self, ticket, user, free, speed, queue, results):
        if want in ("gsearch"):
            output("---------\nSearch: " + str(self.s_query[ticket]) +
                   " Results from: User: " + user)

            for result in results:
                result_list = []
                # Create Result List for future use
                # clear it next interation

                result_list = ticket, user, free, speed, queue, result[
                    0], result[1], result[2], result[3]
                # ticket, user, free, speed, queue, path, size, filetype, [bitrate, length]
                # Count Search Result
                self.search_number += 1
                # Display Search Result

                path = result[0]
                size = str(result[1] / 1024) + 'KB'
                ftype = result[2]

                if ftype in ('mp3', 'ogg'):
                    if result[3] != []:
                        bitrate = result[3][0]
                        length = result[3][1]
                        minutes = int(length) / 60
                        seconds = str(length - (60 * minutes))

                        if len(seconds) < 2:
                            seconds = '0' + seconds
                    else:
                        bitrate = 'None'
                        minutes = '00'
                        seconds = '00'
                        length = 0
                else:
                    bitrate = 'None'
                    minutes = '00'
                    seconds = '00'
                    length = 0
                if free:
                    free = 'Y'
                else:
                    free = 'N'
                output("[%s] slsk://%s/%s" % (str(self.search_number), user,
                                              path.replace("\\", "/")))
                output("Size: " + str(size) + " Bitrate: " + str(bitrate) +
                       " Length: " + str(minutes) + ":" + seconds + " Queue: "
                       + str(queue) + " Speed: " + str(speed) + " Free: " +
                       free + " filetype: " + ftype)
                output(" ")

    def cb_peer_stats(self, username, avgspeed, numdownloads, numfiles,
                      numdirs, slotsfull, country):
        if want == "stats":
            if user == username:
                output(
                    "Peer Stats for: %s \nSpeed: %s \tDownloads: %s\
                            \nFiles: %s \tDirectories: %s"
                    % (user, avgspeed, numdownloads, numfiles, numdirs))
                output("")
                sys.exit()

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

    def cb_server_state(self, state, username):
        if state:
            output("Connected to server, username: " + username)
        else:
            output("Not connected to server")

    def cb_transfer_state(self, downloads, uploads):
        if want in ("mtransfers", "transfers"):
            for transfer in uploads:
                print "Upload: slsk://%s/%s\nSize: %s\
                        Pos: %s Rate: %s State: %s %s" % (
                    transfer.user, transfer.path, transfer.filesize,
                    transfer.filepos, transfer.rate,
                    self.states[int(transfer.state)], transfer.error)
                print "- - - - - - - - - - - - - - - -"
            for transfer in downloads:
                print "Download: slsk://%s/%s\nSize: %s\
                        Pos: %s Rate: %s State: %s %s" % (
                    transfer.user, transfer.path, transfer.filesize,
                    transfer.filepos, transfer.rate,
                    self.states[int(transfer.state)], transfer.error)
                print "- - - - - - - - - - - - - - - -"
        if want == "transfers":
            sys.exit()

    def cb_transfer_update(self, transfer):
        if want == "mtransfers":
            if transfer.is_upload:
                print "Upload: slsk://%s/%s\nSize: %s Pos:\
                        %s Rate: %s State: %s %s" % (
                    transfer.user, transfer.path, transfer.filesize,
                    transfer.filepos, transfer.rate,
                    self.states[int(transfer.state)], transfer.error)
                print "- - - - - - - - - - - - - - - -"
            else:
                print "Download: slsk://%s/%s\nSize: %s Pos:\
                        %s Rate: %s State: %s %s" % (
                    transfer.user, transfer.path, transfer.filesize,
                    transfer.filepos, transfer.rate,
                    self.states[int(transfer.state)], transfer.error)


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
