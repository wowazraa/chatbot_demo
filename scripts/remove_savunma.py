import json

files = [
    'data/raw/chatbot_dataset.json',
    r'C:\Users\KAAN EFE\Downloads\chatbot_dataset_fixed (1).json'
]

for f in files:
    try:
        with open(f, encoding='utf-8-sig') as file:
            d = json.load(file)
        
        orig_len = len(d['kayitlar'])
        d['kayitlar'] = [x for x in d['kayitlar'] if x.get('beklenen_sektor', x.get('sektor', '')) != 'savunma']
        
        if 'sektorler' in d.get('meta', {}):
            d['meta']['sektorler'] = [s for s in d['meta']['sektorler'] if s != 'savunma']
        if 'intent_etiketleri' in d.get('meta', {}) and 'savunma' in d['meta']['intent_etiketleri']:
            del d['meta']['intent_etiketleri']['savunma']
            
        print(f"{f}: Reduced from {orig_len} to {len(d['kayitlar'])}")
        
        with open(f, 'w', encoding='utf-8') as file:
            json.dump(d, file, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error processing {f}: {e}")
