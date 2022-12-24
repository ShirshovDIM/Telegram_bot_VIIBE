from config import token, api_token
from request import *
from visualization import *

from telebot.async_telebot import AsyncTeleBot
import asyncio 

from telebot import types, asyncio_filters
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup

import sqlite3
from SQL import * 
from captchagen import captcha_gen
from dataframe_image import export
import pandas as pd
import time

class User_info(StatesGroup):

	captcha_actual = State()
	captcha_user = State()
	fails = State()
	call = State()

bot = AsyncTeleBot(token, state_storage = StateMemoryStorage())

@bot.message_handler(commands=['start', 'menu'])
async def start_handler(message):
	
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

	await bot.send_message(message.chat.id, f"""Hello, {message.chat.first_name},\n
	I'm Very insight invest bot-estimator (VIIBE), and, actually I'am very-very-very busy analyzing IMMENSELY important data right now. \n
	BUT, if you want to check wether you simple stop-loss strategy is good, I'll allocate you a part of my virtual cash balance.\n
	For that reason I leave these buttons for you 👇""", reply_markup= markup)

@bot.message_handler(func = lambda ms: True if ms.text.lower() in ['/reset'] else False)
async def reset_handler(message):
	
	captcha = captcha_gen()

	await bot.send_photo(message.chat.id, photo = open('./captcha.png', 'rb'), caption=f'''{message.from_user.first_name},
	 solve captcha to reset your balance and portfolio. You have 4 attempts before being banned''')

	await bot.set_state(message.from_user.id, User_info.captcha_user, message.chat.id)

	async with bot.retrieve_data(message.from_user.id, message.chat.id) as user_data:

		user_data['captcha_actual'] = captcha
		user_data['fails'] = 0
		user_data['call'] = 'reset'

@bot.message_handler(state="*", commands='cancel')
async def cancel_state(message):
	
    await bot.send_message(message.chat.id, "Captcha aborted")
    await bot.delete_state(message.from_user.id, message.chat.id)

@bot.message_handler(state = User_info.captcha_user)
async def captcha_handler(message):
	
	chat_id = message.chat.id
	user_captcha = message.text

	async with bot.retrieve_data(message.from_user.id, chat_id) as user_data:

		user_data['captcha_user'] = user_captcha
		actual_captcha = user_data['captcha_actual']
		fs = user_data['fails']
		call = user_data['call']

	if  fs < 3 and actual_captcha != user_captcha:

		async with bot.retrieve_data(message.from_user.id, chat_id) as user_data:

			user_data['captcha_actual'] = captcha_gen()
			user_data['fails'] += 1
			await bot.send_photo(chat_id, photo = open('./captcha.png', 'rb'), caption = f'''{message.from_user.first_name}, you have {4 - user_data['fails']} attempts to solve captcha before being banned''')

		await bot.set_state(message.from_user.id, User_info.captcha_user , chat_id)

	elif fs >= 3 and actual_captcha != user_captcha: 

		await time.sleep(60)

	else:

		await bot.delete_state(message.from_user.id, chat_id)

		if call == 'get_pfl':
			
			con = sqlite3.Connection('VIIBE_data.db')
			cursor = con.cursor()
			var = cursor.execute(f'''SELECT ticker, amount, purchase, date_start FROM {message.from_user.username}; ''').fetchall()
			con.close()

			if len(var) == 0:

				await bot.send_message(chat_id, f'{message.from_user.first_name}, you do not have any stocks in your portfolio yet')

			else: 

				price = [get_daily_data(v[0], api_token, 'sell')[1] for v in var]

				df = pd.DataFrame(var, columns = ['Ticker','Amount','Purchase value','Purchase date'])
				df['Profit'] = np.round(df.Amount * price/df['Purchase value'] * 100 - 100, 3)
				df.index = np.arange(1,df.shape[0]  + 1)
				export(df[['Ticker', 'Amount', 'Purchase value', 'Profit']], 'Trade_protocol.png')

				await bot.send_photo(chat_id, photo= open('Trade_protocol.png', 'rb'), caption = 
				f'Your total portfolio profit is: {np.round(sum(df.Profit * df["Purchase value"])/(df["Purchase value"]).sum(), 3)}% ')

		elif call == 'run_sim':

			await bot.send_message(chat_id, f'{message.chat.first_name}, you successfully solved the captcha. Initializing simulation...')

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

			await bot.send_media_group(chat_id, media = media_group)

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

			await bot.send_message(chat_id, f"""{message.from_user.first_name}, I have successfully reset your balance.
			Feel free to continue your stock market journey and crazy experiments :)""", reply_markup= markup)

