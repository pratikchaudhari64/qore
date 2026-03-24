# from databases import quest_db

# result = quest_db.execute_query(sql_query = "SELECT * from daily_historical_prices limit 10;")
# print(result)

if __name__ == '__main__':
    from databases import quest_db, sqlite_db

    result = quest_db.execute_query(sql_query = "SELECT * from daily_historical_prices limit 10;")
    # result = sqlite_db.get_data(query="select * from users_auth_trades")
    print(result)

    