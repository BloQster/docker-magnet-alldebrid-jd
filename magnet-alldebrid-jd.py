"""Script to watch a folder for new magnet links being put in, uploading them to alldebrid and adding the respective links to a MyJdownloader instance when finished"""
import sys
import os
import requests
import json
import re
import time
import threading
import myjdapi

env_vars_to_check = ['ALLDEBRID_UID', 'MYJDOWNLOADER_EMAIL', 'MYJDOWNLOADER_PASSWORD', 'MYJDOWNLOADER_DEVICENAME', 'MAGNETFILE_DIR']

for env_var in env_vars_to_check:
    if os.environ.get(env_var) is None:
        print("{0} is not set, exiting".format(env_var))
        sys.exit(1)

# Alldebrid API variables
torrent_upload_url = 'https://upload.alldebrid.com/uploadtorrent.php'
torrent_upload_params = {'exte': 'nsion', 'splitfile': '1', 'quick': '1'}
torrent_status_url = 'https://alldebrid.com/api/torrent.php'
torrent_status_params = {'json': 'true', 'randval': '0.5892932157480815', '_': '1483729036651'}
torrent_remove_url = 'https://alldebrid.com/torrent/'
torrent_remove_params = {'action': 'remove'}

cookie_data = {'lang': 'en', 'domain': 'com', 'uid': os.environ.get('ALLDEBRID_UID'), 'ssl': '1'}

def main():
    folder_thread = threading.Thread(target=watch_folder_for_magnet_files)
    alldebrid_thread = threading.Thread(target=watch_alldebrid_torrents)

    folder_thread.daemon = alldebrid_thread.daemon = True
    folder_thread.start()
    alldebrid_thread.start()

    while folder_thread.is_alive() and alldebrid_thread.is_alive():
        time.sleep(10)


def watch_folder_for_magnet_files():
    while True:
        file_list = [files for files in os.listdir(os.environ.get('MAGNETFILE_DIR'))
                     if os.path.isfile(os.path.join(os.environ.get('MAGNETFILE_DIR'), files)) and os.path.splitext(files)[1] == '.magnet']
        for file in file_list:
            print("Found magnet file named {0}".format(file))
            with open(os.path.join(os.environ.get('MAGNETFILE_DIR'), file), 'r') as read_file:
                file_contents = read_file.read()
            add_result = add_magnet_to_alldebrid(file_contents)
            if add_result.get('success') == 1:
                os.rename(os.path.join(os.environ.get('MAGNETFILE_DIR'), file), os.path.join(os.environ.get('MAGNETFILE_DIR'), str(add_result.get('id')) + '.dl'))
                print("Successfully added {0} to Alldebrid".format(file))
            elif add_result.get('error') == 4:
                os.rename(os.path.join(os.environ.get('MAGNETFILE_DIR'), file), os.path.join(os.environ.get('MAGNETFILE_DIR'), os.path.splitext(file)[0] + '.dup'))
                print("{0} was already added to Alldebrid".format(file))
            else:
                os.rename(os.path.join(os.environ.get('MAGNETFILE_DIR'), file), os.path.join(os.environ.get('MAGNETFILE_DIR'), os.path.splitext(file)[0] + '.fail'))
                print("An unknown error has occurred while adding {0}.".format(file))
        time.sleep(1)


def watch_alldebrid_torrents():
    while True:
        torrent_list = json.loads(requests.get(torrent_status_url, cookies=cookie_data, params=torrent_status_params).text or "[]")
        for torrent in torrent_list:
            torrent_id = torrent[1]
            torrent_status = torrent[4]
            if torrent_status == 'finished' and torrent_id in [os.path.splitext(files)[0] for files in os.listdir(os.environ.get('MAGNETFILE_DIR'))
                                                               if os.path.isfile(os.path.join(os.environ.get('MAGNETFILE_DIR'), files)) and os.path.splitext(files)[1] == '.dl']:
                torrent_name = re.sub(r"^<span.*?>(.*?)<\/span>$", r"\1", torrent[3])
                links = [x.replace('http:', 'https:') for x in re.sub(r"^<a value=.*?(http.*),;,.*$", r"\1", torrent[10]).split(',;,')]

                add_result = add_links_to_jd(torrent_name, links)
                if add_result['id'] is not None:
                    print("{0} has been successfully added to myJD (id: {1}, {2} links)".format(torrent_name, add_result['id'], len(links)))
                else:
                    print("{0} could not be added to myJD".format(torrent_name))

                remove_result = remove_torrent_from_alldebrid(torrent_id)
                os.remove(os.path.join(os.environ.get('MAGNETFILE_DIR'), torrent_id + '.dl'))
                if remove_result.status_code == 302:
                    print("{0} has been successfully removed from Alldebrid".format(torrent_name))
                elif remove_result.status_code == 200:
                    print("{0} could not be found on the Alldebrid list".format(torrent_name))
        time.sleep(5)
            

def get_myjd_device():    
    my_jdownloader_controller = myjdapi.Myjdapi()
    my_jdownloader_controller.connect(os.environ.get('MYJDOWNLOADER_EMAIL'), os.environ.get('MYJDOWNLOADER_PASSWORD'))
    return my_jdownloader_controller.get_device(os.environ.get('MYJDOWNLOADER_DEVICENAME'))

def add_magnet_to_alldebrid(magnet_link):
    return json.loads(requests.post(torrent_upload_url, cookies=cookie_data, data={**{'magnet': magnet_link}, **torrent_upload_params}).text or "[]")


def remove_torrent_from_alldebrid(torrent_id):
    return requests.get(torrent_remove_url, cookies=cookie_data, params={**{'id': torrent_id}, **torrent_remove_params}, allow_redirects=False or "[]")


def add_links_to_jd(package_name, links):
    return get_myjd_device().linkgrabber.add_links([{"autostart": True, "links": ','.join(links), "packageName": package_name}])
        
        
if __name__ == '__main__':
    sys.exit(main())
