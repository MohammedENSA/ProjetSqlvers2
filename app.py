from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
import os
from datetime import datetime, timedelta 
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration de la base de données
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Mohammed@2024//sql',
    'database': 'bibliotheque'
}

def get_db_connection():
    return pymysql.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database'],
        cursorclass=pymysql.cursors.DictCursor
    )

def is_admin():
    return 'admin' in session and session['admin'] == True

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form.get('email')       
        password = request.form.get('password')
        
        conn = get_db_connection() 
        cursor = conn.cursor()   
        
        query = "SELECT * FROM bibliothecaire WHERE email_bibliothecaire = %s AND mdpbibliothecaire = %s AND niveau_hierarchique='bibliothécaire principal'"
        cursor.execute(query, (email, password))
        admin = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if admin:
            session['admin'] = True
            session['admin_id'] = admin['id_bibliothecaire']
            session['admin_name'] = f"{admin['nom_bibliothecaire']} {admin['prenom_bibliothecaire']}"
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou mot de passe incorrect')
            return redirect(url_for('index'))
            
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if not is_admin():
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Statistiques générales sur les documents #compter le nombre de documents, le nombre de livres et le nombre de périodiques
    cursor.execute("""
        SELECT   
            CAST(COUNT(*) AS UNSIGNED) as total_documents,
            CAST(SUM(CASE WHEN type_document = 'livre' THEN 1 ELSE 0 END) AS UNSIGNED) as total_livres,
            CAST(SUM(CASE WHEN type_document = 'periodique' THEN 1 ELSE 0 END) AS UNSIGNED) as total_periodiques
        FROM document
    """)
    result = cursor.fetchone()
    doc_stats = {
        'total_documents': int(result['total_documents']) if result['total_documents'] is not None else 0,
        'total_livres': int(result['total_livres']) if result['total_livres'] is not None else 0,
        'total_periodiques': int(result['total_periodiques']) if result['total_periodiques'] is not None else 0
    }
    
    # 2. Statistiques sur les exemplaires
    cursor.execute("""
        SELECT 
            CAST(COUNT(*) AS UNSIGNED) as total_exemplaires,
            CAST(SUM(CASE WHEN statut_exemplaire = 'en prêt' THEN 1 ELSE 0 END) AS UNSIGNED) as exemplaires_pretes,
            CAST(SUM(CASE WHEN statut_exemplaire = 'en rayon' THEN 1 ELSE 0 END) AS UNSIGNED) as exemplaires_disponibles,
            CAST(SUM(CASE WHEN statut_exemplaire = 'endommagé' THEN 1 ELSE 0 END) AS UNSIGNED) as exemplaires_endommages
        FROM exemplaire
    """)
    result = cursor.fetchone()
    exemplaire_stats = {
        'total_exemplaires': int(result['total_exemplaires']) if result['total_exemplaires'] is not None else 0,
        'exemplaires_pretes': int(result['exemplaires_pretes']) if result['exemplaires_pretes'] is not None else 0,
        'exemplaires_disponibles': int(result['exemplaires_disponibles']) if result['exemplaires_disponibles'] is not None else 0,
        'exemplaires_endommages': int(result['exemplaires_endommages']) if result['exemplaires_endommages'] is not None else 0
    }
    
    # 3. Statistiques sur les emprunts actifs
    cursor.execute("""
        SELECT 
            CAST(COUNT(*) AS UNSIGNED) as emprunts_actifs,
            CAST(SUM(CASE WHEN statut_emprunt = 'en retard' THEN 1 ELSE 0 END) AS UNSIGNED) as emprunts_retard
        FROM emprunt
        WHERE statut_emprunt IN ('en cours', 'en retard')
    """)
    result = cursor.fetchone()
    emprunt_stats = {
        'emprunts_actifs': int(result['emprunts_actifs']) if result['emprunts_actifs'] is not None else 0,
        'emprunts_retard': int(result['emprunts_retard']) if result['emprunts_retard'] is not None else 0
    }
    
    # 4. Statistiques sur les utilisateurs
    cursor.execute("""
        SELECT 
            CAST(COUNT(*) AS UNSIGNED) as total_utilisateurs,
            CAST(SUM(CASE WHEN categorie = 'occasionnel' THEN 1 ELSE 0 END) AS UNSIGNED) as utilisateurs_occasionnels,
            CAST(SUM(CASE WHEN categorie = 'abonné' THEN 1 ELSE 0 END) AS UNSIGNED) as utilisateurs_abonnes,
            CAST(SUM(CASE WHEN categorie = 'abonné privilégié' THEN 1 ELSE 0 END) AS UNSIGNED) as utilisateurs_privilegies
        FROM utilisateur
    """)
    result = cursor.fetchone()
    user_stats = {
        'total_utilisateurs': int(result['total_utilisateurs']) if result['total_utilisateurs'] is not None else 0,
        'utilisateurs_occasionnels': int(result['utilisateurs_occasionnels']) if result['utilisateurs_occasionnels'] is not None else 0,
        'utilisateurs_abonnes': int(result['utilisateurs_abonnes']) if result['utilisateurs_abonnes'] is not None else 0,
        'utilisateurs_privilegies': int(result['utilisateurs_privilegies']) if result['utilisateurs_privilegies'] is not None else 0
    }
    
    # 5. Top 5 des livres les plus empruntés
    cursor.execute("""
        SELECT 
            d.titre,
            CAST(COUNT(e.id_emprunt) AS UNSIGNED) as nombre_emprunts
        FROM document d
        JOIN exemplaire ex ON d.id_document = ex.id_document
        JOIN emprunt e ON ex.id_exemplaire = e.id_exemplaire
        GROUP BY d.id_document, d.titre
        ORDER BY nombre_emprunts DESC
        LIMIT 5
    """)
    top_livres = [{'titre': row[0], 'nombre_emprunts': int(row[1])} for row in cursor.fetchall()]
    
    # 6. Statistiques des amendes
    cursor.execute("""
        SELECT 
            CAST(COUNT(*) AS UNSIGNED) as total_amendes,
            CAST(SUM(CASE WHEN statut_paiement = 'en attente' THEN 1 ELSE 0 END) AS UNSIGNED) as amendes_impayees,
            CAST(SUM(montant) AS DECIMAL(10,2)) as montant_total,
            CAST(SUM(CASE WHEN statut_paiement = 'en attente' THEN montant ELSE 0 END) AS DECIMAL(10,2)) as montant_impaye
        FROM amende
    """)
    result = cursor.fetchone()
    amende_stats = {
        'total_amendes': int(result['total_amendes']) if result['total_amendes'] is not None else 0,
        'amendes_impayees': int(result['amendes_impayees']) if result['amendes_impayees'] is not None else 0,
        'montant_total': float(result['montant_total']) if result['montant_total'] is not None else 0.0,
        'montant_impaye': float(result['montant_impaye']) if result['montant_impaye'] is not None else 0.0
    }
    
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html',
                         admin_name=session.get('admin_name'),
                         doc_stats=doc_stats,
                         exemplaire_stats=exemplaire_stats,
                         emprunt_stats=emprunt_stats,
                         user_stats=user_stats,
                         top_livres=top_livres,
                         amende_stats=amende_stats)
    
    
