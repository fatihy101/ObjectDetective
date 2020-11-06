import hashlib
import os
import platform

import mysql.connector as db


# TODO: Add an exit method for closing connection of db when it's called.
class Database:
    def __init__(self):
        try:
            self.connection = db.connect(host='ENTER YOUR HOST IP',
                                         user='ENTER YOUR USERNAME',
                                         password='PASSWORD',
                                         database='DBNAME')
            self.cursor = self.connection.cursor(buffered=True)
        except db.Error as db_err:
            print(db_err)

    def encrpt_password(self, password):
        password = str(password)
        s256_hash = hashlib.sha256(password.encode())
        md5_hash = hashlib.md5(str(s256_hash.hexdigest()).encode())
        return md5_hash.hexdigest()

    def find_id_w_email(self, email):
        user_id = -1
        self.cursor.execute("SELECT userID FROM User WHERE User.email = %s;", (email,))
        for temp in self.cursor:
            user_id = temp[0]

        if user_id == -1:
            print("Given email didn't match with registered ones.")

        return user_id

    def get_reports(self, user_id):
        self.cursor.execute("SELECT * FROM Report where Report.User_userID = %s", (user_id,))
        reports = self.cursor.fetchall()
        (report_id, date, elapsed, total_left, total_right, user_id, enter_position) = [], [], [], [], [], [], []
        var_list = (report_id, date, elapsed, total_left, total_right, user_id, enter_position)

        for report in reports:
            for i in range(len(report)):
                var_list[i].append(report[i])

        return var_list

    def insert_farm_info(self, farm_name, categories, email):

        id = self.find_id_w_email(email)
        self.cursor.execute("Insert Into Farm(User_userID, farm_name, categories) Values (%s, %s, %s)",
                            (id, farm_name, categories))
        self.connection.commit()

    def insert_report(self, date, elapsed_time, total_left, total_right, uid, enter_position):
        is_matching, file_path = self.get_data_n_check()
        if is_matching:
            self.cursor.execute(
                "INSERT INTO Report(User_userID, date, elapsed_time, total_left, total_right, enter_position) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (int(uid), str(date), elapsed_time, total_left, total_right, enter_position))
            self.connection.commit()
            self.cursor.close()
            self.connection.close()
        else:
            print("Security breach.")

    def is_uid_email_match(self, uid, email):
        uid = int(uid)
        email = email.strip()
        try:
            self.cursor.execute(
                "select userID, password from User WHERE User.userID = %s and User.email=%s"
                , (int(uid), email))
            x = self.cursor.next()
            return True
        except StopIteration:
            print("Err")
            return False

    def get_data_n_check(self):
        platform_name = platform.system()
        # For Windows
        if platform_name == "Windows":
            save_dir = os.getenv('APPDATA')
            file_path = save_dir + '\\Provactus\\usr.md'

        elif platform_name == "Linux":
            file_path = '/var/Provactus/usr.md'

        try:
            with open(file_path, 'r') as file:
                read_file = file.readlines()
                uid = read_file[0]
                email = read_file[1]
                if self.is_uid_email_match(uid, email):
                    match = True
                else:
                    match = False
        except FileNotFoundError:
            match = False
        return match, file_path

    def get_id_local(self):
        platform_name = platform.system()
        # For Windows
        if platform_name == "Windows":
            save_dir = os.getenv('APPDATA')
            file_path = save_dir + '\\Provactus\\usr.md'

        elif platform_name == "Linux":
            file_path = '/var/Provactus/usr.md'

        with open(file_path, 'r') as file:
            read_file = file.readlines()
            uid = read_file[0]

        return uid

    def get_current_user_info(self):
        self.cursor.execute(
            "select email, name, surname from User WHERE User.userID = %s", (int(self.get_id_local()),)
        )
        info = self.cursor.next()
        return info



