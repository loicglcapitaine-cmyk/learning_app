# ============================================================
# FICHIER: import_programme.py
# ============================================================
# Fonctions complètes d'import et d'export de programmes
# Compatible avec DatabaseSchema et connexions SQLite
# ============================================================

import json
import sqlite3
from datetime import datetime
import streamlit as st


# ============================================================
# FONCTION D'EXPORT DE PROGRESSION - VERSION ADAPTÉE
# ============================================================

def exporter_progression(db, prog_id):
    """
    Exporte la progression complète d'un programme au format JSON
    VERSION ADAPTÉE pour DatabaseSchema et SQLite standard
    
    Args:
        db: Objet DatabaseSchema ou connexion SQLite ou chemin string
        prog_id: ID du programme à exporter (string ou int)
    
    Returns:
        str: Données JSON formatées
    """
    
    # ========================================
    # DÉTECTION DU TYPE DE DB
    # ========================================
    
    # Cas 1: C'est un objet DatabaseSchema (votre app learning)
    if hasattr(db, 'conn'):
        conn = db.conn
        should_close = False
        table_prefix = "programmes"  # Tables au pluriel
    # Cas 2: C'est un chemin string
    elif isinstance(db, str):
        conn = sqlite3.connect(db)
        should_close = True
        table_prefix = "programme"  # Tables au singulier (app musculation)
    # Cas 3: C'est déjà une connexion SQLite
    else:
        conn = db
        should_close = False
        table_prefix = "programme"  # Par défaut singulier
    
    try:
        cursor = conn.cursor()
        
        # ========================================
        # DÉTECTION DU TYPE DE BASE DE DONNÉES
        # ========================================
        
        # Vérifier quelle table existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND (name='programmes' OR name='programme')
        """)
        tables = cursor.fetchall()
        
        # Déterminer si c'est une base "learning" ou "musculation"
        is_learning_db = any(t[0] == 'programmes' for t in tables)
        
        if is_learning_db:
            # ========================================
            # BASE DE DONNÉES LEARNING
            # ========================================
            return exporter_progression_learning(conn, prog_id, should_close)
        else:
            # ========================================
            # BASE DE DONNÉES MUSCULATION
            # ========================================
            return exporter_progression_musculation(conn, prog_id, should_close)
    
    except Exception as e:
        if should_close:
            conn.close()
        return json.dumps({
            "erreur": "Erreur lors de l'export",
            "details": str(e),
            "type": type(e).__name__
        }, indent=2, ensure_ascii=False)


# ============================================================
# EXPORT POUR BASE LEARNING (programmes/semaines/jours/contenus)
# ============================================================

def exporter_progression_learning(conn, prog_id, should_close):
    """Export pour une base de type learning_programme.db"""
    
    try:
        cursor = conn.cursor()
        
        # Récupération du programme
        cursor.execute("""
            SELECT nom, description, duree_jours
            FROM programmes 
            WHERE id = ?
        """, (prog_id,))
        
        prog_data = cursor.fetchone()
        
        if not prog_data:
            return json.dumps({
                "erreur": "Programme non trouvé",
                "prog_id": prog_id,
                "timestamp": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False)
        
        # Structure principale
        export_data = {
            "version": "1.0",
            "type_base": "learning",
            "programme": {
                "id": prog_id,
                "nom": prog_data[0],
                "description": prog_data[1],
                "duree_jours": prog_data[2]
            },
            "metadata": {
                "date_export": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "format": "JSON",
                "source": "Application Learning"
            },
            "statistiques": {
                "nombre_semaines": 0,
                "nombre_jours": 0,
                "nombre_contenus": 0,
                "contenus_termines": 0,
                "temps_total_passe": 0
            },
            "semaines": []
        }
        
        # Récupération des semaines
        cursor.execute("""
            SELECT id, numero, titre, objectif, temps_quotidien, ordre
            FROM semaines 
            WHERE programme_id = ? 
            ORDER BY ordre
        """, (prog_id,))
        
        semaines = cursor.fetchall()
        export_data["statistiques"]["nombre_semaines"] = len(semaines)
        
        # Traitement de chaque semaine
        for semaine in semaines:
            semaine_id = semaine[0]
            
            semaine_data = {
                "id": semaine_id,
                "numero": semaine[1],
                "titre": semaine[2],
                "objectif": semaine[3],
                "temps_quotidien": semaine[4],
                "ordre": semaine[5],
                "jours": []
            }
            
            # Récupération des jours
            cursor.execute("""
                SELECT id, numero, nom, type, ordre
                FROM jours 
                WHERE semaine_id = ?
                ORDER BY ordre
            """, (semaine_id,))
            
            jours = cursor.fetchall()
            export_data["statistiques"]["nombre_jours"] += len(jours)
            
            # Traitement de chaque jour
            for jour in jours:
                jour_id = jour[0]
                
                jour_data = {
                    "id": jour_id,
                    "numero": jour[1],
                    "nom": jour[2],
                    "type": jour[3],
                    "ordre": jour[4],
                    "contenus": []
                }
                
                # Récupération des contenus
                cursor.execute("""
                    SELECT 
                        id, titre, type, description, enonce,
                        indice, difficulte, temps_estime, ordre
                    FROM contenus 
                    WHERE jour_id = ?
                    ORDER BY ordre
                """, (jour_id,))
                
                contenus = cursor.fetchall()
                export_data["statistiques"]["nombre_contenus"] += len(contenus)
                
                # Traitement de chaque contenu
                for contenu in contenus:
                    contenu_id = contenu[0]
                    
                    contenu_data = {
                        "id": contenu_id,
                        "titre": contenu[1],
                        "type": contenu[2],
                        "description": contenu[3],
                        "enonce": contenu[4],
                        "indice": contenu[5],
                        "difficulte": contenu[6],
                        "temps_estime": contenu[7],
                        "ordre": contenu[8],
                        "progression": None
                    }
                    
                    # Récupération de la progression
                    cursor.execute("""
                        SELECT statut, date_debut, date_fin, temps_passe, notes
                        FROM progression 
                        WHERE contenu_id = ?
                    """, (contenu_id,))
                    
                    progression = cursor.fetchone()
                    
                    if progression:
                        contenu_data["progression"] = {
                            "statut": progression[0],
                            "date_debut": progression[1],
                            "date_fin": progression[2],
                            "temps_passe": progression[3],
                            "notes": progression[4]
                        }
                        
                        if progression[0] == 'termine':
                            export_data["statistiques"]["contenus_termines"] += 1
                        
                        if progression[3]:
                            export_data["statistiques"]["temps_total_passe"] += progression[3]
                    
                    jour_data["contenus"].append(contenu_data)
                
                semaine_data["jours"].append(jour_data)
            
            export_data["semaines"].append(semaine_data)
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "erreur": "Erreur lors de l'export learning",
            "details": str(e),
            "type": type(e).__name__
        }, indent=2, ensure_ascii=False)
    
    finally:
        if should_close:
            conn.close()


# ============================================================
# EXPORT POUR BASE MUSCULATION (programme/seance/exercice/serie)
# ============================================================

def exporter_progression_musculation(conn, prog_id, should_close):
    """Export pour une base de type musculation"""
    
    try:
        cursor = conn.cursor()
        
        # Récupération du programme
        cursor.execute("""
            SELECT nom, description, date_debut, date_fin, statut 
            FROM programme 
            WHERE id = ?
        """, (prog_id,))
        
        prog_data = cursor.fetchone()
        
        if not prog_data:
            return json.dumps({
                "erreur": "Programme non trouvé",
                "prog_id": prog_id
            }, indent=2, ensure_ascii=False)
        
        # Structure principale
        export_data = {
            "version": "1.0",
            "type_base": "musculation",
            "programme": {
                "id": prog_id,
                "nom": prog_data[0],
                "description": prog_data[1],
                "date_debut": prog_data[2],
                "date_fin": prog_data[3],
                "statut": prog_data[4]
            },
            "metadata": {
                "date_export": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "format": "JSON"
            },
            "statistiques": {
                "nombre_seances": 0
            },
            "seances": []
        }
        
        # Récupération des séances
        cursor.execute("""
            SELECT id, nom, date, commentaire, duree_min, statut 
            FROM seance 
            WHERE programme_id = ? 
            ORDER BY date
        """, (prog_id,))
        
        seances = cursor.fetchall()
        export_data["statistiques"]["nombre_seances"] = len(seances)
        
        # Traitement de chaque séance
        for seance in seances:
            seance_id, nom_seance, date_seance, commentaire, duree, statut = seance
            
            seance_data = {
                "id": seance_id,
                "nom": nom_seance,
                "date": date_seance,
                "duree_minutes": duree,
                "statut": statut,
                "commentaire": commentaire,
                "nombre_exercices": 0,
                "exercices": []
            }
            
            # Récupération des exercices
            cursor.execute("""
                SELECT e.id, e.nom, se.ordre, se.notes, se.id as seance_exercice_id
                FROM seance_exercice se
                JOIN exercice e ON se.exercice_id = e.id
                WHERE se.seance_id = ?
                ORDER BY se.ordre
            """, (seance_id,))
            
            exercices = cursor.fetchall()
            seance_data["nombre_exercices"] = len(exercices)
            
            # Traitement de chaque exercice
            for exercice in exercices:
                exercice_id, nom_exercice, ordre, notes, seance_exercice_id = exercice
                
                exercice_data = {
                    "id": exercice_id,
                    "nom": nom_exercice,
                    "ordre": ordre,
                    "notes": notes,
                    "nombre_series": 0,
                    "series": []
                }
                
                # Récupération des séries
                cursor.execute("""
                    SELECT 
                        numero_serie,
                        poids_kg,
                        repetitions,
                        duree_sec,
                        distance_m,
                        rpe,
                        notes
                    FROM serie
                    WHERE seance_exercice_id = ?
                    ORDER BY numero_serie
                """, (seance_exercice_id,))
                
                series = cursor.fetchall()
                exercice_data["nombre_series"] = len(series)
                
                # Ajout des séries
                for serie in series:
                    serie_data = {
                        "numero": serie[0],
                        "poids_kg": serie[1],
                        "repetitions": serie[2],
                        "duree_sec": serie[3],
                        "distance_m": serie[4],
                        "rpe": serie[5],
                        "notes": serie[6]
                    }
                    exercice_data["series"].append(serie_data)
                
                seance_data["exercices"].append(exercice_data)
            
            export_data["seances"].append(seance_data)
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "erreur": str(e),
            "type_erreur": type(e).__name__
        }, indent=2, ensure_ascii=False)
    
    finally:
        if should_close:
            conn.close()


# ============================================================
# FONCTION D'IMPORT DE PROGRESSION
# ============================================================

def importer_progression(db, json_data):
    """
    Importe la progression depuis des données JSON
    
    Args:
        db: Objet DatabaseSchema ou connexion SQLite
        json_data: Dictionnaire Python (déjà parsé) ou string JSON
    
    Returns:
        dict: Statistiques de l'import {nb_importes, nb_erreurs, succes}
    """
    
    # Gérer le cas où json_data est déjà un dict ou une string
    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data
    
    # Détection du type de DB
    if hasattr(db, 'conn'):
        conn = db.conn
        should_close = False
    elif isinstance(db, str):
        conn = sqlite3.connect(db)
        should_close = True
    else:
        conn = db
        should_close = False
    
    try:
        cursor = conn.cursor()
        nb_importes = 0
        nb_erreurs = 0
        
        # Vérifier le type de base
        type_base = data.get("type_base", "learning")
        
        if type_base == "learning":
            # Import pour base learning
            if "semaines" in data:
                for semaine in data["semaines"]:
                    for jour in semaine.get("jours", []):
                        for contenu in jour.get("contenus", []):
                            prog = contenu.get("progression")
                            
                            if prog and prog.get("statut"):
                                try:
                                    # Vérifier si une progression existe
                                    cursor.execute("""
                                        SELECT id FROM progression 
                                        WHERE contenu_id = ?
                                    """, (contenu["id"],))
                                    
                                    existe = cursor.fetchone()
                                    
                                    if existe:
                                        # Mise à jour
                                        cursor.execute("""
                                            UPDATE progression 
                                            SET statut = ?,
                                                date_debut = ?,
                                                date_fin = ?,
                                                temps_passe = ?,
                                                notes = ?
                                            WHERE contenu_id = ?
                                        """, (
                                            prog["statut"],
                                            prog.get("date_debut"),
                                            prog.get("date_fin"),
                                            prog.get("temps_passe"),
                                            prog.get("notes"),
                                            contenu["id"]
                                        ))
                                    else:
                                        # Insertion
                                        cursor.execute("""
                                            INSERT INTO progression 
                                            (contenu_id, statut, date_debut, date_fin, temps_passe, notes)
                                            VALUES (?, ?, ?, ?, ?, ?)
                                        """, (
                                            contenu["id"],
                                            prog["statut"],
                                            prog.get("date_debut"),
                                            prog.get("date_fin"),
                                            prog.get("temps_passe"),
                                            prog.get("notes")
                                        ))
                                    
                                    nb_importes += 1
                                    
                                except Exception as e:
                                    nb_erreurs += 1
        
        conn.commit()
        
        return {
            "succes": True,
            "nb_importes": nb_importes,
            "nb_erreurs": nb_erreurs
        }
    
    except Exception as e:
        if hasattr(conn, 'rollback'):
            conn.rollback()
        return {
            "succes": False,
            "nb_importes": 0,
            "nb_erreurs": 1,
            "erreur": str(e)
        }
    
    finally:
        if should_close:
            conn.close()


# ============================================================
# IMPORT DE PROGRAMME COMPLET DEPUIS CSV
# ============================================================

class ProgrammeImporter:
    """Classe pour importer des programmes depuis CSV"""
    
    def __init__(self, db):
        """
        Args:
            db: Objet DatabaseSchema ou connexion SQLite
        """
        if hasattr(db, 'conn'):
            self.conn = db.conn
        else:
            self.conn = db
    
    def importer_depuis_csv(self, csv_file, nom_programme, sujet):
        """
        Importe un programme depuis un fichier CSV
        
        Args:
            csv_file: Objet file-like du CSV
            nom_programme: Nom du programme à créer
            sujet: Sujet du programme
        
        Returns:
            dict: Statistiques de l'import
        """
        import csv
        from datetime import date
        
        try:
            reader = csv.DictReader(csv_file)
            cursor = self.conn.cursor()
            
            # Créer le programme
            prog_id = f"prog_{sujet.lower().replace(' ', '_')}"
            
            cursor.execute("""
                INSERT INTO programmes (id, nom, description, sujet, duree_jours)
                VALUES (?, ?, ?, ?, ?)
            """, (prog_id, nom_programme, f"Programme {nom_programme}", sujet, 30))
            
            semaines_cache = {}
            jours_cache = {}
            
            nb_semaines = 0
            nb_jours = 0
            nb_contenus = 0
            erreurs = []
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    type_ligne = row.get('Type', '').lower().strip()
                    semaine_num = int(row.get('Semaine', 0))
                    
                    if not type_ligne or not semaine_num:
                        continue
                    
                    # SEMAINE
                    if type_ligne == 'semaine':
                        titre = row.get('Titre', f'Semaine {semaine_num}')
                        objectif = row.get('Description', '')
                        temps = row.get('TempsEstime', '2h')
                        
                        semaine_id = f"sem_{prog_id}_{semaine_num}"
                        
                        cursor.execute("""
                            INSERT INTO semaines 
                            (id, programme_id, numero, titre, objectif, temps_quotidien, ordre)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (semaine_id, prog_id, semaine_num, titre, objectif, temps, semaine_num))
                        
                        semaines_cache[semaine_num] = semaine_id
                        nb_semaines += 1
                    
                    # JOUR
                    elif type_ligne == 'jour':
                        jour_num = int(row.get('Jour', 1))
                        
                        if semaine_num not in semaines_cache:
                            erreurs.append(f"Ligne {row_num}: Semaine {semaine_num} non trouvée")
                            continue
                        
                        semaine_id = semaines_cache[semaine_num]
                        jour_type = 'weekend' if jour_num >= 99 else 'normal'
                        jour_nom = f"jour_{jour_num}" if jour_num < 99 else "weekend"
                        
                        jour_id = f"jour_{semaine_id}_{jour_num}"
                        
                        cursor.execute("""
                            INSERT INTO jours 
                            (id, semaine_id, numero, nom, type, ordre)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (jour_id, semaine_id, jour_num, jour_nom, jour_type, jour_num))
                        
                        jours_cache[(semaine_num, jour_num)] = jour_id
                        nb_jours += 1
                    
                    # CONTENU
                    elif type_ligne in ['theorie', 'exercice', 'projet', 'ressource']:
                        jour_num = int(row.get('Jour', 1))
                        
                        if (semaine_num, jour_num) not in jours_cache:
                            erreurs.append(f"Ligne {row_num}: Jour {jour_num} de semaine {semaine_num} non trouvé")
                            continue
                        
                        jour_id = jours_cache[(semaine_num, jour_num)]
                        
                        titre = row.get('Titre', 'Sans titre')
                        description = row.get('Description', '')
                        enonce = row.get('Enonce', '')
                        indice = row.get('Indice', '')
                        
                        try:
                            difficulte = int(row.get('Difficulte', 0)) if row.get('Difficulte') else None
                        except:
                            difficulte = None
                        
                        try:
                            temps_estime = int(row.get('TempsEstime', 0)) if row.get('TempsEstime') else None
                        except:
                            temps_estime = None
                        
                        contenu_id = f"cont_{jour_id}_{nb_contenus}"
                        
                        cursor.execute("""
                            INSERT INTO contenus 
                            (id, jour_id, titre, type, description, enonce, 
                             indice, difficulte, temps_estime, ordre)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            contenu_id, jour_id, titre, type_ligne, description,
                            enonce, indice, difficulte, temps_estime, nb_contenus
                        ))
                        
                        nb_contenus += 1
                
                except Exception as e:
                    erreurs.append(f"Ligne {row_num}: {str(e)}")
            
            self.conn.commit()
            
            return {
                "succes": True,
                "programme_id": prog_id,
                "nb_semaines": nb_semaines,
                "nb_jours": nb_jours,
                "nb_contenus": nb_contenus,
                "erreurs": erreurs
            }
        
        except Exception as e:
            self.conn.rollback()
            return {
                "succes": False,
                "erreur": str(e),
                "erreurs": [str(e)]
            }
    
    def generer_template_csv(self):
        """Génère un template CSV vide"""
        template = """Type,Semaine,Jour,Titre,Description,Enonce,Indice,Difficulte,TempsEstime
# Exemple de structure:
semaine,1,,Fondations Python,Maîtriser les bases,,,,
jour,1,1,,,,,,,
theorie,1,1,Introduction à Python,Vue d'ensemble du langage,,,,15
exercice,1,1,Premier exercice,Créer des variables,"Créez 3 variables différentes",Utilisez =,1,20
jour,1,2,,,,,,,
theorie,1,2,Les types de données,Nombres et strings,,,,20
"""
        return template


