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
import json, fnmatch

def check(src, dest):
    if src.isEA3():
        dest.run_command("yum install -y ea-php56 ea-php56{{-build,-libc-client,-pear.noarch,-php,-php-bcmath,-php-bz2,-php-calendar,-php-cli,-php-common,-php-curl,-php-devel,-php-exif,-php-fileinfo,-php-ftp,-php-gd,-php-gettext,-php-iconv,-php-imap,-php-litespeed,-php-mbstring,-php-mysqlnd,-php-opcache,-php-pdo,-php-posix,-php-soap,-php-sockets,-php-xml,-php-xmlrpc,-php-zip,-runtime}}")
        return True
    else:
        retrieve_profiles(src, dest)

        compare_profiles(src, dest)

def retrieve_profiles(src, dest):
    # First we'll convert the current EA4 config into a profile
    src.ea4_profile = src.run_command("/usr/local/bin/ea_current_to_profile")[2:-1]
    dest.ea4_profile = dest.run_command("/usr/local/bin/ea_current_to_profile")[2:-1]
    
    # Transfer profile to local directory for checking
    with SCPClient(src.client.get_transport()) as scp:
        scp.get(src.ea4_profile, ".")

    # Transfer file to dest server
    with SCPClient(dest.client.get_transport()) as scp:
        scp.get(dest.ea4_profile, ".")

    with open('./{}'.format(src.ea4_profile.split("/")[6])) as f:
        src.ea4_profile_json = json.load(f)

    with open('./{}'.format(dest.ea4_profile.split("/")[6])) as f:
        dest.ea4_profile_json = json.load(f)

def compare_profiles(src, dest):
    #set the minified PHP version
    src_primary_php = '{}{}'.format(src.php_version.split('.')[0], src.php_version.split('.')[1])
    dest_primary_php = '{}{}'.format(dest.php_version.split('.')[0], dest.php_version.split('.')[1])

    combined_profiles = src.ea4_profile_json.copy()
    combined_profiles.update(src.ea4_profile_json)

    #check 
    if dest.php_handler == 'dso':
        to_remove = ['ea-apache24-mod_suexec', 'ea-apache24-mod_suphp']

        for item in to_remove:
            if item in src.ea4_profile_json['pkgs']:
                src.ea4_profile_json['pkgs'].remove(item)


        #combine the two profiles
        combined_profiles = src.ea4_profile_json.copy()
        combined_profiles.update(src.ea4_profile_json)

        #remove duplicates while keeping the order
        dest.ea4_profile_json['pkgs'] = list(OrderedDict.fromkeys(combined_profiles['pkgs']))

        with open('combined_profile.json', 'w') as file:
            file.write(json.dumps(dest.ea4_profile_json)) 

        with SCPClient(dest.client.get_transport()) as scp:
            scp.put("./combined_profile.json", "/root/combined_profile.json")

        install_profile(dest)
        print("EasyApache profile migration passed!")
        return True

    elif dest.php_handler == 'suphp':
        src.ea4_profile_json['pkgs'].remove('ea-apache24-mod_ruid2')
        mod_php_list = fnmatch.filter(combined_profiles['pkgs'], 'ea-php??-php')
        for dso_version in mod_php_list:
            src.ea4_profile_json['pkgs'].remove(dso_version)
        
        #combine the two profiles
        combined_profiles = src.ea4_profile_json.copy()
        combined_profiles = combined_profiles.update(src.ea4_profile_json)

        #remove duplicates while keeping the order
        dest.ea4_profile_json['pkgs'] = list(OrderedDict.fromkeys(combined_profiles['pkgs']))

        print(dest.ea4_profile_json)

    elif dest.php_handler == 'lsapi' or dest.isRunningCloudLinux() is True:

        #combine the two profiles
        combined_profiles = src.ea4_profile_json.copy()
        combined_profiles = combined_profiles.update(src.ea4_profile_json)

        #remove duplicates while keeping the order
        combined_profiles['pkgs'] = list(OrderedDict.fromkeys(combined_profiles['pkgs']))

        print(combined_profiles)

    else:
        return False

def install_profile(dest):
    dest.run_command("/usr/local/bin/ea_install_profile --install /root/combined_profile.json")