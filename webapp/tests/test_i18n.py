""" The Italian interface: every text has a translation, and each user sees (and is notified in) their language. """
import ast
import os
import re

from webapp import i18n, i18n_it
from webapp.tests.test_app import Browser, app_fixture, email_of, invite, link_token  # pylint: disable=unused-import
from webapp.tests.test_notifications import payloads, set_deadline, subscribe_all
from webapp.tests.test_webpush import FakePushService

WEBAPP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Not translated yet: the cheat sheet (step 2 of the translation).
UNTRANSLATED_TEMPLATES = {'help.html'}
UNTRANSLATED_MODULES = {'tutorial.py', 'i18n.py', 'i18n_it.py'}
GETTEXT_NAMES = {'_', 'gettext', 'ngettext'}
PLACEHOLDER_RE = re.compile(r'%\((\w+)\)[-#0 +]*\d*(?:\.\d+)?[sdifr]')


def template_msgids(app):
    """ {msgid: [where]} of the gettext calls in the templates (msgid is a tuple for ngettext). """
    found = {}
    folder = os.path.join(WEBAPP_DIR, 'templates')
    for name in sorted(os.listdir(folder)):
        if name in UNTRANSLATED_TEMPLATES:
            continue
        with open(os.path.join(folder, name), encoding='utf-8') as file:
            source = file.read()
        for line, function, strings in app.jinja_env.extract_translations(source):
            strings = (strings,) if isinstance(strings, str) else strings
            count = 2 if function == 'ngettext' else 1
            assert all(isinstance(text, str) for text in strings[:count]), (name, line, 'not a literal text')
            msgid = tuple(strings[:2]) if function == 'ngettext' else strings[0]
            found.setdefault(msgid, []).append('%s:%d' % (name, line))
    return found


