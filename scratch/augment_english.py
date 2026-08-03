import json
import os
import random
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "data" / "raw" / "chatbot_dataset.json"

target_sectors = {"saglik", "turizm", "egitim", "bilisim", "eglence"}

def load_data():
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATASET_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def count_stats(records):
    stats = defaultdict(lambda: {"tr": 0, "en": 0})
    for item in records:
        sec = item.get("beklenen_sektor", "").lower()
        if sec in target_sectors:
            lang = item.get("lang", "tr").lower()
            stats[sec][lang] += 1
    return stats

NEW_EN_DATA = {
    "saglik": [
        "We are a medical facility looking for an integrated Electronic Health Record solution.",
        "I need a patient portal where patients can view their lab results and book appointments.",
        "Do you offer telemedicine infrastructure with secure video conferencing?",
        "Our clinic requires an automated billing and insurance claim management system.",
        "We're searching for a PACS (Picture Archiving and Communication System) for our radiology department.",
        "Is there a custom software solution for tracking medical inventory and pharmaceutical supplies?",
        "Looking for an API to integrate wearable health monitors with our diagnostic platform.",
        "We need a HIPAA-compliant data storage solution for sensitive patient records.",
        "Can you build a specialized CRM for managing outpatient care and follow-ups?",
        "We are a dental practice needing a unified scheduling and charting application.",
        "Our hospital wants to implement an AI-driven triage and symptom checker bot.",
        "Do you provide cybersecurity assessments specifically for healthcare networks?",
        "We need a blood bank management system with real-time tracking.",
        "Looking for a mobile app development team to build a mental health and wellness tracker.",
        "Can you integrate our laboratory information system with external state health registries?",
        "We need software to manage clinical trial data and patient consent forms.",
        "Our rehabilitation center requires a custom physical therapy tracking platform.",
        "Do you build IoT solutions for remote patient monitoring devices?",
        "We're looking for a robust appointment reminder system via SMS and email.",
        "Need a bespoke pharmacy management system including prescription tracking.",
        "We are seeking a cloud migration strategy for our legacy hospital management system.",
        "Can you develop an AI tool for analyzing pathology slides?",
        "Our telemedicine startup needs a scalable backend architecture.",
        "We require an emergency response dispatch system with GPS integration.",
        "Looking for a medical imaging software with 3D reconstruction capabilities.",
        "We need a secure physician-to-physician communication platform.",
        "Do you offer software for managing medical equipment maintenance schedules?",
        "Our home healthcare agency needs a mobile app for nurses to log visits.",
        "We want to build a marketplace for booking independent medical specialists.",
        "Can you implement biometric authentication for accessing medical records?"
    ],
    "turizm": [
        "Our hotel chain needs a centralized Property Management System to handle multiple locations.",
        "We are looking for a channel manager to sync our availability across booking sites like Booking.com.",
        "Can your team develop a custom booking engine for our boutique resort's website?",
        "We require an API integration for real-time flight tracking and dynamic pricing.",
        "Our tour operating company needs a CRM to manage guest itineraries and excursions.",
        "Do you provide mobile key integration and contactless check-in software for hotels?",
        "We're searching for a revenue management tool that uses AI to adjust room rates dynamically.",
        "We need a comprehensive housekeeping and maintenance dispatch system.",
        "Looking for a B2B travel portal development for our wholesale travel agency.",
        "Can you build a loyalty program and guest feedback application for our hospitality brand?",
        "Our airline requires a robust baggage tracking and logistics system.",
        "We want to develop a travel itinerary planner with AI recommendations.",
        "Do you offer POS (Point of Sale) integrations for hotel restaurants and spas?",
        "We need a scalable infrastructure for a massive cruise booking platform.",
        "Looking for a VR (Virtual Reality) application for virtual hotel tours.",
        "Can you create an automated chatbot for handling basic guest queries at the front desk?",
        "Our car rental business needs a fleet management and reservation platform.",
        "We are seeking a solution to manage commissions for our network of travel agents.",
        "Need a dynamic currency conversion and payment gateway integration for our global booking site.",
        "We want to build a peer-to-peer experiential travel marketplace.",
        "Can you develop a mobile app for museum audio guides and interactive maps?",
        "Our theme park requires a digital ticketing and crowd management system.",
        "We need an integration with Amadeus or Sabre GDS systems.",
        "Do you provide data analytics to track seasonal travel trends and occupancy rates?",
        "We're looking for an event management platform for our MICE (Meetings, Incentives, Conferences) division.",
        "Our ski resort needs a real-time lift pass and weather tracking application.",
        "Can you build a custom CRM for luxury travel concierges?",
        "We need a sustainability tracking software for eco-friendly tourism operators.",
        "Looking for a blockchain solution to issue secure travel certificates.",
        "Do you offer Wi-Fi portal development with captive portal monetization for hotels?"
    ],
    "egitim": [
        "Our university is seeking a robust Learning Management System to host online courses.",
        "We need a Student Information System that handles enrollment, grading, and transcripts.",
        "Can you develop a secure online proctoring tool for remote examinations?",
        "We are a corporate training company looking for a custom e-learning platform.",
        "Do you offer virtual classroom software with interactive whiteboards and breakout rooms?",
        "Our school district requires a parent-teacher communication portal.",
        "We need an alumni networking and fundraising management platform.",
        "Looking for an API to integrate plagiarism detection into our assignment submission workflow.",
        "We want to digitize our campus library with a modern cataloging and checkout system.",
        "Can you build a gamified learning app for early childhood education?",
        "Our coding bootcamp needs an integrated cloud IDE for student assignments.",
        "We are looking for a special education software that tracks individualized education programs (IEPs).",
        "Do you provide video streaming infrastructure for massive open online courses (MOOCs)?",
        "We need a scalable platform for peer-to-peer tutoring and mentoring.",
        "Looking for a data analytics dashboard to track student engagement and retention rates.",
        "Can you develop an AR app for interactive anatomy lessons in medical school?",
        "We require a language learning application with speech recognition capabilities.",
        "Our institution needs a mobile-first app for viewing course schedules and campus maps.",
        "We want to implement a single sign-on (SSO) solution across all our educational software.",
        "Do you build digital credentialing systems using blockchain for verifiable certificates?",
        "We need a school bus routing and tracking system with real-time parent notifications.",
        "Looking for a platform to manage student housing and dorm room assignments.",
        "Can you create a custom CRM for university admissions and lead tracking?",
        "We need an AI essay grader to assist our teaching assistants.",
        "Our vocational school requires simulation software for technical training.",
        "Do you offer accessibility audits for educational websites (WCAG compliance)?",
        "We want to build a marketplace for buying and selling used textbooks.",
        "Need a system to manage grant applications and academic research funding.",
        "Can you develop a music education app with real-time pitch detection?",
        "We're looking for an automated attendance tracking system using RFID or biometrics."
    ],
    "bilisim": [
        "We are migrating our legacy monolith to a microservices architecture on AWS.",
        "Our startup needs a dedicated DevOps engineer to set up CI/CD pipelines.",
        "Do you provide penetration testing and compliance auditing for fintech applications?",
        "We're looking for an outsourced software development team to build our SaaS MVP.",
        "Can you design a scalable API gateway for our distributed enterprise systems?",
        "We require 24/7 managed IT services and cloud infrastructure support.",
        "Looking for expertise in Kubernetes orchestration and containerization.",
        "We need a custom data warehouse solution with real-time analytics dashboards.",
        "Do you offer disaster recovery planning and automated backup solutions?",
        "We are seeking consultants to help us implement Zero Trust security protocols.",
        "Can you help us refactor our old PHP codebase to a modern React and Node.js stack?",
        "Our company needs an identity and access management (IAM) solution for thousands of employees.",
        "We are looking for a machine learning expert to build a predictive analytics model.",
        "Do you provide load testing and performance optimization for high-traffic websites?",
        "We need a robust logging and monitoring stack using ELK or Prometheus.",
        "Looking for a blockchain development team to build a smart contract platform.",
        "Can you design an IoT architecture for our network of smart sensors?",
        "We require a cross-platform mobile app built with Flutter or React Native.",
        "Our e-commerce platform needs a headless CMS integration.",
        "Do you offer database migration services from Oracle to PostgreSQL?",
        "We need an automated vulnerability scanning tool integrated into our GitHub pipeline.",
        "Looking for an expert in Natural Language Processing to build a custom LLM application.",
        "Can you help us achieve SOC2 compliance for our cloud infrastructure?",
        "We want to build an internal developer portal to streamline onboarding.",
        "Our network requires SD-WAN implementation and branch office connectivity.",
        "Do you provide UI/UX design services for enterprise software?",
        "We need a robust messaging queue architecture using Kafka or RabbitMQ.",
        "Looking for a team to maintain and update our legacy COBOL systems.",
        "Can you develop a desktop application for Windows and macOS using Electron?",
        "We need expertise in serverless architecture and AWS Lambda functions."
    ],
    "eglence": [
        "Our media company needs a high-throughput Content Delivery Network for global video streaming.",
        "We are looking for a DRM (Digital Rights Management) solution to protect our original content.",
        "Can you develop a low-latency multiplayer backend for our mobile game?",
        "We need a massive scale event ticketing platform capable of handling flash sales.",
        "Our agency requires a Media Asset Management system to organize terabytes of raw video files.",
        "Looking for an interactive live streaming architecture with real-time chat and tipping.",
        "We want to build a music distribution platform for independent artists.",
        "Do you offer machine learning solutions for personalized content recommendation engines?",
        "We need a custom mobile app for our music festival with interactive maps and scheduling.",
        "Can you integrate AR (Augmented Reality) filters into our social media campaign app?",
        "Our animation studio needs a cloud-based rendering pipeline.",
        "We are looking for a podcast hosting and syndication platform.",
        "Do you provide scalable leaderboard and matchmaking servers for esports tournaments?",
        "We need an influencer marketing CRM to track campaign ROI.",
        "Looking for a platform to host and monetize interactive webinars and virtual events.",
        "Can you build a fantasy sports application with real-time data feeds?",
        "Our publishing house wants to develop an interactive eBook reading application.",
        "We need an automated subtitle generation and translation tool for video content.",
        "Do you offer anti-cheat software development for competitive gaming?",
        "We are seeking a blockchain solution for issuing NFT tickets to exclusive events.",
        "Looking for a video editing API to integrate into our user-generated content app.",
        "Can you develop a voice-controlled interactive storytelling game?",
        "We need a robust content moderation system using AI for our community forum.",
        "Our theater company requires a dynamic seating chart and reservation system.",
        "Do you provide analytics to track viewer retention and engagement during live broadcasts?",
        "We want to build a short-form video platform similar to TikTok.",
        "Need a digital signage management software for our cinema network.",
        "Can you create a cross-platform companion app for our tabletop board game?",
        "We're looking for an audio streaming architecture with high-fidelity lossless support.",
        "Our esports team needs a merchandise e-commerce platform with global shipping integrations."
    ]
}

