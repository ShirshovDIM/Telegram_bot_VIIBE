from config import token, api_token
from request import *
from visualization import *
import telebot
from telebot import types
import sqlite3
from SQL import * 
from captchagen import captcha_gen
from dataframe_image import export
import pandas as pd
from datetime import datetime

user_dict = {}

class User_info:
    def __init__(self, name):
        self.name = name
        self.captcha = None
        self.fails = 0

bot = telebot.TeleBot(token)

@bot.message_handler(commands=['start', 'menu'])
def start_handler(message):
	markup = types.ReplyKeyboardMarkup(resize_keyboard= True)
	btn1 = types.KeyboardButton('Activate retro VIIBE')
	btn2 = types.KeyboardButton('FAQ')
	btn3 = types.KeyboardButton('Activate live VIIBE')
	markup.add(btn1,btn2,btn3)

	con = sqlite3.connect('VIIBE_data.db')
	cursor = con.cursor()
	
	try:
		cursor.execute(f'''SELECT user_name FROM user_data WHERE user_name = '{message.chat.username}'; ''').fetchone()[0]
	except Exception: 
		cursor.execute(f"""INSERT INTO user_data(
		user_name, balance,
		score, ticker,
		amount,date_start,
		date_end, stop_loss,
		sr_window, lr_window
		)
		VALUES (
		'{message.chat.username}', 100000,
		 0, 'Set ticker', 0,
		'Set start date', 'Set end date',
		 7, 30, 60);""")
		con.commit()

		cursor.execute(f'''CREATE TABLE {message.chat.username}(
			ticker VARCHAR(20),
			date_start DATE,
			amount INT,
			price_buy NUMERIC(8, 2), 
			purchase NUMERIC(12,2))''')
		con.commit()

	con.close()

	bot.send_message(message.chat.id, f"""Hello, {message.chat.first_name},\n
	I'm Very insight invest bot-estimator (VIIBE), and, actually I'am very-very-very busy analyzing IMMENSELY important data right now. \n
	BUT, if you want to check wether you simple stop-loss strategy is good, I'll allocate you a part of my virtual cash balance.\n
	For that reason I leave these buttons for you 👇""", reply_markup= markup)

@bot.message_handler(func = lambda ms: True if ms.text.lower() in ['/reset'] else False)
def reset_handler(message):

	name = message.from_user.username
	user = User_info(name)
	user.captcha = captcha_gen()
	user_dict[message.chat.id] = user
	bot.send_photo(message.chat.id, photo = open('./captcha.png', 'rb'))

	msg = bot.reply_to(message, f'{message.from_user.first_name}, solve captcha to reset your balance. You have 3 attempts')
	bot.register_next_step_handler(msg, captcha_reset)

def captcha_reset(message):
	chat_id = message.chat.id
	user = user_dict[chat_id]

	if message.text != user.captcha and user.fails < 3:

		user.fails += 1
		user.captcha = captcha_gen()
		bot.send_photo(chat_id, photo = open('./captcha.png', 'rb'))
		msg = bot.reply_to(message, f'{message.from_user.first_name}, I got wrong captcha solution. You have {3-user.fails} attempts before being banned')
		bot.register_next_step_handler(msg, captcha_reset)

	elif user.fails >= 3 and message.text != user.captcha: 

		bot.ban_chat_member(chat_id, message.from_user.id, until_date=datetime.minute(1))

	else:

		markup = types.ReplyKeyboardMarkup(resize_keyboard= True)
		btn1 = types.KeyboardButton('Activate retro VIIBE')
		btn2 = types.KeyboardButton('FAQ')
		btn3 = types.KeyboardButton('Activate live VIIBE')
		markup.add(btn1,btn2,btn3)

		con = sqlite3.connect('VIIBE_data.db')
		cursor = con.cursor()

		cursor.execute(f'DROP TABLE {message.from_user.username}; ') 
		con.commit()

		cursor.execute(f'''CREATE TABLE {message.from_user.username}(
			ticker VARCHAR(20),
			date_start DATE,
			amount INT,
			price_buy NUMERIC(8, 2), 
			purchase NUMERIC(12,2))''')
		con.commit()

		cursor.execute(f'''UPDATE user_data 
		SET balance = 100000 
		WHERE user_name = "{message.from_user.username}"; ''')
		con.commit()

		con.close()

		bot.send_message(message.chat.id, f"""{message.from_user.first_name}, I have successfully reset your balance.
		Feel free to continue your stock market journey and crazy experiments :)""", reply_markup= markup)


