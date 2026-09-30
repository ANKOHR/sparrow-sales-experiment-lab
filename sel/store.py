"""Validated JSON persistence with atomic replacement (single writer)."""
import json
import os
import tempfile
from datetime import date
from pathlib import Path

from .errors import (CorruptStoreError, DuplicateEntryError,
                     DuplicateExperimentError, InvalidResultError,
                     MinSampleTooSmallError, UnknownExperimentError)

DEFAULT_STORE = '.sel-experiments.json'


def validate_result(sent, replies, variant):
    if type(sent) is not int or type(replies) is not int or sent <= 0 or not 0 <= replies <= sent:
        raise InvalidResultError('sent must be positive and 0 <= replies <= sent')
    if not isinstance(variant, str) or variant.lower() not in ('a', 'b'):
        raise InvalidResultError('variant must be a or b')
    return variant.lower()


def validate(data):
    try:
        if data['version'] != 1 or not isinstance(data['experiments'], list):
            raise CorruptStoreError('unsupported store schema')
        names = set()
        for exp in data['experiments']:
            for field in ('name', 'variant_a', 'variant_b', 'niche'):
                if not isinstance(exp[field], str) or not exp[field].strip():
                    raise CorruptStoreError('experiment text fields must be nonempty')
            if exp['name'] in names:
                raise DuplicateExperimentError(exp['name'])
            names.add(exp['name'])
            if type(exp['min_n']) is not int or exp['min_n'] < 10:
                raise MinSampleTooSmallError('min_n must be at least 10')
            date.fromisoformat(exp['registered'])
            if type(exp['synthetic']) is not bool or not isinstance(exp['observations'], list):
                raise CorruptStoreError('invalid synthetic marker or observations')
            seen = set()
            for obs in exp['observations']:
                variant = validate_result(obs['sent'], obs['replies'], obs['variant'])
                if variant != obs['variant']:
                    raise CorruptStoreError('stored variant must be lowercase')
                date.fromisoformat(obs['date'])
                if not isinstance(obs['note'], str):
                    raise CorruptStoreError('note must be text')
                key = (variant, obs['sent'], obs['replies'], obs['date'])
                if key in seen:
                    raise DuplicateEntryError('duplicate stored observation')
                seen.add(key)
    except (KeyError, TypeError, ValueError) as exc:
        from .errors import SelError
        if isinstance(exc, SelError):
            raise
        raise CorruptStoreError('invalid store schema or date') from exc
    return data


def load(path=DEFAULT_STORE):
    path = Path(path)
    if not path.exists():
        return {'version': 1, 'experiments': []}
    try:
        return validate(json.loads(path.read_text(encoding='utf-8')))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise CorruptStoreError('store is not valid UTF-8 JSON') from exc


def save(data, path=DEFAULT_STORE):
    validate(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.sel-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(data, indent=2, sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def find(data, name):
    for exp in data['experiments']:
        if exp['name'] == name:
            return exp
    raise UnknownExperimentError(name)


def register(name, variant_a, variant_b, niche, min_n=30, path=DEFAULT_STORE,
             registered=None, synthetic=False):
    if type(min_n) is not int or min_n < 10:
        raise MinSampleTooSmallError('min_n must be at least 10')
    data = load(path)
    if any(exp['name'] == name for exp in data['experiments']):
        raise DuplicateExperimentError(name)
    exp = dict(name=name, variant_a=variant_a, variant_b=variant_b, niche=niche,
               min_n=min_n, registered=registered or date.today().isoformat(),
               synthetic=synthetic, observations=[])
    data['experiments'].append(exp)
    save(data, path)
    return exp
