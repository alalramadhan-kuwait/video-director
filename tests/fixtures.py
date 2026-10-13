import os
from pathlib import Path
S = Path(os.environ.get('VD_SCRATCH', '/tmp/claude-0/-home-user-timekeeper-online/d12c441f-3b9e-54a5-94c3-c8a78268d6ad/scratchpad'))
RO = S / 'audit/claude_success-story-video/video/royal-oak'              # read-only clone of the published branch
RO_AUDIO = S / 'phase05/royal-oak/audio'                                   # the 30 recovered takes (read-only)
DH_LEXICON = S / 'skills/arabic-narration/scripts/arabic_tts/examples/diabetes-lexicon.yaml'
EP7 = S / 'ep7'
PROFILES = Path(__file__).resolve().parent.parent / 'profiles'
have_ro = (RO / 'voice-abdullah/clips.json').exists() and RO_AUDIO.exists()