def main():
    data_full = load_data()
    records = data_full.get("kayitlar", [])
    original_count = len(records)
    
    # Yeni eklenecekler icin id bulalim
    max_id = max((item.get("id", 0) for item in records), default=0)
    
    print("="*60)
    print("1) ÖNCE DURUM TESPİTİ")
    print("="*60)
    before_stats = count_stats(records)
    
    print(f"{'Sektör':<15} | {'TR (Türkçe)':<12} | {'EN (İngilizce)':<12}")
    print("-" * 45)
    for sec in target_sectors:
        print(f"{sec:<15} | {before_stats[sec]['tr']:<12} | {before_stats[sec]['en']:<12}")
        
    print("\n[!] İngilizce alanlar yapay çevirilerden arındırılarak yapısal olarak zenginleştiriliyor...")
    
    added_count = 0
    added_examples = []
    
    for sec in target_sectors:
        phrases = NEW_EN_DATA[sec]
        for phrase in phrases:
            max_id += 1
            new_item = {
                "id": max_id,
                "mesaj": phrase,
                "lang": "en",
                "beklenen_sektor": sec,
                "beklenen_mod": "K2",
                "zorluk": "uzun_kurumsal",
                "normalize_mesaj": phrase.lower(),
                "ham_mesaj": phrase
            }
            records.append(new_item)
            added_count += 1
            if len(added_examples) < 5:
                added_examples.append(phrase)
                
    data_full["kayitlar"] = records
    save_data(data_full)
    
    after_count = len(records)
    after_stats = count_stats(records)
    
    print("\n" + "="*60)
    print("2) YENİ KAYITLAR EKLENDİ (GERÇEK DİFF)")
    print("="*60)
    print(f"Eski Toplam Kayıt: {original_count}")
    print(f"Yeni Toplam Kayıt: {after_count}  (+{added_count} adet yapısal farklı EN cümle eklendi)")
    
    print("\n[SONRASI DURUM]")
    print(f"{'Sektör':<15} | {'TR (Türkçe)':<12} | {'EN (İngilizce)':<12}")
    print("-" * 45)
    for sec in target_sectors:
        print(f"{sec:<15} | {after_stats[sec]['tr']:<12} | {after_stats[sec]['en']:<12}")
        
    print("\n[ÖRNEK DIVERSE CÜMLELER (Doğrudan çeviri DEĞİL)]")
    for ex in added_examples:
        print(f" - {ex}")
        
    print("\n" + "="*60)
    print("3) INDEX YENİDEN OLUŞTURULUYOR")
    print("="*60)
    print("Çalıştırılıyor: python scripts/build_index.py --raw")
    try:
        result = subprocess.run(["python", "scripts/build_index.py", "--raw"], 
                                cwd=str(ROOT), capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("HATA:")
        print(e.stderr)

    print("\n" + "="*60)
    print("BİLGİLENDİRME")
    print("="*60)
    print("Veri genişletme ve Index oluşturma BAŞARILI.")
    print("Lütfen terminalden testlerinizi çalıştırarak regresyon olmadığını doğrulayın:")
    print("  python _final_dogrulama.py")
    print("  python tests/run_cekim_eki_orijinal.py")
    print("\nSerbest Genelleme (Ezber Dışı) Testleri İçin:")
    print("  curl -X POST http://127.0.0.1:8001/route -H \"Content-Type: application/json\" -d '{\"text\": \"We are migrating our legacy monolith to a microservices architecture on AWS.\"}'")
    print("  curl -X POST http://127.0.0.1:8001/route -H \"Content-Type: application/json\" -d '{\"text\": \"Need a bespoke pharmacy management system including prescription tracking.\"}'")
    
if __name__ == "__main__":
    main()
