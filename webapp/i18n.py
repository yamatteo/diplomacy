""" English / Italian interface.

    User-visible text is written in English in the code and templates and goes through `gettext` (``_``) or
    `ngettext`; the English text is the key of the Italian catalog in `webapp/i18n_it.py`.
    `webapp/tests/test_i18n.py` checks that every such text has a translation, with the same placeholders.

    - Placeholders are named (``_('Name changed to %(name)s.', name=new)``) so a translation can reorder them; a
      literal percent sign is written ``%%``. In templates the same calls are available (Jinja's i18n extension,
      "newstyle": parameters are HTML-escaped).
    - The language of a request is ``g.lang``: the logged-in user's choice (`users.User.lang`), else
      ``config['LANGUAGE']`` (DIPLOMACY_LANGUAGE); for anonymous visitors the browser's Accept-Language.
      `using(lang)` switches it temporarily, e.g. to build a push notification in the recipient's language.
    - Logs stay in English: the texts returned by `gettext` and `ngettext` remember their English version, which
      `english()` returns (also for an exception raised with such a text).
    - Order notation and province abbreviations (``A PAR - BUR``) are the same in every language.
"""
import contextlib
import logging

from flask import g, request

from webapp import i18n_it

LOGGER = logging.getLogger(__name__)

LANGUAGES = ('en', 'it')
LANGUAGE_NAMES = {'en': 'English', 'it': 'Italiano'}      # each in its own language, for the profile page
DEFAULT_LANGUAGE = 'en'
CATALOGS = {'it': i18n_it.MESSAGES}
POWER_NAMES = {'it': i18n_it.POWERS}
DAY_NAMES = {'en': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], 'it': i18n_it.DAYS}
MONTH_NAMES = {'en': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
               'it': i18n_it.MONTHS}
_missing = set()


class Text(str):
    """ A translated text that also knows its English version (`english`), for the logs. """
    english = ''


def current_lang():
    """ Language of the current request ('en' outside requests). """
    try:
        return g.get('lang') or DEFAULT_LANGUAGE
    except RuntimeError:                    # outside an application context
        return DEFAULT_LANGUAGE


def lookup(lang, msgid):
    """ The translation of `msgid` (a string, or (singular, plural) for plurals) in `lang`, without placeholders
        filled in. A missing translation falls back to English and is logged once. """
    if lang == DEFAULT_LANGUAGE:
        return msgid
    try:
        return CATALOGS[lang][msgid]
    except KeyError:
        if (lang, msgid) not in _missing:
            _missing.add((lang, msgid))
            LOGGER.warning('Missing %s translation for %r', lang, msgid)
        return msgid


def _text(translated, english, params):
    text = Text(translated % params)
    text.english = english % params
    return text


def gettext(msgid, **params):
    """ `msgid` in the current language, with its %(name)s placeholders filled in from `params`. """
    return _text(lookup(current_lang(), msgid), msgid, params)


def ngettext(singular, plural, num, **params):
    """ Like `gettext`, choosing the singular or plural form by `num` (also available as %(num)d). Italian and
        English share the plural rule: singular for 1. """
    params.setdefault('num', num)
    forms = lookup(current_lang(), (singular, plural))
    return _text(forms[0] if num == 1 else forms[1], singular if num == 1 else plural, params)


def english(value):
    """ English version of a text from `gettext`/`ngettext`, or of an exception raised with one, for logs. """
    if isinstance(value, BaseException) and value.args:
        value = value.args[0]
    return getattr(value, 'english', None) or str(value)


@contextlib.contextmanager
def using(lang):
    """ Temporarily switches the current request's language (e.g. to write to another user). """
    previous = g.get('lang')
    g.lang = lang
    try:
        yield
    finally:
        g.lang = previous


def power_name(power, lang=None):
    """ 'FRANCE' -> 'France' / 'Francia'. """
    lang = lang or current_lang()
    return POWER_NAMES.get(lang, {}).get(power.upper(), power.title())


def day_name(weekday):
    """ Abbreviated name of a weekday (0 = Monday). """
    return DAY_NAMES.get(current_lang(), DAY_NAMES['en'])[weekday]


def month_name(month):
    """ Abbreviated name of a month (1 = January). """
    return MONTH_NAMES.get(current_lang(), MONTH_NAMES['en'])[month - 1]


def user_lang(user, default):
    """ The language a user sees (and gets notifications in): their choice, else the site's default. """
    return user.lang if user and user.lang in LANGUAGES else default


def install(app):
    """ Sets up translations in the app's templates and the language of anonymous requests (the blueprint's
        `load_user` replaces it with the logged-in user's). """
    app.jinja_env.add_extension('jinja2.ext.i18n')
    app.jinja_env.install_gettext_callables(lambda msgid: lookup(current_lang(), msgid),
                                            lambda singular, plural, num: lookup(current_lang(), (singular, plural))
                                            [0 if num == 1 else 1], newstyle=True)
    app.jinja_env.filters['power_name'] = power_name

    @app.before_request
    def browser_language():
        g.lang = request.accept_languages.best_match(LANGUAGES) or app.config['LANGUAGE']
