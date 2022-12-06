# import sqlite3


# con = sqlite3.connect('VIIBE_data.db')
# cursor = con.cursor()
# cursor.execute('''CREATE TABLE user_data(
#     user_name VARCHAR(60),
#     balance NUMERIC(10,2),
#     score INT,
#     ticker VARCHAR(20),
#     amount INT,
#     date_start VARCHAR(20),
#     date_end VARCHAR(20),
#     stop_loss INT, 
#     sr_window INT, 
#     lr_window INT)''')
# con.commit()
# con.close()

def execute_query(con, query):
    cursor = con.cursor()
    try:
        return cursor.execute(query)
    except Exception as ex: 
        raise ex

def execute_many_querry(con, query, data):
    cursor = con.cursor()
    try:
        return cursor.executemany(query, data)
    except Exception as ex: 
        raise ex