import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

en_seeds = {
    "bilisim": [
        "custom cloud infrastructure DevOps automation software deployment server management CI CD pipeline",
        "cybersecurity protection firewall setup network security database protection penetration testing endpoint security",
        "enterprise custom software development API integration microservices backend architecture SaaS engineering",
        "IT infrastructure management system monitoring data center security network engineering tech support",
        "database management data warehousing cloud migration data engineering artificial intelligence software"
    ],
    "egitim": [
        "learning management system LMS student portal campus automation digital classroom e-learning platform",
        "online examination assessment platform digital proctoring automated grading quiz software certification",
        "course registration curriculum planning academic software student information system SIS gradebook",
        "remote training platform professional development e-learning content delivery live class streaming",
        "educational institution management school ERP teacher parent communication portal online academy"
    ],
    "eglence": [
        "digital ticketing platform event queue management ticketing system access control venue management software",
        "video streaming platform infrastructure interactive gaming backend media distribution server live stream API",
        "concert hall festival entertainment venue management ticket sales event booking system interactive media",
        "game server infrastructure multiplayer backend broadcasting streaming service media asset management",
        "event organization app participant registration digital badge ticketing ecosystem entertainment software"
    ],
    "saglik": [
        "HIPAA compliant patient scheduling software clinic management system EHR Electronic Health Records SQL integration",
        "telemetry patient monitoring dashboard tools hospital medical software vital signs tracking ICU software",
        "appointment scheduling software polyclinic doctor reservation system electronic prescription medical billing",
        "hospital information system HIS radiology PACS integration laboratory information system LIS patient portal",
        "telemedicine app video consultation prescription tracking medical clinic automation healthcare platform"
    ],
    "turizm": [
        "hotel reservation property management system PMS POS integration resort front desk room booking software",
        "dynamic tour booking engine flight API aggregator travel agency itinerary management system booking portal",
        "boutique hotel reservation management channel manager OTA integration guest check-in desk software",
        "vacation rental booking system tour operator platform transfer reservation flight booking system",
        "hospitality management concierge app hotel guest engagement loyalty program travel booking platform"
    ]
}

def main():
    if not DATASET_PATH.exists():
        print(f"Dataset path not found: {DATASET_PATH}")
        sys.exit(1)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    kayitlar = data.get("kayitlar", [])
    max_id = 100000

    # Add EN seeds
    for sector, messages in en_seeds.items():
        for i, msg in enumerate(messages):
            max_id += 1
            rec = {
                "id": f"en_{max_id}",
                "source_id": max_id,
                "lang": "en",
                "mesaj": msg,
                "varyant": "duz",
                "prefix": "",
                "suffix": "",
                "ham_mesaj": msg,
                "normalize_mesaj": msg.lower(),
                "beklenen_sektor": sector,
                "beklenen_mod": "K2",
                "zorluk": "dogrudan"
            }
            kayitlar.append(rec)

    data["kayitlar"] = kayitlar

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[+] Added 25 EN seeds. Total records: {len(kayitlar)}")
    print("[+] Re-indexing using scripts/build_index.py...")

    # Run build_index.py
    subprocess.run(["python", str(ROOT / "scripts" / "build_index.py")], check=True)
    print("[+] Re-indexing successfully completed!")

if __name__ == "__main__":
    main()
