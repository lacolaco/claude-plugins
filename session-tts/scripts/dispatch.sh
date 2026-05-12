#!/bin/bash
# Stop / StopFailure hook adapter — intentionally a no-op.
#
# Previous designs (full-text playback / decision:block / reminder
# injection) all had unacceptable trade-offs:
#   - Full-text playback: too long, multi-paragraph responses ran tens
#     of seconds of audio.
#   - decision:block: forced Claude to take an extra action inside the
#     turn, which fired Stop again, looped, and added two redundant
#     "acknowledge" lines per turn for nothing.
#   - additionalContext on Stop: only readable on the NEXT turn, so the
#     audio came too late to be useful.
#
# The Stop hook is therefore intentionally silent. Turn-end audio is
# delegated entirely to the mid-turn `say.sh` path that the model
# invokes from inside the turn (driven by SessionStart guidance and
# the remind-say.sh reminders).
exit 0
