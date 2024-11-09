from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import or_
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# Configuration CORS pour accepter les requêtes de www.immo-rama.ch
CORS(app, resources={
    r"/api/*": {
        "origins": os.getenv('CORS_ORIGINS', 'https://www.immo-rama.ch').split(','),
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Configuration
is_vercel = os.environ.get('VERCEL', False)
if is_vercel:
    # Configuration pour Vercel
    db_path = '/tmp/real_estate.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
else:
    # Configuration locale
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'real_estate.db'))
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{db_path}')
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(db_path), 'uploads'))

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

db = SQLAlchemy(app)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    preferences = db.Column(db.String(200))
    budget = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    interactions = db.relationship('Interaction', backref='client', lazy=True)
    visits = db.relationship('Visit', backref='client', lazy=True)
    offers = db.relationship('Offer', backref='client', lazy=True)
    documents = db.relationship('Document', backref='client', lazy=True)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(200))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)

class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200))
    description = db.Column(db.Text)
    property_type = db.Column(db.String(50))
    rooms = db.Column(db.Integer)
    surface = db.Column(db.Float)
    status = db.Column(db.String(50), default='Disponible')
    link = db.Column(db.String(300))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    visits = db.relationship('Visit', backref='announcement', lazy=True)

class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcement.id'))
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='Planifiée')
    notes = db.Column(db.Text)
    feedback = db.Column(db.Text)

class Offer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcement.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='En attente')
    date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# API Routes pour l'intégration Wix
