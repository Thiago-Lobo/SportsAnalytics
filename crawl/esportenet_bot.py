# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Job
from os.path import exists
from os import makedirs
from datetime import datetime, timedelta
import crawler
import ConfigParser
import logging

# ------ Init Config ------

config_path = "./config.ini"
config_section = "telegram"
logging_section = "logging"

config = ConfigParser.SafeConfigParser()
config.read(config_path)

def config_section_map(section):
    result = {}
    options = config.options(section)
    for option in options:
        try:
            result[option] = config.get(section, option)
        except:
            result[option] = None
    return result

# ------ Init Config ------

# ------ Logging Config ------

log_path = config_section_map(logging_section)['log_path']

complete_path = config_section_map(logging_section)['complete_path']
debug_path = config_section_map(logging_section)['debug_path']
general_path = config_section_map(logging_section)['general_path']

general_format = config_section_map(logging_section)['general_format']
specific_format = config_section_map(logging_section)['specific_format']

if not exists(log_path):
    makedirs(log_path)

class SingleLevelFilter(logging.Filter):
    def __init__(self, pass_level, reject):
        self.pass_level = pass_level
        self.reject = reject

    def filter(self, record):
        if self.reject:
            return (record.levelno != self.pass_level)
        else:
            return (record.levelno == self.pass_level)

logger = logging.getLogger('esportenet_bot.py')
logger.setLevel(logging.DEBUG)

general_formatter = logging.Formatter(general_format)
specific_formatter = logging.Formatter(specific_format)

complete_handler = logging.FileHandler(complete_path)
complete_handler.setLevel(logging.DEBUG)
complete_handler.setFormatter(general_formatter)
logger.addHandler(complete_handler)

debug_handler = logging.FileHandler(debug_path)
debug_handler.addFilter(SingleLevelFilter(logging.DEBUG, False))
debug_handler.setFormatter(specific_formatter)
logger.addHandler(debug_handler)

general_handler = logging.FileHandler(general_path)
general_handler.setLevel(logging.INFO)
general_handler.setFormatter(general_formatter)
logger.addHandler(general_handler)

# ------ Logging Config ------

subscription_password = config_section_map(config_section)['subscription_password']
subscribers_file = config_section_map(config_section)['subscribers_file']
token_file = config_section_map(config_section)['token_file']
digest_schedule_hour = config_section_map(config_section)['digest_schedule_hour']

def read_token():
	logger.info("Attempting to read bot token")
	
	try:
		with open(token_file, "r") as f:
			bot_token = [x.rstrip('\n') for x in f.readlines()][0]
			return bot_token
	except Exception as e:
		logger.critical("Couldn't read bot token: {}".format(e.message))

	return None

def callback_digest(bot, job):
	logger.info("Sending digest message")

	if exists(subscribers_file):
		with open(subscribers_file, "r") as f:
			lines = [x.rstrip('\n') for x in f.readlines()]
			for chat_id in lines:
				bot.send_message(chat_id=chat_id,
								 text=u"Essa mensagem chega a cada dia às 08:00!\n")

def add_subscription(chat_id):
	if exists(subscribers_file):
		with open(subscribers_file, "r") as f:
			lines = [x.rstrip('\n') for x in f.readlines()]
			if str(chat_id) in lines:
				return u"Assinatura já existente.\n"

	if not exists(subscribers_file):
		with open(subscribers_file, "w") as f:
			f.write(str(chat_id))
			f.write("\n")
			f.close()
	else:
		with open(subscribers_file, "a") as f:
			f.write(str(chat_id))
			f.write("\n")
			f.close()

	return u"Assinatura adicionada com sucesso.\n"
	
def start(bot, update):
	me = bot.get_me()

	msg = u"Oi!\n"
	msg += u"Sou o {0}.\n".format(me.first_name)
	msg += u"O que você quer fazer?\n\n"
	msg += u"/start - Exibe essa mensagem\n"
	msg += u"/subscribe <senha> - Inscreve você na lista de receptores de apostas\n\n"
	
	bot.send_message(chat_id=update.message.chat_id,
	                 text=msg)

def subscribe(bot, update, args):
	if len(args) > 0 and args[0] == subscription_password:
		result = add_subscription(update.message.chat_id)
		bot.send_message(chat_id=update.message.chat_id,
	                 	 text=result)
	else:
		bot.send_message(chat_id=update.message.chat_id,
	                 	 text=u"Senha incorreta.\n")

def test(bot, update):
	with open(subscribers_file, "r") as f:
		lines = [x.rstrip('\n') for x in f.readlines()]
		for chat_id in lines:
			bot.send_message(chat_id=chat_id,
							 text=u"Mensagem de teste.\n")

def unknown(bot, update):
	msg = u"Desculpe, esse comando não parece existir."
	bot.send_message(chat_id=update.message.chat_id,
	                 text=msg)
	start(bot, update)

# ------ Bot Startup ------

# Connecting to Telegram API
# Updater retrieves information and dispatcher connects commands
updater = Updater(token=read_token())
dispatcher = updater.dispatcher
job_q = updater.job_queue

# Determine remaining seconds until next digest message (1 per day)
today = datetime(year=datetime.today().year,
				 month=datetime.today().month,
				 day=datetime.today().day)
target = today + timedelta(days=1, hours=digest_schedule_hour)
deltaseconds = (target - datetime.now()).total_seconds()

# Add new Job to the dispatcher's job queue.
# Will happen every deltaseconds seconds, starting from now
job_q.put(Job(callback_digest, (24 * 60 * 60)), next_t=deltaseconds)

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

subscribe_handler = CommandHandler('subscribe', subscribe, pass_args=True)
dispatcher.add_handler(subscribe_handler)

test_handler = CommandHandler('test', test)
dispatcher.add_handler(test_handler)

unknown_handler = MessageHandler([Filters.command], unknown)
dispatcher.add_handler(unknown_handler)

updater.start_polling()
updater.idle()