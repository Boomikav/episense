import sqlite3

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

uids = [
    "MP/EAS/2026/20/796", "MP/EAS/2026/21/840",  # East Nimar Chikungunya
    "JK/UDH/2026/21/830", "JK/UDH/2026/21/831",  # Udhampur Cholera
    "MP/DIN/2026/10/385", "MP/DIN/2026/10/386", "MP/DIN/2026/14/549", # Dindori Malaria
    "CG/UBK/2026/31/1251", "CG/UBK/2026/31/1252", "CG/UBK/2026/31/1285", # Kanker Malaria
    "JH/SIM/2026/30/1207", "JH/SIM/2026/30/1208", # Simdega Malaria
    "JH/KHU/2026/31/1256", "JH/KHU/2026/31/1257", # Khunti Malaria
]

for u in uids:
    r = cur.execute("SELECT text FROM documents WHERE metadata_json LIKE ?", (f"%{u}%",)).fetchone()
    print("=" * 80)
    print(f"UID: {u}")
    if r:
        print(r[0])

conn.close()
