import sqlite3
from uuid import uuid4
from datetime import datetime

# print(datetime.now())
conn = sqlite3.connect('db.sqlite')
# with conn:
#     conn.execute("""CREATE TABLE dicks (
#                         uuid CHARACTER(36) PRIMARY KEY,
#                         filename TEXT NOT NULL,
#                         upload_date TEXT
#                     );""")

print('WOOOOOOOOOO')

cur = conn.cursor()

# query = f"""INSERT INTO filenames VALUES (
#                 :uuid,
#                 :name,
#                 :datetime
#             );
#          """

query = f"""SELECT filename, upload_date
            FROM filepaths 
            WHERE uuid=:uuid;
        """

cur.execute(query, {'uuid': '8cfdc5ed-8ded-4134-912b-2984891cc025'})

# conn.execute(query, {'uuid': str(uuid4()), 'datetime': datetime.now(), 'name': 2})
# print(conn.)
# conn.commit()
# query = f"""SELECT filename FROM filenames;"""
# cur.execute(query)
# conn.close()
print(cur.fetchone())

conn.close()

# import re
# string = {'Content-Disposition': 'form-data; name="fo_3-o–  bar.jpeg"'}

# # file_extension = re.findall(r'\.(\w+)"$', string['Content-Disposition'])[0]
# file_extension = re.findall(r'name="([^/\\:*?"<>|]+)\.\w+"$', string['Content-Disposition'])[0]

# print(file_extension)