@app.route('/api/wix-form-submission', methods=['POST'])
def wix_form_submission():
    try:
        data = request.json
        
        # Extraction des données du formulaire Wix
        name = data.get('name', '')
        contact = data.get('contact', '')
        preferences = data.get('preferences', '')
        budget = data.get('budget', 0)
        
        # Validation des données requises
        if not name or not contact:
            return jsonify({
                'success': False,
                'error': 'Les champs nom et contact sont obligatoires'
            }), 400
        
        # Création du nouveau client
        new_client = Client(
            name=name,
            contact=contact,
            preferences=preferences,
            budget=float(budget) if budget else 0.0
        )
        db.session.add(new_client)
        db.session.commit()
        
        # Création d'une interaction
        interaction = Interaction(
            client_id=new_client.id,
            details=f"Client créé depuis le formulaire www.immo-rama.ch/formulaire\nPréférences: {preferences}\nBudget: CHF {budget}"
        )
        db.session.add(interaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Client créé avec succès',
            'client_id': new_client.id
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/')
def index():
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    sort_by = request.args.get('sort', 'date')

    clients_query = Client.query
    if search_query:
        clients_query = clients_query.filter(
            or_(
                Client.name.ilike(f'%{search_query}%'),
                Client.contact.ilike(f'%{search_query}%')
            )
        )
    clients = clients_query.all()

    announcements_query = Announcement.query
    if search_query:
        announcements_query = announcements_query.filter(
            or_(
                Announcement.title.ilike(f'%{search_query}%'),
                Announcement.address.ilike(f'%{search_query}%')
            )
        )
    if status_filter:
        announcements_query = announcements_query.filter(Announcement.status == status_filter)

    if sort_by == 'price_asc':
        announcements_query = announcements_query.order_by(Announcement.price.asc())
    elif sort_by == 'price_desc':
        announcements_query = announcements_query.order_by(Announcement.price.desc())
    else:
        announcements_query = announcements_query.order_by(Announcement.date_added.desc())

    announcements = announcements_query.all()

    stats = {
        'total_clients': Client.query.count(),
        'total_announcements': Announcement.query.count(),
        'active_visits': Visit.query.filter(Visit.status == 'Planifiée').count(),
        'pending_offers': Offer.query.filter(Offer.status == 'En attente').count()
    }

    return render_template('index.html', 
                         clients=clients, 
                         announcements=announcements,
                         stats=stats,
                         search_query=search_query,
                         status_filter=status_filter,
                         sort_by=sort_by)

@app.route('/add_client', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        preferences = request.form['preferences']
        budget = request.form.get('budget', 0.0)

        if not name or not contact:
            flash('Les informations du client doivent être complètes.')
            return redirect(url_for('add_client'))

        new_client = Client(
            name=name,
            contact=contact,
            preferences=preferences,
            budget=float(budget) if budget else 0.0
        )
        db.session.add(new_client)
        db.session.commit()

        # Gérer les documents uploadés
        if 'documents' in request.files:
            files = request.files.getlist('documents')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    
                    new_doc = Document(
                        filename=unique_filename,
                        original_filename=filename,
                        file_type=filename.rsplit('.', 1)[1].lower(),
                        description=request.form.get('doc_description', ''),
                        client_id=new_client.id
                    )
                    db.session.add(new_doc)
                    db.session.commit()

        flash('Client ajouté avec succès')
        return redirect(url_for('index'))

    return render_template('add_client.html')

@app.route('/client/<int:id>')
def client_detail(id):
    client = Client.query.get_or_404(id)
    client_visits = Visit.query.filter_by(client_id=id).order_by(Visit.date.desc()).all()
    client_offers = Offer.query.filter_by(client_id=id).order_by(Offer.date.desc()).all()
    return render_template('client_detail.html', 
                         client=client, 
                         visits=client_visits,
                         offers=client_offers)

@app.route('/add_document/<int:client_id>', methods=['POST'])
def add_document(client_id):
    client = Client.query.get_or_404(client_id)
    
    if 'document' not in request.files:
        flash('Aucun fichier sélectionné')
        return redirect(url_for('client_detail', id=client_id))
    
    file = request.files['document']
    if file.filename == '':
        flash('Aucun fichier sélectionné')
        return redirect(url_for('client_detail', id=client_id))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        new_doc = Document(
            filename=unique_filename,
            original_filename=filename,
            file_type=filename.rsplit('.', 1)[1].lower(),
            description=request.form.get('description', ''),
            client_id=client_id
        )
        db.session.add(new_doc)
        db.session.commit()
        flash('Document ajouté avec succès')
    else:
        flash('Type de fichier non autorisé')
    
    return redirect(url_for('client_detail', id=client_id))

@app.route('/download_document/<int:doc_id>')
def download_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filename)
    return send_file(file_path, 
                    download_name=document.original_filename,
                    as_attachment=True)

@app.route('/delete_document/<int:doc_id>', methods=['POST'])
def delete_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    client_id = document.client_id
    
    # Supprimer le fichier physique
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Supprimer l'entrée de la base de données
    db.session.delete(document)
    db.session.commit()
    
    flash('Document supprimé avec succès')
    return redirect(url_for('client_detail', id=client_id))

@app.route('/add_announcement', methods=['GET', 'POST'])
def add_announcement():
    if request.method == 'POST':
        new_announcement = Announcement(
            title=request.form['title'],
            price=float(request.form['price']),
            address=request.form['address'],
            description=request.form.get('description', ''),
            property_type=request.form.get('property_type', ''),
            rooms=int(request.form.get('rooms', 0)),
            surface=float(request.form.get('surface', 0)),
            status='Disponible',
            link=request.form.get('link', '')
        )
        db.session.add(new_announcement)
        db.session.commit()
        flash('Annonce ajoutée avec succès')
        return redirect(url_for('index'))

    return render_template('add_announcement.html')

@app.route('/add_visit', methods=['GET', 'POST'])
def add_visit():
    if request.method == 'POST':
        client_id = request.form['client_id']
        announcement_id = request.form['announcement_id']
        date = request.form['date']
        notes = request.form['notes']

        new_visit = Visit(
            client_id=client_id,
            announcement_id=announcement_id,
            date=datetime.strptime(date, '%Y-%m-%dT%H:%M'),
            notes=notes,
            status='Planifiée'
        )
        db.session.add(new_visit)
        db.session.commit()
        flash('Visite programmée avec succès')
        return redirect(url_for('index'))

    clients = Client.query.all()
    announcements = Announcement.query.filter_by(status='Disponible').all()
    return render_template('add_visit.html', clients=clients, announcements=announcements)

@app.route('/update_visit_status/<int:id>', methods=['POST'])
def update_visit_status(id):
    visit = Visit.query.get_or_404(id)
    status = request.form.get('status')
    feedback = request.form.get('feedback', '')
    
    if status in ['Planifiée', 'Effectuée', 'Annulée']:
        visit.status = status
        visit.feedback = feedback
        db.session.commit()
        flash('Statut de la visite mis à jour')
    
    return redirect(url_for('client_detail', id=visit.client_id))

@app.route('/add_offer/<int:announcement_id>', methods=['POST'])
def add_offer(announcement_id):
    client_id = request.form['client_id']
    amount = request.form['amount']
    notes = request.form.get('notes', '')

    new_offer = Offer(
        client_id=client_id,
        announcement_id=announcement_id,
        amount=float(amount),
        notes=notes
    )
    db.session.add(new_offer)
    db.session.commit()
    flash('Offre ajoutée avec succès')
    return redirect(url_for('client_detail', id=client_id))

@app.route('/update_offer_status/<int:id>', methods=['POST'])
def update_offer_status(id):
    offer = Offer.query.get_or_404(id)
    status = request.form.get('status')
    
    if status in ['En attente', 'Acceptée', 'Refusée']:
        offer.status = status
        if status == 'Acceptée':
            announcement = Announcement.query.get(offer.announcement_id)
            announcement.status = 'Réservé'
        db.session.commit()
        flash('Statut de l\'offre mis à jour')
    
    return redirect(url_for('client_detail', id=offer.client_id))

# Point d'entrée pour Vercel
@app.route('/_vercel/deploy-complete', methods=['POST'])
def deploy_complete():
    # Créer la base de données si elle n'existe pas
    with app.app_context():
        db.create_all()
    return 'OK', 200

if __name__ == '__main__':
    # S'assurer que les répertoires nécessaires existent
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    with app.app_context():
        # Créer une nouvelle base de données avec le schéma à jour
        db.create_all()
        
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5001)), debug=False)