bot.enable_save_next_step_handlers()

bot.load_next_step_handlers()

@bot.message_handler(func= lambda ms: True if ms.text in ['Activate retro VIIBE','/menu_retro'] else False)
def menu_responder_retro(message):
	markup = types.InlineKeyboardMarkup()
	btn1 = types.InlineKeyboardButton("Show virtual balance", callback_data = 'vb')
	btn2 = types.InlineKeyboardButton("Run simulation", callback_data = 'run_sim')
	btn3 = types.InlineKeyboardButton("Show set simulation parameters", callback_data = 'sim_par')
	markup.add(btn1, btn2, btn3)
	bot.send_message(message.chat.id, 'Here is your menu:', reply_markup = markup)

@bot.message_handler(func= lambda ms: True if ms.text in ['Activate live VIIBE','/menu_live'] else False)
def menu_responder_live(message):
	markup = types.InlineKeyboardMarkup()
	btn1 = types.InlineKeyboardButton("Show virtual balance", callback_data = 'vb')
	btn2 = types.InlineKeyboardButton("Buy", callback_data = 'buy_live')
	btn3 = types.InlineKeyboardButton("Sell", callback_data = 'sell_live')
	btn4 = types.InlineKeyboardButton("Manage portfolio", callback_data = 'get_pfl')
	btn5 = types.InlineKeyboardButton('Show buy/sell set options', callback_data = 'live_par')
	markup.add(btn1, btn2, btn3, btn4, btn5)
	bot.send_message(message.chat.id, 'Here is your menu:', reply_markup = markup)

@bot.message_handler(func= lambda ms: True if ms.text.lower() in ['faq','/help'] else False)
def help_responder(message):
	bot.send_message(message.chat.id, f'''My creator is very lazy, so I was said to support only these commans or messages:\n\n1. /start or /menu - to go to my main menu\n
	2. /menu_retro or "Activate retro VIIBE" - to run my trade strategy based on previous data of american stock market and your PRE-specified parameters (make sure you passed them to me)\n
	3. /menu_live of "Activate live VIIBE" - to test your own invest strategy in american stock market. I will provide you with (almost) real-time financial data of ASM, so you do not have to search for it by yourself\n\n
	To specify neede parameters use following instances:\n\n
		a. "set ticker <your ticker>" - to set a stock ticker from ASM that you need\n
		b. "starting from <YYYY-MM-DD>" - to set a starting date for your retro simulation research\n
		c. "by <YYYY-MM-DD>" - to set an ending date for your retro simulation research\n
		d. "set stoploss <percent of your portfolio as an integer in 0:100>" 
		- to set a desirable stop-loss percent to control retrospective trader's tendency to withstand the risk\n
		e. "set short window <days to aggregate in short-term as an integer>" 
		- to set preferable SR window in days (Warning: SR must be less then research date period you investigate)\n
		f. "set long window <days to aggregate in long-term as an integer>"
		 - to set preferable SR window in days (Warning: SR must be less then research date period you investigate)\n
		d. "set amount <amount of stocks to buy as an integer>" - to set an amount of stocks to buy (for ALMOST real-time trading)''')

