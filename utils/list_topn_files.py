#-*- coding:utf-8 -*-

import requests
import time
import json
from collections import defaultdict

# get your token from here -> https://api.slack.com/docs/oauth-test-tokens
token = ''
# get top n size files
topn = 50
nickname = ''
blind_username = False

def get_user_list():
    params = {
        'token': token
    }
    uri = 'https://slack.com/api/users.list'
    response = requests.get(uri, params=params)
    return json.loads(response.text)['members']

def check_id(nick, user_list):
    for user in user_list:
        if user['name'] == nick:
            return user['id']
    print('no such user')
    return None

def check_nick(user_id, user_list):
    for user in user_list:
        if user['id'] == user_id:
            return user['name']
    print('No such user')
    return None

def list_files(before_n_days=30, user_id='', file_type='images', exclude_starred_items=True):
    """
    :param before_n_days: n일 이전에 올라온 파일만 받아옴. default=30
    :param user_id: 특정 유저가 업로드한 파일만 받아옴. 빈 문자열일 경우 모든 유저의 파일을 받아옴. default=''
    :param file_type: 특정 타입의 파일만 받아옴. default='images'
                      * 'all': All files
                      * 'spaces: Posts
                      * 'snippets': Snippets
                      * 'images': Image files
                      * 'videos': Video files
                      * 'audios': Audio files
                      * 'gdocs': Google docs
                      * 'zips': Zip files
                      * 'pdfs': PDF files
    :param exclude_starred_items: 유저에게 Star되어있는 파일을 제외할지의 옵션. default=True
    """
    types = file_type
    if file_type == 'videos' or file_type == 'audios':
        types = 'all'
    
    params = {
        'token': token,
        'ts_to': int(time.time()) - before_n_days * 24 * 60 * 60,
        'ts_from': 0,
        'count': 1000,
        'types': types,
    }
    if user_id != '':
        params['user'] = user_id
        
    uri = 'https://slack.com/api/files.list'
    response = requests.get(uri, params=params)
    pages_num = json.loads(response.text)['paging']['pages']
    
    result_files = []
    for i in range(1, pages_num+1):
        params['page'] = i
        response = requests.get(uri, params=params)
        files = json.loads(response.text)['files']
        
        for file in files:
            # Starred items 제외
            if exclude_starred_items:
                try:
                    is_starred = file['is_starred']
                    if is_starred: continue
                except KeyError:
                    pass
            
            # Video & Audio files 수동 
            if file_type == 'videos' or file_type == 'audios':
                if file['mimetype'].split('/')[0] != file_type[:-1]:
                    continue

            result_files.append(file)
    
    return result_files


if __name__ == '__main__':
    if nickname != '':
        user_id = check_id(nickname, get_user_list())
    else:
        user_id = ''

    files = list_files(before_n_days=0, user_id=user_id, file_type='all', exclude_starred_items=False)

    users = get_user_list()
    user_size_dict = defaultdict(lambda: 0)

    file_size_dict = defaultdict(lambda: ())
    for file in files:
        file_size_dict[file['id']] = (file['title'], file['name'], file['user'], file['size'])
        
    sorted_file_size = sorted(file_size_dict.items(), key=lambda x:x[1][3], reverse=True)

    for i, file_size in enumerate(sorted_file_size[:topn]):
        name = check_nick(file_size[1][2], users)
        size = file_size[1][3] / 1048576
        if blind_username:
            print('%2d위 : %15s\t%50s\t%3dMB' % (i+1, name[0]+'.'+name[1:], file_size[1][0], size))
        else:
            print('%2d위 : %15s\t%50s\t%3dMB' % (i+1, name, file_size[1][0], size))