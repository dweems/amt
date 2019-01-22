# Automated Migration Tool
# Copyright (C) 2019 BronzeEagle

# This file is part of Automated Migration Tool.

# Automated Migration Tool is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Automated Migration Tool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Automated Migration Tool.  If not, see <http://www.gnu.org/licenses/>.

from scp import SCPClient
from collections import OrderedDict
import os, paramiko, sys, json, fnmatch

class Server:
    def __init__(self, username, hostname, password, port):
        #set the SSH creds and host info
        self.username = username
        self.hostname = hostname
        self.password = password
        self.port = port

        # attept establish an SSH connection
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(self.hostname, port=self.port, username=self.username, password=self.password)

            #gather facts for premigration check
            self.disk_info = self.run_command("df -h | grep -w / | awk '{print $2, $3, $4}'")[2:-3].split(" ")

            self.max_disk_space = self.disk_info[0]
            self.used_disk_space = self.disk_info[1]
            self.avail_disk_space = self.disk_info[2]

            self.php_info = {}
            
            self.php_version = self.run_command("php -v | grep PHP | grep -v 'Loader\|Copyright' | awk '{print $2}'")[2:-3]
            self.php_handler = self.run_command("/usr/local/cpanel/bin/rebuild_phpconf --current | grep $(/usr/local/cpanel/bin/rebuild_phpconf --current | grep DEFAULT | awk '{print $3}') | grep -v DEFAULT | awk '{print $3}'")[2:-3]
            self.mysql_version = self.run_command("mysql -V | awk '{print $5}' | sed 's/,//g'")[2:-3]

        except Exception as e:
            print(e)
            sys.exit()

    def run_command(self, command):
        stdin, stdout, stderr = self.client.exec_command(command)
        return str(stdout.read())

    def isRunningLSWS(self):
        lsws_processes = self.run_command("ps aux | grep -v grep | grep lshttpd -c")[2:-3]
        if int(lsws_processes) >= 1:
            return True
        return False

    def isRunningCloudLinux(self):
        cl = self.run_command("cat /etc/redhat-release")[2:-3]
        if "CloudLinux" in cl:
            return True
        return False


class Source(Server):
    def __init__(self, username, hostname, password, port, src_accounts):
        Server.__init__(self, username, hostname, password, port)
    
        try:
            self.accounts = src_accounts
            self.accounts_split = src_accounts.split(" ")

            self.packages = self.run_command("whmapi1 listpkgs | grep -Po '(?<=(name: )).*' | grep -v default | tr '\n' ','")[2:-2]
            self.account_disk_usage = self.run_command("cd /home; du -sch {} | tail -1 | awk '{{print $1}}'".format(self.accounts))[2:-3]

        except Exception as e:
            print(e)
            sys.exit()

    def isEA3(self):
        if self.run_command("httpd -v | grep 'Easy::Apache'")[2:-1] is "":
            return False
        return True
