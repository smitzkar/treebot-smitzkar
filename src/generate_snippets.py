import json
from elevenlabs_tts import elevenlabs_tts_to_file  

def generate_audio_snippets(config_file):
    with open(config_file, 'r', encoding='utf-8') as file:
        config = json.load(file)

    for category_name, languages in config.items():
        print(f"\n🎵 Generating {category_name}...")
        for language, items in languages.items():
            print(f"  📢 Language: {language}")
            for item in items:
                print(f"    ⏳ Generating: {item['filename']}")
                elevenlabs_tts_to_file(item['text'], item['filename'])

if __name__ == "__main__":
    generate_audio_snippets('goodbyes.json')