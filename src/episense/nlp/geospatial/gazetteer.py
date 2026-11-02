"""
Local SQLite Gazetteer for Indian and South Asian Administrative Hierarchy.
Provides deterministic grounding for Admin 0 to Admin 4 entities without fabricating IDs.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process

from episense.schemas.location import Location, GeographicLevel


# Curated verified gazetteer records
# (name, level, parent_name, gazetteer_id, latitude, longitude)
VERIFIED_RECORDS: List[Tuple[str, GeographicLevel, Optional[str], Optional[str], Optional[float], Optional[float]]] = [
    # Countries (Admin 0)
    ("India", GeographicLevel.COUNTRY, None, "GeoNames:1269750", 20.5937, 78.9629),
    ("Bangladesh", GeographicLevel.COUNTRY, None, "GeoNames:1210997", 23.6850, 90.3563),
    ("Nepal", GeographicLevel.COUNTRY, None, "GeoNames:1831722", 28.3949, 84.1240),
    ("Bhutan", GeographicLevel.COUNTRY, None, "GeoNames:1252634", 27.5142, 90.4336),
    ("Sri Lanka", GeographicLevel.COUNTRY, None, "GeoNames:1227603", 7.8731, 80.7718),
    ("Pakistan", GeographicLevel.COUNTRY, None, "GeoNames:1168579", 30.3753, 69.3451),

    # States & Union Territories (Admin 1)
    ("Kerala", GeographicLevel.REGION, "India", "GeoNames:1267254", 10.8505, 76.2711),
    ("West Bengal", GeographicLevel.REGION, "India", "GeoNames:1252881", 22.9868, 87.8550),
    ("Gujarat", GeographicLevel.REGION, "India", "GeoNames:1270770", 22.2587, 71.1924),
    ("Maharashtra", GeographicLevel.REGION, "India", "GeoNames:1264418", 19.7515, 75.7139),
    ("Odisha", GeographicLevel.REGION, "India", "GeoNames:1261029", 20.9517, 85.0985),
    ("Tamil Nadu", GeographicLevel.REGION, "India", "GeoNames:1255053", 11.1271, 78.6569),
    ("Delhi", GeographicLevel.REGION, "India", "GeoNames:1273293", 28.7041, 77.1025),
    ("Sikkim", GeographicLevel.REGION, "India", "GeoNames:1256312", 27.5330, 88.5122),
    ("Karnataka", GeographicLevel.REGION, "India", "GeoNames:1267701", 15.3173, 75.7139),
    ("Assam", GeographicLevel.REGION, "India", "GeoNames:1278253", 26.2006, 92.9376),
    ("Bihar", GeographicLevel.REGION, "India", "GeoNames:1275715", 25.0961, 85.3131),
    ("Uttar Pradesh", GeographicLevel.REGION, "India", "GeoNames:1253626", 26.8467, 80.9462),
    ("Madhya Pradesh", GeographicLevel.REGION, "India", "GeoNames:1264542", 22.9734, 78.6569),
    ("Rajasthan", GeographicLevel.REGION, "India", "GeoNames:1258899", 27.0238, 74.2179),
    ("Telangana", GeographicLevel.REGION, "India", "GeoNames:1253184", 18.1124, 79.0193),
    ("Andhra Pradesh", GeographicLevel.REGION, "India", "GeoNames:1278647", 15.9129, 79.7400),
    ("Punjab", GeographicLevel.REGION, "India", "GeoNames:1259223", 31.1471, 75.3412),
    ("Haryana", GeographicLevel.REGION, "India", "GeoNames:1270260", 29.0588, 76.0856),

    # Districts (Admin 2)
    ("Nagaon", GeographicLevel.DISTRICT, "Assam", "GeoNames:1262243", 26.3452, 92.6840),
    ("Nagaon district", GeographicLevel.DISTRICT, "Assam", "GeoNames:1262243", 26.3452, 92.6840),
    ("Anand", GeographicLevel.DISTRICT, "Gujarat", "GeoNames:1278877", 22.5645, 72.9289),
    ("Anand district", GeographicLevel.DISTRICT, "Gujarat", "GeoNames:1278877", 22.5645, 72.9289),
    ("Haveri", GeographicLevel.DISTRICT, "Karnataka", "GeoNames:1270252", 14.7954, 75.3991),
    ("Haveri district", GeographicLevel.DISTRICT, "Karnataka", "GeoNames:1270252", 14.7954, 75.3991),
    ("Kozhikode", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1265873", 11.2588, 75.7804),
    ("Kozhikode district", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1265873", 11.2588, 75.7804),
    ("Ernakulam", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1272304", 9.9816, 76.2999),
    ("Ernakulam district", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1272304", 9.9816, 76.2999),
    ("Palakkad", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1261807", 10.7867, 76.6548),
    ("Palakkad district", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1261807", 10.7867, 76.6548),
    ("Thrissur", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1254360", 10.5276, 76.2144),
    ("Wayanad", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1253164", 11.6854, 76.1320),
    ("Malappuram", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1264014", 11.0510, 76.0711),
    ("Kannur", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1267499", 11.8745, 75.3704),
    ("Kasaragod", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1267431", 12.5102, 74.9852),
    ("Kottayam", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1266072", 9.5916, 76.5222),
    ("Idukki", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1269507", 9.8500, 76.9700),
    ("Pathanamthitta", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1259955", 9.2648, 76.7870),
    ("Kollam", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1265888", 8.8932, 76.6141),
    ("Thiruvananthapuram", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1254163", 8.5241, 76.9366),
    ("Malda", GeographicLevel.DISTRICT, "West Bengal", "GeoNames:1264024", 25.0108, 88.1411),
    ("Malda district", GeographicLevel.DISTRICT, "West Bengal", "GeoNames:1264024", 25.0108, 88.1411),
    ("North 24 Parganas", GeographicLevel.DISTRICT, "West Bengal", "GeoNames:1260275", 22.7214, 88.4816),
    ("North 24 Parganas district", GeographicLevel.DISTRICT, "West Bengal", "GeoNames:1260275", 22.7214, 88.4816),
    ("South 24 Parganas", GeographicLevel.DISTRICT, "West Bengal", "GeoNames:1257404", 22.1352, 88.4016),
    ("Pune", GeographicLevel.DISTRICT, "Maharashtra", "GeoNames:1259229", 18.5204, 73.8567),
    ("Pune Municipal Corporation", GeographicLevel.CITY, "Maharashtra", "GeoNames:1259229", 18.5204, 73.8567),
    ("Vellore", GeographicLevel.DISTRICT, "Tamil Nadu", "GeoNames:1253272", 12.9165, 79.1325),
    ("Puri", GeographicLevel.DISTRICT, "Odisha", "GeoNames:1259184", 19.8135, 85.8312),
    ("Alappuzha", GeographicLevel.DISTRICT, "Kerala", "GeoNames:1278917", 9.4981, 76.3388),
    ("Mangan", GeographicLevel.DISTRICT, "Sikkim", "GeoNames:1263884", 27.5050, 88.5342),
    ("Kolkata", GeographicLevel.CITY, "West Bengal", "GeoNames:1275004", 22.5726, 88.3639),
    ("Rayagada", GeographicLevel.DISTRICT, "Odisha", "GeoNames:1258674", 19.1717, 83.4163),
    ("Dhaka", GeographicLevel.CITY, "Bangladesh", "GeoNames:1185241", 23.8103, 90.4125),
    ("Arvalli", GeographicLevel.DISTRICT, "Gujarat", "GeoNames:8411039", 23.5400, 73.1800),
    ("Sri Sathya Sai", GeographicLevel.DISTRICT, "Andhra Pradesh", "GeoNames:12108873", 14.1600, 77.8100),
    ("Balod", GeographicLevel.DISTRICT, "Chhattisgarh", "GeoNames:1277884", 20.7300, 81.2000),
    ("Ahmedabad", GeographicLevel.DISTRICT, "Gujarat", "GeoNames:1279233", 23.0225, 72.5714),
    ("Surat", GeographicLevel.DISTRICT, "Gujarat", "GeoNames:1255364", 21.1702, 72.8311),
    ("Vadodara", GeographicLevel.DISTRICT, "Gujarat", "GeoNames:1253573", 22.3072, 73.1812),
    ("Gurugram", GeographicLevel.DISTRICT, "Haryana", "GeoNames:1270580", 28.4595, 77.0266),
    ("Bengaluru", GeographicLevel.CITY, "Karnataka", "GeoNames:1277333", 12.9716, 77.5946),
    ("Bengaluru Urban", GeographicLevel.DISTRICT, "Karnataka", "GeoNames:1277333", 12.9716, 77.5946),
    ("Mysuru", GeographicLevel.DISTRICT, "Karnataka", "GeoNames:1262321", 12.2958, 76.6394),
    ("Indore", GeographicLevel.DISTRICT, "Madhya Pradesh", "GeoNames:1269743", 22.7196, 75.8577),
    ("Bhopal", GeographicLevel.DISTRICT, "Madhya Pradesh", "GeoNames:1275841", 23.2599, 77.4126),
    ("Mumbai", GeographicLevel.CITY, "Maharashtra", "GeoNames:1275339", 19.0760, 72.8777),
    ("Thane", GeographicLevel.DISTRICT, "Maharashtra", "GeoNames:1254661", 19.2183, 72.9781),
    ("Nagpur", GeographicLevel.DISTRICT, "Maharashtra", "GeoNames:1262180", 21.1458, 79.0882),
    ("Cuttack", GeographicLevel.DISTRICT, "Odisha", "GeoNames:1273442", 20.4625, 85.8830),
    ("Khordha", GeographicLevel.DISTRICT, "Odisha", "GeoNames:1266579", 20.1809, 85.6178),
    ("Ludhiana", GeographicLevel.DISTRICT, "Punjab", "GeoNames:1264733", 30.9010, 75.8573),
    ("Jaipur", GeographicLevel.DISTRICT, "Rajasthan", "GeoNames:1269515", 26.9124, 75.7873),
    ("Jodhpur", GeographicLevel.DISTRICT, "Rajasthan", "GeoNames:1269321", 26.2389, 73.0243),
    ("Chennai", GeographicLevel.CITY, "Tamil Nadu", "GeoNames:1264527", 13.0827, 80.2707),
    ("Coimbatore", GeographicLevel.DISTRICT, "Tamil Nadu", "GeoNames:1273865", 11.0168, 76.9558),
    ("Madurai", GeographicLevel.DISTRICT, "Tamil Nadu", "GeoNames:1264521", 9.9252, 78.1198),
    ("Hyderabad", GeographicLevel.CITY, "Telangana", "GeoNames:1269843", 17.3850, 78.4867),
    ("Lucknow", GeographicLevel.DISTRICT, "Uttar Pradesh", "GeoNames:1264731", 26.8467, 80.9462),
    ("Varanasi", GeographicLevel.DISTRICT, "Uttar Pradesh", "GeoNames:1253405", 25.3176, 82.9739),
    ("Agra", GeographicLevel.DISTRICT, "Uttar Pradesh", "GeoNames:1279259", 27.1767, 78.0081),
    ("Kanpur", GeographicLevel.DISTRICT, "Uttar Pradesh", "GeoNames:1267995", 26.4499, 80.3319),
    ("Nadia", GeographicLevel.DISTRICT, "West Bengal", "GeoNames:1262307", 23.4710, 88.5565),
    ("Murshidabad", GeographicLevel.DISTRICT, "West Bengal", "GeoNames:1262335", 24.1800, 88.2700),
    ("Hooghly", GeographicLevel.DISTRICT, "West Bengal", "GeoNames:1269986", 22.9000, 88.3900),
    ("Howrah", GeographicLevel.DISTRICT, "West Bengal", "GeoNames:1269841", 22.5958, 88.2636),
    ("Darjeeling", GeographicLevel.DISTRICT, "West Bengal", "GeoNames:1273187", 27.0410, 88.2663),
    ("Patna", GeographicLevel.DISTRICT, "Bihar", "GeoNames:1260086", 25.5941, 85.1376),
    ("Gaya", GeographicLevel.DISTRICT, "Bihar", "GeoNames:1271439", 24.7964, 85.0002),
    ("Chittoor", GeographicLevel.DISTRICT, "Andhra Pradesh", "GeoNames:1273934", 13.2172, 79.1003),
    ("Guntur", GeographicLevel.DISTRICT, "Andhra Pradesh", "GeoNames:1270583", 16.3067, 80.4365),
    ("Krishna", GeographicLevel.DISTRICT, "Andhra Pradesh", "GeoNames:1266008", 16.1800, 81.1300),
    ("Visakhapatnam", GeographicLevel.DISTRICT, "Andhra Pradesh", "GeoNames:1253102", 17.6868, 83.2185),
    ("Kamrup", GeographicLevel.DISTRICT, "Assam", "GeoNames:1267926", 26.2500, 91.5000),

    # Subdistricts / Localities (Admin 3 / 4)
    ("Katpadi", GeographicLevel.SUBDISTRICT, "Vellore", None, 12.9798, 79.1408),
    ("Brahmagiri", GeographicLevel.SUBDISTRICT, "Puri", None, 19.8000, 85.6500),
]


class LocalGazetteer:
    """
    Manages an embedded SQLite gazetteer for administrative resolution.
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            self.db_path = Path("data/gazetteer/south_asia_gazetteer.sqlite")
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gazetteer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    norm_name TEXT NOT NULL,
                    level TEXT NOT NULL,
                    parent_name TEXT,
                    gazetteer_id TEXT,
                    latitude REAL,
                    longitude REAL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_norm_name ON gazetteer(norm_name)")

            # Ensure all verified records are present in the table
            for name, level, parent, gid, lat, lon in VERIFIED_RECORDS:
                cursor.execute("SELECT id FROM gazetteer WHERE norm_name = ?", (name.lower(),))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO gazetteer (name, norm_name, level, parent_name, gazetteer_id, latitude, longitude)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (name, name.lower(), level.value, parent, gid, lat, lon))
            conn.commit()

    def lookup(self, query: str) -> List[Location]:
        """
        Looks up candidates by exact normalized match or high-scoring RapidFuzz match.
        """
        clean = query.strip().lower()
        root = clean

        # Strip prefixes (e.g. "district: ernakulam", "district palakkad")
        for prefix in [
            "district:", "district ", "dist.:", "dist. ", "dist:", "dist ",
            "state:", "state ", "city:", "city ", "sub-district:", "sub-district ",
            "tehsil:", "tehsil ", "taluk:", "taluk ", "village:", "village "
        ]:
            if root.startswith(prefix):
                root = root[len(prefix):].strip()

        # Remove trailing words like "district", "state", "city" for root match
        for suffix in [" district", " state", " city", " corporation", " sub-district", " tehsil", " taluk", " block", " village"]:
            if root.endswith(suffix):
                root = root[:-len(suffix)].strip()

        root = root.strip(" :,.|")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 1. Exact match on clean query or root
            cursor.execute(
                "SELECT name, level, parent_name, gazetteer_id, latitude, longitude FROM gazetteer WHERE norm_name IN (?, ?)",
                (clean, root),
            )
            rows = cursor.fetchall()
            if rows:
                return [
                    Location(
                        original_text=query,
                        normalized_name=r[0],
                        geographic_level=GeographicLevel(r[1]),
                        parent_location=r[2],
                        gazetteer_id=r[3],
                        latitude=r[4],
                        longitude=r[5],
                        confidence=1.0,
                        provenance_method="gazetteer:exact",
                    )
                    for r in rows
                ]

            # 2. RapidFuzz candidate match
            cursor.execute("SELECT name, norm_name, level, parent_name, gazetteer_id, latitude, longitude FROM gazetteer")
            all_records = cursor.fetchall()

        names = [r[1] for r in all_records]
        best_matches = process.extract(root, names, scorer=fuzz.ratio, limit=3)

        candidates: List[Location] = []
        for match_norm, score, idx in best_matches:
            if score >= 85.0:
                r = all_records[idx]
                candidates.append(
                    Location(
                        original_text=query,
                        normalized_name=r[0],
                        geographic_level=GeographicLevel(r[2]),
                        parent_location=r[3],
                        gazetteer_id=r[4],
                        latitude=r[5],
                        longitude=r[6],
                        confidence=round(score / 100.0, 2),
                        provenance_method="gazetteer:rapidfuzz",
                    )
                )

        return candidates