def python_msgids():
    """ {msgid: [where]} of the gettext calls (``_``, ``gettext``, ``ngettext``, also as attributes) in the
        web app's modules. """
    found = {}
    for name in sorted(os.listdir(WEBAPP_DIR)):
        if not name.endswith('.py') or name in UNTRANSLATED_MODULES:
            continue
        with open(os.path.join(WEBAPP_DIR, name), encoding='utf-8') as file:
            tree = ast.parse(file.read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = getattr(node.func, 'id', None) or getattr(node.func, 'attr', None)
            if function not in GETTEXT_NAMES:
                continue
            count = 2 if function == 'ngettext' else 1
            texts = [arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None
                     for arg in node.args[:count]]
            assert len(texts) == count and None not in texts, (name, node.lineno, 'not a literal text')
            msgid = tuple(texts) if count == 2 else texts[0]
            found.setdefault(msgid, []).append('%s:%d' % (name, node.lineno))
    return found


def placeholders(text):
    return sorted(PLACEHOLDER_RE.findall(text))


def tags(text):
    return sorted(re.findall(r'</?\w+', text))


def test_every_text_has_an_italian_translation_with_the_same_placeholders(app):
    msgids = template_msgids(app)
    for msgid, where in python_msgids().items():
        msgids.setdefault(msgid, []).extend(where)
    missing = {msgid: where for msgid, where in msgids.items() if msgid not in i18n_it.MESSAGES}
    assert not missing, 'Missing Italian translations:\n%s' % '\n'.join('%r: %s' % item for item in missing.items())
    stale = sorted(set(i18n_it.MESSAGES) - set(msgids), key=str)
    assert not stale, 'Translations of texts that are no longer used: %s' % stale
    for msgid, translation in i18n_it.MESSAGES.items():
        pairs = zip(msgid, translation) if isinstance(msgid, tuple) else [(msgid, translation)]
        assert isinstance(translation, tuple) == isinstance(msgid, tuple), msgid
        for english, italian in pairs:
            assert placeholders(english) == placeholders(italian), (english, italian)
            assert tags(english) == tags(italian), (english, italian)
            for text in (english, italian):
                # A literal % must be written %%: the texts are always %-formatted.
                assert '%' not in PLACEHOLDER_RE.sub('', text).replace('%%', ''), text


def test_power_names_and_dates():
    assert i18n.power_name('FRANCE', 'it') == 'Francia' and i18n.power_name('FRANCE', 'en') == 'France'
    assert set(i18n_it.POWERS) == {'AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY'}
    assert len(i18n_it.DAYS) == 7 and len(i18n_it.MONTHS) == 12


def set_lang(app, name, lang):
    app.config['USER_STORE'].set_lang(email_of(name), lang)


def italian_browser(app, name=None):
    """ A browser whose Accept-Language prefers Italian (logged in as `name`, if given). """
    browser = Browser(app)
    browser.client.environ_base['HTTP_ACCEPT_LANGUAGE'] = 'it-IT,it;q=0.9,en;q=0.5'
    return Browser.__init__(browser, app, name) or browser if name else browser


def test_each_user_sees_the_game_in_their_language(app):
    set_lang(app, 'anna', 'it')
    anna, bruno = Browser(app, 'anna'), Browser(app, 'bruno')
    assert anna.post('/admin/new-game', confirm='yes').status_code == 302
    page = anna.text('/')
    assert '<html lang="it">' in page and 'Primavera 1901, Movimento' in page and 'I tuoi ordini (Francia)' in page
    assert re.search(r'(lun|mar|mer|gio|ven|sab|dom) \d\d (gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic) '
                     r'\d{4}, \d\d:\d\d \(Europe/Rome\), tra 1 g 23 h', page), page
    assert 'Francia' in page and 'Germania' in page and 'in attesa di ordini' in page       # status table
    for path, text in [('/profile', 'Il tuo profilo'), ('/history', 'Nessuna fase è stata ancora risolta'),
                       ('/notifications', 'Questo dispositivo'), ('/admin', 'Assegna le Potenze')]:
        page = anna.text(path)
        assert '<html lang="it">' in page and text in page, path
    page = bruno.text('/')                                          # bruno did not choose: the default, English
    assert '<html lang="en">' in page and 'Spring 1901, Movement' in page and 'Your orders (Germany)' in page
    # After a bounce, the results of the previous phase are in each user's language too.
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', ready='yes')
    bruno.post('/orders', phase='S1901M', order_MUN='A MUN - BUR', ready='yes')
    assert '(stallo)' in anna.text('/') and 'Autunno 1901, Movimento' in anna.text('/')
    assert '(stallo)' in anna.text('/history') and 'Primavera 1901, Movimento' in anna.text('/history')
    assert '(bounce)' in bruno.text('/') and 'Fall 1901, Movement' in bruno.text('/')


def test_order_dialog_and_autosave_work_in_italian(app):
    set_lang(app, 'anna', 'it')
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes')
    page = anna.text('/')
    # The dialog's script recognizes order groups by their English key; the labels are Italian.
    assert '<optgroup label="Spostamento" data-group="Move">' in page
    assert '<optgroup label="Appoggio" data-group="Support">' in page
    assert '<option value="" data-group="Hold">— Fermo —</option>' in page
    assert "name === 'Hold'" in page and '"move": ' not in page and 'move: "Spostamento"' in page
    assert '<option value="A PAR - BUR"' in page                       # orders themselves are not translated
    reply = anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', autosave='yes').get_json()
    assert reply['ok'] and not reply['ready'] and 'I tuoi ordini sono salvati' in reply['summary']
    assert 'Francia' in reply['status']
    reply = anna.post('/orders', phase='S1901M', order_PAR='A PAR - XXX', autosave='yes').get_json()
    assert reply['errors'] == ['"A PAR - XXX" non è un ordine valido per PAR in S1901M.']
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', ready='yes')
    assert 'Ordini salvati per S1901M; risulti pronto.' in anna.text('/')
    game, meta = app.config['GAME_STORE'].load()
    assert meta['ready']['FRANCE'] is True and game.get_orders('FRANCE') == ['A PAR - BUR']
    # Logs stay in English.
    log = open(app.config['LOG_FILE'], encoding='utf-8').read()
    assert 'errors=[\'"A PAR - XXX" is not a valid order for PAR in S1901M.\']' in log


def test_language_is_chosen_on_the_profile_page(app):
    bruno = Browser(app, 'bruno')
    page = bruno.text('/profile')
    assert 'name="lang"' in page and '<option value="en" lang="en" selected>English</option>' in page
    assert bruno.post('/profile/lang', lang='it').status_code == 302
    page = bruno.text('/profile')
    assert 'Lingua cambiata in Italiano.' in page and '<option value="it" lang="it" selected>Italiano</option>' in page
    assert app.config['USER_STORE'].load()['bruno@example.com'].lang == 'it'
    bruno.post('/profile/lang', lang='de')
    assert 'Lingua non cambiata: Lingua sconosciuta: de.' in bruno.text('/profile')
    assert app.config['USER_STORE'].load()['bruno@example.com'].lang == 'it'
    # A refused name change: the message is translated, the log is not.
    bruno.post('/profile/name', name='anna')
    assert 'Nome non cambiato: Il nome &#34;anna&#34; è già usato.' in bruno.text('/profile')
    log = open(app.config['LOG_FILE'], encoding='utf-8').read()
    assert "User 'bruno@example.com' changed their language: None -> it" in log
    assert "Language change of 'bruno@example.com' to 'de' refused: Unknown language: de." in log
    assert 'refused: The name "anna" is already taken.' in log
    assert bruno.post('/profile/lang', lang='en').status_code == 302
    assert 'Language changed to English.' in bruno.text('/profile')


def test_anonymous_pages_follow_the_browser_and_users_the_site_default(app):
    assert 'Accedi' in italian_browser(app).text('/login') and '<html lang="it">' in italian_browser(app).text('/login')
    english = Browser(app)
    english.client.environ_base['HTTP_ACCEPT_LANGUAGE'] = 'de-DE,de;q=0.9'      # not offered: the site default
    assert '<html lang="en">' in english.text('/login') and 'Log in' in english.text('/login')
    reply = italian_browser(app).post('/login', email='bruno@example.com', password='wrong')
    assert 'Email o password errata.' in reply.get_data(as_text=True)
    # A user who has not chosen sees the site's default language, whatever the browser says.
    assert '<html lang="en">' in italian_browser(app, 'bruno').text('/profile')
    app.config['LANGUAGE'] = 'it'
    assert '<html lang="it">' in Browser(app, 'bruno').text('/profile')
    assert '<html lang="it">' in Browser(app).text('/login')


def test_bad_default_language_falls_back_to_english(tmp_path, monkeypatch):
    from webapp import create_app                     # pylint: disable=import-outside-toplevel
    monkeypatch.setenv('DIPLOMACY_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('DIPLOMACY_LANGUAGE', 'fr')
    app = create_app()
    assert app.config['LANGUAGE'] == 'en'
    assert "Unknown DIPLOMACY_LANGUAGE 'fr'" in open(app.config['LOG_FILE'], encoding='utf-8').read()
    monkeypatch.setenv('DIPLOMACY_LANGUAGE', ' IT ')
    assert create_app().config['LANGUAGE'] == 'it'


def test_set_password_link_stores_the_language_of_the_page(app):
    anna = Browser(app, 'anna')
    token = invite(anna, 'dario@example.com', 'Dario')
    dario = italian_browser(app)
    page = dario.text('/set-password?token=' + token)
    assert 'Imposta la tua password' in page and 'che gli altri giocatori vedono come <strong>Dario</strong>' in page
    reply = dario.post('/set-password', token=token, password='dario-password', confirm='dario-password')
    assert reply.status_code == 302
    assert 'Password salvata.' in dario.text('/')
    assert app.config['USER_STORE'].load()['dario@example.com'].lang == 'it'
    assert "Language of 'dario@example.com' set to it" in open(app.config['LOG_FILE'], encoding='utf-8').read()
    # A language already chosen is kept.
    set_lang(app, 'bruno', 'en')
    anna.post('/admin/users/link', email='bruno@example.com')
    token = link_token(anna.text('/admin'))
    italian_browser(app).post('/set-password', token=token, password='bruno-password', confirm='bruno-password')
    assert app.config['USER_STORE'].load()['bruno@example.com'].lang == 'en'


def test_push_notifications_are_in_the_recipients_language(app):
    service = FakePushService()
    app.config['NOTIFIER'].opener = service
    set_lang(app, 'anna', 'it')
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes')
    keys = subscribe_all(app, 'anna', 'bruno')
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', ready='yes')
    Browser(app, 'bruno').post('/orders', phase='S1901M', order_MUN='A MUN - BUR', ready='yes')  # English request
    received = {endpoint.rsplit('/', 1)[1]: note for endpoint, note in payloads(service, keys)}
    assert received['anna']['title'] == 'Diplomacy: Autunno 1901, Movimento'
    assert re.match(r'Servono ordini per Francia\. Scadenza: (lun|mar|mer|gio|ven|sab|dom) ', received['anna']['body'])
    assert received['bruno']['title'] == 'Diplomacy: Fall 1901, Movement'
    assert received['bruno']['body'].startswith('Orders needed for Germany. Deadline: ')
    anna.post('/admin/draw', confirm='yes')                                                     # Italian request
    notes = {endpoint.rsplit('/', 1)[1]: note for endpoint, note in payloads(service, keys)[2:]}
    assert notes['anna']['title'] == 'Diplomacy: la partita è finita'
    assert notes['anna']['body'].startswith('Parità tra:')
    assert notes['bruno']['title'] == 'Diplomacy: the game is over'
    assert notes['bruno']['body'].startswith('Draw between:')
    assert 'Austria, Inghilterra, Francia' in notes['anna']['body']


def test_deadline_reminders_are_in_the_recipients_language(app):
    app.config['CRON_TOKEN'] = 'cron-secret'
    service = FakePushService()
    app.config['NOTIFIER'].opener = service
    set_lang(app, 'anna', 'it')
    anna = Browser(app, 'anna')
    anna.post('/admin/new-game', confirm='yes')
    keys = subscribe_all(app, 'anna', 'bruno')
    anna.post('/orders', phase='S1901M', order_PAR='A PAR - BUR', autosave='yes')     # saved, not done
    set_deadline(app, 3600 + 90)
    Browser(app).get('/cron/tick?token=cron-secret')
    received = {endpoint.rsplit('/', 1)[1]: note for endpoint, note in payloads(service, keys)}
    assert received['anna']['title'] == 'Diplomacy: mancano 1 h 1 min per Primavera 1901, Movimento'
    assert received['anna']['body'].startswith('Non hai ancora finito: Francia (ordini salvati, ma senza "Ho finito"). '
                                               'Scadenza: ')
    assert received['bruno']['title'] == 'Diplomacy: 1 h 1 min left for Spring 1901, Movement'
    assert received['bruno']['body'].startswith('Not done yet: Germany (no orders yet). Deadline: ')
