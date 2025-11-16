# ============================================================
# FICHIER: import_programme.py
# ============================================================
# Fonctions d'import et d'export de programmes d'entraînement
# ============================================================

import json
import sqlite3
from datetime import datetime
import streamlit as st


# ============================================================
# FONCTION D'EXPORT DE PROGRESSION (NOUVELLE)
# ============================================================

def exporter_progression(db_path, prog_id):
    """
    Exporte la progression complète d'un programme au format JSON
    
    Args:
        db_path: Chemin vers la base de données ou connexion SQLite
        prog_id: ID du programme à exporter
    
    Returns:
        str: Données JSON formatées
    """
    
    # Gestion de la connexion
    if isinstance(db_path, str):
        conn = sqlite3.connect(db_path)
        should_close = True
    else:
        conn = db_path
        should_close = False
    
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
            "programme": {
                "id": prog_id,
                "nom": prog_data[0],
                "description": prog_data[1],
                "date_debut": prog_data[2],
                "date_fin": prog_data[3],
                "statut": prog_data[4]
            },
            "date_export": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "nombre_seances": 0,
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
        export_data["nombre_seances"] = len(seances)
        
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
        
        # Sérialisation JSON
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
# FONCTIONS D'IMPORT EXISTANTES
# ============================================================

def importer_programme(db, fichier_json):
    """
    Importe un programme depuis un fichier JSON
    
    Args:
        db: Connexion à la base de données
        fichier_json: Contenu du fichier JSON
    
    Returns:
        tuple: (succès: bool, message: str, prog_id: int ou None)
    """
    try:
        # Parser le JSON
        data = json.loads(fichier_json)
        
        # Validation de base
        if "programme" not in data:
            return False, "Structure JSON invalide: clé 'programme' manquante", None
        
        prog = data["programme"]
        
        # Gestion de la connexion
        if isinstance(db, str):
            conn = sqlite3.connect(db)
            should_close = True
        else:
            conn = db
            should_close = False
        
        try:
            cursor = conn.cursor()
            
            # Insertion du programme
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
            
            # Import des séances si présentes
            if "seances" in data:
                for seance in data["seances"]:
                    cursor.execute("""
                        INSERT INTO seance (programme_id, nom, date, commentaire, duree_min, statut)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        prog_id,
                        seance.get("nom", "Séance"),
                        seance.get("date", datetime.now().strftime("%Y-%m-%d")),
                        seance.get("commentaire"),
                        seance.get("duree_minutes"),
                        seance.get("statut", "planifie")
                    ))
                    
                    seance_id = cursor.lastrowid
                    
                    # Import des exercices
                    if "exercices" in seance:
                        for exercice in seance["exercices"]:
                            # Vérifier si l'exercice existe
                            cursor.execute("SELECT id FROM exercice WHERE nom = ?", (exercice.get("nom"),))
                            ex_result = cursor.fetchone()
                            
                            if ex_result:
                                exercice_id = ex_result[0]
                            else:
                                # Créer l'exercice s'il n'existe pas
                                cursor.execute("""
                                    INSERT INTO exercice (nom, description, categorie)
                                    VALUES (?, ?, ?)
                                """, (exercice.get("nom"), "", "autre"))
                                exercice_id = cursor.lastrowid
                            
                            # Lier l'exercice à la séance
                            cursor.execute("""
                                INSERT INTO seance_exercice (seance_id, exercice_id, ordre, notes)
                                VALUES (?, ?, ?, ?)
                            """, (
                                seance_id,
                                exercice_id,
                                exercice.get("ordre", 0),
                                exercice.get("notes")
                            ))
                            
                            seance_exercice_id = cursor.lastrowid
                            
                            # Import des séries
                            if "series" in exercice:
                                for serie in exercice["series"]:
                                    cursor.execute("""
                                        INSERT INTO serie (
                                            seance_exercice_id, numero_serie, 
                                            poids_kg, repetitions, duree_sec, 
                                            distance_m, rpe, notes
                                        )
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (
                                        seance_exercice_id,
                                        serie.get("numero", 1),
                                        serie.get("poids_kg"),
                                        serie.get("repetitions"),
                                        serie.get("duree_sec"),
                                        serie.get("distance_m"),
                                        serie.get("rpe"),
                                        serie.get("notes")
                                    ))
            
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
    """
    Valide la structure d'un JSON de programme
    
    Args:
        data: Dictionnaire Python issu du JSON
    
    Returns:
        tuple: (valide: bool, erreurs: list)
    """
    erreurs = []
    
    # Vérifications de base
    if not isinstance(data, dict):
        erreurs.append("Le JSON doit être un objet")
        return False, erreurs
    
    if "programme" not in data:
        erreurs.append("Clé 'programme' manquante")
    else:
        prog = data["programme"]
        if "nom" not in prog:
            erreurs.append("Le programme doit avoir un nom")
    
    # Vérifications des séances
    if "seances" in data:
        if not isinstance(data["seances"], list):
            erreurs.append("'seances' doit être une liste")
        else:
            for i, seance in enumerate(data["seances"]):
                if "exercices" in seance:
                    if not isinstance(seance["exercices"], list):
                        erreurs.append(f"Les exercices de la séance {i+1} doivent être une liste")
    
    return len(erreurs) == 0, erreurs