@bot.callback_query_handler(func = lambda call: call.data in ['run_sim', 'vb', 'sim_par', 'buy_live', 'sell_live','get_pfl', 'live_par'])
def query_handler_main_menu(call):

	global api_token

	chat = call.message.chat

	con = sqlite3.connect('VIIBE_data.db')
	cursor = con.cursor()

	if call.data == "run_sim":
		
		name = chat.username
		user = User_info(name)
		user.captcha = captcha_gen()
		user_dict[chat.id] = user
		print(user_dict[chat.id].captcha)
		bot.send_photo(chat.id, photo = open('./captcha.png', 'rb'))

		msg = bot.reply_to(call.message, f'{chat.first_name}, solve captcha to proceed. You have 3 attemps')
		bot.register_next_step_handler(msg, captcha_handler_sim)

	elif call.data == "sim_par":

		var = cursor.execute(f'''SELECT ticker, date_start, date_end, stop_loss, sr_window, lr_window FROM user_data WHERE user_name = '{call.from_user.username}'; ''').fetchall()[0]

		bot.answer_callback_query(call.id, text = f"""Your current simulation parameters are:\nTicker: {var[0]}
		\nStarting from: {var[1]}
		\nBy: {var[2]}\nStop loss: {var[3]}\nShort window: {var[4]}\nLong window: {var[5]}""", show_alert = True)

	elif call.data == "vb":

		var = cursor.execute(f'''SELECT balance FROM user_data WHERE user_name = '{call.from_user.username}'; ''').fetchall()[0]
		bot.answer_callback_query(call.id, text = f"Your current virtual balance is:\n{var[0]}", show_alert = True)


	elif call.data == 'buy_live':

		try:
			
			var = cursor.execute(f'''SELECT balance, ticker, amount 
			FROM user_data WHERE user_name = '{call.from_user.username}'; ''').fetchall()[0]

			time, price = get_daily_data(var[1], api_token, 'buy')
			time = time.strftime("%Y-%m-%d %H:%M:%S")
			bal = var[0] - price * var[2]
			print(price)


			if bal >= 0:

				cursor.execute(f'''UPDATE user_data 
				SET balance = ROUND({bal}), amount = 0 
				WHERE user_name = "{call.from_user.username}"; ''')
				con.commit()

				try:

					amt = cursor.execute(f'''SELECT amount, purchase FROM {call.from_user.username} WHERE ticker = "{var[1]}"; ''').fetchall()[0]

					cursor.execute(f'''UPDATE {call.from_user.username} 
					SET amount = {var[2] + amt[0]}, purchase = ROUND({amt[1] + price * var[2]},2)
					WHERE ticker = "{var[1]}"; ''')
					con.commit()

				except Exception as ex:

					cursor.execute(f'''INSERT INTO {call.from_user.username}(ticker, date_start, amount, price_buy, purchase) 
					VALUES ("{var[1]}", "{time}", {var[2]}, {price}, ROUND({price * var[2]}, 2));''')
					con.commit()

			else:
				
				bot.send_message(chat.id, f'You are out of balance. For this purchase\nBalance is: {var[0]}\nPurchase value is: {price * var[2]}\nNeed additional: {-bal}')


		except Exception: 

			bot.send_message(chat.id, f'{call.from_user.username}, I fail to initialize your purchase session. Make sure that your buy/sell parameters are correct.')

	elif call.data == 'sell_live':

		try:
			
			var = cursor.execute(f'''SELECT balance, ticker, amount 
			FROM user_data WHERE user_name = '{call.from_user.username}'; ''').fetchall()[0]

			amt = cursor.execute(f'''SELECT amount, purchase, price_buy FROM {call.from_user.username} 
			WHERE ticker = "{var[1]}"; ''').fetchall()[0]

			time, price = get_daily_data(var[1], api_token, 'sell')
			time = time.strftime("%Y-%m-%d %H:%M:%S")
			print(price)
			if var[2] < amt[0]:

				bal = var[0] + price * var[2]

				cursor.execute(f'''UPDATE user_data 
				SET balance = ROUND({bal}), amount = 0 
				WHERE user_name = "{call.from_user.username}"; ''')
				con.commit()

				cursor.execute(f'''UPDATE {call.from_user.username} 
				SET amount = {amt[0] - var[2]}, purchase = {amt[1] - amt[2] * var[2]}
				WHERE ticker = "{var[1]}"; ''')
				con.commit()
			
			elif var[2] == amt[0]:

				bal = var[0] + price * amt[0]

				cursor.execute(f'''UPDATE user_data 
				SET balance = ROUND({bal}), amount = 0 
				WHERE user_name = "{call.from_user.username}"; ''')
				con.commit()

				cursor.execute(f'''DELETE FROM {call.from_user.username}
				WHERE ticker = "{var[1]}";''')
				con.commit()

			else:

				bot.send_message(chat.id, f'You do not have such amount of stocks needed to sell. For this sell session\nAmount to sell: {var[2]}\nAmount in portfolio: {amt}\nFor stock: {var[1]}')


		except Exception: 

			bot.send_message(chat.id, f'{call.from_user.username}, I fail to initialize your sell session. Make sure that your buy/sell parameters are correct.')
		
	elif call.data == 'get_pfl':

		name = chat.username
		user = User_info(name)
		user.captcha = captcha_gen()
		user_dict[chat.id] = user
		print(user_dict[chat.id].captcha)
		bot.send_photo(chat.id, photo = open('./captcha.png', 'rb'))
		
		msg = bot.reply_to(call.message, f'{chat.first_name}, solve captcha to proceed. You have 3 attemps')
		bot.register_next_step_handler(msg, captcha_handler_pfl)

	else:

		var = cursor.execute(f'''SELECT ticker, amount FROM user_data WHERE user_name = '{call.from_user.username}'; ''').fetchall()[0]
		bot.answer_callback_query(call.id, text = f"Ticker set: {var[0]}\nAmount set:{var[1]}", show_alert = True)
	
	con.close()

