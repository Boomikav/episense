import re

def extract_inst_tokens(raw_text, geo_names):
    combined = raw_text.lower()
    facility_markers = [
        "school", "hostel", "college", "hospital", "vidyalaya",
        "vidyanikethan", "ashram", "campus", "academy", "university",
        "mess", "residential", "girls hostel", "boys hostel", "jail", "prison"
    ]
    if not any(m in combined for m in facility_markers):
        return set()
    
    stop_words = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
        "from", "by", "as", "is", "was", "were", "are", "cases", "reported", "rural",
        "urban", "village", "sub-district", "district", "state", "status", "control",
        "surveillance", "under", "pre-metric", "post-metric", "government", "govt",
        "school", "hostel", "college", "vidyalaya", "vidyanikethan", "residential",
        "facility", "hospital", "mess", "girls", "boys", "students", "staff", "ward"
    }
    for g in geo_names:
        for p in g.lower().split():
            stop_words.add(p)
            
    tokens = set(re.findall(r"[a-z0-9]{3,}", combined))
    return tokens - stop_words

# Raichur test
t1 = extract_inst_tokens("Minority Morarji Desai Residential School, Sindhnur", ["Sindhnur", "Raichur", "Karnataka"])
t2 = extract_inst_tokens("Dr. B. R. Ambedkar Government Pre-Metric Girls Hostel Sindhnur", ["Sindhnur", "Raichur", "Karnataka"])
print("Raichur t1:", t1)
print("Raichur t2:", t2)
print("Raichur overlap:", t1.intersection(t2))

# Kottayam test
k1 = extract_inst_tokens("St John's The Baptist's English School, Village Nedumkunnam", ["Nedumkunnam", "Changanassery", "Kottayam", "Kerala"])
k2 = extract_inst_tokens("Little Flower Vidyanikethan School, Village Nedumkunnam", ["Nedumkunnam", "Changanassery", "Kottayam", "Kerala"])
print("\nKottayam k1:", k1)
print("Kottayam k2:", k2)
print("Kottayam overlap:", k1.intersection(k2))
