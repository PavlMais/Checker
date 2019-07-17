# Checker v2.0
import json
import time
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
        self.items[bot_id] = time.time()
        self.timers.new(bot_id)


    def receive(self, bot_id):
        print('[Queue] receiv item id: ', bot_id)
        try:
            time_create = self.items.pop(bot_id)
        except KeyError:
            return False
        else:
            self.timers.remove(bot_id)
            return time.time() - time_create


    def _timer_handler(self, bot_id):
        print('[Queue] Call not work hadler ')
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

    def _main_loop(self):
        while True:
            self._loop()
            time.sleep(config.SLEEP_LOOP)

    def _loop(self):
        self.bots_queue = db.get_bots_ids()
        if len(self.bots_queue) == 0:
            return
        bot_wait = 60 / len(self.bots_queue)

        print('--------------------------------------------')
        print('[Checker] Start loop all bots: ', len(self.bots_queue), '  wait bot: ', bot_wait)
        print('[Checker] All bots: ', self.bots_queue)
        print('--------------------------------------------')


        for i, (bot_username, bot_id) in enumerate(self.bots_queue):
            self.send_start(bot_username = bot_username, bot_id = bot_id, id = i)
            time.sleep(bot_wait)


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

        print('[Checker] Get msg from:', msg.from_user.id,)

        bot_id = msg.from_user.id

        time_wait = self.queue.receive(bot_id)

        if time_wait is False:
            print('[Checker] Get msg from:', msg.from_user.username, ' no find in queue')

            return 

        db.set_time_wait(bot_id, time_wait)


    def not_work_handler(self, bot_id):
        print('[Checker] send not work')
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

