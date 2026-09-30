"""Append user-entered batches only."""
from datetime import date
from .errors import DuplicateEntryError
from .store import DEFAULT_STORE, find, load, save, validate_result


def log_result(experiment, variant, sent, replies, note='', path=DEFAULT_STORE, batch_date=None):
    data = load(path)
    exp = find(data, experiment)
    variant = validate_result(sent, replies, variant)
    day = batch_date or date.today().isoformat()
    key = (variant, sent, replies, day)
    if any((o['variant'], o['sent'], o['replies'], o['date']) == key for o in exp['observations']):
        raise DuplicateEntryError('identical batch already logged on this date')
    obs = dict(variant=variant, sent=sent, replies=replies, date=day, note=note)
    exp['observations'].append(obs)
    save(data, path)
    return obs
