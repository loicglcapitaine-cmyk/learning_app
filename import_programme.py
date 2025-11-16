import json
import streamlit as st
from datetime import datetime

def exporter_progression(db, prog_id):
    """
    Exporte la progression complète d'un programme au format JSON
    
    Méthodologie:
    1. Récupération des données du programme
    2. Récupération de toutes les séances associées
    3. Pour chaque séance, récupération des exercices et leurs séries
    4. Construction d'une structure de données hiérarchique
    5. Sérialisation en JSON avec formatage lisible
    
    Args:
        db: Connexion à la base de données
        prog_id: ID du programme à exporter
    
    Returns:
        str: Données JSON formatées
    """
    
    # Étape 1: Récupération des informations du programme
    cursor = db.cursor()
    cursor.execute("""
        SELECT nom, description, date_debut, date_fin, statut 
        FROM programme 
        WHERE id = ?
    """, (prog_id,))
    
    prog_data = cursor.fetchone()
    
    if not prog_data:
        return json.dumps({"erreur": "Programme non trouvé"}, indent=2)
    
    # Étape 2: Construction de la structure principale
    export_data = {
        "programme": {
            "nom": prog_data[0],
            "description": prog_data[1],
            "date_debut": prog_data[2],
            "date_fin": prog_data[3],
            "statut": prog_data[4]
        },
        "date_export": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "seances": []
    }
    
    # Étape 3: Récupération de toutes les séances
    cursor.execute("""
        SELECT id, nom, date, commentaire, duree_min, statut 
        FROM seance 
        WHERE programme_id = ? 
        ORDER BY date
    """, (prog_id,))
    
    seances = cursor.fetchall()
    
    # Étape 4: Pour chaque séance, récupérer les exercices
    for seance in seances:
        seance_id, nom_seance, date_seance, commentaire, duree, statut = seance
        
        seance_data = {
            "nom": nom_seance,
            "date": date_seance,
            "duree_minutes": duree,
            "statut": statut,
            "commentaire": commentaire,
            "exercices": []
        }
        
        # Étape 5: Récupération des exercices de la séance
        cursor.execute("""
            SELECT e.nom, se.ordre, se.notes
            FROM seance_exercice se
            JOIN exercice e ON se.exercice_id = e.id
            WHERE se.seance_id = ?
            ORDER BY se.ordre
        """, (seance_id,))
        
        exercices = cursor.fetchall()
        
        # Étape 6: Pour chaque exercice, récupérer les séries
        for exercice in exercices:
            nom_exercice, ordre, notes = exercice
            
            exercice_data = {
                "nom": nom_exercice,
                "ordre": ordre,
                "notes": notes,
                "series": []
            }
            
            # Récupération des séries
            cursor.execute("""
                SELECT 
                    s.numero_serie,
                    s.poids_kg,
                    s.repetitions,
                    s.duree_sec,
                    s.distance_m,
                    s.rpe,
                    s.notes
                FROM serie s
                JOIN seance_exercice se ON s.seance_exercice_id = se.id
                JOIN exercice e ON se.exercice_id = e.id
                WHERE se.seance_id = ? AND e.nom = ?
                ORDER BY s.numero_serie
            """, (seance_id, nom_exercice))
            
            series = cursor.fetchall()
            
            # Étape 7: Ajout des séries à l'exercice
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
    
    # Étape 8: Sérialisation en JSON
    # Solution 1: Utilisation standard (devrait fonctionner)
    try:
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    except TypeError:
        # Solution 2: Si ensure_ascii pose problème, utiliser la version par défaut
        # (les caractères non-ASCII seront échappés mais le JSON reste valide)
        return json.dumps(export_data, indent=2)


# SOLUTION ALTERNATIVE si le problème persiste
def exporter_progression_alternative(db, prog_id):
    """
    Version alternative utilisant une approche différente pour le JSON
    """
    import json as json_module  # Import explicite avec alias
    
    # [Même code que ci-dessus jusqu'à l'étape 8]
    
    # Puis :
    return json_module.dumps(export_data, indent=2, ensure_ascii=False)


# FONCTION DE DIAGNOSTIC
def diagnostiquer_probleme_json():
    """
    Fonction pour identifier la source du problème
    """
    import json as test_json
    import sys
    
    diagnostic = {
        "version_python": sys.version,
        "module_json": str(type(test_json)),
        "methode_dumps": hasattr(test_json, 'dumps'),
        "test_simple": None
    }
    
    try:
        test_data = {"test": "données", "valeur": 123}
        result = test_json.dumps(test_data, indent=2, ensure_ascii=False)
        diagnostic["test_simple"] = "SUCCÈS"
    except Exception as e:
        diagnostic["test_simple"] = f"ÉCHEC: {str(e)}"
    
    return diagnostic


# UTILISATION DANS STREAMLIT
def interface_export_streamlit(db, prog_id):
    """
    Interface Streamlit pour l'export avec gestion d'erreur
    """
    st.subheader("📥 Exporter la progression")
    
    if st.button("Exporter en JSON"):
        try:
            json_data = exporter_progression(db, prog_id)
            
            # Téléchargement du fichier
            st.download_button(
                label="📥 Télécharger le fichier JSON",
                data=json_data,
                file_name=f"progression_programme_{prog_id}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
            
            st.success("✅ Export réussi !")
            
            # Aperçu (optionnel)
            with st.expander("👁️ Aperçu des données"):
                st.code(json_data, language="json")
                
        except Exception as e:
            st.error(f"❌ Erreur lors de l'export: {str(e)}")
            
            # Afficher le diagnostic en cas d'erreur
            with st.expander("🔍 Diagnostic technique"):
                diag = diagnostiquer_probleme_json()
                st.json(diag)