bot.add_custom_filter(asyncio_filters.StateFilter(bot))

@bot.message_handler(func= lambda ms: True if ms.text in ['Activate retro VIIBE','/menu_retro'] else False)
async def menu_responder_retro(message):
	
	markup = types.InlineKeyboardMarkup()
	btn1 = types.InlineKeyboardButton("Show virtual balance", callback_data = 'vb')
	btn2 = types.InlineKeyboardButton("Run simulation", callback_data = 'run_sim')
	btn3 = types.InlineKeyboardButton("Show set simulation parameters", callback_data = 'sim_par')
	markup.add(btn1, btn2, btn3)
	await bot.send_message(message.chat.id, 'Stop-loss strategy menu:', reply_markup = markup)

@bot.message_handler(func= lambda ms: True if ms.text in ['Activate live VIIBE','/menu_live'] else False)
async def menu_responder_live(message):
	
	markup = types.InlineKeyboardMarkup()
	btn1 = types.InlineKeyboardButton("Show virtual balance", callback_data = 'vb')
	btn2 = types.InlineKeyboardButton("Buy", callback_data = 'buy_live')
	btn3 = types.InlineKeyboardButton("Sell", callback_data = 'sell_live')
	btn4 = types.InlineKeyboardButton("Manage portfolio", callback_data = 'get_pfl')
	btn5 = types.InlineKeyboardButton('Show buy/sell set options', callback_data = 'live_par')
	markup.add(btn1, btn2, btn3, btn4, btn5)
	await bot.send_message(message.chat.id, 'Live trading menu:', reply_markup = markup)

