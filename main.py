'__author__' == 'egrove'
import base64
import os
import settings
import logging
import requests
import json
import traceback

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

def upload_files_to_git(file, name_dicts):
    params = dict()

    with open(file.name) as infile:
        content_encoded = base64.b64encode(infile.read())
    params['message'] = file.name + " updated"
    params['content'] = content_encoded
    params['branch'] = settings.GIT_BRANCH
    params['path'] = file.name
    params['committer'] = {'name':name_dicts['AUTHOR'], 'email':settings.GIT_EMAIL}
    url = settings.GITHUP_API_URL + file.name
    request_status = requests.put(url, auth=(settings.GIT_USERNAME, settings.GIT_PASSWORD), data=json.dumps(params))
    if request_status.status_code == 201:
        print file.name + ' is created'
    elif request_status.status_code == 422:
        print file.name + ' already created'
    return True


def file_reader(filename):
    search_for_start = True
    search_for_finish = False
    with open(filename) as infile:
        for each_line in infile:
            if search_for_start:
                if each_line.startswith('START:') or each_line.startswith('START TABLE:'):
                    name_dicts = get_names(each_line)
                    search_for_start = False
                    search_for_finish = True
                    file_name = name_dicts.get('START') or name_dicts.get('TABLE')
                    #name_dicts['START'] = check_for_dup_file(name_dicts['START'])
                    f_obj = open(file_name+'.txt','w')

            if search_for_finish:
                f_obj.writelines(each_line)
                if each_line.startswith('FINISH:') or each_line.startswith('FINISH TABLE:'):
                    search_for_start = True
                    search_for_finish = False
                    msg = name_dicts.get('START') or name_dicts.get('TABLE')
                    logging.info(msg +':: write-completed')
                    f_obj.close()
                    upload_files_to_git(f_obj, name_dicts)


def main():

    try:
        for root, dirs, files in os.walk(settings.SAP_FILE_PATH):
            for file in files:
                file_path = root +'/' + str(file)
                if file.startswith('TABLE'):
                    settings.GIT_BRANCH = 'table'
                else:
                    settings.GIT_BRANCH = 'abab'
                file_reader(file_path)
        logging.info('STOP')
    except Exception as e:

        logging.error(traceback.print_exc())

if __name__ == '__main__':
     main()


