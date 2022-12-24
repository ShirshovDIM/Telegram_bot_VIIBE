
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