def captcha_handler_pfl(message):
	chat_id = message.chat.id
	user = user_dict[chat_id]

	if message.text != user.captcha and user.fails < 3:

		user.fails += 1
		user.captcha = captcha_gen()
		bot.send_photo(chat_id, photo = open('./captcha.png', 'rb'))
		msg = bot.reply_to(message, f'{message.from_user.first_name}, I got wrong captcha solution. You have {3-user.fails} attempts before being banned')
		bot.register_next_step_handler(msg, captcha_handler_pfl)

	elif user.fails >= 3 and message.text != user.captcha: 

		bot.ban_chat_member(chat_id, message.from_user.id, until_date=datetime.minute(1))

	else:
		
		con = sqlite3.Connection('VIIBE_data.db')
		cursor = con.cursor()
		var = cursor.execute(f'''SELECT ticker, amount, purchase, date_start FROM {message.from_user.username}; ''').fetchall()
		con.close()

		price = [get_daily_data(v[0], api_token, 'sell')[1] for v in var]

		df = pd.DataFrame(var, columns = ['Ticker','Amount','Purchase value','Purchase date'])
		df['Profit'] = np.round(df.Amount * price/df['Purchase value'] * 100 - 100, 3)
		df.index = np.arange(1,df.shape[0]  + 1)
		export(df[['Ticker', 'Amount', 'Purchase value', 'Profit']], 'Trade_protocol.png')

		bot.send_photo(chat_id, photo= open('Trade_protocol.png', 'rb'), caption = 
		f'Your total portfolio profit is: {np.round(sum(df.Profit * df["Purchase value"])/(df["Purchase value"]).sum(), 3)}% ')


def captcha_handler_sim(message):

	chat_id = message.chat.id
	user = user_dict[chat_id]

	if message.text != user.captcha and user.fails < 3:

		user.fails += 1
		user.captcha = captcha_gen()
		bot.send_photo(chat_id, photo = open('./captcha.png', 'rb'))
		msg = bot.reply_to(message, f'{message.from_user.first_name}, I got wrong captcha solution. You have {3-user.fails} attempts before being banned')
		bot.register_next_step_handler(msg, captcha_handler_sim)

	elif user.fails >= 3 and message.text != user.captcha: 

		bot.ban_chat_member(chat_id, message.from_user.id, until_date=datetime.minute(1))

	else:

		bot.send_message(chat_id, f'{message.chat.first_name}, you successfully solved the captcha. Initializing simulation...')

		con = sqlite3.connect('VIIBE_data.db')
		cursor = con.cursor()
		var = cursor.execute(f'''SELECT balance, ticker, date_start, date_end, stop_loss, sr_window, lr_window
		FROM user_data 
		WHERE user_name = '{message.chat.username}'; ''').fetchall()[0]
		con.close()

		df = get_historical_data(var[1], var[2], var[3])
		sim_data = trader(df, var[0],  var[4], var[5], var[6])
		write_plots(graph(sim_data[0], sim_data[1], var[5], var[6]))

		con = sqlite3.connect('VIIBE_data.db')
		cursor = con.cursor()
		cursor.execute(f'''UPDATE user_data SET balance = ROUND({sim_data[2]}, 2) WHERE user_name = '{message.chat.username}'; ''')
		con.commit()
		con.close()

		sim_data[1].index = np.arange(1, sim_data[1].shape[0] + 1)
		export(sim_data[1], 'Trade_protocol.png')

		media_group = []
		for num in ['plot.png', 'position.png', 'Trade_protocol.png']:
			media_group.append(types.InputMediaPhoto(open('%s' % num, 'rb'), 
			caption = "Trade protocol" if num == 'Trade_protocol.png' else ''))
		bot.send_media_group(chat_id, media = media_group)
		
bot.enable_save_next_step_handlers()

bot.load_next_step_handlers()

