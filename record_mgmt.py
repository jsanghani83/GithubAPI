#!/usr/bin/env python
#coding:utf-8
"""
  Author: Swagat
  Purpose: Handle all records available in config.txt
  Created: Tuesday 24 May 2016
"""
import logging
logging.basicConfig(filename='records.log', level=logging.INFO)

import time
import os
import base64
import requests
import json
from datetime import datetime

import settings
from main import githash


class Records(object):

    def __init__(self):
        self.github_rate_limit_count = 0
        self.downloaded_file = "CONFIG.txt"
        self.email = "PMOLINEUX@HOTMAIL.COM"
        self.murakh = ''

    def run(self):
        self.downloaded_file = settings.CONFIG_FILE
        self.extract_objects()
        self.file_handler()
    
    def extract_objects(self):
        self.record_list = []

        with open(settings.CONFIG_FILE, 'r') as f:
            one_record = ''
            for line in f:
                if line.startswith("OBJECT:"):
                    if one_record:
                        self.record_list.append(one_record)
                        one_record = ''
                one_record += line
            if one_record and one_record.startswith("OBJECT:"):
                self.record_list.append(one_record)
        print "self.record_list = ", self.record_list
    
    def file_handler(self):
        for each_object in self.record_list:
            self.get_or_create_files(each_object)
    
    def get_or_create_files(self, each_object):
        _split_records = each_object.split()
        obj_details = self._get_object_details(_split_records[:2])
        file_name = "{}.txt".format(obj_details['OBJECT']) 
        with open(file_name, "a") as ofile:
            file_content = "\n".join(each_object.split('\n')[1:])
            self.murakh = file_content[32:62].strip()
            ofile.write(file_content)
        self.commit_file_code(file_name, obj_details)
    
    def commit_file_code(self, file_name, obj_details):
        file_content = open(file_name).read()
        self.commit_response = {}
        self.email = obj_details.get("EMAIL")
        params = {}
        content_encoded = base64.b64encode(file_content)
        params['message'] = file_name + " created"
        params['content'] = content_encoded
        params['branch'] = "abap"
        params['path'] = file_name
        params['committer'] = {'name': "1", 'email': self.email}
        url = settings.CONFIG_GITHUB_URL + file_name
        self.check_sleep_and_set_api_count()
        request_status = requests.put(url, auth=(settings.GIT_USERNAME, settings.GIT_PASSWORD), data=json.dumps(params))
        if request_status.status_code == 201:
            self.commit_response = request_status.json()
        elif request_status.status_code == 422:
            new_params = {}
            new_params['ref'] = 'abap'
            new_params['path'] = file_name
            self.check_sleep_and_set_api_count()
            get_file = requests.get(url, auth=(settings.GIT_USERNAME, settings.GIT_PASSWORD), params=new_params).json()
            new_checksum = githash(open(file_name).read())
            if new_checksum != get_file['sha']:
                params['sha'] = get_file['sha']
                params['message'] = file_name + " updated"
                self.check_sleep_and_set_api_count()
                request_status = requests.put(url, auth=(settings.GIT_USERNAME, settings.GIT_PASSWORD), data=json.dumps(params))
                self.commit_response = request_status.json()
        self.log_to_db()

    @staticmethod
    def _get_object_details(_split):
        r = {}
        # sample = OBJECT:TVAK
        for _o in _split:
            _ = _o.split(":")
            r[_[0]] = _[1]
        return r
    
    def log_to_db(self):
        if not self.commit_response:
            return None

        file_name = self.commit_response['commit']['message']
        #if file_name.endswith('created'):
        head_sha = self.commit_response['commit']['sha']
        if self.commit_response['commit']['parents'] == []:
            base_sha = head_sha
            print base_sha, "base ----> first file commit_id"
        else:
            base_commit = self.commit_response['commit']['parents'][0]
            base_sha = base_commit['sha']
            print base_sha, "base ----> commit_id of previous file"
         
        print head_sha, "head ----> current file commit_id"
        #else:
            #res_url = '{}commits?path={}'.format(settings.CONFIG_GITHUB_URL.replace("contents/", ""), file_name.split(" ")[0])
            #file_history = requests.get(res_url).json()
            #print file_history, "file_history"
            #head_sha = file_history[0]['sha']
            #print head_sha, "head ----> updated file commit_id"
            #if len(file_history) > 1:
                #base_sha = file_history[1]['sha']
                #print base_sha, "base ----> created file commit_id"
            #else:
                #base_sha = head_sha
        
        reponame = self.commit_response['commit']['html_url'].split("/")[-3]
        author_name = self.commit_response['commit']['author']['name']
        url = settings.GET_DELTA_API + '?USER_EMAIL={}&SAP_OBJECT={}&BASE={}&HEAD={}&REPO_NAME={}&USER_AUTHOR={}'.format(self.email,
            self.murakh,
            base_sha,head_sha,
            str(reponame),author_name)
        response = requests.get(url)
    
    def check_sleep_and_set_api_count(self):
        if self.github_rate_limit_count > 28:
            self.github_rate_limit_count = 0
            time.sleep(30)
        self.github_rate_limit_count += 1

if __name__ == '__main__':
    r = Records()
    r.run()
