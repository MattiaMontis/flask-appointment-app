# Importazione delle librerie necessarie
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user, login_user, logout_user, UserMixin
from flask_bcrypt import Bcrypt
from flask_session import Session
import os

# Creazione dell'istanza principale dell'app Flask
app = Flask(__name__)

# Configurazione dell'app Flask
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'hard_to_guess_string'  # Chiave segreta per la sicurezza dell'app
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'  # Configurazione del database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disattiva notifiche inutili di modifiche al database
app.config['SESSION_TYPE'] = 'filesystem'  # Specifica che le sessioni saranno salvate nel file system

# Inizializzazione degli strumenti utilizzati
db = SQLAlchemy(app)  # Gestione del database
bcrypt = Bcrypt(app)  # Per hashing sicuro delle password
login_manager = LoginManager(app)  # Gestione delle sessioni degli utenti autenticati
login_manager.login_view = 'login'  # Specifica la pagina di login da mostrare per gli utenti non autenticati
Session(app)  # Abilita Flask-Session per gestire le sessioni lato server

# Modello per gli account utente
class Account(UserMixin, db.Model):  # UserMixin aggiunge metodi standard per la gestione dell'utente
    id = db.Column(db.Integer, primary_key=True)  # ID univoco dell'utente
    username = db.Column(db.String(20), unique=True, nullable=False)  # Nome utente
    email_address = db.Column(db.String(40), unique=True, nullable=False)  # Indirizzo email
    hashed_password = db.Column(db.String(128), nullable=False)  # Password hashata

    def __repr__(self):  # Metodo per rappresentare l'oggetto come stringa
        return f"Account({self.username})"

# Modello per le prenotazioni
class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID univoco della prenotazione
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)  # ID dell'utente che ha fatto la prenotazione
    reservation_date = db.Column(db.String(10), nullable=False)  # Data della prenotazione
    reservation_time = db.Column(db.String(5), nullable=False)  # Ora della prenotazione
    details = db.Column(db.String(100), nullable=False)  # Dettagli aggiuntivi

    def __repr__(self):  # Metodo per rappresentare l'oggetto come stringa
        return f"Reservation({self.reservation_date} {self.reservation_time} {self.details})"

# Funzione di callback per caricare un utente in base al suo ID
@login_manager.user_loader
def load_user(user_id):
    return Account.query.get(int(user_id))

# Rotta per la homepage
@app.route('/')
@app.route('/home')
def home():
    nome = "Mattia Montis Project"  # Titolo per la homepage
    return render_template('index.html', nome=nome)

# Rotta per la pagina "Chi siamo"
@app.route('/about')
def about():
    return render_template('about.html')

# Rotta per la pagina dei contatti
@app.route('/contact')
def contact():
    return render_template('contact.html')

# Funzione per validare gli orari di prenotazione
def is_valid_time(time):
    valid_times = [
        "9:00", "9:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
        "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"
    ]  # Elenco degli orari validi
    return time in valid_times

# Rotta per effettuare una prenotazione
@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    if request.method == 'POST':  # Gestione del form di prenotazione
        date = request.form['date']
        time = request.form['time']
        details = request.form['details']

        if not is_valid_time(time):  # Controllo orario valido
            flash('Orario non valido. Seleziona un orario disponibile.')
            return redirect(url_for('book'))

        # Controllo se l'orario è già prenotato
        existing_reservation = Reservation.query.filter_by(reservation_date=date, reservation_time=time).first()
        if existing_reservation:
            flash('Orario già prenotato. Scegli un altro orario.')
            return redirect(url_for('book'))

        # Creazione della prenotazione
        new_reservation = Reservation(account_id=current_user.id, reservation_date=date, reservation_time=time, details=details)
        db.session.add(new_reservation)
        db.session.commit()
        flash('Prenotazione effettuata con successo.')
        return redirect(url_for('book'))
    
    # Mostra tutte le prenotazioni dell'utente
    reservations = Reservation.query.filter_by(account_id=current_user.id).all()
    return render_template('book.html', reservations=reservations)

# Rotta per modificare una prenotazione
@app.route('/modify/<int:reservation_id>', methods=['GET', 'POST'])
@login_required
def modify(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)  # Recupera la prenotazione o restituisce un errore 404
    if request.method == 'POST':
        reservation.reservation_date = request.form['date']
        reservation.reservation_time = request.form['time']
        reservation.details = request.form['details']
        db.session.commit()
        flash('Prenotazione modificata con successo.')
        return redirect(url_for('book'))
    return render_template('modify.html', reservation=reservation)

# Rotta per cancellare una prenotazione
@app.route('/remove/<int:reservation_id>')
@login_required
def remove(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    db.session.delete(reservation)
    db.session.commit()
    flash('Prenotazione cancellata con successo.')
    return redirect(url_for('book'))

# Rotta per il login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Account.query.filter_by(username=username).first()
        if not user or not bcrypt.check_password_hash(user.hashed_password, password):
            flash('Username o password non validi.')
            return redirect(url_for('login'))
        
        login_user(user)  # Autentica l'utente
        flash('Login effettuato con successo.')
        return redirect(url_for('book'))
    return render_template('login.html')

# Rotta per il logout
@app.route('/logout')
@login_required
def logout():
    logout_user()  # Disconnette l'utente
    flash('Logout effettuato con successo.')
    return redirect(url_for('home'))

# Rotta per la registrazione
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Verifica se username o email sono già utilizzati
        existing_user = Account.query.filter((Account.username == username) | (Account.email_address == email)).first()
        if existing_user:
            flash('Username o email già esistenti.')
            return redirect(url_for('register'))
        
        if password == confirm_password:  # Controllo che le password coincidano
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')  # Hashing della password
            new_user = Account(username=username, email_address=email, hashed_password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registrazione completata con successo. Effettua il login.')
            return redirect(url_for('login'))
        else:
            flash('Le password non corrispondono.')
    return render_template('register.html')

# Punto di ingresso dell'app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)  
