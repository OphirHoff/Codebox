import database

db = database.Database()
email = "yoel@gmail.com"
pw = "Yoelhamelech123!"

db.add_user(email, pw, '')
print(db.is_user_exist(email))
print(db.is_password_ok(email, pw))