# ============================================================
# FONCTIONS D'IMPORT EXISTANTES (COMPATIBILITÉ)
# ============================================================

def importer_programme(db, fichier_json):
    """
    Importe un programme depuis un fichier JSON
    (Conservé pour compatibilité)
    """
    try:
        data = json.loads(fichier_json)
        
        if "programme" not in data:
            return False, "Structure JSON invalide: clé 'programme' manquante", None
        
        prog = data["programme"]
        
        if isinstance(db, str):
            conn = sqlite3.connect(db)
            should_close = True
        else:
            conn = db
            should_close = False
        
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO programme (nom, description, date_debut, date_fin, statut)
                VALUES (?, ?, ?, ?, ?)
            """, (
                prog.get("nom", "Programme importé"),
                prog.get("description", ""),
                prog.get("date_debut", datetime.now().strftime("%Y-%m-%d")),
                prog.get("date_fin"),
                prog.get("statut", "actif")
            ))
            
            prog_id = cursor.lastrowid
            conn.commit()
            return True, f"Programme importé avec succès (ID: {prog_id})", prog_id
        
        finally:
            if should_close:
                conn.close()
    
    except json.JSONDecodeError as e:
        return False, f"Erreur de parsing JSON: {str(e)}", None
    except Exception as e:
        return False, f"Erreur lors de l'import: {str(e)}", None


def valider_structure_json(data):
    """Valide la structure d'un JSON de programme"""
    erreurs = []
    
    if not isinstance(data, dict):
        erreurs.append("Le JSON doit être un objet")
        return False, erreurs
    
    if "programme" not in data:
        erreurs.append("Clé 'programme' manquante")
    else:
        prog = data["programme"]
        if "nom" not in prog:
            erreurs.append("Le programme doit avoir un nom")
    
    return len(erreurs) == 0, erreurs


