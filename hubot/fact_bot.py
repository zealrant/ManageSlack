#-*- coding:utf-8 -*-

import time
import json
import random
import datetime
import asyncio
import websockets
from slacker import Slacker
from collections import defaultdict


class FactBot:
    """

    """

    def __init__(self, token, admin_name, default_path):
        self.token = token
        self.slacker = Slacker(self.token)
        self.default_path = default_path
        self.ignore_channel_list = []
        self.load_ignore_channel_list()
        self.ignore_user_list = []
        self.load_ignore_user_list()
        self.id = self.slacker.auth.test().body['user_id']
        self.admin_id = self.get_user_id(admin_name)

        self.slacking_dict = defaultdict(lambda: defaultdict(lambda: 0))

        self.commands = {'help': 'help', 'ping': 'ping', 'count_auth': 'count',
                         'print_stats': 'stats', 'die': 'die'}
        self.hello_message = 'Factbot Start running!'
        self.error_message = 'Error Error <@nerrtica>'
        self.stop_message = 'Too many Error... <@nerrtica>'
        self.die_messages = [':innocent: :gun:', '으앙듀금', '꿲', '영웅은 죽지않아요']

    def run(self):
        async def execute_bot():
            response = self.slacker.rtm.start()
            sock_endpoint = response.body['url']
            ws = await websockets.connect(sock_endpoint)
            now = time.localtime()
            day = '%4d' % now.tm_year + '%02d' % now.tm_mon + '%02d' % now.tm_mday
            today = now.tm_mday
            error_count = 0

            if len(list(self.slacking_dict.keys())) == 0:
                self.slacking_dict = self.get_slacking_counts(day)
            self.slacker.chat.post_message('#_factbot_notice', self.hello_message, as_user=True)

            while True:

                try:
                    if error_count > 10:
                        self.slacker.chat.post_message('#_factbot_notice', self.stop_message, as_user=True)
                        self.save_slacking_counts(day)
                        return

                    message = await ws.recv()
                    message_json = json.loads(message)

                    # Print Slacking
                    now = time.localtime()
                    if now.tm_mday != today:
                        self.print_slacking()
                        self.save_slacking_counts(day)

                        today = now.tm_mday
                        day = '%04d' % now.tm_year + '%02d' % now.tm_mon + '%02d' % now.tm_mday
                        self.slacking_dict = defaultdict(lambda: defaultdict(lambda: 0))
                        error_count = 0

                    # Command Message
                    main_command, sub_command = FactBot.get_command(message_json)
                    is_command = False
                    if main_command and (main_command in self.commands.values()):
                        is_command = self.react_command(message_json, main_command, sub_command, day)

                    # Slacking Count
                    if not is_command:
                        self.slacking_count(message_json)

                except:
                    self.slacker.chat.post_message('#_factbot_notice', self.error_message, as_user=True)
                    for im in self.slacker.im.list().body['ims']:
                        if im['user'] == self.admin_id:
                            self.slacker.chat.post_message(im['id'], str(message_json), as_user=True)
                    error_count += 1
                    continue

        while True:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            asyncio.get_event_loop().run_until_complete(execute_bot())

    @staticmethod
    def get_command(message_json):
        """If a user calls factbot, get bot command string.

        :param message_json: Slack message json
        :return: command string or None
        """
        try:
            if message_json.get('type') != 'message':
                return '', ''
            if 'subtype' in message_json.keys():
                return '', ''
            if message_json.get('text')[:8] != 'factbot ':
                return '', ''
            if 'bot_id' in message_json.keys():
                return '', ''

            full_command = message_json.get('text')[8:]
            if full_command.find(' ') == -1:
                return full_command, ''
            else:
                return full_command[:full_command.find(' ')], full_command[full_command.find(' ')+1:]

        except:
            raise TypeError

    def slacking_count(self, message_json):
        """Count user's message for Today's Slacking.

        :param message_json: Slack message json
        """
        try:
            if message_json.get('type') != 'message':
                return
            if 'subtype' in message_json.keys():
                return
            if 'bot_id' in message_json.keys():
                return
            if message_json.get('user') in self.ignore_user_list:
                return

            self.slacking_dict[message_json.get('channel', '')][message_json.get('user', '')] += 1

        except:
            raise TypeError

    def react_command(self, message_json, main_command, sub_command, day):
        if message_json.get('channel') in self.get_im_id_list():
            pass
        elif not self.get_channel_info(message_json.get('channel')).get('is_member', False):
            return

        if main_command == self.commands.get('help'):
            return self.print_help(message_json, sub_command)

        elif main_command == self.commands.get('ping'):
            if sub_command == '':
                answer = '<@%s> pong' % message_json.get('user', 'UNDEFINED')
                self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
                return True
            return False

        elif main_command == self.commands.get('count_auth'):
            return self.swap_count_auth(message_json, sub_command)

        elif main_command == self.commands.get('print_stats'):
            return self.print_stats(message_json, sub_command, day)

        elif main_command == self.commands.get('die'):
            # TODO: 코드 정리
            if sub_command == '':
                answer = self.die_messages[random.randrange(len(self.die_messages))]
                self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
                return True

            if self.get_channel_info(message_json.get('channel'))['name'] != 'zero-bot':
                return False
            elif 'add ' in sub_command:
                if sub_command[4:] in self.die_messages:
                    self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), '이미 있음', as_user=True)
                    return True
                self.die_messages.append(sub_command[4:])
                self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), '유언 추가 완료', as_user=True)
                return True
            elif 'remove ' in sub_command:
                try:
                    self.die_messages.remove(sub_command[7:])
                    self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), '유언 제거', as_user=True)
                except ValueError:
                    self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), '그런 말 모름', as_user=True)
                return True
            return False

        else:
            return False

    def print_help(self, message_json, sub_command):
        if sub_command == '':
            answer = '※ factbot을 사용하기 위해서는 각 채널에 초대를 하시기 바랍니다.\n\n'
            answer += 'factbot은 각 채널 별로 매일 가장 슬랙 사용량이 높은 유저를 슬랙왕으로 추대합니다 :innocent: \n'
            answer += '사용량 통계는 *사용자별, 날짜별 메시지 count* 로만 추정하며, 지난 정보 저장을 위해 로컬에 파일로 저장됩니다.'
            self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)

            answer = 'factbot %s - 헬푸미\n' % self.commands.get('help')
            answer += 'factbot %s - 핑퐁핑퐁핑핑퐁퐁\n' % self.commands.get('ping')
            answer += 'factbot %s stop - 명령어 사용 당사자를 더 이상 count하지 않습니다.\n' % self.commands.get('count_auth')
            answer += 'factbot %s start - 명령어 사용 당사자를 count하기 시작합니다.\n' % self.commands.get('count_auth')
            answer += 'factbot %s - 명령어 사용 당사자의 당일 슬랙 사용량을 출력합니다.\n' % self.commands.get('print_stats')
            answer += 'factbot %s <yyyymmdd> - 명령어 사용 당사자의 해당 일 슬랙 사용량을 출력합니다.\n' % \
                      self.commands.get('print_stats')
            answer += 'factbot %s - 네?\n' % self.commands.get('die')
            self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)

            answer = '기능 추가 및 버그 수정은 GitHub Repository에 Pull Request로 보내주시기 바랍니다.\n'
            answer += 'Repository : https://github.com/Nerrtica/ManageSlack'
            self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
            return True
        # TODO: 특정 명령어의 help 메시지
        else:
            return False

    def swap_count_auth(self, message_json, sub_command):
        if sub_command == 'start':
            try:
                self.ignore_user_list.remove(message_json.get('user'))
                self.save_ignore_user_list()
                answer = '다시 <@%s> 님의 메시지 개수를 저장하기 시작했어요.' % message_json.get('user', 'UNDEFINED')
                self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
            except ValueError:
                answer = '이미 <@%s> 님의 메시지 개수를 저장하고 있어요.' % message_json.get('user', 'UNDEFINED')
                self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
            return True
        elif sub_command == 'stop':
            if self.ignore_user_list.count(message_json.get('user')) == 0:
                self.ignore_user_list.append(message_json.get('user'))
                self.save_ignore_user_list()
                answer = '더 이상 <@%s> 님의 메시지 개수를 저장하지 않아요.' % message_json.get('user', 'UNDEFINED')
                self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
            else:
                answer = '이미 <@%s> 님의 메시지 개수를 저장하지 않고 있어요.' % message_json.get('user', 'UNDEFINED')
                self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
            return True
        else:
            return False

    def print_stats(self, message_json, sub_command, day):
        if self.ignore_user_list.count(message_json.get('user')) != 0:
            answer = '메시지 개수를 저장하지 않는 유저는 사용할 수 없는 기능이에요.'
            self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
            return True

        if sub_command == '' or sub_command == '%s' % day:
            date = day
            channel_count_dict = self.slacking_dict

        # easter egg
        elif sub_command == '석양이진다빵빵빵':
            date = '석양이진다빵빵빵'
            channel_count_dict = defaultdict(lambda: defaultdict(lambda: 0))

        elif len(sub_command) == 8:
            date = sub_command

            try:
                _ = datetime.datetime(int(date[:4]), int(date[4:6]), int(date[6:8]))

                if int(date[:4]) < 2017:
                    answer = '그 때는 제가 태어나기 전이라구요 :sob:'
                    self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
                    return True

                elif int(date) > int(day):
                    answer = '뭐에요, 저보고 미래라도 보라는 건가요?'
                    self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
                    return True

                channel_count_dict = self.get_slacking_counts(date)

            except ValueError:
                answer = '제대로 된 포맷으로 적어주세요. <YYYYMMDD>'
                self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
                return True

        else:
            answer = '제대로 된 포맷으로 적어주세요. <YYYYMMDD>'
            self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
            return True

        answer = '<@%s> 님의 %s년 %s월 %s일 통계에요.\n\n' % \
                 (message_json.get('user', 'UNDEFINED'), date[:4], date[4:6], date[6:8])

        user_count_dict = defaultdict(lambda: 0)
        im_id_list = self.get_im_id_list()
        for channel in sorted(list(channel_count_dict.keys())):
            if channel in im_id_list:
                continue
            # _factbot_notice
            if channel == 'C47D40HFA':
                continue
            my_ch_count = channel_count_dict[channel][message_json.get('user')]
            channel_count_sum = sum(channel_count_dict[channel].values())
            for user in channel_count_dict[channel].keys():
                user_count_dict[user] += channel_count_dict[channel][user]
            if my_ch_count != 0:
                ch_count = sorted(channel_count_dict[channel].items(), key=lambda x: x[1], reverse=True)
                answer += '<#%s> %d회 (%d위, 점유율 %d%%)\n' % \
                          (channel, my_ch_count, [i[0] for i in ch_count].index(message_json['user']) + 1,
                           my_ch_count / channel_count_sum * 100)

        if user_count_dict[message_json.get('user')] == 0:
            answer += '해당 날짜의 메시지 카운트 정보가 없어요.'
            self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
            return True

        all_count = sorted(user_count_dict.items(), key=lambda x: x[1], reverse=True)
        answer += '\n전체 %d회 (%d위, 점유율 %d%%)\n' % \
                  (user_count_dict[message_json.get('user')],
                   [i[0] for i in all_count].index(message_json.get('user')) + 1,
                   user_count_dict[message_json.get('user')] / sum([i[1] for i in all_count]) * 100)

        self.slacker.chat.post_message(message_json.get('channel', '#zero-bot'), answer, as_user=True)
        return True

    def print_slacking(self):
        im_id_list = self.get_im_id_list()
        for channel in self.slacking_dict.keys():
            if channel in self.ignore_channel_list:
                continue
            if channel in im_id_list:
                continue
            if not self.get_channel_info(channel).get('is_member', False):
                continue
            bot_say = '[오늘의 슬랙왕]\n\n'

            ch_count = sorted(self.slacking_dict[channel].items(), key=lambda x: x[1], reverse=True)
            chat_count_sum = sum([i[1] for i in ch_count])
            if chat_count_sum < 5:
                bot_say += '오늘은 <#%s> 채널의 채팅이 거의 없었네요. 많은 참여 부탁드립니다! :3\n' % channel
            else:
                bot_say += '오늘 <#%s> 채널에서는 총 %d회의 채팅이 오갔어요!\n' % (channel, chat_count_sum)
                king_name = self.get_user_info(ch_count[0][0]).get('name', 'UNDEFINED')
                bot_say += '오늘의 <#%s> 채널 슬랙왕은 %s입니다! %d회의 채팅을 하셨어요!\n' % \
                           (channel, king_name[0] + '.' + king_name[1:], ch_count[0][1])
            bot_say += '\n(factbot의 사용법이 필요하시면 `factbot %s`! 피드백은 DM <@%s>!)' % \
                       (self.commands.get('help', 'help'), self.admin_id)

            self.slacker.chat.post_message(channel, bot_say, as_user=True)

    def save_slacking_counts(self, day):
        with open(self.default_path+'data/slacking_counts/'+day+'.log', 'w') as f:
            for channel in self.slacking_dict.keys():
                f.write('#%s\n' % channel)
                for user in self.slacking_dict[channel].keys():
                    f.write('%s : %d\n' % (user, self.slacking_dict[channel][user]))
                f.write('\n')

    def get_slacking_counts(self, day):
        try:
            with open(self.default_path+'data/slacking_counts/'+day+'.log', 'r') as f:
                channel_count_dict = defaultdict(lambda: defaultdict(lambda: 0))
                channel = ''
                for line in f.readlines():
                    line = line.strip()
                    if '#' in line:
                        channel = line[1:]
                    elif ':' in line:
                        channel_count_dict[channel][line.split(':')[0].strip()] = int(line.split(':')[1].strip())
            return channel_count_dict

        except FileNotFoundError:
            return defaultdict(lambda: defaultdict(lambda: 0))

    def get_past_count_history(self, day):
        def _slacking_count(message_json, chan):
            try:
                if message_json.get('type') != 'message':
                    return
                if 'subtype' in message_json.keys():
                    return
                if 'bot_id' in message_json.keys():
                    return

                self.slacking_dict[chan][message_json.get('user', '')] += 1
            except:
                raise TypeError

        start_unix_sec = '%.6f' % time.mktime(time.strptime(day[:4]+'/'+day[4:6]+'/'+day[6:], '%Y/%m/%d'))
        end_unix_sec = '%.6f' % time.mktime(time.strptime(day[:4]+'/'+day[4:6]+'/'+day[6:]+' 23:59:59',
                                                          '%Y/%m/%d %H:%M:%S'))
        channels = self.get_channel_id_list()

        for channel in channels:
            if not self.get_channel_info(channel).get('is_member', False):
                continue

            while True:
                channel_history = self.slacker.channels.history(channel=channel, count=1000, oldest=start_unix_sec,
                                                                latest=end_unix_sec).body
                for msg in channel_history['messages']:
                    _slacking_count(msg, channel)
                if not channel_history.get('has_more', False):
                    break
                end_unix_sec = '%.6f' % (float(channel_history['messages'][-1].get('ts', 1)) - 0.00001)

    def save_ignore_channel_list(self):
        with open(self.default_path+'data/ignore_channel_list.txt', 'w') as f:
            for channel in self.ignore_channel_list:
                f.write('%s\n' % channel)

    def load_ignore_channel_list(self):
        with open(self.default_path+'data/ignore_channel_list.txt', 'r') as f:
            self.ignore_channel_list = [line.strip() for line in f.readlines()]

    def save_ignore_user_list(self):
        with open(self.default_path+'data/ignore_user_list.txt', 'w') as f:
            for user in self.ignore_user_list:
                f.write('%s\n' % user)

    def load_ignore_user_list(self):
        with open(self.default_path+'data/ignore_user_list.txt', 'r') as f:
            self.ignore_user_list = [line.strip() for line in f.readlines()]

    def get_user_id_list(self):
        return [user['id'] for user in self.slacker.users.list().body['members']]

    def get_channel_id_list(self):
        return [channel['id'] for channel in self.slacker.channels.list().body['channels']]

    def get_im_id_list(self):
        return [im['id'] for im in self.slacker.im.list().body['ims']]

    def get_user_id(self, user_name):
        users = self.slacker.users.list().body['members']
        for user in users:
            if user['name'] == user_name:
                return user['id']
        return None

    def get_user_info(self, user_id):
        """

        :param user_id: user id
        :return: {'color': 'hex color',
                  'deleted': True/False,
                  'id': 'user id',
                  'is_admin': True/False,
                  'is_bot': True/False,
                  'is_owner': True/False,
                  'is_primary_owner': True/False,
                  'is_restricted': True/False,
                  'is_ultra_restricted': True/False,
                  'name': 'user nickname',
                  'profile': {'avatar_hash', 'email', 'first_name', 'last_name', 'real_name',
                              'real_name_normalized', 'image_<size>', 'title'},
                  'real_name': 'user realname',
                  ...
                  }
        """
        return self.slacker.users.info(user=user_id).body['user']

    def get_channel_info(self, channel_id):
        """

        :param channel_id: channel id
        :return: {'created': Unix time,
                  'creator': 'user id',
                  'id': 'channel id',
                  'is_archived': True/False,
                  'is_channel': True/False,
                  'is_general': True/False,
                  'is_member': True/False,
                  'members': [user id],
                  'name': 'channel name',
                  'previous_names': [previous name],
                  'purpose': {'creator': 'user id', 'last_set': Unix time, 'value': 'text'},
                  'topic': {'creator': 'user id', 'last_set': Unix time, 'value': 'text'}}
        """
        return self.slacker.channels.info(channel=channel_id).body['channel']
