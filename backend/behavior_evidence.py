"""Offline research evidence summaries. No inference, media fetch, storage or diagnosis.

Frame identity/alignment is supplied by a trusted caller, not verified by this module.
Heuristics are deliberately unvalidated and must not become production decisions.
"""
from collections import Counter
from pydantic import BaseModel, ConfigDict, Field
import numpy as np
from backend.vlm import VisionResult


class Frame(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    seconds: float = Field(ge=0, le=30, allow_inf_nan=False)
    observation: VisionResult


def summarize(frames: list[Frame], *, same_dog_confirmed: bool):
    if not isinstance(same_dog_confirmed, bool) or not 1 <= len(frames) <= 30:
        raise ValueError('Expected 1–30 frames and explicit identity confirmation')
    frames = [Frame.model_validate(f) for f in frames]
    if any(b.seconds <= a.seconds for a, b in zip(frames, frames[1:])):
        raise ValueError('Frame times must strictly increase')
    accepted = [f for f in frames if same_dog_confirmed and f.observation.species == 'dog'
                and not f.observation.abstained and f.observation.visibility == 'clear'
                and f.observation.confidence >= .6]
    # Subjective confidence is a quality filter, never combined into a probability.
    support = [f.seconds for f in accepted if f.observation.posture == 'crouching'
               and f.observation.ears == 'back' and f.observation.tail == 'tucked']
    enough = len(accepted) >= 2 and accepted[-1].seconds - accepted[0].seconds >= .5
    candidates = []
    if enough and len(support) >= 2 and len(support) == len(accepted):
        candidates.append({'label':'possible_avoidance','status':'unvalidated_hypothesis',
            'support_seconds':support,'observed_cues':['crouching','ears_back','tail_tucked'],
            'alternatives':['reaction_to_camera_or_environment','temporary_posture','unobserved_context'],
            'next_observation':'Record trigger, distance, voluntary approach/retreat and recovery without provoking the dog.'})
    return {'schema_version':1,'frame_count':len(frames),'accepted_frames':len(accepted),
        'identity_source':'caller_confirmation_not_tracking','timeline':[{'seconds':f.seconds,
            'observation':f.observation.model_dump()} for f in frames],
        'posture_counts':dict(Counter(f.observation.posture for f in accepted)),
        'candidates':candidates,'abstained':not bool(candidates),'emotion':None,'intent':None,
        'validated_behavior_accuracy':False,'production_ready':False,
        'limitations':['Caller-supplied observations; no video decoding, tracking or inference',
            'Sampled posture agreement does not establish continuous motion or causation',
            'Confidence and heuristic thresholds are uncalibrated',
            'No inference of pain, aggression, intent or emotion from posture or vocalization alone']}


from training.audio_quality import audio_quality
