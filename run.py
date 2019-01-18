#! /usr/bin/env python

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
# along with cPanel Automated Migration Tool.  If not, see <http://www.gnu.org/licenses/>.

from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient
import getpass, os, time
import numpy as np

class Server:
  def __init__(self, username, hostname, password, port):
    #set the SSH creds and host info
    self.username = username
    self.hostname = hostname
    self.password = password
    self.port = port

    #establish an SSH connection
    self.client = SSHClient()
    self.client.set_missing_host_key_policy(AutoAddPolicy())
    self.client.connect(self.hostname, port=self.port, username=self.username, password=self.password)

    #gather facts for premigration check
    self.disk_info = self.run_command("df -h | grep -w / | awk '{print $2, $3, $4}'")[2:-3].split(" ")

    self.used_disk_space = self.disk_info[1]
    self.avail_disk_space = self.disk_info[2]
    self.max_disk_space = self.disk_info[0]
    
    self.php_version = self.run_command("php -v | grep PHP | grep -v 'Loader\|Copyright' | awk '{print $2}'")[2:-3]
    self.php_handler = self.run_command("/usr/local/cpanel/bin/rebuild_phpconf --current | grep $(/usr/local/cpanel/bin/rebuild_phpconf --current | grep DEFAULT | awk '{print $3}') | grep -v DEFAULT | awk '{print $3}'")[2:-3]
    self.mysql_version = self.run_command("mysql -V | awk '{print $5}' | sed 's/,//g'")[2:-3]

  def run_command(self, command):
      stdin, stdout, stderr = self.client.exec_command(command)
      return str(stdout.read())

class Source(Server):
    def __init__(self, username, hostname, password, port, src_accounts):
        Server.__init__(self, username, hostname, password, port)
    
        self.accounts = src_accounts
        self.accounts_split = src_accounts.split(" ")

        self.packages = self.run_command("whmapi1 listpkgs | grep -Po '(?<=(name: )).*' | grep -v default | tr '\n' ','")[2:-2]
        self.account_disk_usage = self.run_command("cd /home; du -sch {} | tail -1 | awk '{{print $1}}'".format(self.accounts))[2:-3]

    def isEA3(self):
        if self.run_command("httpd -v | grep 'Easy::Apache'")[2:-1] is "":
            return False
        return True

# check disk space based off of (accounts to migrate total combined disk usage)
def disk_check(src, dest):
    if "G" in src.account_disk_usage and "G" in dest.avail_disk_space:
        if float(dest.avail_disk_space[:-1]) > float(src.account_disk_usage[:-1]):
            return True
    elif "M" in src.account_disk_usage and "G" in dest.avail_disk_space:
        if float(dest.avail_disk_space[:-1]*1024) > float(src.account_disk_usage[:-1]):
            return True
    elif "G" in src.account_disk_usage and "M" in dest.avail_disk_space:
        if float(dest.avail_disk_space[:-1]) > float(src.account_disk_usage[:-1]*1024):
            return True
    elif "M" in src.account_disk_usage and "M" in dest.avail_disk_space:
        if float(dest.avail_disk_space[:-1]) > float(src.account_disk_usage[:-1]):
            return True
    else:
        print("There does not appear to be enough disk space on the destination server.")
        return False

    print("There is not enough available disk space.")
    return False

def ea3_php_version_check(src, dest):
    # If running EA3 the best thing to do is just install PHP 5.6. at this point it's all EOL
    dest.run_command("yum install ea-php56 ea-php56{{-build,-libc-client,-pear.noarch,-php,-php-bcmath,-php-bz2,-php-calendar,-php-cli,-php-common,-php-curl,-php-devel,-php-exif,-php-fileinfo,-php-ftp,-php-gd,-php-gettext,-php-iconv,-php-imap,-php-litespeed,-php-mbstring,-php-mysqlnd,-php-opcache,-php-pdo,-php-posix,-php-soap,-php-sockets,-php-xml,-php-xmlrpc,-php-zip,-runtime}}")

    return True

def migrate_ea4_profile(src, dest):
    # First we'll convert the current EA4 config into a profile
    src.ea4_profile = src.run_command("/usr/local/bin/ea_current_to_profile")[2:-1]
    
    # Transfer file to dest server
    with SCPClient(src.client.get_transport()) as scp:
        scp.get(src.ea4_profile, ".")

    with SCPClient(dest.client.get_transport()) as scp:
        scp.put(src.ea4_profile[32:], "/root/{}".format(src.ea4_profile[32:]))

    dest.run_command("/usr/local/bin/ea_install_profile --install {}".format("/root/{}".format(src.ea4_profile[32:])))

    return True

