""" Messages between powers (press), pure functions on the game, no Flask.

    Storage: the engine's own press fields. A message is a `diplomacy.engine.message.Message` (sender power,
    recipient power or `GLOBAL`, phase, text, `time_sent` in microseconds). Messages of the current phase are in
    ``game.messages``; processing a phase moves them to ``game.message_history[phase]``. Both are part of
    ``Game.to_dict()``, so messages are saved in game.json, copied to backups/ and archived with the game.

    Secrecy: a message is visible only to its sender, its recipient (or everybody, for `GLOBAL`), as the engine's
    `Game.filter_messages` decides. Messages never become public: the history page does not show them, nothing logs
    their text and /debug/info only has counts (`counts`).

    A conversation is identified by (my power, other), `other` being a power name or `GLOBAL`. The ``GLOBAL``
    conversation holds the messages to everyone, whoever sent them.

    Read state: ``meta["read"][email]["<MYPOWER>:<OTHER>"] = time_sent`` of the last message seen in that private
    conversation, and ``meta["read"][email]["GLOBAL"]`` for the messages to everyone, which are the same for all the
    powers of a user (so they count once, and reading them as any power reads them for all). A message is unread if it is newer than that, and was not sent by one of the user's own powers.
"""
from diplomacy.engine.message import GLOBAL, Message

MAX_LENGTH = 2000


def all_messages(game):
    """ Every message of the game (history and current phase), oldest first. Private: for `counts` and `visible`. """
    result = []
    for phase_messages in list(game.message_history.values()) + [game.messages]:
        result.extend(phase_messages.values())
    return sorted(result, key=lambda message: message.time_sent)


def counts(game):
    """ {'current': n, 'total': n}: the only thing about messages that diagnostics may show. """
    current = len(game.messages)
    return {'current': current, 'total': current + sum(len(phase) for phase in game.message_history.values())}


def visible(game, power):
    """ The messages `power` may see (global ones and those it sent or received), oldest first. """
    seen = {}
    for phase_messages in list(game.message_history.values()) + [game.messages]:
        seen.update(game.filter_messages(phase_messages, power))
    return [seen[time_sent] for time_sent in sorted(seen)]


def other_of(message, power):
    """ The `other` side of the conversation of `power` that `message` belongs to. """
    if message.recipient == GLOBAL:
        return GLOBAL
    return message.recipient if message.sender == power else message.sender


def conversation(game, power, other):
    """ The messages of the conversation (`power`, `other`), oldest first. """
    return [message for message in visible(game, power)
            if message.sender != 'SYSTEM' and other_of(message, power) == other]


def recipients(game, meta, users, my_powers):
    """ Who `my_powers` may write to: `GLOBAL`, then the other powers that have a player. """
    from webapp import gameplay                 # pylint: disable=import-outside-toplevel
    players = gameplay.players_by_power(game, meta, users)
    return [GLOBAL] + sorted(power for power in players if power not in my_powers)


def clean_text(text):
    """ The text to send: stripped, with plain newlines. :raise ValueError: if empty or too long (English reason). """
    text = (text or '').replace('\r\n', '\n').replace('\r', '\n').strip()
    if not text:
        raise ValueError('empty message')
    if len(text) > MAX_LENGTH:
        raise ValueError('message of %d characters (maximum %d)' % (len(text), MAX_LENGTH))
    return text


def send(game, sender, recipient, text):
    """ Adds a message from power `sender` to power `recipient` (or `GLOBAL`) in the current phase. The caller checks
        that the sender and recipient are allowed. :raise ValueError: if the text is not acceptable. :return: the
        message, with its `time_sent`. """
    message = Message(sender=sender, recipient=recipient, phase=game.current_short_phase,
                      message=clean_text(text))
    game.add_message(message)
    return message


def read_key(power, other):
    """ Key of a conversation in the read state: per power for a private one, per user for `GLOBAL`. """
    if other == GLOBAL:
        return GLOBAL
    return '%s:%s' % (power, other)


def last_read(meta, email, power, other):
    """ `time_sent` of the last message `email` has seen in the conversation (0: none). """
    return meta.get('read', {}).get(email, {}).get(read_key(power, other), 0)


def mark_read(meta, email, power, other, time_sent):
    """ Records that `email` has seen the conversation up to `time_sent`. :return: True if that changed anything. """
    if time_sent <= last_read(meta, email, power, other):
        return False
    meta.setdefault('read', {}).setdefault(email, {})[read_key(power, other)] = time_sent
    return True


def unread(game, meta, email, power, own_powers=()):
    """ {other: number of unread messages} for the conversations of `power` that have any. Messages sent by
        `own_powers` (all the powers of the user) are never unread. """
    result = {}
    for message in visible(game, power):
        if message.sender == 'SYSTEM' or message.sender in own_powers or message.sender == power:
            continue
        other = other_of(message, power)
        if message.time_sent > last_read(meta, email, power, other):
            result[other] = result.get(other, 0) + 1
    return result


def total_unread(game, meta, email, my_powers):
    """ Unread messages over all the conversations of all `my_powers`; each message to everyone counts once. """
    total, global_count = 0, 0
    for power in my_powers:
        counts = unread(game, meta, email, power, my_powers)
        global_count = counts.pop(GLOBAL, 0)
        total += sum(counts.values())
    return total + global_count