# ============================================================
# INTERFACE STREAMLIT (OPTIONNELLE)
# ============================================================

def interface_export_streamlit(db, prog_id):
    """Interface Streamlit pour l'export"""
    
    st.subheader("📥 Exporter la progression")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write("Exportez toutes les données de ce programme au format JSON.")
    
    with col2:
        if st.button("📥 Exporter", use_container_width=True):
            try:
                json_data = exporter_progression(db, prog_id)
                
                data = json.loads(json_data)
                if "erreur" in data:
                    st.error(f"❌ Erreur: {data['erreur']}")
                    return
                
                filename = f"progression_programme_{prog_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                st.download_button(
                    label="💾 Télécharger le fichier JSON",
                    data=json_data,
                    file_name=filename,
                    mime="application/json",
                    use_container_width=True
                )
                
                st.success(f"✅ Export réussi !")
                
                # Statistiques selon le type
                if "statistiques" in data:
                    stats = data["statistiques"]
                    if "nombre_semaines" in stats:
                        st.info(f"📊 {stats['nombre_semaines']} semaine(s), {stats['nombre_contenus']} contenu(s)")
                    elif "nombre_seances" in stats:
                        st.info(f"📊 {stats['nombre_seances']} séance(s) exportée(s)")
                    
            except Exception as e:
                st.error(f"❌ Erreur lors de l'export: {str(e)}")


