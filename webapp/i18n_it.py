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
    'Order simulator': 'Simulatore di ordini',
    'Let me guess the orders of the other powers and see how they would be resolved':
        'Voglio ipotizzare gli ordini delle altre potenze e vedere come verrebbero risolti',
    'Save': 'Salva',
    'Only for you: your guesses are never saved or shown to anybody, and your real orders are not changed.':
        'Solo per te: le tue ipotesi non vengono mai salvate né mostrate a nessuno e i tuoi ordini veri non '
        'cambiano.',
    'Order simulator turned on.': 'Simulatore di ordini attivato.',
    'Order simulator turned off.': 'Simulatore di ordini disattivato.',
    'The order simulator is off. Turn it on in your profile.':
        'Il simulatore di ordini è disattivato. Attivalo nel tuo profilo.',
    'The previous simulation is still running: try again in a moment.':
        'La simulazione precedente è ancora in corso: riprova tra un attimo.',
    'The game moved on to %(phase)s: the page is out of date.':
        'La partita è passata a %(phase)s: la pagina non è aggiornata.',
    'The order simulator only works in movement phases.':
        'Il simulatore di ordini funziona solo nelle fasi di movimento.',
    'There is no unit at %(loc)s to guess an order for.': 'In %(loc)s non c\'è nessuna unità di cui ipotizzare l\'ordine.',
    '%(loc)s is your own unit: give its order in the orders form.':
        '%(loc)s è una tua unità: dai il suo ordine nel modulo degli ordini.',
    '%(power)s is neutral in this game: its units just hold.':
        '%(power)s è neutrale in questa partita: le sue unità restano ferme.',
    '"%(order)s" is not a valid guess for %(loc)s in %(phase)s.':
        '"%(order)s" non è un\'ipotesi valida per %(loc)s in %(phase)s.',
    'Click a unit of another power to guess its order. The map shows your orders and your guesses and how they '
    'would be resolved; units nobody ordered hold. Nothing is saved or shown to anybody.':
        'Clicca su un\'unità di un\'altra potenza per ipotizzare il suo ordine. La mappa mostra i tuoi ordini e le '
        'tue ipotesi e come verrebbero risolti; le unità senza ordine restano ferme. Niente viene salvato né '
        'mostrato a nessuno.',
    'Clear all guesses': 'Cancella tutte le ipotesi',
    'What would happen': 'Cosa succederebbe',
    'What the marks mean': 'Cosa significano i segni',
    'Green ✓: the order works (a move arrives, a support or a convoy counts).':
        '✓ verde: l\'ordine funziona (il movimento arriva, l\'appoggio o il trasporto contano).',
    'Red ✕: the move bounces; its line stops half way.':
        '✕ rossa: il movimento va in stallo; la sua linea si ferma a metà.',
    'Red slash and faded line: the support is cut.':
        'Barra rossa e linea sbiadita: l\'appoggio è neutralizzato.',
    'Faded line: the convoy is disrupted.': 'Linea sbiadita: il trasporto è interrotto.',
    'Grey ? and faded line: the order is void, for example a support for a move that does not happen.':
        '? grigio e linea sbiadita: l\'ordine è nullo, per esempio un appoggio a un movimento che non avviene.',
    'Red ring: the unit is dislodged.': 'Anello rosso: l\'unità è sloggiata.',
    'Dotted ring: nobody ordered this unit, so it holds.':
        'Anello a puntini: nessuno ha dato un ordine a questa unità, quindi resta ferma.',
    'Dashed halo: the order is a guess. Your own orders have none.':
        'Alone tratteggiato: l\'ordine è un\'ipotesi. I tuoi ordini non ce l\'hanno.',
    'No guess: it holds': 'Nessuna ipotesi: resta ferma',
    'Current guess:': 'Ipotesi attuale:',
    'Only a simulation: nothing is saved.': 'Solo una simulazione: niente viene salvato.',
    'Hide simulation': 'Nascondi la simulazione',
    'Show simulation': 'Mostra la simulazione',
    'Simulating…': 'Simulazione in corso…',
    'Simulation failed: connection problem. Change a guess to retry.':
        'Simulazione non riuscita: problema di connessione. Cambia un\'ipotesi per riprovare.',
    'guess': 'ipotesi',
    'bounces': 'va in stallo',
    'is cut': 'è neutralizzato',
    'is disrupted': 'è interrotto',
    'is void': 'è nullo',
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
    "Choose what each device gets. <em>Turns</em>: a new phase, deadline reminders and the end of the game. "
    "<em>Messages</em>: messages from other players.":
        'Scegli cosa riceve ogni dispositivo. <em>Turni</em>: una nuova fase, i promemoria prima della scadenza e '
        'la fine della partita. <em>Messaggi</em>: i messaggi degli altri giocatori.',
    'Notify me about': 'Avvisami per',
    'Turns': 'Turni',
    'Messages': 'Messaggi',
    'Device settings saved.': 'Impostazioni del dispositivo salvate.',
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
    'Set powers': 'Imposta le Potenze',
    'Unknown power: %(power)s.': 'Potenza sconosciuta: %(power)s.',
    '%(power)s is already played by %(name)s.': '%(power)s è già giocata da %(name)s.',
    '%(powers)s is neutral in this game: nobody can play it.':
        '%(powers)s è neutrale in questa partita: nessuno può giocarla.',
    'Cannot set powers: %(error)s': 'Impossibile impostare le Potenze: %(error)s',
    'The powers of %(name)s were already like that.': 'Le Potenze di %(name)s erano già queste.',
    '%(name)s now plays %(powers)s.': '%(name)s ora gioca %(powers)s.',
    '%(name)s now plays no power.': '%(name)s ora non gioca nessuna Potenza.',
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

    # Help page (help.html, tutorial.py)
    'Cheat sheet': 'Promemoria',
    'The game in brief': 'Il gioco in breve',
    '<strong>Goal:</strong> control 18 of the 34 supply centers (the dots on the map). Players can also agree to a '
    'draw between the survivors.':
        '<strong>Scopo:</strong> controllare 18 dei 34 centri di approvvigionamento (i pallini sulla mappa). I '
        'giocatori possono anche accordarsi per una parità tra i sopravvissuti.',
    '<strong>Units:</strong> armies (<code>A</code>) move on land, fleets (<code>F</code>) on sea and along coasts. '
    'All units have the same strength, and a province holds one unit at most. Sea provinces are written in italics '
    '(<code><span class="sea">NTH</span></code>), land ones upright (<code>LON</code>).':
        "<strong>Unità:</strong> le armate (<code>A</code>) si muovono per terra, le flotte (<code>F</code>) per mare "
        "e lungo le coste. Tutte le unità hanno la stessa forza, e in una provincia può stare al massimo un'unità. Le "
        'zone di mare sono scritte in corsivo (<code><span class="sea">NTH</span></code>), le province di terra in '
        'tondo (<code>LON</code>).',
    '<strong>Everybody moves at once.</strong> Orders are secret, then revealed and resolved together. Talk, promise '
    'and lie as you like: nothing said is binding.':
        '<strong>Tutti muovono contemporaneamente.</strong> Gli ordini sono segreti, poi vengono rivelati e risolti '
        'tutti insieme. Trattate, promettete e mentite quanto volete: niente di ciò che si dice è vincolante.',
    '<strong>You have as many units as supply centers.</strong> Centers change hands only at the end of Fall, by '
    'having a unit there.':
        "<strong>Hai tante unità quanti centri di approvvigionamento.</strong> I centri cambiano proprietario solo "
        "alla fine dell'Autunno, occupandoli con una propria unità.",
    'A game year': 'Un anno di gioco',
    'Phase': 'Fase',
    'Code': 'Codice',
    'What happens': 'Cosa succede',
    'Spring, movement': 'Primavera, movimento',
    'Everybody orders all their units.': 'Ognuno dà gli ordini a tutte le sue unità.',
    'Spring, retreats': 'Primavera, ritirate',
    'Dislodged units retreat or disband.': 'Le unità sloggiate si ritirano o vengono sciolte.',
    'Fall, movement': 'Autunno, movimento',
    'As in Spring.': 'Come in Primavera.',
    'Fall, retreats': 'Autunno, ritirate',
    'As in Spring. Then supply centers change owner.':
        'Come in Primavera. Poi i centri di approvvigionamento cambiano proprietario.',
    'Winter, adjustments': 'Inverno, aggiustamenti',
    'Build new units or disband the excess.': 'Si costruiscono nuove unità o si sciolgono quelle in eccesso.',
    'Retreat and adjustment phases are skipped when nobody has anything to do in them.':
        'Le fasi di ritirata e di aggiustamento vengono saltate quando nessuno ha niente da fare.',
    'Order': 'Ordine',
    'Written': 'Si scrive',
    'Meaning': 'Significato',
    'Stay. A unit without orders holds.': "Resta ferma. Un'unità senza ordini sta ferma.",
    'Go to an adjacent province. Moving into an occupied province is an attack.':
        'Va in una provincia adiacente. Spostarsi in una provincia occupata è un attacco.',
    'Support a move': 'Appoggio a uno spostamento',
    'Add 1 to the strength of that exact move. You must be able to move to the target province yourself (here '
    'Burgundy).':
        'Aggiunge 1 alla forza di quello spostamento preciso. Devi poterti spostare tu stesso nella provincia di '
        'destinazione (qui la Borgogna).',
    'Support a unit in place': "Appoggio a un'unità ferma",
    'Add 1 to the defence of a unit that is not moving (holding, supporting or convoying).':
        "Aggiunge 1 alla difesa di un'unità che non si sposta (ferma, che appoggia o che trasporta).",
    'A fleet at sea carries an army between two coasts. The army is ordered <code>A LON - NWY VIA</code>. Several '
    'fleets can form a chain.':
        "Una flotta in una zona di mare trasporta un'armata da una costa all'altra. L'armata riceve l'ordine "
        '<code>A LON - NWY VIA</code>. Più flotte possono formare una catena.',
    'Retreat phase only.': 'Solo nella fase di ritirata.',
    'Remove the unit (retreat and adjustment phases).':
        "Toglie l'unità dalla mappa (fasi di ritirata e di aggiustamento).",
    'Adjustment phase only.': 'Solo nella fase di aggiustamento.',
    "You can support, or convoy, another player's unit, without asking. A support cannot be refused.":
        "Puoi appoggiare, o trasportare via mare, un'unità di un altro giocatore, senza chiedere. Un appoggio non si "
        'può rifiutare.',
    'Who wins a conflict': 'Chi vince un conflitto',
    '<strong>Strength</strong> is 1 plus the number of valid supports. The strongest wins; if the best are equal, '
    'nobody moves (a <em>bounce</em>). A bounce does not dislodge a unit already there.':
        '<strong>La forza</strong> è 1 più il numero di appoggi validi. Vince il più forte; se i più forti sono '
        "pari, nessuno si sposta (uno <em>stallo</em>). Uno stallo non sloggia un'unità che si trova già lì.",
    'To <strong>dislodge</strong> a unit you need more strength than it has holding there. A dislodged unit must '
    'retreat.':
        "Per <strong>sloggiare</strong> un'unità serve più forza di quella che ha restando ferma lì. Un'unità "
        'sloggiata deve ritirarsi.',
    'A unit that fails to move stays where it is, and can in turn block those trying to enter its province.':
        "Un'unità che non riesce a spostarsi resta dov'è, e può a sua volta bloccare chi cerca di entrare nella sua "
        'provincia.',
    '<strong>Two units cannot swap places</strong> (except by convoy). Three or more can rotate in a circle.':
        '<strong>Due unità non possono scambiarsi di posto</strong> (salvo con un trasporto via mare). Tre o più '
        'possono ruotare in cerchio.',
    '<strong>A support is cut</strong> if the supporting unit is attacked from anywhere except the province it is '
    'supporting an attack on, even if that attack fails. It is also cut if the supporting unit is dislodged.':
        "<strong>Un appoggio è neutralizzato</strong> se l'unità che appoggia viene attaccata da qualunque provincia "
        "tranne quella contro cui sta appoggiando un attacco, anche se l'attacco fallisce. È neutralizzato anche se "
        "l'unità che appoggia viene sloggiata.",
    'A support must match the order exactly: supporting <code>A MUN - SIL</code> does nothing if Munich goes '
    'elsewhere or holds.':
        "Un appoggio deve corrispondere esattamente all'ordine: appoggiare <code>A MUN - SIL</code> non serve a "
        'niente se Monaco va altrove o sta ferma.',
    '<strong>You cannot dislodge your own unit</strong>, nor support someone doing so, and attacking your own unit '
    'does not cut its support.':
        '<strong>Non puoi sloggiare una tua unità</strong>, né appoggiare qualcuno che lo fa, e attaccare una tua '
        "unità non ne neutralizza l'appoggio.",
    '<strong>A convoy fails</strong> if one of its fleets is dislodged (attacking the fleet is not enough) and no '
    'other route is left. The army then stays where it was.':
        '<strong>Un trasporto via mare fallisce</strong> se una delle sue flotte viene sloggiata (attaccarla non '
        "basta) e non resta nessun'altra rotta. L'armata allora resta dov'era.",
    'Only fleets in sea provinces convoy; fleets in coastal provinces cannot.':
        'Solo le flotte nelle zone di mare trasportano; quelle nelle province costiere no.',
    'Examples': 'Esempi',
    "These pictures and results come from this site's own rule engine.":
        'Queste immagini e questi risultati vengono dal motore di regole del sito stesso.',
    'Map for: %(title)s': 'Mappa per: %(title)s',
    'Result words': 'Parole dei risultati',
    'The move failed; the unit stayed.': "Lo spostamento è fallito; l'unità è rimasta dov'era.",
    'The support was cut and did not count.': "L'appoggio è stato neutralizzato e non è contato.",
    'The unit was forced out and must retreat.': "L'unità è stata cacciata e deve ritirarsi.",
    'The order had no effect, e.g. a support for a move that was not ordered.':
        "L'ordine non ha avuto effetto, per esempio un appoggio a uno spostamento che non è stato ordinato.",
    'The army had no complete chain of convoying fleets.':
        "L'armata non aveva una catena completa di flotte che la trasportassero.",
    'The convoy was broken because a fleet was dislodged.':
        'Il trasporto è stato interrotto perché una flotta è stata sloggiata.',
    'The unit was removed.': "L'unità è stata tolta dalla mappa.",
    'Map oddities': 'Particolarità della mappa',
    '<strong>Spain, Bulgaria and St Petersburg have two coasts.</strong> A fleet there sits on one coast (<code>F '
    'SPA/NC</code>, <code>F STP/SC</code>, <code>F BUL/EC</code>) and can only leave along it. It still occupies '
    'the whole province.':
        '<strong>Spagna, Bulgaria e San Pietroburgo hanno due coste.</strong> Una flotta lì sta su una delle due '
        '(<code>F SPA/NC</code>, <code>F STP/SC</code>, <code>F BUL/EC</code>) e può ripartire solo lungo quella. '
        "Occupa comunque l'intera provincia.",
    '<strong>Kiel and Constantinople</strong> have a single coast: fleets pass through them (Kiel canal, the '
    'straits).':
        '<strong>Kiel e Costantinopoli</strong> hanno una sola costa: le flotte le attraversano (il canale di Kiel, '
        'gli stretti).',
    'Armies and fleets can go between <strong>Sweden and Denmark</strong>. A fleet cannot go from the Baltic '
    'straight to the Skagerrak.':
        'Armate e flotte possono passare tra <strong>Svezia e Danimarca</strong>. Una flotta non può andare dal Mar '
        'Baltico direttamente allo Skagerrak.',
    'A fleet on a coast moves only to provinces adjacent <em>along that coast</em>: Rome to Tuscany or Naples, not '
    'to Venice.':
        'Una flotta su una costa si sposta solo nelle province adiacenti <em>lungo quella costa</em>: da Roma in '
        'Toscana o a Napoli, non a Venezia.',
    'Switzerland cannot be entered.': 'In Svizzera non si può entrare.',
    'A dislodged unit retreats to an adjacent province it could normally move to, but not to an occupied one, not '
    'to where its attacker came from, and not to one left empty by a bounce this turn.':
        "Un'unità sloggiata si ritira in una provincia adiacente in cui potrebbe normalmente spostarsi, ma non in una "
        "occupata, non in quella da cui è venuto l'attaccante, e non in una rimasta vuota per uno stallo in questo "
        'turno.',
    'With nowhere to go it is disbanded. You may also choose to disband.':
        'Se non ha dove andare viene sciolta. Puoi anche scegliere di scioglierla.',
    'Two units retreating to the same province are both disbanded.':
        'Due unità che si ritirano nella stessa provincia vengono sciolte entrambe.',
    'Builds and disbands (Winter)': 'Costruzioni e scioglimenti (Inverno)',
    'More centers than units: you may <strong>build</strong>, only in your own <em>home</em> centers (★ in the '
    'table below), if you still own them and they are empty. Armies anywhere, fleets on the coast. You may build '
    'fewer than allowed.':
        'Più centri che unità: puoi <strong>costruire</strong>, solo nei centri della tua <em>madrepatria</em> (★ '
        'nella tabella qui sotto), se li possiedi ancora e sono liberi. Armate ovunque, flotte sulla costa. Puoi '
        'costruire meno unità di quante ti spettano.',
    'Fewer centers than units: you must <strong>disband</strong> the difference.':
        'Meno centri che unità: devi <strong>sciogliere</strong> le unità in più.',
    'A center you walked through in Spring but left before the end of Fall is not yours.':
        "Un centro che hai attraversato in Primavera ma lasciato prima della fine dell'Autunno non è tuo.",
    'Using this site': 'Usare il sito',
    '<strong>Game page.</strong> The map, the deadline, your orders and a table of all powers. Negotiate however '
    'you like (in person, chat, phone): the site only collects orders.':
        '<strong>Pagina della partita.</strong> La mappa, la scadenza, i tuoi ordini e una tabella di tutte le '
        'Potenze. Trattate come volete (di persona, in chat, al telefono): il sito raccoglie solo gli ordini.',
    '<strong>Giving orders.</strong> Each of your units has a menu listing every legal order for it; you can also '
    'click (or tap) the unit on the map. Leaving the first entry means the default: hold in movement, disband in '
    'retreats, no build or keep in winter. Each order is saved as soon as you choose it, and your saved orders '
    'appear as arrows on your own map. (Without JavaScript, press <em>Save orders</em> instead.)':
        "<strong>Dare gli ordini.</strong> Ogni tua unità ha un menu con tutti gli ordini validi per lei; puoi anche "
        "cliccare (o toccare) l'unità sulla mappa. Lasciare la prima voce vuol dire il predefinito: “Fermo” nel "
        'movimento, “Scioglimento” nelle ritirate, “Nessuna costruzione” o “Mantieni” in inverno. Ogni ordine è '
        'salvato appena lo scegli, e i tuoi ordini salvati compaiono come frecce sulla tua mappa. (Senza '
        'JavaScript, premi invece <em>Salva gli ordini</em>.)',
    '<strong>Secrecy.</strong> Nobody else sees your orders until the phase is processed. Others only see whether '
    'you have submitted. You can change your orders as often as you like until then.':
        '<strong>Segretezza.</strong> Nessun altro vede i tuoi ordini finché la fase non è risolta. Gli altri vedono '
        'solo se li hai dati. Fino ad allora puoi cambiarli quante volte vuoi.',
    '<strong>"I\'m done".</strong> Press it when you have finished: you are then <em>ready</em>, and as soon as '
    'every player is ready the phase is processed, without waiting for the deadline. Changing an order afterwards '
    'takes it back; <em>I\'m not done</em> keeps your orders saved but makes the game wait for you. (Without '
    'JavaScript: tick the <em>I\'m done</em> box before saving.)':
        '<strong>“Ho finito”.</strong> Premilo quando hai finito: risulti allora <em>pronto</em>, e appena tutti i '
        'giocatori sono pronti la fase viene risolta, senza aspettare la scadenza. Se poi cambi un ordine non sei '
        'più pronto; <em>Non ho finito</em> tiene salvati i tuoi ordini ma fa aspettare la partita. (Senza '
        'JavaScript: spunta la casella <em>Ho finito</em> prima di salvare.)',
    '<strong>Deadline.</strong> When it passes, the phase is processed with whatever was saved, within a few '
    'minutes (or as soon as anyone opens a page). Standard lengths are %(movement)s hours for movement and '
    '%(other)s for retreats and adjustments; the admin can change them.':
        '<strong>Scadenza.</strong> Quando passa, la fase viene risolta con quello che è stato salvato, entro pochi '
        'minuti (o appena qualcuno apre una pagina). Le durate standard sono %(movement)s ore per il movimento e '
        "%(other)s per ritirate e aggiustamenti; l'admin può cambiarle.",
    '<strong>If you miss it:</strong> your units hold; dislodged units are disbanded; builds are lost; if you had '
    'to disband, the engine chooses which units.':
        '<strong>Se la manchi:</strong> le tue unità stanno ferme; le unità sloggiate vengono sciolte; le '
        'costruzioni vanno perse; se dovevi sciogliere delle unità, il motore sceglie quali.',
    '<strong>Powers without a player</strong> never give orders: their units hold, and nobody waits for them. With '
    'fewer than seven players the admin starts the game for 3-7 (or 2) players as in the rulebook\'s "Alternate '
    'way to play": neutral powers hold and never support, and one user may control several countries, all in the '
    'same orders form.':
        '<strong>Le Potenze senza giocatore</strong> non danno mai ordini: le loro unità stanno ferme, e nessuno le '
        "aspetta. Con meno di sette giocatori l'admin avvia la partita per 3-7 (o 2) giocatori come nel regolamento "
        '(“Per giocare con meno di sette persone”): le Potenze neutrali stanno ferme e non appoggiano mai, e un '
        'utente può controllare più Potenze, tutte nello stesso modulo di ordini.',
    '<strong>Notifications.</strong> On the <em>Notifications</em> page you can get a notification on your phone '
    'when a new phase needs your orders, and a reminder before the deadline if you are not done yet. On iPhone, add '
    'the site to your home screen first (Safari: <em>Share → Add to Home Screen</em>) and enable them from there.':
        '<strong>Notifiche.</strong> Nella pagina <em>Notifiche</em> puoi ricevere una notifica sul telefono quando '
        'una nuova fase richiede i tuoi ordini, e un promemoria prima della scadenza se non hai ancora finito. Su '
        'iPhone aggiungi prima il sito alla schermata Home (Safari: <em>Condividi → Aggiungi alla schermata '
        'Home</em>) e attivale da lì.',
    "<strong>History</strong> shows every past phase: the map with everybody's orders, and the results.":
        'Lo <strong>Storico</strong> mostra ogni fase passata: la mappa con gli ordini di tutti, e i risultati.',
    'Status in the powers table': 'Stato nella tabella delle Potenze',
    'Has not saved orders in this phase.': 'Non ha ancora salvato ordini in questa fase.',
    'Saved orders, but the game waits for them until the deadline.':
        'Ha salvato degli ordini, ma la partita lo aspetta fino alla scadenza.',
    'Saved orders and pressed "I\'m done".': 'Ha salvato gli ordini e premuto “Ho finito”.',
    'No unit to order in this phase (common in retreats and winter).':
        'Nessuna unità a cui dare ordini in questa fase (capita spesso nelle ritirate e in inverno).',
    'Nobody plays this power.': 'Nessuno gioca questa Potenza.',
    'Provinces on our map': 'Le province sulla nostra mappa',
    '● supply center &nbsp; ★ home supply center (the owner can build there)':
        '● centro di approvvigionamento &nbsp; ★ centro della madrepatria (il proprietario può costruirvi)',
    'Inland': 'Province interne',
    'Coastal': 'Province costiere',
    'Sea': 'Zone di mare',
    'A standoff (bounce)': 'Uno stallo',
    'Germany and Russia both order an army into Silesia. The forces are equal, one against one, so nobody moves and '
    'Silesia stays empty.':
        "Germania e Russia ordinano entrambe a un'armata di entrare in Slesia. Le forze sono pari, uno contro uno, "
        'quindi nessuno si sposta e la Slesia resta vuota.',
    'A supported attack': 'Un attacco con appoggio',
    'The French army in Marseilles attacks Burgundy with the support of the army in Gascony: two against one. The '
    'German army is dislodged and will have to retreat.':
        "L'armata francese di Marsiglia attacca la Borgogna con l'appoggio dell'armata in Guascogna: due contro uno. "
        "L'armata tedesca è sloggiata e dovrà ritirarsi.",
    'Cutting a support': 'Neutralizzare un appoggio',
    'Germany attacks Warsaw from Prussia with support from Silesia. But Russia attacks Silesia from Bohemia: that '
    'attack fails, yet it is enough to cut the support. The attack on Warsaw is now one against one and bounces.':
        "La Germania attacca Varsavia dalla Prussia con l'appoggio dell'armata in Slesia. Ma la Russia attacca la "
        "Slesia dalla Boemia: quell'attacco fallisce, ma basta a neutralizzare l'appoggio. L'attacco a Varsavia ora è "
        'uno contro uno e finisce in stallo.',
    'Supporting a unit that stays': "Appoggiare un'unità ferma",
    'France attacks the Tyrrhenian Sea with support (two), but the Italian fleet there is supported in place by the '
    'fleet in Rome (two). Equal forces: the attack bounces.':
        'La Francia attacca il Mar Tirreno con un appoggio (due), ma la flotta italiana che vi si trova è appoggiata '
        "sul posto dalla flotta di Roma (due). Forze pari: l'attacco finisce in stallo.",
    'A convoy': 'Un trasporto via mare',
    'The English fleet in the North Sea carries the army from London to Norway in a single turn. Both orders are '
    'needed: the army moves, the fleet convoys.':
        "La flotta inglese nel Mare del Nord trasporta l'armata da Londra in Norvegia in un solo turno. Servono "
        "entrambi gli ordini: l'armata si sposta, la flotta la trasporta.",
    'support given': 'appoggio dato',
    'convoy made': 'trasporto fatto',
    'holds': 'resta ferma',
    'succeeds': 'riesce',
    'Messages (%(count)d)': 'Messaggi (%(count)d)',
    'Everyone': 'Tutti',
    'You cannot send messages like that.': 'Non puoi inviare messaggi in questo modo.',
    'The message must have between 1 and %(max)d characters.':
        'Il messaggio deve avere da 1 a %(max)d caratteri.',
    'To everyone.': 'A tutti.',
    'To %(power)s.': 'A %(power)s.',
    'Message from %(power)s': 'Messaggio da %(power)s',
    'You do not play a power in this game, so you have no messages.':
        'Non giochi nessuna potenza in questa partita, quindi non hai messaggi.',
    'Messages of:': 'Messaggi di:',
    'Messages are private: only you and the other player can read them, except those to everyone. Reload the page to see new ones.':
        "I messaggi sono privati: solo tu e l'altro giocatore potete leggerli, tranne quelli a tutti. Ricarica la pagina per vedere i nuovi.",
    'Conversation': 'Conversazione',
    'Unread': 'Da leggere',
    'Last message': 'Ultimo messaggio',
    'All conversations': 'Tutte le conversazioni',
    'No messages yet.': 'Ancora nessun messaggio.',
    'Your message to %(to)s:': 'Il tuo messaggio per %(to)s:',
    'Send': 'Invia',
}