# ============================================================
# INTERFACE STREAMLIT POUR L'EXPORT
# ============================================================

def interface_export_streamlit(db, prog_id):
    """
    Interface Streamlit pour exporter la progression
    
    Args:
        db: Connexion ou chemin vers la base de données
        prog_id: ID du programme à exporter
    """
    st.subheader("📥 Exporter la progression")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write("Exportez toutes les données de ce programme au format JSON.")
    
    with col2:
        if st.button("📥 Exporter", use_container_width=True):
            try:
                # Génération du JSON
                json_data = exporter_progression(db, prog_id)
                
                # Vérifier s'il y a une erreur
                data = json.loads(json_data)
                if "erreur" in data:
                    st.error(f"❌ Erreur: {data['erreur']}")
                    return
                
                # Nom du fichier
                filename = f"progression_programme_{prog_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                # Bouton de téléchargement
                st.download_button(
                    label="💾 Télécharger le fichier JSON",
                    data=json_data,
                    file_name=filename,
                    mime="application/json",
                    use_container_width=True
                )
                
                # Statistiques
                st.success(f"✅ Export réussi !")
                st.info(f"📊 {data['nombre_seances']} séance(s) exportée(s)")
                
                # Aperçu optionnel
                with st.expander("👁️ Aperçu des données"):
                    st.json(data, expanded=False)
                    
            except Exception as e:
                st.error(f"❌ Erreur lors de l'export: {str(e)}")


# ============================================================
# INTERFACE STREAMLIT POUR L'IMPORT
# ============================================================

def interface_import_streamlit(db):
    """
    Interface Streamlit pour importer un programme
    
    Args:
        db: Connexion ou chemin vers la base de données
    
    Returns:
        int ou None: ID du programme importé si succès
    """
    st.subheader("📤 Importer un programme")
    
    fichier = st.file_uploader(
        "Choisissez un fichier JSON",
        type=['json'],
        help="Sélectionnez un fichier JSON de programme exporté précédemment"
    )
    
    if fichier is not None:
        try:
            # Lecture du fichier
            contenu = fichier.read().decode('utf-8')
            
            # Validation préalable
            data = json.loads(contenu)
            valide, erreurs = valider_structure_json(data)
            
            if not valide:
                st.error("❌ Structure JSON invalide:")
                for erreur in erreurs:
                    st.write(f"  • {erreur}")
                return None
            
            # Aperçu
            with st.expander("👁️ Aperçu du programme"):
                if "programme" in data:
                    st.write(f"**Nom:** {data['programme'].get('nom', 'N/A')}")
                    st.write(f"**Description:** {data['programme'].get('description', 'N/A')}")
                    if "seances" in data:
                        st.write(f"**Nombre de séances:** {len(data['seances'])}")
            
            # Bouton d'import
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
