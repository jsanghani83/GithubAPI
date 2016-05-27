'__author__' == 'egrove'
import base64
import os
import sys
import settings
import logging
import requests
import json
import traceback
from hashlib import sha1


logging.basicConfig(filename='myapp.log', level=logging.INFO)
logging.info('Started')


def get_names(line):
    name_dict = dict()
    start_vs_author_array = line.strip().split()
    for each_split in start_vs_author_array:
        try:
            name_dict[each_split.split(':')[0]] = each_split.split(':')[1]
        except:
            #todo:Pass for getting Author
            pass
    print name_dict, "name_dict name_dict name_dict"
    return name_dict


def check_for_dup_file(ref_name):
    incrementer = 1
    if os.path.isfile(ref_name+'.txt'):
        while True:
            temp_name = ref_name + '__' + str(incrementer) + '.txt'
            if not os.path.isfile(temp_name):
                return temp_name
            incrementer += 1
    return ref_name + '.txt'


def githash(data):
    # format is sha1("blob " + filesize + "\0" + data)
    s = sha1()
    s.update("blob %u\0" % len(data))
    s.update(data)
    return s.hexdigest()


def upload_files_to_git(file, name_dicts):
    commit_data = None
    commit_response = ""
    if name_dicts.get('START', False):
        settings.GIT_BRANCH = 'abap'
    elif name_dicts.get('TABLE', False):
        settings.GIT_BRANCH = 'table'

    params = dict()
    file_content = None

    with open(file.name) as infile:
        file_content = infile.read()
        content_encoded = base64.b64encode(file_content)
    params['message'] = file.name + " created"
    params['content'] = content_encoded
    params['branch'] = settings.GIT_BRANCH
    params['path'] = file.name
    params['committer'] = {'name': name_dicts.get('AUTHOR'), 'email': name_dicts.get("EMAIL")}
    url = settings.GITHUP_API_URL + file.name

    request_status = requests.put(url, auth=(settings.GIT_USERNAME, settings.GIT_PASSWORD), data=json.dumps(params))
    print request_status, "request_status"
    if request_status.status_code == 201:
        commit_response = request_status.json()
        is_created = True
    elif request_status.status_code == 422:
        new_params = dict()
        new_params['ref'] = settings.GIT_BRANCH
        new_params['path'] = file.name
        get_file = requests.get(url, auth=(settings.GIT_USERNAME, settings.GIT_PASSWORD), params=new_params).json()
        new_checksum = githash(file_content)
        if new_checksum != get_file['sha']:
            params['sha'] = get_file['sha']
            params['message'] = file.name + " updated"
            request_status = requests.put(url, auth=(settings.GIT_USERNAME, settings.GIT_PASSWORD), data=json.dumps(params))
            commit_response = request_status.json()
        else:
            return None
    else:
        print "Got %s response code instead.. exiting..." % request_status.status_code
    
    print commit_response,"commit_response"

    if "commit" in commit_response:
        commit_data = {
            "commit_url": commit_response["commit"]["html_url"],
            "committer_details": commit_response["commit"]["committer"],
            "file_path": commit_response["content"]["path"]
        }

    file_name = commit_response['commit']['message']
    #if file_name.endswith('created'):
    head_sha = commit_response['commit']['sha']
    if commit_response['commit']['parents'] == []:
        base_sha = head_sha
        print base_sha, "base ----> first file commit_id"
    else:
        base_commit = commit_response['commit']['parents'][0]
        base_sha = base_commit['sha']
        print base_sha, "base ----> commit_id of previous file"
     
    print head_sha, "head ----> current file commit_id"
    #else:
        #res_url = '{}commits?path={}'.format(settings.GITHUP_API_URL.replace("contents/", ""), file_name.split(" ")[0])
        #file_history = requests.get(res_url).json()
        #print file_history, "file_history"
        #head_sha = file_history[0]['sha']
        #print head_sha, "head ----> updated file commit_id"
        #if len(file_history) > 1:
            #base_sha = file_history[1]['sha']
            #print base_sha, "base ----> created file commit_id"
        #else:
            #base_sha = head_sha
    
    reponame = commit_response['commit']['html_url'].split("/")[-3]
    author_name = commit_response['commit']['author']['name']
    url = settings.GET_DELTA_API + '?USER_EMAIL={}&SAP_OBJECT=PROG&BASE={}&HEAD={}&REPO_NAME={}&USER_AUTHOR={}'.format(name_dicts.get("EMAIL"),
        base_sha,head_sha,
        str(reponame),author_name)
    response = requests.get(url)
    
    print response.content
    return response

    
def file_reader(filename):
    commit_data = []
    search_for_start = True
    #search_for_finish = False
    with open(filename) as infile:
        for each_line in infile:
            if search_for_start:
                if each_line.startswith('START:') or each_line.startswith('START TABLE:'):
                    name_dicts = get_names(each_line)
                    print name_dicts, "name_dicts"
                    search_for_start = False
                    #search_for_finish = True
                    file_name = name_dicts.get('START') or name_dicts.get('TABLE')
                    #name_dicts['START'] = check_for_dup_file(name_dicts['START'])
                    f_obj = open(file_name+'.txt','w')

            else:

                if each_line.startswith('FINISH:') or each_line.startswith('FINISH TABLE:'):
                    search_for_start = True
                    #search_for_finish = False
                    msg = name_dicts.get('START') or name_dicts.get('TABLE')
                    logging.info(msg +':: write-completed')
                    f_obj.close()
                    _commit_data = upload_files_to_git(f_obj, name_dicts)
                    commit_data.append(_commit_data) if _commit_data else None
                else:
                    f_obj.writelines(each_line)
    return commit_data


def main():
    commit_data = []

    try:
        for root, dirs, files in os.walk(settings.SAP_FILE_PATH):
            for file in files:
                file_path = root +'/' + str(file)
                _commit_data = file_reader(file_path)
                print _commit_data, "_commit_data _commit_data"
                commit_data.append(_commit_data) if _commit_data else None
        logging.info("Please find the commit details for the day")
        print commit_data, "commit_data commit_data final"
        logging.info('STOP')
    except Exception as e:

        logging.error(traceback.print_exc())

if __name__ == '__main__':
    main()