@bot.message_handler(func= lambda ms: True if ms.text.lower() in ['faq','/help'] else False)
async def help_responder(message):
	
	await bot.send_message(message.chat.id, f'''My creator is very lazy, so I was said to support only these commans or messages:\n\n1. /start or /menu - to go to my main menu\n
	2. /menu_retro or "Activate retro VIIBE" - to run my trade strategy based on previous data of american stock market and your PRE-specified parameters (make sure you passed them to me)\n
	3. /menu_live of "Activate live VIIBE" - to test your own invest strategy in american stock market. I will provide you with (almost) real-time financial data of ASM, so you do not have to search for it by yourself\n
	4. /reset - to reset your balance and investment portfolio (you will not be able to return to your old portfolio and balace)\n
	5. /cancel - if you do not want to solve captcha (but query will not be executed)\n\n
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
async def query_handler_main_menu(call):

	global api_token

	chat = call.message.chat

	con = sqlite3.connect('VIIBE_data.db')
	cursor = con.cursor()

	if call.data == "run_sim":
		
		captcha = captcha_gen()

		await bot.send_photo(chat.id, photo = open('./captcha.png', 'rb'), caption=f'''{call.from_user.first_name},
		solve captcha to run the simulation. You have 4 attempts before being banned''')

		await bot.set_state(call.from_user.id, User_info.captcha_user, chat.id)

		async with bot.retrieve_data(call.from_user.id, chat.id) as user_data:

			user_data['captcha_actual'] = captcha
			user_data['fails'] = 0
			user_data['call'] = 'run_sim'

	elif call.data == "sim_par":

		var = cursor.execute(f'''SELECT ticker, date_start, date_end, stop_loss, sr_window, lr_window FROM user_data WHERE user_name = '{call.from_user.username}'; ''').fetchall()[0]

		await bot.answer_callback_query(call.id, text = f"""Your current simulation parameters are:\nTicker: {var[0]}
		\nStarting from: {var[1]}
		\nBy: {var[2]}\nStop loss: {var[3]}\nShort window: {var[4]}\nLong window: {var[5]}""", show_alert = True)

	elif call.data == "vb":

		var = cursor.execute(f'''SELECT balance FROM user_data WHERE user_name = '{call.from_user.username}'; ''').fetchall()[0]
		await bot.answer_callback_query(call.id, text = f"Your current virtual balance is:\n{var[0]}", show_alert = True)


	elif call.data == 'buy_live':

		try:
			
			var = cursor.execute(f'''SELECT balance, ticker, amount 
			FROM user_data WHERE user_name = '{call.from_user.username}'; ''').fetchall()[0]

			time, price = get_daily_data(var[1], api_token, 'buy')
			time = time.strftime("%Y-%m-%d %H:%M:%S")
			bal = var[0] - price * var[2]

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
				
				await bot.send_message(chat.id, f'You are out of balance. For this purchase\nBalance is: {var[0]}\nPurchase value is: {price * var[2]}\nNeed additional: {-bal}')


		except Exception: 

			await bot.send_message(chat.id, f'{call.from_user.username}, I fail to initialize your purchase session. Make sure that your buy/sell parameters are correct.')

	elif call.data == 'sell_live':

		try:
			
			var = cursor.execute(f'''SELECT balance, ticker, amount 
			FROM user_data WHERE user_name = '{call.from_user.username}'; ''').fetchall()[0]

			amt = cursor.execute(f'''SELECT amount, purchase, price_buy FROM {call.from_user.username} 
			WHERE ticker = "{var[1]}"; ''').fetchall()[0]

			time, price = get_daily_data(var[1], api_token, 'sell')
			time = time.strftime("%Y-%m-%d %H:%M:%S")
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

				await bot.send_message(chat.id, f'You do not have such amount of stocks needed to sell. For this sell session\nAmount to sell: {var[2]}\nAmount in portfolio: {amt}\nFor stock: {var[1]}')


		except Exception: 

			await bot.send_message(chat.id, f'{call.from_user.username}, I fail to initialize your sell session. Make sure that your buy/sell parameters are correct.')
		
	elif call.data == 'get_pfl':

		captcha = captcha_gen()

		await bot.send_photo(chat.id, photo = open('./captcha.png', 'rb'), caption=f'''{call.from_user.first_name},
		solve captcha to see your current investment portfolio. You have 4 attempts before being banned''')

		await bot.set_state(call.from_user.id, User_info.captcha_user, chat.id)

		async with bot.retrieve_data(call.from_user.id, chat.id) as user_data:

			user_data['captcha_actual'] = captcha
			user_data['fails'] = 0
			user_data['call'] = 'get_pfl'

	else:

		var = cursor.execute(f'''SELECT ticker, amount FROM user_data WHERE user_name = '{call.from_user.username}'; ''').fetchall()[0]
		await bot.answer_callback_query(call.id, text = f"Ticker set: {var[0]}\nAmount set:{var[1]}", show_alert = True)
	
	con.close()

@bot.message_handler(content_types=['text'])
async def param_handler(message):

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

			await bot.send_message(message.chat.id, 'No such ticker found or such ticker is irrelevant for American stock market nowadays. Try again in a correct form:\nSet ticker <ticker_name>')

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

			await bot.send_message(message.chat.id, 'Entered wrong amount to buy/sell. Expected any natural number. Try again in a correct form:\nSet amount <your_integer>')

	elif message.text.replace(' ', '')[:12].lower() == 'startingfrom':
		try: 

			date_start = message.text.replace(' ', '').replace("'", "").replace('"', '')[12:]
			con = sqlite3.connect('VIIBE_data.db')
			cursor = con.cursor()
			cursor.execute(f'''UPDATE user_data SET date_start = '{date_start}' WHERE user_name = '{message.chat.username}';  ''')
			con.commit()
			con.close()

		except Exception:

			await bot.send_message(message.chat.id, 'Specify correct starting date in the format:\nStarting from Year-month-day')

	elif message.text.replace(' ', '')[:2].lower() == 'by':
		try: 

			date_end = message.text.replace(' ', '').replace("'", "").replace('"', '')[2:]
			con = sqlite3.connect('VIIBE_data.db')
			cursor = con.cursor()
			cursor.execute(f'''UPDATE user_data SET date_end = '{date_end}' WHERE user_name = '{message.chat.username}';  ''')
			con.commit()
			con.close()
			
		except Exception:

			await bot.send_message(message.chat.id, 'Specify correct ending date in the format:\nStarting from Year-month-day')

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

				await bot.send_message('Stop loss must be an integer in range between 0 and 100.\nCannot excecute change your query, sorry :(')

		except Exception:

			await bot.send_message(message.chat.id, '''Stop loss specification must be integer between 0 and 100 
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

			await bot.send_message(message.chat.id, '''Long window specification must be an integer within the range of days you set in your dates range 
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

			await bot.send_message(message.chat.id, '''Long window specification must be an integer within the range of days you set in your dates range 
			(as an absolute whole number in given range),\ni.e written in the form: "Set ling window <your value>" ''')

asyncio.run(bot.polling())
