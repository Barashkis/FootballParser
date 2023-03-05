import pymysql

from src import config


class Database:
    @staticmethod
    def execute(sql, commit, fetchall, fetchone, parameters):
        result = None

        connection = pymysql.connect(host=config.host,
                                     user=config.user,
                                     password=config.password,
                                     database=config.database,
                                     cursorclass=pymysql.cursors.DictCursor)

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, parameters)
                if fetchall:
                    result = cursor.fetchall()
                elif fetchone:
                    result = cursor.fetchone()

                if commit:
                    connection.commit()

        return result

    def select(self, table, fetchall, *args, **kwargs):
        sql = f"SELECT {', '.join(map(str, args)) if args else '*'} FROM {table}"
        if kwargs:
            sql += f" WHERE {' AND '.join([f'{key}=%s' for key in kwargs])}"
        sql += ";"

        result = self.execute(
            sql,
            commit=False,
            fetchall=fetchall,
            fetchone=not fetchall,
            parameters=tuple(kwargs.values())
        )

        return result

    def insert(self, table, **kwargs):
        sql = f"INSERT INTO {table} ({', '.join(map(str, kwargs.keys()))}) " \
              f"VALUES ({', '.join(map(str, kwargs.values()))});"

        self.execute(sql, commit=True, fetchall=False, fetchone=False, parameters=tuple())

    def update(self, table, update_values, where_values):
        sql = f"UPDATE {table} " \
              f"SET {', '.join([f'{column} = {value}' for column, value in update_values.items()])} " \
              f"WHERE {' AND '.join([f'{key}=%s' for key in where_values])};"

        self.execute(sql, commit=True, fetchall=False, fetchone=False, parameters=tuple(where_values.values()))

    def custom_query(self, sql, commit, fetchall, fetchone, parameters):
        result = self.execute(sql, commit=commit, fetchall=fetchall, fetchone=fetchone, parameters=parameters)

        return result

