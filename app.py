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

# Fonction pour établir la connexion à la base de données
def get_db_connection():
    return pymysql.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database'],
        cursorclass=pymysql.cursors.DictCursor  # Pour obtenir les résultats sous forme de dictionnaires
    )



@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form.get('email')       
        password = request.form.get('password')
        
        conn = get_db_connection() 
        cursor = conn.cursor()   
        
        # Vérifier si l'administrateur existe avec cet email et mot de passe
        query = "SELECT * FROM bibliothecaire WHERE email_bibliothecaire = %s AND mdpbibliothecaire = %s AND niveau_hierarchique='bibliothécaire principal'"
        cursor.execute(query, (email, password))
        admin = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if admin:
            # Si l'administrateur existe, rediriger vers la page de gestion admin
            return redirect(url_for('gestionadmin'))
        else:
            # Si non, afficher un message d'erreur
            flash('Email ou mot de passe incorrect')
            return redirect(url_for('index'))
            
    return render_template('index.html')
@app.route('/gestionadmin', methods=['GET', 'POST'])
def gestionadmin():
    conn = get_db_connection()   #Une connexion à la base de données est créée
    cursor = conn.cursor()       #Un curseur est créé pour exécuter des commandes SQL.
    
    
    search_type = request.args.get('search_type')
    search_query = request.args.get('search_query')
    type_document_query = request.args.get('type_document_query')
    
    if search_type:
        try:
            if search_type == 'type_document':
                query = """
                    SELECT * FROM document 
                    WHERE type_document = %s
                """
                cursor.execute(query, (type_document_query,))
            
            elif search_type in ['date_creation', 'date_modification']:
                query = f"""
                    SELECT * FROM document 
                    WHERE DATE({search_type}) = DATE(%s)
                """
                cursor.execute(query, (search_query,))
            
            elif search_type in ['id_fonds', 'nombre_exemplaires']:
                query = f"""
                    SELECT * FROM document 
                    WHERE {search_type} = %s
                """
                cursor.execute(query, (search_query,))
            
            elif search_type == 'annee_publication':
                query = """
                    SELECT * FROM document 
                    WHERE annee_publication = %s
                """
                cursor.execute(query, (search_query,))
            
            else:
                query = f"""
                    SELECT * FROM document 
                    WHERE {search_type} LIKE %s
                """
                cursor.execute(query, (f'%{search_query}%',))
            
            documents = cursor.fetchall()
            return render_template('gestionadmin.html', documents=documents)
            
        except Exception as e:
            flash(f'Erreur lors de la recherche: {str(e)}', 'error')
            return redirect(url_for('gestionadmin'))
    
    # Si pas de recherche, afficher tous les documents
    cursor.execute("SELECT * FROM document")
    documents = cursor.fetchall()
    return render_template('gestionadmin.html', documents=documents)
    
    
    # Gestion des documents
    if request.method == 'POST':        #Gestion des actions via POST
        action = request.form.get('action')   #On récupère les données du formulaire avec request.form.get.
    
        # Ajouter un document
        if action == 'add_document':
            titre = request.form.get('titredoc')
            annee = request.form.get('annerpub')
            editeur = request.form.get('editeur')
            reference = request.form.get('referenceunique')
            type_doc = request.form.get('type_document')
            id_fonds = request.form.get('idfond')
            nbr_exemplaire = request.form.get('nbrexemplaire')
            
            try:
                cursor.execute("""
                    INSERT INTO document (titre, annee_publication, editeur, reference_unique, type_document, id_fonds,nombre_exemplaires)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (titre, annee, editeur, reference, type_doc, id_fonds,nbr_exemplaire))
                
                conn.commit()
                flash('Document ajouté avec succès', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Erreur lors de l\'ajout du document: {str(e)}', 'error')
        
        # Modifier un document
        elif action == 'edit_document':
            doc_id = request.form.get('id_document')
            titre = request.form.get('titre')
            annee = request.form.get('annee_publication')
            editeur = request.form.get('editeur')
            type_document = request.form.get('type_document')
            nbrexemplaire = request.form.get('nbrexemplaire')
            idfond = request.form.get('idfond')
            referenceunique = request.form.get('referenceunique')
    
            try:
                    
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
            except Exception as e:
                    conn.rollback()
                    flash(f'Erreur lors de la modification: {str(e)}', 'error')
                    
                    
                    # Supprimer un document
        elif action == 'delete_document':
            doc_id = request.form.get('id_document')
            try:
                cursor.execute("DELETE FROM document WHERE id_document = %s", (doc_id,))
                conn.commit()
                flash('Document supprimé avec succès', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Erreur lors de la suppression: {str(e)}', 'error')
                
                
                
                                        #gestion des utilisateurs
          
                                      
        
         # Ajouter un utilisateur
        elif action == 'add_user':
            nom = request.form.get('nom_utilisateur')
            prenom = request.form.get('prenom_utilisateur')
            email = request.form.get('email_utilisateur')
            categorie = request.form.get('categorie')
            limite_emprunts = request.form.get('limite_emprunts')
            duree_emprunt_max = request.form.get('duree_emprunt_max')
            Mot_de_passe_user=request.form.get('Mot_de_passe_user')
            
            try:
                cursor.execute("""
                    INSERT INTO utilisateur (nom_utilisateur, prenom_utilisateur, email_utilisateur, categorie, limite_emprunts, duree_emprunt_max, Mot_de_passe_user)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (nom, prenom, email, categorie, limite_emprunts, duree_emprunt_max, Mot_de_passe_user))
                
                conn.commit()
                flash('Utilisateur ajouté avec succès', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Erreur lors de l\'ajout de l\'utilisateur: {str(e)}', 'error')

    
        
        # Modifier un utilisateur
        
        
        elif action == 'edit_user':
            user_id = request.form.get('id_utilisateur')
            nom = request.form.get('nom_utilisateur')
            prenom = request.form.get('prenom_utilisateur')
            email = request.form.get('email_utilisateur')
            categorie = request.form.get('categorie')
            limite_emprunts = request.form.get('limite_emprunts')
            duree_emprunt_max = request.form.get('duree_emprunt_max')
            Mot_de_passe_user = request.form.get('Mot_de_passe_user')
            
            try:
                cursor.execute("""
                    UPDATE utilisateur 
                    SET nom_utilisateur = %s, prenom_utilisateur = %s, 
                        email_utilisateur = %s, categorie = %s ,limite_emprunts = %s,duree_emprunt_max = %s ,Mot_de_passe_user = %s
                    WHERE id_utilisateur = %s
                """, (nom, prenom, email, categorie,limite_emprunts,duree_emprunt_max,Mot_de_passe_user, user_id))
                conn.commit()
                flash('Utilisateur modifié avec succès', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Erreur lors de la modification: {str(e)}', 'error')
                
        # Supprimer un utilisateur
        
        elif action == 'delete_user':
            user_id = request.form.get('id_utilisateur')
            try:
                cursor.execute("DELETE FROM utilisateur WHERE id_utilisateur = %s", (user_id,))
                conn.commit()
                flash('Utilisateur supprimé avec succès', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Erreur lors de la suppression: {str(e)}', 'error')
                
                
                
    # Recherche d'utilisateurs
    # la barre de recherche de l'utilisateur
        
    search_type = request.args.get('search_type')
    search_query = request.args.get('search_query')
    categorie_query = request.args.get('categorie_query')
    
    if search_type and (search_query or categorie_query):
        try:
            if search_type == 'categorie':
                query = """
                    SELECT * FROM utilisateur 
                    WHERE categorie = %s
                """
                cursor.execute(query, (categorie_query,))
            else:
                query = f"""
                    SELECT * FROM utilisateur 
                    WHERE {search_type}_utilisateur LIKE %s
                """
                cursor.execute(query, (f'%{search_query}%',))
            
            users = cursor.fetchall()
            return render_template('gestionadmin.html', users=users)
            
        except Exception as e:
            flash(f'Erreur lors de la recherche: {str(e)}', 'error')
            return redirect(url_for('gestionadmin'))
    
    # Si pas de recherche, afficher tous les utilisateurs
    cursor.execute("SELECT * FROM utilisateur")
    users = cursor.fetchall()
                
    # Récupérer les documents et utilisateurs pour l'affichage
    cursor.execute("""
        SELECT d.*, l.isbn, p.issn, p.volume, p.numero 
        FROM document d
        LEFT JOIN livre l ON d.id_document = l.id_document
        LEFT JOIN periodique p ON d.id_document = p.id_document
    """)
    documents = cursor.fetchall()
    
    cursor.execute("SELECT * FROM utilisateur")
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('gestionadmin.html', documents=documents, users=users)

# Route pour l'emprunt


# Route pour le retour


if __name__ == '__main__':
    app.run(debug=True) 
    