def mysql_version_check(src, dest):
    if int(src.mysql_version.split(".")[0]) >= 5 and int(src.mysql_version.split(".")[1]) <=5 and "MariaDB" not in src.mysql_version:
        src.old_hash_accounts = src.run_command("mysql -t -e \"select distinct User,Password from mysql.user where Password not like '*%' and Password not like '-%' and Password not like '\!%';\" | awk '{print $2}' | grep -v User | grep [a-z] | tr \"\n\" \" \"")
        if src.old_hash_accounts is not "":
            print("The server is using an old hashing method, you'll need to reset the passwords for: {}".format(src.old_hash_accounts))
    if int(src.mysql_version.split(".")[0]) >= 5 and int(src.mysql_version.split(".")[1]) >= 6 or "MariaDB" in src.mysql_version and int(src.mysql_version.split(".")[1]) >= 1:
        return True
    
    print("MySQL version failure.")
    return False

def migration_failed(msg, src, dest):
    if msg is not "":
        print("The migration failed: {}".format(msg))
        clean_up(src, dest)

def premigration_check(src, dest):
    print("Starting pre-migration check")
    
    while dest.run_command("ps uax | grep yum | grep -v grep")[2:-1] is not "":
        print("waiting for yum to finish")
        time.sleep(1)

    # Check if EA3 or EA4
    if src.isEA3() is False:
        if disk_check(src, dest) and mysql_version_check(src, dest):
            if migrate_ea4_profile(src, dest):
                migrate_server(src, dest)
            else:
                migration_failed("could not migrate ea4 profile", src, dest)
        else:
            migration_failed("", src, dest)
            
    else:
        if disk_check(src, dest) and ea3_php_version_check(src, dest) and mysql_version_check(src, dest):
            migrate_server(src, dest)
        else:
            migration_failed("", src, dest)

def migrate_server( src, dest):
    print("Migration in progress")

    # connect to source server and generate session_id
    dest.session_id = dest.run_command("whmapi1 create_remote_root_transfer_session remote_server_type=cpanel host={} port={} user=root password={} transfer_threads=1 restore_threads=1 unrestricted_restore=1 copy_reseller_privs=0 compressed=0 unencrypted=0 low_priority=0 | grep -Po '(?<=(transfer_session_id: )).*'".format(src.hostname, src.port, src.password))[2:-3]
    
    # Transfer all packages to dest server
    if src.packages is not "":
        for package in src.packages.split(","):
            dest.run_command("whmapi1 enqueue_transfer_item transfer_session_id={} module=PackageRemoteRoot package={}".format(dest.session_id, package))

    #loop through accounts and enqueue them
    for account in src.accounts_split:
        dest.run_command("whmapi1 enqueue_transfer_item transfer_session_id={} module=AccountRemoteRoot localuser={} user={}".format(dest.session_id, account, account))
    
    #when loop is done begin the transfer session
    dest.run_command("whmapi1 start_transfer_session transfer_session_id={}".format(dest.session_id))
    
    print("Transfer Process has started!")
    clean_up(src, dest)

def clean_up(src, dest):
    #remove our ea4 profile after it's installed
    dest.run_command("rm -f /root/current_state_at*")
    os.remove(src.ea4_profile[32:])

    #make sure we close our SSH connection(s) when we are finished
    src.client.close()
    dest.client.close()

if __name__ == "__main__":
    # Gather source and destination server information:
    # Source
    print("Source server information:")
    print("Please provide the source server's hostname or IP: ", end='')
    src_host = input()

    src_password = getpass.getpass("Please provide the source server's root password: ")

    print("Please provide the source server's SSH port: ", end='')
    src_port = input()

    print("Please provide a list of users separated by spaces(ONLY SPACES): ", end='')
    src_accounts = input()
    
    # Destination
    print("Destination server information:", end='')
    print("Please provide the Destination server's hostname or IP: ", end='')
    dest_host = input()

    dest_password = getpass.getpass("Please provide the Destination server's root password: ")

    print("Please provide the Destination server's SSH port: ", end='')
    dest_port = input()

    #define source and destination with gathered info
    source = Source("root", src_host, src_password, src_port, src_accounts)
    destination = Server("root", dest_host, dest_password, dest_port)

    # start pre mig check
    premigration_check(source, destination)