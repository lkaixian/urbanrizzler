import re
from taibun import Converter

# Initialize Converter once
t_converter = Converter(system='Tailo', dialect='south')

def penang_patch(tailo_text):
    """
    Converts Standard Taiwanese Tailo -> Penang Hokkien
    """
    if not tailo_text: return ""
    t = tailo_text.lower()
    
    # Pronoun Shifts
    t = re.sub(r'\blí\b', 'lu', t)
    t = re.sub(r'\bgóa\b', 'wa', t)
    t = re.sub(r'\bguá\b', 'wa', t)
    
    # Particle Shifts
    t = re.sub(r'\bko̍k\b', 'lor', t)
    t = re.sub(r'\bkoh\b', 'lor', t)
    
    # Vowel Shifts
    t = t.replace("ts", "c").replace("ing", "eng").replace("ue", "ua").replace("liáu", "liao")
    
    return t

def get_hokkien_romanization(hanzi):
    try:
        raw = t_converter.get(hanzi)
        return penang_patch(raw)
    except:
        return ""
