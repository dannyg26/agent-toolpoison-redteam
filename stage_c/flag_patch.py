"""Replace fresh secrets in validated plaintext service data/configuration only."""


def validate_template(data, secret):
    old = secret.encode('ascii')
    offsets = []
    start = 0
    while True:
        found = data.find(old, start)
        if found < 0:
            break
        offsets.append(found)
        start = found+len(old)
    if not offsets or len(data) > 1_000_000 or b'\x00' in data:
        raise ValueError('Expected secret is not in a reviewed plaintext template')
    return {'kind': 'text', 'offsets': offsets}


def replace_secret(data, old, new):
    specification = validate_template(data, old)
    if len(old.encode('ascii')) != len(new.encode('ascii')):
        raise ValueError('Secret replacement must preserve byte length')
    changed = data.replace(old.encode('ascii'), new.encode('ascii'))
    allowed = {byte for offset in specification['offsets'] for byte in range(offset, offset+len(old))}
    if len(changed) != len(data) or any(a != b and i not in allowed
                                      for i, (a, b) in enumerate(zip(data, changed))):
        raise ValueError('Replacement changed bytes outside the reviewed secret')
    return changed
