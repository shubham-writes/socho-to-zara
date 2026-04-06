import re
from moviepy import AudioFileClip

def estimate_subtitles(ssml_text, output_audio):
    # Strip the <speak> wrapper to avoid misinterpreting its attributes as words
    inner_ssml = re.sub(r'<speak[^>]*>', '', ssml_text)
    inner_ssml = re.sub(r'</speak>', '', inner_ssml)

    # Tokenize: either a break tag OR a word
    tokens = re.findall(r'<break time="(\d+)ms"/>|([^<>\s]+)', inner_ssml)
    
    total_breaks = sum(int(t[0])/1000.0 for t in tokens if t[0])
    
    audio = AudioFileClip(str(output_audio))
    actual_duration = audio.duration
    audio.close()
    
    speech_duration = max(0.5, actual_duration - total_breaks)
    words = [t[1] for t in tokens if t[1].strip()]
    sec_per_word = speech_duration / max(1, len(words))
    
    current_time = 0.0
    entries = []
    
    for brk, wrd in tokens:
        if brk:
            current_time += int(brk) / 1000.0
        elif wrd.strip():
            w = wrd.strip("“”,.!?।")
            if not w: continue
            end_time = current_time + sec_per_word
            entries.append({
                "start": round(current_time, 3),
                "end": round(end_time, 3),
                "text": w
            })
            current_time = end_time
            
    return entries

# Test it
ssml = '<speak version="1.0" xmlns="...">کیا اپ <break time="800ms"/> تھوڑا سوچئے</speak>'
fake_audio = "dummy"
# Let's mock AudioFileClip
class MockAudio:
    duration = 4.0
    def close(self): pass

import sys
sys.modules['moviepy'] = type('Mock', (), {'AudioFileClip': lambda x: MockAudio()})

print(estimate_subtitles(ssml, 'fake'))