def interface_import_streamlit(db):
    """Interface Streamlit pour l'import"""
    
    st.subheader("📤 Importer un programme")
    
    fichier = st.file_uploader(
        "Choisissez un fichier JSON",
        type=['json'],
        help="Sélectionnez un fichier JSON de programme exporté"
    )
    
    if fichier is not None:
        try:
            contenu = fichier.read().decode('utf-8')
            data = json.loads(contenu)
            valide, erreurs = valider_structure_json(data)
            
            if not valide:
                st.error("❌ Structure JSON invalide:")
                for erreur in erreurs:
                    st.write(f"  • {erreur}")
                return None
            
            with st.expander("👁️ Aperçu du programme"):
                if "programme" in data:
                    st.write(f"**Nom:** {data['programme'].get('nom', 'N/A')}")
                    st.write(f"**Description:** {data['programme'].get('description', 'N/A')}")
            
            if st.button("✅ Importer le programme", type="primary"):
                with st.spinner("Import en cours..."):
                    succes, message, prog_id = importer_programme(db, contenu)
                    
                    if succes:
                        st.success(message)
                        st.balloons()
                        return prog_id
                    else:
                        st.error(message)
                        return None
        
        except json.JSONDecodeError:
            st.error("❌ Le fichier n'est pas un JSON valide")
        except Exception as e:
            st.error(f"❌ Erreur: {str(e)}")
    
    return None
