import json
from pathlib import Path
import subprocess
import re

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "processed" / "chatbot_dataset_augmented.json"

# Turkish B2B patterns to English B2B templates with appropriate terminology and jargons
TRANSLATION_MAP = {
    # Sağlık / Healthcare
    "hastane": "hospital clinic management systems with EHR and patient portal integration",
    "randevu": "HIPAA compliant patient scheduling and appointment booking software",
    "tahlil": "laboratory information system LIS with HL7 interface and automated analyzer support",
    "hekim": "physician scheduling doctor portal clinical workflow coordination app",
    "reçete": "electronic prescription e-Rx tracking medical billing software",
    "klinik": "practice management software clinic automation medical scheduling system",
    "tıbbi": "medical imaging PACS integration DICOM viewer clinical platform",
    "hbys": "hospital information system HIS HBYS software suite and database integration",
    "e-nabız": "personal health record system integrated with national e-Nabiz health portal",
    "enabız": "national health database integration and patient dashboard electronic records",
    "doktor": "doctor dashboard clinical notes system virtual consultation telemedicine app",
    
    # Bilişim / IT
    "api": "enterprise RESTful B2B API gateway integration and microservices architecture",
    "saas": "multi-tenant SaaS platform architecture secure user licensing system",
    "bulut": "scalable cloud infrastructure orchestration AWS Azure DevOps deployment pipeline",
    "sunucu": "high-availability dedicated cloud servers virtualization load balancer setup",
    "veri tabanı": "relational database clustering data warehousing SQL backup solutions",
    "siber güvenlik": "cybersecurity protection SIEM dashboard next-gen firewall monitoring",
    "yazılım": "custom enterprise software engineering backend development API integrations",
    "kod": "source code repository management automated CI CD testing pipelines",
    "lisanslama": "digital rights management user licensing and entitlement server implementation",
    "entegrasyon": "third-party platform integration ESB middleware workflow orchestration",
    
    # Eğitim / Education
    "kurs": "online course creation tools e-learning content delivery portal",
    "uzaktan eğitim": "learning management system LMS distance learning classroom virtualization software",
    "okul": "school ERP automation student information system SIS tuition billing dashboard",
    "sınav": "secure online examination platform digital proctoring automated grading",
    "öğrenci": "student performance analytics gradebook tracking attendance dashboard",
    "ders": "digital curriculum planning interactive lesson building tools e-learning",
    "eğitmen": "teacher dashboard classroom management tool grading portal virtual school",
    "devamsızlık": "student attendance monitoring automated absence tracking notifications system",
    "müfredat": "academic curriculum builder syllabus management school admin portal",
    "lms": "SCORM compliant enterprise learning management system LMS platform",
    
    # Turizm / Tourism
    "otel": "hotel reservation property management system PMS check-in desk automation",
    "rezervasyon": "booking engine flight API aggregator real-time travel portal GDS",
    "uçak bileti": "global distribution system GDS flight ticketing booking aggregation software",
    "acente": "travel agency itinerary creator custom holiday package booking portal",
    "tur": "guided tour reservation system operator scheduling transfer booking portal",
    "konaklama": "hospitality guest experience loyalty portal OTA channel manager",
    "uçuş": "airline flight scheduling management tracking travel inventory systems",
    "tatil": "vacation package builder resort reservation online travel agency OTA dashboard",
    
    # Eğlence / Entertainment
    "konser": "live concert ticketing engine venue queue management access control",
    "tiyatro": "theatre seat allocation digital box office ticketing management dashboard",
    "etkinlik": "corporate event participant registration digital badge ticketing platform",
    "bilet": "event ticket sales digital checkout system queue processing software",
    "organizasyon": "entertainment venue management booking scheduling organizer backend tools",
    "mekan": "interactive seating chart event venue dashboard capacity planning",
    "koltuk seçimi": "real-time interactive seat selection box office ticket system",
    "gösteri": "performance scheduler stage booking live event ticketing software",
    "ott": "OTT streaming platform infrastructure HLS live distribution server",
    "yayın": "low-latency live broadcast streaming platform media distribution server"
}

def translate_message(msg: str) -> str:
    msg_lower = msg.lower()
    matches = []
    for tr_keyword, en_phrase in TRANSLATION_MAP.items():
        if re.search(r'\b' + re.escape(tr_keyword) + r'\b', msg_lower) or tr_keyword in msg_lower:
            matches.append((len(tr_keyword), en_phrase))
            
    if not matches:
        return "custom business operations software application workflow automation integration"
        
    # Sort matches by length of keyword to prioritize longer terms
    matches.sort(reverse=True, key=lambda x: x[0])
    return "looking for " + " and ".join(m[1] for m in matches[:3])

def main():
    if not DATASET_PATH.exists():
        print(f"Dataset path not found: {DATASET_PATH}")
        return

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    kayitlar = data.get("kayitlar", data) if isinstance(data, dict) else data
    
    # Find existing Turkish records that do not have parallel English versions
    tr_records = [r for r in kayitlar if r.get("lang") == "tr"]
    en_mesajlar = {r.get("mesaj", "").lower() for r in kayitlar if r.get("lang") == "en"}
    
    new_en_records = []
    added_count = 0
    
    for r in tr_records:
        # Generate clean B2B English parallel message
        en_mesaj = translate_message(r.get("mesaj", ""))
        
        # Avoid duplicate English messages
        if en_mesaj.lower() not in en_mesajlar:
            new_id = f"en_{r.get('id')}"
            new_en = {
                "id": new_id,
                "source_id": r.get("source_id"),
                "lang": "en",
                "mesaj": en_mesaj,
                "varyant": r.get("varyant", "duz"),
                "prefix": "",
                "suffix": "",
                "ham_mesaj": en_mesaj,
                "normalize_mesaj": en_mesaj.lower(),
                "beklenen_sektor": r.get("beklenen_sektor", "ood"),
                "beklenen_mod": r.get("beklenen_mod", "K2"),
                "zorluk": r.get("zorluk", "dogrudan")
            }
            new_en_records.append(new_en)
            en_mesajlar.add(en_mesaj.lower())
            added_count += 1

    kayitlar.extend(new_en_records)
    
    if isinstance(data, dict):
        data["kayitlar"] = kayitlar
        
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"[+] Başarıyla {added_count} adet yeni paralel İngilizce B2B kayıt oluşturuldu ve eklendi.")
    print(f"[+] Toplam kayıt sayısı: {len(kayitlar)}")
    print("[+] Re-indexing başlatılıyor...")
    
    # Run build_index.py to compile new index files
    subprocess.run(["python", str(ROOT / "scripts" / "build_index.py")], check=True)
    print("[+] Yeniden indeksleme başarıyla tamamlandı!")

if __name__ == "__main__":
    main()
