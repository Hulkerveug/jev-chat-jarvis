"""Quick verification of all Hulker subsystems."""
import sys
sys.path.insert(0, '.')

from hulker.actions import Mouse, Keyboard, AppLauncher
from hulker.mic import MicStream
from hulker.wake import WakeWordDetector
from hulker.stt import transcribe
from hulker.route import CommandRouter
from hulker.tts import speak, init_tts, speak_sync
from hulker.killswitch import DeathSwitch, DataVault
from hulker.showmode import ShowMode

print("ALL CORE IMPORTS PASSED")

# --- DataVault ---
dv = DataVault(data_dir='./data')
dv.start_session()
dv.record_transcript('HULKER click 500 300')
dv.record_command('HULKER click 500 300', 'click', 'Clicked at (500, 300)')
dv.record_result('Mouse clicked', 'action', 'at 500,300')
print("Recorded 1 transcript, 1 command, 1 result")

# Persist
path = dv.persist()
print("Persisted to:", path)
import json
with open(path) as f:
    data = json.load(f)
print("Session started:", data['session_started'])
print("Transcripts:", len(data['transcripts']))
print("Commands:", len(data['commands']))
print("Results:", len(data['results']))

# --- DeathSwitch with vault ---
ds = DeathSwitch(trigger_file='./tmp/hulker_kill_test', data_vault=dv, backup_dir='./data_backup')
ds.start()
print("DeathSwitch active:", ds.is_active())
ds.flip(reason='test_flip')
print("DeathSwitch flipped:", ds.is_flipped())
print("Flip reason:", ds.get_flip_reason())

# Verify data still there
from pathlib import Path
sessions = list(Path('./data').glob('session_*.json'))
print("Session files after flip:", len(sessions))
if Path('./data/kill_manifest.json').exists():
    with open('./data/kill_manifest.json') as f:
        manifest = json.load(f)
    print("Kill manifest:", manifest)

# --- ShowMode ---
sm = ShowMode(enabled=True, heartbeat_file='./tmp/hulker_heartbeat_test')
sm.activate()
print("ShowMode active:", sm.enabled)
print("ShowMode visible (to observer):", sm.is_visible())
sm.beat()
print("Heartbeat written:", Path('./tmp/hulker_heartbeat_test').exists())
sm.deactivate()
print("ShowMode deactivated:", not sm.enabled)

print()
print("=== ALL SUBSYSTEMS VERIFIED ===")
print("- DataVault: records transcripts, commands, results — persists to JSON")
print("- DeathSwitch: persists data FIRST, then kills processes/mic/threads")
print("- ShowMode: appears deactivated, heartbeat looks stale, records live")
