""" Italian catalog of the interface (see webapp/i18n.py).

    Terms follow the Italian rulebook (webapp/regole.pdf): centro di approvvigionamento, appoggio, trasporto via
    mare, ritirata, scioglimento / sciogliere, costruzione, stallo, sloggiata, armata, flotta, unità, parità.
    Exception: "Fall" is Autunno (the rulebook's "Fine del 1901" could be confused with the winter adjustments).
    Order notation and province abbreviations stay English (A PAR - BUR, S, C, VIA) in both languages.
"""

POWERS = {'AUSTRIA': 'Austria', 'ENGLAND': 'Inghilterra', 'FRANCE': 'Francia', 'GERMANY': 'Germania',
          'ITALY': 'Italia', 'RUSSIA': 'Russia', 'TURKEY': 'Turchia'}
DAYS = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']
MONTHS = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic']

MESSAGES = {
    # Pages shared by everybody
    'Game': 'Partita',
    'History': 'Storico',
    'Notifications': 'Notifiche',
    'Admin': 'Admin',
    'Help': 'Aiuto',
    'Log out': 'Esci',
    'Log in': 'Accedi',
    'Email': 'Email',
    'Password': 'Password',
    'Name': 'Nome',
    'New here, or forgot your password? Ask the admin for a link to set it.':
        'Sei nuovo, o hai dimenticato la password? Chiedi all\'admin un link per impostarla.',
    'Wrong email or password.': 'Email o password errata.',
    'Form expired or invalid. Go back, reload the page and try again.':
        'Modulo scaduto o non valido. Torna indietro, ricarica la pagina e riprova.',
    'Internal error. Report this request id to the admin: %(request_id)s':
        'Errore interno. Comunica all\'admin questo codice di richiesta: %(request_id)s',

    # Set-password link and profile
    'Set your password': 'Imposta la tua password',
    'This link has expired.': 'Questo link è scaduto.',
    'This link does not work: it was already used, replaced by a newer one, or mistyped.':
        'Questo link non funziona: è già stato usato, è stato sostituito da uno più recente o è stato copiato '
        'male.',
    'Ask the admin for a new link.': 'Chiedi all\'admin un nuovo link.',
    'Account <strong>%(email)s</strong>, shown to the other players as <strong>%(name)s</strong>.':
        'Account <strong>%(email)s</strong>, che gli altri giocatori vedono come <strong>%(name)s</strong>.',
    'New password': 'Nuova password',
    'Repeat it': 'Ripetila',
    'Save password and log in': 'Salva la password e accedi',
    'This link works once. From now on you log in with your email and this password.':
        'Questo link funziona una volta sola. D\'ora in poi accedi con la tua email e questa password.',
    'Password saved. You are logged in.': 'Password salvata. Hai effettuato l\'accesso.',
    'Your profile': 'Il tuo profilo',
    'Account <strong>%(email)s</strong> <span class="muted">(you log in with it; it cannot be changed)</span>.':
        'Account <strong>%(email)s</strong> <span class="muted">(lo usi per accedere; non si può cambiare)</span>.',
    'Name shown to the other players': 'Nome che vedono gli altri giocatori',
    'Change name': 'Cambia nome',
    'Language': 'Lingua',
    'Language of the site and of your notifications': 'Lingua del sito e delle tue notifiche',
    'Change language': 'Cambia lingua',
    'Current password': 'Password attuale',
    'Change password': 'Cambia password',
    'Changing the password logs you out on your other devices.':
        'Cambiando la password esci dall\'account sugli altri tuoi dispositivi.',
    'Name not changed: %(error)s': 'Nome non cambiato: %(error)s',
    'Name changed to %(name)s.': 'Nome cambiato in %(name)s.',
    'Language not changed: %(error)s': 'Lingua non cambiata: %(error)s',
    'Language changed to %(language)s.': 'Lingua cambiata in %(language)s.',
    'Password not changed: the current password is wrong.': 'Password non cambiata: la password attuale è errata.',
    'Password not changed: %(error)s': 'Password non cambiata: %(error)s',
    'Password changed. Your other devices have to log in again.':
        'Password cambiata. Sugli altri tuoi dispositivi devi accedere di nuovo.',
    'The two passwords differ.': 'Le due password sono diverse.',
    'The password must be %(min)d to %(max)d characters long.':
        'La password deve essere lunga da %(min)d a %(max)d caratteri.',
    'There is no user %(email)s.': 'Non esiste l\'utente %(email)s.',
    'The name must be 1 to %(max)d characters long.': 'Il nome deve essere lungo da 1 a %(max)d caratteri.',
    'The name cannot contain control characters.': 'Il nome non può contenere caratteri di controllo.',
    '"%(email)s" is not a valid email address.': '"%(email)s" non è un indirizzo email valido.',
    'Unknown language: %(lang)s.': 'Lingua sconosciuta: %(lang)s.',
    'There is already a user %(email)s.': 'Esiste già l\'utente %(email)s.',
    'The name "%(name)s" is already taken.': 'Il nome "%(name)s" è già usato.',

    # The game page
    'No game yet': 'Nessuna partita',
    'Start one from the <a href="%(url)s">admin page</a>.': 'Avviane una dalla <a href="%(url)s">pagina admin</a>.',
    'The admin has not started a game yet.': 'L\'admin non ha ancora avviato una partita.',
    'The game is over.': 'La partita è finita.',
    'Winner: %(powers)s.': 'Vincitore: %(powers)s.',
    'Draw between: %(powers)s.': 'Parità tra: %(powers)s.',
    'Deadline:': 'Scadenza:',
    'Your orders (%(powers)s)': 'I tuoi ordini (%(powers)s)',
    "Each order is saved as soon as you choose it; press <em>I'm done</em> when you have finished.":
        'Ogni ordine viene salvato appena lo scegli; premi <em>Ho finito</em> quando hai terminato.',
    'Other players cannot see your orders until the phase is processed; you can change them until then.':
        'Gli altri giocatori non vedono i tuoi ordini finché la fase non viene risolta; fino ad allora puoi '
        'cambiarli.',
    'How orders work': 'Come funzionano gli ordini',
    'Tip: click (or tap) one of your units on the map to choose its order.':
        'Suggerimento: clicca (o tocca) una delle tue unità sulla mappa per sceglierne l\'ordine.',
    "I'm done: process the phase as soon as everybody is ready":
        'Ho finito: risolvi la fase appena tutti sono pronti',
    'Save orders': 'Salva gli ordini',
    "I'm done": 'Ho finito',
    "I'm not done": 'Non ho finito',
    'Close': 'Chiudi',
    'The order you choose is saved right away.': 'L\'ordine che scegli viene salvato subito.',
    'Via convoy': 'Via mare',
    'Current order:': 'Ordine attuale:',
    'Saving…': 'Salvataggio…',
    'Saved.': 'Salvato.',
    'Not saved:': 'Non salvato:',
    'Saved. You changed an order, so you are no longer marked ready.':
        'Salvato. Hai cambiato un ordine, quindi non risulti più pronto.',
    'Not saved: connection problem. Change the order again to retry.':
        'Non salvato: problema di connessione. Cambia di nuovo l\'ordine per riprovare.',
    'You have nothing to order in this phase.': 'In questa fase non hai niente da ordinare.',
    'Powers': 'Potenze',
    'Previous phase:': 'Fase precedente:',
    'You are marked ready: the phase is processed as soon as everybody is. Changing an order takes this back.':
        'Risulti pronto: la fase viene risolta appena lo sono tutti. Se cambi un ordine non risulti più pronto.',
    'Your orders are saved, but you are not marked ready.': 'I tuoi ordini sono salvati, ma non risulti pronto.',
    'You have not submitted orders for this phase yet.': 'Non hai ancora dato ordini per questa fase.',
    'Power': 'Potenza',
    'Orders': 'Ordini',
    'no orders': 'nessun ordine',
    'Player': 'Giocatore',
    'Centers': 'Centri',
    'Units': 'Unità',
    'This phase': 'Questa fase',
    'Processed: %(phases)s.': 'Risolte: %(phases)s.',
    'There is no game in progress.': 'Non c\'è una partita in corso.',
    'The game moved on to %(phase)s before your orders arrived: they were NOT recorded. '
    'Please enter orders for the new phase.':
        'La partita è passata a %(phase)s prima che arrivassero i tuoi ordini: NON sono stati registrati. '
        'Inserisci gli ordini per la nuova fase.',
    'You cannot give orders for %(locations)s.': 'Non puoi dare ordini per %(locations)s.',
    'Orders saved for %(phase)s and marked ready.': 'Ordini salvati per %(phase)s; risulti pronto.',
    'Orders saved for %(phase)s (not marked ready: the phase waits for you until the deadline).':
        'Ordini salvati per %(phase)s (non risulti pronto: la fase ti aspetta fino alla scadenza).',
    'Your dislodged units must retreat or be disbanded.':
        'Le tue unità sloggiate devono ritirarsi o essere sciolte.',
    ('You may build up to %(num)d unit.', 'You may build up to %(num)d units.'):
        ('Puoi costruire al massimo %(num)d unità.', 'Puoi costruire al massimo %(num)d unità.'),
    ('You must disband %(num)d unit. If you choose none, the engine picks it for you.',
     'You must disband %(num)d units. If you choose fewer, the engine picks the rest for you.'):
        ('Devi sciogliere %(num)d unità. Se non la scegli tu, la sceglie il programma.',
         'Devi sciogliere %(num)d unità. Se ne scegli meno, le altre le sceglie il programma.'),
    'Build at %(loc)s': 'Costruzione a %(loc)s',
    '%(power)s is neutral in this game and cannot be given orders.':
        '%(power)s è neutrale in questa partita e non può ricevere ordini.',
    '"%(order)s" is not a valid order for %(loc)s in %(phase)s.':
        '"%(order)s" non è un ordine valido per %(loc)s in %(phase)s.',
    'Too many orders: at most %(limit)d in this phase, you gave %(given)d.':
        'Troppi ordini: al massimo %(limit)d in questa fase, ne hai dati %(given)d.',

    # Phases, deadlines, the game's own words
    'Spring': 'Primavera',
    'Fall': 'Autunno',
    'Winter': 'Inverno',
    '%(season)s %(year)s, %(type)s': '%(season)s %(year)s, %(type)s',
    'Movement': 'Movimento',
    'Retreats': 'Ritirate',
    'Adjustments': 'Aggiustamenti',
    'No deadline: the phase is processed when all players are ready.':
        'Nessuna scadenza: la fase viene risolta quando tutti i giocatori sono pronti.',
    '%(time)s (%(zone)s), in %(left)s. Processed earlier if all players are ready.':
        '%(time)s (%(zone)s), tra %(left)s. Risolta prima se tutti i giocatori sono pronti.',
    '%(days)d d %(hours)d h': '%(days)d g %(hours)d h',
    '%(hours)d h %(minutes)d min': '%(hours)d h %(minutes)d min',
    '%(minutes)d min': '%(minutes)d min',
    'Hold': 'Fermo',
    'Move': 'Spostamento',
    'Move via convoy': 'Spostamento via mare',
    'Support': 'Appoggio',
    'Convoy': 'Trasporto via mare',
    'Retreat': 'Ritirata',
    'Build': 'Costruzione',
    'Disband': 'Scioglimento',
    'No build': 'Nessuna costruzione',
    'Keep': 'Mantieni',
    'eliminated': 'eliminata',
    'neutral (units hold)': 'neutrale (le unità stanno ferme)',
    'no player (units hold)': 'nessun giocatore (le unità stanno ferme)',
    'nothing to order': 'niente da ordinare',
    'ready': 'pronto',
    'orders submitted, not ready': 'ordini dati, non pronto',
    'waiting for orders': 'in attesa di ordini',
    'no convoy': 'trasporto mancato',
    'bounce': 'stallo',
    'void': 'nullo',
    'cut': 'neutralizzato',
    'dislodged': 'sloggiata',
    'disrupted': 'interrotto',
    'disband': 'disciolta',
    'maybe': 'forse',

    # History
    'No phase has been processed yet.': 'Nessuna fase è stata ancora risolta.',
    'The map shows the position at the start of the phase, with the orders given.':
        'La mappa mostra la situazione all\'inizio della fase, con gli ordini dati.',

    # Notifications
    'Notifications are not available on this server right now. Tell the admin.':
        'Le notifiche non sono disponibili su questo server al momento. Avvisa l\'admin.',
    "Get a notification on your phone (or computer) when a new phase starts and you have orders to give, and a "
    "reminder before the deadline if you have not pressed <em>I'm done</em> yet.":
        'Ricevi una notifica sul telefono (o sul computer) quando inizia una nuova fase e hai ordini da dare, e un '
        'promemoria prima della scadenza se non hai ancora premuto <em>Ho finito</em>.',
    "Notifications never contain anybody's orders.": 'Le notifiche non contengono mai gli ordini di nessuno.',
    'This device': 'Questo dispositivo',
    'Checking…': 'Verifica in corso…',
    'Notifications need JavaScript.': 'Le notifiche richiedono JavaScript.',
    '<strong>On iPhone and iPad</strong> notifications only work once the site is on your home screen:':
        '<strong>Su iPhone e iPad</strong> le notifiche funzionano solo se il sito è nella schermata Home:',
    'In Safari, tap the <em>Share</em> button and choose <em>Add to Home Screen</em>.':
        'In Safari tocca il pulsante <em>Condividi</em> e scegli <em>Aggiungi alla schermata Home</em>.',
    'Open Diplomacy from the new icon on your home screen and log in.':
        'Apri Diplomacy dalla nuova icona nella schermata Home e accedi.',
    'Come back to this page (it is in the menu at the top) and tap <em>Enable notifications</em>.':
        'Torna su questa pagina (è nel menu in alto) e tocca <em>Attiva le notifiche</em>.',
    'This needs iOS 16.4 or later.': 'Serve iOS 16.4 o successivo.',
    'Enable notifications': 'Attiva le notifiche',
    'Disable on this device': 'Disattiva su questo dispositivo',
    "Notifications are blocked for this site. Allow them in your browser's site settings (on Android: tap the icon "
    "left of the address, then <em>Permissions</em>; on iPhone: <em>Settings → Notifications → Diplomacy</em>), "
    "then reload this page.":
        'Le notifiche sono bloccate per questo sito. Consentile nelle impostazioni del sito del browser (su '
        'Android: tocca l\'icona a sinistra dell\'indirizzo, poi <em>Autorizzazioni</em>; su iPhone: '
        '<em>Impostazioni → Notifiche → Diplomacy</em>), poi ricarica questa pagina.',
    'Your devices': 'I tuoi dispositivi',
    'Device': 'Dispositivo',
    'Since': 'Dal',
    'Last delivered': 'Ultima consegna',
    'Last error': 'Ultimo errore',
    'Remove': 'Rimuovi',
    'Send me a test notification': 'Mandami una notifica di prova',
    'None yet.': 'Ancora nessuno.',
    'server error': 'errore del server',
    'Notifications are blocked on this device.': 'Le notifiche sono bloccate su questo dispositivo.',
    'Notifications are enabled on this device.': 'Le notifiche sono attive su questo dispositivo.',
    'Notifications are not enabled on this device.': 'Le notifiche non sono attive su questo dispositivo.',
    'Something went wrong: %(error)s. Reload the page and try again; if it keeps failing, tell the admin.':
        'Qualcosa è andato storto: %(error)s. Ricarica la pagina e riprova; se continua a non funzionare, avvisa '
        'l\'admin.',
    'Not enabled yet.': 'Non ancora attive.',
    'This browser does not support notifications. Try Chrome or Firefox (or Safari from the home screen on iPhone).':
        'Questo browser non supporta le notifiche. Prova Chrome o Firefox (o Safari dalla schermata Home su '
        'iPhone).',
    'Asking for permission…': 'Richiesta del permesso…',
    'Browser': 'Browser',
    '%(browser)s on %(system)s': '%(browser)s su %(system)s',
    'never': 'mai',
    'unreachable': 'irraggiungibile',
    'This browser sent an unusable subscription: %(error)s.':
        'Questo browser ha inviato un\'iscrizione inutilizzabile: %(error)s.',
    'Device removed: it will not get notifications any more.':
        'Dispositivo rimosso: non riceverà più notifiche.',
    'Device not found.': 'Dispositivo non trovato.',
    'Test: notifications work on this device.': 'Prova: le notifiche funzionano su questo dispositivo.',
    'You have not enabled notifications on any device yet.':
        'Non hai ancora attivato le notifiche su nessun dispositivo.',
    ('Test notification sent to %(num)d device. It should appear within a few seconds.',
     'Test notification sent to %(num)d devices. It should appear within a few seconds.'):
        ('Notifica di prova inviata a %(num)d dispositivo. Dovrebbe comparire entro pochi secondi.',
         'Notifica di prova inviata a %(num)d dispositivi. Dovrebbe comparire entro pochi secondi.'),
    ('Test notification: %(failed)d of %(num)d device failed (%(errors)s). Devices that no longer exist were '
     'removed; if the others keep failing, tell the admin.',
     'Test notification: %(failed)d of %(num)d devices failed (%(errors)s). Devices that no longer exist were '
     'removed; if the others keep failing, tell the admin.'):
        ('Notifica di prova: %(failed)d dispositivo su %(num)d non l\'ha ricevuta (%(errors)s). I dispositivi '
         'che non esistono più sono stati rimossi; se gli altri continuano a non riceverle, avvisa l\'admin.',
         'Notifica di prova: %(failed)d dispositivi su %(num)d non l\'hanno ricevuta (%(errors)s). I dispositivi '
         'che non esistono più sono stati rimossi; se gli altri continuano a non riceverle, avvisa l\'admin.'),
    'Diplomacy: %(phase)s': 'Diplomacy: %(phase)s',
    'Orders needed for %(powers)s.': 'Servono ordini per %(powers)s.',
    'Deadline: %(time)s.': 'Scadenza: %(time)s.',
    'Diplomacy: the game is over': 'Diplomacy: la partita è finita',
    'See the final position.': 'Guarda la situazione finale.',
    '%(power)s (orders saved, but not marked done)': '%(power)s (ordini salvati, ma senza "Ho finito")',
    '%(power)s (no orders yet)': '%(power)s (ancora nessun ordine)',
    'Diplomacy: %(left)s left for %(phase)s': 'Diplomacy: mancano %(left)s per %(phase)s',
    'Not done yet: %(states)s. Deadline: %(time)s.': 'Non hai ancora finito: %(states)s. Scadenza: %(time)s.',

    # Admin
    'Current phase: %(phase)s': 'Fase attuale: %(phase)s',
    'Set the deadline of this phase to': 'Imposta la scadenza di questa fase a',
    'hours from now': 'ore da adesso',
    '(leave empty for no deadline)': '(lascia vuoto per nessuna scadenza)',
    'Set deadline': 'Imposta la scadenza',
    'Process this phase now': 'Risolvi ora questa fase',
    'with the orders submitted so far; units without orders hold.':
        'con gli ordini dati finora; le unità senza ordini stanno ferme.',
    'Phase lengths': 'Durata delle fasi',
    'Hours given to each kind of phase; 0 means no deadline. Applies from the next phase.':
        'Ore concesse per ogni tipo di fase; 0 vuol dire nessuna scadenza. Vale dalla prossima fase.',
    'hours': 'ore',
    'Save phase lengths': 'Salva la durata delle fasi',
    'End the game': 'Termina la partita',
    'End the game now as a draw between the surviving powers':
        'Termina ora la partita in parità tra le Potenze superstiti',
    'End as a draw': 'Termina in parità',
    'New game': 'Nuova partita',
    'Starts a standard game at Spring 1901, following the rulebook\'s "Alternate way to play" when there are fewer '
    'than seven players. Give each player their countries first (see Assign powers below).':
        'Avvia una partita standard dalla Primavera 1901, seguendo il "modo alternativo di giocare" del regolamento '
        'se i giocatori sono meno di sette. Prima assegna a ogni giocatore le sue Potenze (vedi Assegna le Potenze '
        'qui sotto).',
    'The current game is moved to the archive folder, not deleted.':
        'La partita attuale viene spostata nella cartella dell\'archivio, non cancellata.',
    'Number of players': 'Numero di giocatori',
    'Players': 'Giocatori',
    'Who controls what': 'Chi controlla cosa',
    'Neutral (units hold)': 'Neutrali (le unità stanno ferme)',
    'Players check': 'Controllo dei giocatori',
    'matches': 'corrisponde',
    'Yes, start a new game and archive the current one': 'Sì, avvia una nuova partita e archivia quella attuale',
    'Yes, start a new game': 'Sì, avvia una nuova partita',
    'Start new game': 'Avvia una nuova partita',
    'Set-password link for <strong>%(email)s</strong>, shown only now. It works once, until %(expires)s.':
        'Link per impostare la password di <strong>%(email)s</strong>, mostrato solo ora. Funziona una volta '
        'sola, fino a %(expires)s.',
    'Send it by email': 'Invialo per email',
    'One account per email address. New users get a link to set their password; send it to them (by email or '
    'chat). Links work once, for %(days)d days; for a forgotten password, make a new link.':
        'Un account per indirizzo email. I nuovi utenti ricevono un link per impostare la password; mandaglielo '
        '(per email o in chat). I link funzionano una volta sola, per %(days)d giorni; per una password '
        'dimenticata crea un nuovo link.',
    'Powers without a player give no orders: their units hold.':
        'Le Potenze senza giocatore non danno ordini: le loro unità stanno ferme.',
    'This game was started for %(players)d players; neutral: %(powers)s.':
        'Questa partita è stata avviata per %(players)d giocatori; neutrali: %(powers)s.',
    'This game was started for %(players)d players.': 'Questa partita è stata avviata per %(players)d giocatori.',
    'Actions': 'Azioni',
    'yes': 'sì',
    'set': 'impostata',
    'not set': 'non impostata',
    'link pending until %(expires)s': 'link valido fino a %(expires)s',
    'link expired': 'link scaduto',
    'New link': 'Nuovo link',
    'Remove admin': 'Togli admin',
    'Make admin': 'Rendi admin',
    'sure': 'sicuro',
    'Delete': 'Cancella',
    'Add a user': 'Aggiungi un utente',
    'Admin (can start games, manage users, force processing)':
        'Admin (può avviare partite, gestire gli utenti, forzare la risoluzione)',
    'Add user and make a link': 'Aggiungi l\'utente e crea un link',
    'Assign powers': 'Assegna le Potenze',
    'Gives the users their powers for an N player game, following the rulebook groupings listed under New game. '
    'Users who are not ticked, or not picked, get no power. Start the new game afterwards, with the same number of '
    'players.':
        'Assegna agli utenti le Potenze per una partita a N giocatori, secondo i raggruppamenti del regolamento '
        'elencati sotto Nuova partita. Gli utenti non spuntati, o non estratti, non ricevono Potenze. Poi avvia la '
        'nuova partita, con lo stesso numero di giocatori.',
    'Who can play:': 'Chi può giocare:',
    'Pick the players at random among the ticked users (otherwise the first ones in the list above)':
        'Estrai a sorte i giocatori tra gli utenti spuntati (altrimenti i primi della lista qui sopra)',
    'Shuffle the powers (otherwise in rulebook order)': 'Mescola le Potenze (altrimenti nell\'ordine del regolamento)',
    'A game is in progress: change who plays what anyway': 'C\'è una partita in corso: cambia comunque chi gioca cosa',
    'Diplomacy: set your password': 'Diplomacy: imposta la tua password',
    'Open this link to set your password for our Diplomacy game (it works once, until %(expires)s):\n\n%(url)s\n':
        'Apri questo link per impostare la password per la nostra partita a Diplomacy (funziona una volta sola, '
        'fino a %(expires)s):\n\n%(url)s\n',
    'Unsupported number of players: %(players)s.': 'Numero di giocatori non previsto: %(players)s.',
    '%(available)d users available, %(needed)d needed.': '%(available)d utenti disponibili, ne servono %(needed)d.',
    'Nobody plays %(powers)s.': 'Nessuno gioca %(powers)s.',
    '%(powers)s should be played by a single user, but is split between %(names)s.':
        '%(powers)s dovrebbe essere giocata da un solo utente, ma è divisa tra %(names)s.',
    'nobody': 'nessuno',
    '%(power)s is neutral with %(players)d players, but %(name)s is assigned to it.':
        '%(power)s è neutrale con %(players)d giocatori, ma è assegnata a %(name)s.',
    '%(name)s controls %(powers)s, which is not a group of the %(players)d player game.':
        '%(name)s controlla %(powers)s, che non è un gruppo della partita a %(players)d giocatori.',
    'Tick the confirmation box to start a new game.': 'Spunta la casella di conferma per avviare una nuova partita.',
    'The number of players must be between %(min)d and %(max)d.':
        'Il numero di giocatori deve essere tra %(min)d e %(max)d.',
    'New game started for %(players)d players.': 'Nuova partita avviata per %(players)d giocatori.',
    'Check users file: %(warning)s': 'Controlla gli utenti: %(warning)s',
    'Cannot assign powers: %(error)s': 'Impossibile assegnare le Potenze: %(error)s',
    'A game is in progress: tick the confirmation box to change who plays what.':
        'C\'è una partita in corso: spunta la casella di conferma per cambiare chi gioca cosa.',
    'Powers assigned: %(assignment)s.': 'Potenze assegnate: %(assignment)s.',
    'Cannot add the user: %(error)s': 'Impossibile aggiungere l\'utente: %(error)s',
    'User %(name)s added. Send them the link below.': 'Utente %(name)s aggiunto. Mandagli il link qui sotto.',
    'New link for %(name)s. Send it to them; the previous link no longer works.':
        'Nuovo link per %(name)s. Mandaglielo; il link precedente non funziona più.',
    'You cannot change your own admin rights.': 'Non puoi cambiare i tuoi diritti di admin.',
    '%(name)s is now an admin.': '%(name)s ora è admin.',
    '%(name)s is no longer an admin.': '%(name)s non è più admin.',
    'You cannot delete yourself.': 'Non puoi cancellare te stesso.',
    'User %(name)s deleted.': 'Utente %(name)s cancellato.',
    'Tick the confirmation box to delete a user.': 'Spunta la casella di conferma per cancellare un utente.',
    'Hours must be a number between 0 and 1440, or empty for no deadline.':
        'Le ore devono essere un numero tra 0 e 1440, o vuote per nessuna scadenza.',
    'Deadline updated.': 'Scadenza aggiornata.',
    'Phase lengths must be numbers between 0 and 1440 hours.':
        'La durata delle fasi deve essere un numero di ore tra 0 e 1440.',
    'There is no game.': 'Non c\'è nessuna partita.',
    'Phase lengths updated. They apply from the next phase.':
        'Durata delle fasi aggiornata. Vale dalla prossima fase.',
    'Tick the confirmation box to end the game.': 'Spunta la casella di conferma per terminare la partita.',
    'Game ended as a draw.': 'Partita terminata in parità.',
}
