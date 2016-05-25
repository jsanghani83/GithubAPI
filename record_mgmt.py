#!/usr/bin/env python
#coding:utf-8
"""
  Author: Swagat
  Purpose: Handle all records available in config.txt
  Created: Tuesday 24 May 2016
"""
import logging
logging.basicConfig(filename='records.log', level=logging.INFO)

import os
import base64
import requests
import json
from datetime import datetime

import settings
from main import githash


class Records(object):

    def __init__(self):
        self.downloaded_file = "CONFIG.txt"
        self.has_downloaded = self.get_download_file()

    def run(self):
        if not self.has_downloaded:
            print "Oops, The file from github couldn't downloaded, Please try after sometime!"
            return
        self.extract_objects()
        self.file_handler()
    
    def get_download_file(self):
        os.system("wget {} -O {}".format(settings.CONFIG_GITHUB_LINK, self.downloaded_file))
        return os.path.isfile(self.downloaded_file)
    
    def extract_objects(self):
        self.record_list = []
        try:
            last_line_num = int(open(settings.CONFIG_LAST_LINE_FILE).read().strip('\n'))
        except ValueError:
            last_line_num = 0

        with open(self.downloaded_file, 'r') as f:
            one_record = ''
            for line_number, line in enumerate(f):
                if not last_line_num or line_number > last_line_num:
                    if line.startswith("OBJECT:"):
                        if one_record:
                            self.record_list.append(one_record)
                            one_record = ''
                    one_record += line
            if one_record:
                
                self.record_list.append(one_record)
        print "self.record_list = ", self.record_list
        with open(settings.CONFIG_LAST_LINE_FILE, 'w') as lf:
            lf.write(str(line_number))
        print "Done"
    
    def file_handler(self):
        for each_object in self.record_list:
            self.get_or_create_files(each_object)
    
    def get_or_create_files(self, each_object):
        _split_records = each_object.split()
        obj_details = self._get_object_details(_split_records[:2])
        file_name = "{}.txt".format(obj_details['OBJECT']) 
        with open(file_name, "a") as ofile:
            #_record = ' '.join(_split_records[2:])
            file_content = "\n".join(each_object.split('\n')[1:])
            ofile.write(file_content)
        self.commit_file_code(file_content, file_name, obj_details)
    
    def commit_file_code(self, file_content, file_name, obj_details):
        params = {}
        content_encoded = base64.b64encode(file_content)
        params['message'] = "{}_{}".format(str(datetime.now()), file_name)
        params['content'] = content_encoded
        params['branch'] = "abap"
        params['path'] = file_name
        params['committer'] = {'name': "1", 'email': obj_details.get("EMAIL")}
        url = settings.GITHUP_API_URL + file_name
        request_status = requests.put(url, auth=(settings.GIT_USERNAME, settings.GIT_PASSWORD), data=json.dumps(params))
        if request_status.status_code == 201:
            commit_response = request_status.json()
        elif request_status.status_code == 422:
            new_params = {}
            new_params['ref'] = 'abap'
            new_params['path'] = file_name
            get_file = requests.get(url, auth=(settings.GIT_USERNAME, settings.GIT_PASSWORD), params=new_params).json()
            new_checksum = githash(open(file_name).read())
            if new_checksum != get_file['sha']:
                params['sha'] = get_file['sha']
                params['message'] = "{}_{}".format(str(datetime.now()), file_name)
                request_status = requests.put(url, auth=(settings.GIT_USERNAME, settings.GIT_PASSWORD), data=json.dumps(params))
                commit_response = request_status.json()

    @staticmethod
    def _get_object_details(_split):
        r = {}
        # sample = OBJECT:TVAK
        for _o in _split:
            _ = _o.split(":")
            r[_[0]] = _[1]
        return r

if __name__ == '__main__':
    r = Records()
    r.run()