@bot.message_handler(content_types=['text'])
def param_handler(message):

	if message.text.replace(' ', '')[:9].lower() == 'setticker': 
		try: 

			ticker = message.text.replace(' ', '')[9:].upper()
			get_historical_data(ticker)
			con = sqlite3.connect('VIIBE_data.db')
			cursor = con.cursor()
			cursor.execute(f'''UPDATE user_data SET ticker = '{ticker}' WHERE user_name = '{message.chat.username}';  ''')
			con.commit()
			con.close()

		except Exception:

			bot.send_message(message.chat.id, 'No such ticker found or such ticker is irrelevant for American stock market nowadays. Try again in a correct form:\nSet ticker <ticker_name>')

	elif message.text.replace(' ', '')[:9].lower() == 'setamount': 
		try: 

			amount = int(message.text.replace(' ', '')[9:])
			amount =  amount if amount > 0 else ValueError

			con = sqlite3.connect('VIIBE_data.db')
			cursor = con.cursor()
			cursor.execute(f'''UPDATE user_data SET amount = {amount} WHERE user_name = '{message.chat.username}';  ''')
			con.commit()
			con.close()

		except Exception:

			bot.send_message(message.chat.id, 'Entered wrong amount to buy/sell. Expected any natural number. Try again in a correct form:\nSet amount <your_integer>')

	elif message.text.replace(' ', '')[:12].lower() == 'startingfrom':
		try: 

			date_start = message.text.replace(' ', '').replace("'", "").replace('"', '')[12:]
			con = sqlite3.connect('VIIBE_data.db')
			cursor = con.cursor()
			cursor.execute(f'''UPDATE user_data SET date_start = '{date_start}' WHERE user_name = '{message.chat.username}';  ''')
			con.commit()
			con.close()

		except Exception:
			bot.send_message(message.chat.id, 'Specify correct starting date in the format:\nStarting from Year-month-day')

	elif message.text.replace(' ', '')[:2].lower() == 'by':
		try: 

			date_end = message.text.replace(' ', '').replace("'", "").replace('"', '')[2:]
			con = sqlite3.connect('VIIBE_data.db')
			cursor = con.cursor()
			cursor.execute(f'''UPDATE user_data SET date_end = '{date_end}' WHERE user_name = '{message.chat.username}';  ''')
			con.commit()
			con.close()
			
		except Exception:
			bot.send_message(message.chat.id, 'Specify correct ending date in the format:\nStarting from Year-month-day')

	elif message.text.replace(' ', '')[:11].lower() == 'setstoploss':
		try: 

			stop_loss = int(message.text.replace(' ', '')[11:].lower()) 

			if stop_loss <= 100 and stop_loss >= 0:  

				con = sqlite3.connect('VIIBE_data.db')
				cursor = con.cursor()
				cursor.execute(f'''UPDATE user_data SET stop_loss = {stop_loss} WHERE user_name = '{message.chat.username}'; ''')
				con.commit()
				con.close()

			else: 

				bot.send_message('Stop loss must be an integer in range between 0 and 100.\nCannot excecute change your query, sorry :(')

		except Exception:

			bot.send_message(message.chat.id, '''Stop loss specification must be integer between 0 and 100 
			(as an absolute whole number in given range),\ni.e written in the form: "Set stop loss <your value>" ''')

	elif message.text.replace(' ', '')[:14].lower() == 'setshortwindow':
		try: 

			sr_window = int(message.text.replace(' ', '')[14:].lower()) 
			con = sqlite3.connect('VIIBE_data.db')
			cursor = con.cursor()
			cursor.execute(f'''UPDATE user_data SET sr_window = {sr_window} WHERE user_name = '{message.chat.username}'; ''')
			con.commit()
			con.close()

		except Exception:

			bot.send_message(message.chat.id, '''Long window specification must be an integer within the range of days you set in your dates range 
			(as an absolute whole number in given range),\ni.e written in the form: "Set ling window <your value>" ''')

	elif message.text.replace(' ', '')[:13].lower() == 'setlongwindow':
		try: 

			lr_window = int(message.text.replace(' ', '')[13:].lower()) 
			con = sqlite3.connect('VIIBE_data.db')
			cursor = con.cursor()

			cursor.execute(f'''UPDATE user_data SET lr_window = {lr_window} WHERE user_name = '{message.chat.username}'; ''')
			con.commit()
			con.close()

		except Exception:

			bot.send_message(message.chat.id, '''Long window specification must be an integer within the range of days you set in your dates range 
			(as an absolute whole number in given range),\ni.e written in the form: "Set ling window <your value>" ''')

bot.polling()