@app.route('/documents', methods=['GET', 'POST'])
def manage_documents():
    if not is_admin():
        return redirect(url_for('index'))
        
    conn = get_db_connection()   
    cursor = conn.cursor()

    # Traiter d'abord les requêtes POST
    if request.method == 'POST':
        action = request.form.get('action')
        
        try:
            if action == 'add_document':
                titre = request.form.get('titredoc')
                annee = request.form.get('annerpub')
                editeur = request.form.get('editeur')
                reference = request.form.get('referenceunique')
                type_doc = request.form.get('type_document')
                id_fonds = request.form.get('idfond')
                nbr_exemplaire = request.form.get('nbrexemplaire')
                
                cursor.execute("""
                    INSERT INTO document (titre, annee_publication, editeur, reference_unique, 
                                        type_document, id_fonds, nombre_exemplaires)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (titre, annee, editeur, reference, type_doc, id_fonds, nbr_exemplaire))
                
                conn.commit()
                flash('Document ajouté avec succès', 'success')
                
            elif action == 'edit_document':
                doc_id = request.form.get('id_document')
                titre = request.form.get('titre')
                annee = request.form.get('annee_publication')
                editeur = request.form.get('editeur')
                type_document = request.form.get('type_document')
                nbrexemplaire = request.form.get('nbrexemplaire')
                idfond = request.form.get('idfond')
                referenceunique = request.form.get('referenceunique')
                
                cursor.execute("""
                    UPDATE document 
                    SET titre = %s, 
                        annee_publication = %s,
                        editeur = %s,
                        type_document = %s,
                        nombre_exemplaires = %s,
                        id_fonds = %s,
                        reference_unique = %s
                    WHERE id_document = %s
                """, (titre, annee, editeur, type_document, nbrexemplaire, 
                      idfond, referenceunique, doc_id))
                
                conn.commit()
                flash('Document modifié avec succès', 'success')
                
            elif action == 'delete_document':
                doc_id = request.form.get('id_document')
                cursor.execute("DELETE FROM document WHERE id_document = %s", (doc_id,))
                conn.commit()
                flash('Document supprimé avec succès', 'success')
                
        except Exception as e:
            conn.rollback()
            flash(f'Erreur lors de l\'opération: {str(e)}', 'error')
    
    # Traiter ensuite les recherches (GET)
    documents = []
    try:
        search_type = request.args.get('search_type')
        search_query = request.args.get('search_query')
        type_document_query = request.args.get('type_document_query')
        
        if search_type:
            if search_type == 'type_document':
                cursor.execute("""
                    SELECT * FROM document 
                    WHERE type_document = %s
                """, (type_document_query,))
                
            elif search_type in ['date_creation', 'date_modification']:
                cursor.execute(f"""
                    SELECT * FROM document 
                    WHERE DATE({search_type}) = DATE(%s)
                """, (search_query,))
                
            elif search_type in ['id_fonds', 'nombre_exemplaires']:
                cursor.execute(f"""
                    SELECT * FROM document 
                    WHERE {search_type} = %s
                """, (search_query,))
                
            elif search_type == 'annee_publication':
                cursor.execute("""
                    SELECT * FROM document 
                    WHERE annee_publication = %s
                """, (search_query,))
                
            else:
                cursor.execute(f"""
                    SELECT * FROM document 
                    WHERE {search_type} LIKE %s
                """, (f'%{search_query}%',))
        else:
            # Si pas de recherche, récupérer tous les documents avec leurs détails
            cursor.execute("""
                SELECT d.*, l.isbn, p.issn, p.volume, p.numero 
                FROM document d
                LEFT JOIN livre l ON d.id_document = l.id_document
                LEFT JOIN periodique p ON d.id_document = p.id_document
            """)
        
        documents = cursor.fetchall()
        
    except Exception as e:
        flash(f'Erreur lors de la recherche: {str(e)}', 'error')
        
    finally:
        cursor.close()
        conn.close()
    
    return render_template('documents.html', documents=documents)
@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    if not is_admin():
        return redirect(url_for('index'))
        
    conn = get_db_connection()   
    cursor = conn.cursor()

    # Traitement des requêtes POST en premier
    if request.method == 'POST':
        action = request.form.get('action')
        
        try:
            if action == 'add_user':
                nom = request.form.get('nom_utilisateur')
                prenom = request.form.get('prenom_utilisateur')
                email = request.form.get('email_utilisateur')
                categorie = request.form.get('categorie')
                limite_emprunts = request.form.get('limite_emprunts')
                duree_emprunt_max = request.form.get('duree_emprunt_max')
                Mot_de_passe_user = request.form.get('Mot_de_passe_user')
                
                cursor.execute("""
                    INSERT INTO utilisateur (nom_utilisateur, prenom_utilisateur, email_utilisateur, 
                                          categorie, limite_emprunts, duree_emprunt_max, Mot_de_passe_user)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (nom, prenom, email, categorie, limite_emprunts, duree_emprunt_max, Mot_de_passe_user))
                
                conn.commit()
                flash('Utilisateur ajouté avec succès', 'success')
                
            elif action == 'edit_user':
                user_id = request.form.get('id_utilisateur')
                nom = request.form.get('nom_utilisateur')
                prenom = request.form.get('prenom_utilisateur')
                email = request.form.get('email_utilisateur')
                categorie = request.form.get('categorie')
                limite_emprunts = request.form.get('limite_emprunts')
                duree_emprunt_max = request.form.get('duree_emprunt_max')
                Mot_de_passe_user = request.form.get('Mot_de_passe_user')
                
                cursor.execute("""
                    UPDATE utilisateur 
                    SET nom_utilisateur = %s, prenom_utilisateur = %s, 
                        email_utilisateur = %s, categorie = %s,
                        limite_emprunts = %s, duree_emprunt_max = %s,
                        Mot_de_passe_user = %s
                    WHERE id_utilisateur = %s
                """, (nom, prenom, email, categorie, limite_emprunts, 
                      duree_emprunt_max, Mot_de_passe_user, user_id))
                conn.commit()
                flash('Utilisateur modifié avec succès', 'success')
                
            elif action == 'delete_user':
                user_id = request.form.get('id_utilisateur')
                cursor.execute("DELETE FROM utilisateur WHERE id_utilisateur = %s", (user_id,))
                conn.commit()
                flash('Utilisateur supprimé avec succès', 'success')
                
        except Exception as e:
            conn.rollback()
            flash(f'Erreur lors de l\'opération: {str(e)}', 'error')
            
    # Traitement des recherches (GET)
    search_type = request.args.get('search_type')
    search_query = request.args.get('search_query')
    categorie_query = request.args.get('categorie_query')
    
    try:
        if search_type and (search_query or categorie_query):
            if search_type == 'categorie':
                cursor.execute("""
                    SELECT * FROM utilisateur 
                    WHERE categorie = %s
                """, (categorie_query,))
            else:
                cursor.execute(f"""
                    SELECT * FROM utilisateur 
                    WHERE {search_type}_utilisateur LIKE %s
                """, (f'%{search_query}%',))
        else:
            cursor.execute("SELECT * FROM utilisateur")
            
        users = cursor.fetchall()
        
    except Exception as e:
        flash(f'Erreur lors de la recherche: {str(e)}', 'error')
        users = []
    
    finally:
        cursor.close()
        conn.close()
    
    return render_template('users.html', users=users)
