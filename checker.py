# Checker v2.0
import json
import time
from datetime import datetime
from threading import Thread, Timer

from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client, MessageHandler, Filters

import data_base as db
try:
    import config_loc as config
except ImportError:
    import config



bot = TeleBot(config.BOT_TOKEN)
cli = Client('session', api_id = config.API_ID, api_hash = config.API_HASH)




class Timers(object):
    def __init__(self, callback):
        self.callback = callback
        self.timers = {}

    def new(self, bot_id):
        print('[Timer] Added new timer for bot id:', bot_id)
        if bot_id in self.timers:
            raise Exception('Bot elready exists!')

        timer = Timer(
            config.TIMEOUT_NOTWORK, self._timer_handler, args = [bot_id]
        )
        timer.start()
        self.timers[bot_id] = timer

    def _timer_handler(self, bot_id):
        print('[Timer] Call timer for bot id:', bot_id)

        del self.timers[bot_id]

        self.callback(bot_id)



    def remove(self, bot_id):

        print('[Timer] Del timer for bot id:', bot_id)
        self.timers[bot_id].cancel()
        del self.timers[bot_id]

class Queue(object):
    def __init__(self, callback_notwork):
        self.timers = Timers(self._timer_handler)   
        self.items = {}
        self.callback_notwork = callback_notwork
    


    def new(self, bot_id):
        print('[Queue] Create new item id:', bot_id)
        self.items[bot_id] = {
            'time_send':time.time(),
            'is_answered':False
            }
        self.timers.new(bot_id)


    def receive(self, bot_id):
        print('[Queue] receiv item id: ', bot_id)
        try:
            info = self.items[bot_id]
        except KeyError:
            return None
        else:
            return info


    def _timer_handler(self, bot_id):
        print('[Queue] Call time hadler ')

        if self.items[bot_id]['is_answered']:
            del self.items[bot_id]
            
            return


        del self.items[bot_id]

        self.callback_notwork(bot_id)


private = Filters.create(
    name=  'def',
    func= lambda _, m: bool(m.from_user)
)

bot_filter = Filters.create(
    name = "BotFilter",
    func = lambda _, msg: msg.from_user.is_bot
)


class Checker(object):
    def __init__(self, bot, cli):
        self.bot = bot
        self.cli = cli
        self.bots_queue = []
        self.queue = Queue(self.not_work_handler)
        self.cli.add_handler(MessageHandler(self._bot_handler, private & bot_filter ))

        self._main_loop()

        self.stats = []

    def _main_loop(self):
        while True:
            self._loop()
            time.sleep(config.SLEEP_LOOP)

    def _loop(self):
        self.bots_queue = db.get_bots_ids()
        if len(self.bots_queue) == 0:
            print('no bots to check')
            return
        all_bots = len(self.bots_queue)
        bot_wait = 60 / all_bots
        self.stats = []
        print('--------------------------------------------')
        print('[Checker] Start loop all bots: ', len(self.bots_queue), '  wait bot: ', bot_wait)
        print('[Checker] All bots: ', self.bots_queue)
        print('--------------------------------------------')

        start_time = time.time()

        for i, (bot_username, bot_id) in enumerate(self.bots_queue):
            self.send_start(bot_username = bot_username, bot_id = bot_id, id = i)
            time.sleep(bot_wait)
        
        
        time_loop = time.time() - start_time

        sum_tw = 0
        work_bots = 0
        for tw in self.stats:
            if tw:
                sum_tw += tw
                work_bots += 1

        avg_tw = float(sum_tw / work_bots)
        







        print('Time loop: ', time_loop)

        db.stats_loop_check(time_loop, all_bots, work_bots, avg_tw)


    def send_start(self, bot_id, bot_username = None, id = None):
        bot_username = bot_username or bot_id
        print('_____________________________________________')
        print(f'[Checker] {id} Send > /start to: {bot_username}')

        try:
            
            self.cli.send_message(bot_username, '/start')
        except Exception as e:
            print('[Checker] Error send msg: ', e)
        else:   
            self.queue.new(bot_id)


    def _bot_handler(self, cli, msg):
        bot_id = msg.from_user.id

        print('[Checker] Get msg from:', msg.from_user.username)


        info = self.queue.receive(bot_id)

        if info:
            if info['is_answered']: # second< msg from bot
                print('receive two+ msgs')
                return
            else: # first msg from bot
                print('norm msg set time wait')
                info['is_answered'] = True
                time_wait = time.time() - info['time_send']
                self.stats.append(time_wait)
                db.set_time_wait(bot_id, time_wait)
        
        else: # msg from no handle bot
            print('bot no handle')
            try:
                bot_status = db.get_status(bot_id)
            except Exception:
                return
            print(bot_status)
            if  bot_status == 'not_work': # bot start work (maybe)
                print('retry check')
                self.send_start(bot_id, msg.from_user.username)
            else: # bot spam 
                print('spam')
                return









    def not_work_handler(self, bot_id):
        print('[Checker] send not work')
        self.stats.append(False)
        db.set_not_work(bot_id)
        creator_id, bot_username = db.get_creator(bot_id)
        try:
            
            msg = self.bot.send_message(
                creator_id,
                text = f'Привет, твой бот @{bot_username} перестал работать и был скрыт от пользователей.'
            )

            markup = InlineKeyboardButton()

            markup.add(InlineKeyboardButton(
                text='Починил!', callback_data = f'checkfix bot_id:{bot_id} msg_id:{msg.message_id}'
            ))

            markup.add(InlineKeyboardButton(
                text='Закрить!', callback_data = 'hide'
            ))

            self.bot.edit_message_reply_markup(
                chat_id = msg.chat.id,
                message_id = msg.message_id,
                reply_markup = markup    
            )
            
        except Exception as e:
            print(f'[Checker] Error send msg not work to: {creator_id}')
            


cli.start()

Checker(bot, cli)
cli.idle()