@app.route('/emprunts', methods=['GET', 'POST'])
def manage_emprunts():
    cur = pymysql.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database'],
        cursorclass=pymysql.cursors.DictCursor
    ).cursor()
    




    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            # Récupération des données du formulaire
            id_exemplaire = request.form.get('id_exemplaire')
            id_utilisateur = request.form.get('id_utilisateur')
            duree = int(request.form.get('duree', 30))  # durée par défaut : 30 jours
            
            try:
                # Vérifier si l'exemplaire est disponible
                cur.execute("""
                    SELECT statut_exemplaire 
                    FROM exemplaire 
                    WHERE id_exemplaire = %s
                """, [id_exemplaire])
                exemplaire = cur.fetchone()
                
                if exemplaire and exemplaire[0] == 'en rayon':
                    # Calculer la date de fin
                    date_fin = datetime.now() + timedelta(days=duree)
                    
                    # Créer l'emprunt
                    cur.execute("""
                        INSERT INTO emprunt 
                        (id_exemplaire, id_utilisateur, date_debut, date_fin) 
                        VALUES (%s, %s, NOW(), %s)
                    """, (id_exemplaire, id_utilisateur, date_fin))
                    
                    # Mettre à jour le statut de l'exemplaire
                    cur.execute("""
                        UPDATE exemplaire 
                        SET statut_exemplaire = 'en prêt' 
                        WHERE id_exemplaire = %s
                    """, [id_exemplaire])
                    
                    pymysql.connection.commit()
                    flash('Emprunt créé avec succès!', 'success')
                else:
                    flash('Exemplaire non disponible', 'error')
                    
            except Exception as e:
                flash(f'Erreur lors de la création de l\'emprunt: {str(e)}', 'error')
                
        elif action == 'extend':
            # Prolongation d'un emprunt
            id_emprunt = request.form.get('id_emprunt')
            extension_days = int(request.form.get('extension_days', 15))
            
            try:
                # Vérifier si l'emprunt existe et n'est pas en retard
                cur.execute("""
                    SELECT date_fin, statut_emprunt 
                    FROM emprunt 
                    WHERE id_emprunt = %s
                """, [id_emprunt])
                emprunt = cur.fetchone()
                
                if emprunt and emprunt[1] != 'en retard':
                    nouvelle_date_fin = emprunt[0] + timedelta(days=extension_days)
                    
                    cur.execute("""
                        UPDATE emprunt 
                        SET date_fin = %s 
                        WHERE id_emprunt = %s
                    """, (nouvelle_date_fin, id_emprunt))
                    
                    pymysql.connection.commit()
                    flash('Emprunt prolongé avec succès!', 'success')
                else:
                    flash('Impossible de prolonger cet emprunt', 'error')
                    
            except Exception as e:
                flash(f'Erreur lors de la prolongation: {str(e)}', 'error')
    
    # Récupérer la liste des emprunts pour affichage
    cur.execute("""
        SELECT e.id_emprunt, u.nom_utilisateur, d.titre, 
               e.date_debut, e.date_fin, e.statut_emprunt,
               ex.numero_ordre
        FROM emprunt e
        JOIN utilisateur u ON e.id_utilisateur = u.id_utilisateur
        JOIN exemplaire ex ON e.id_exemplaire = ex.id_exemplaire
        JOIN document d ON ex.id_document = d.id_document
        ORDER BY e.date_debut DESC
    """)
    
    
    emprunts = cur.fetchall()
    
    
    # Récupérer la liste des utilisateurs pour le formulaire
    cur.execute("SELECT id_utilisateur, nom_utilisateur FROM utilisateur")
    utilisateurs = cur.fetchall()
    
    # Récupérer la liste des exemplaires disponibles
    cur.execute("""
        SELECT ex.id_exemplaire, d.titre, ex.numero_ordre 
        FROM exemplaire ex
        JOIN document d ON ex.id_document = d.id_document
        WHERE ex.statut_exemplaire = 'en rayon'
    """)
    exemplaires = cur.fetchall()
    
    return render_template('emprunts.html', 
                         emprunts=emprunts,
                         utilisateurs=utilisateurs,
                         exemplaires=exemplaires)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)