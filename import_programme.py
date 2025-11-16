"""
Module d'importation de programmes depuis CSV
Format accessible à tous pour créer facilement de nouveaux programmes
"""

import csv
import io
from database_schema import DatabaseSchema, generate_id
from datetime import datetime

class ProgrammeImporter:
    """
    Importe un programme depuis un fichier CSV
    Format simple et accessible à tous
    """
    
    def __init__(self, db: DatabaseSchema):
        self.db = db
        self.cursor = db.conn.cursor()
    
    def importer_depuis_csv(self, fichier_csv: str or io.StringIO, 
                           nom_programme: str, sujet: str) -> dict:
        """
        Importe un programme depuis un CSV
        
        Format CSV attendu (sans header) :
        Type, Semaine, Jour, Titre, Description, Enonce, Indice, Difficulte, TempsEstime
        
        Exemple:
        programme,,,Python 30 jours,Programme complet Python,,,,
        semaine,1,,Fondations,Maîtriser les bases,,,,
        theorie,1,1,Variables et types,Introduction aux variables,,,,15
        exercice,1,1,Créer 10 variables,Exercice pratique,Créez 10 variables...,Utilisez print(),2,30
        
        Returns:
            dict avec statistiques d'import
        """
        
        stats = {
            'succes': False,
            'programme_id': None,
            'nb_semaines': 0,
            'nb_jours': 0,
            'nb_contenus': 0,
            'erreurs': []
        }
        
        try:
            # Lire le CSV
            if isinstance(fichier_csv, str):
                with open(fichier_csv, 'r', encoding='utf-8') as f:
                    lecteur = csv.reader(f)
                    lignes = list(lecteur)
            else:
                lecteur = csv.reader(fichier_csv)
                lignes = list(lecteur)
            
            # Variables de contexte
            prog_id = generate_id("prog", sujet, "custom")
            semaines_map = {}  # {numero: id}
            jours_map = {}     # {(semaine_num, jour_num): id}
            
            # Créer le programme
            self.cursor.execute("""
                INSERT INTO programmes (id, titre, sujet, duree_jours, niveau, temps_quotidien, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                prog_id,
                nom_programme,
                sujet,
                30,  # Par défaut
                'débutant',
                2,
                f"Programme importé le {datetime.now().strftime('%Y-%m-%d')}"
            ))
            
            stats['programme_id'] = prog_id
            
            # Parser les lignes
            for i, ligne in enumerate(lignes, 1):
                if not ligne or len(ligne) < 4:
                    continue
                
                type_ligne = ligne[0].strip().lower()
                
                try:
                    if type_ligne == 'semaine':
                        self._creer_semaine(ligne, prog_id, semaines_map)
                        stats['nb_semaines'] += 1
                    
                    elif type_ligne == 'jour':
                        self._creer_jour(ligne, semaines_map, jours_map)
                        stats['nb_jours'] += 1
                    
                    elif type_ligne in ['theorie', 'exercice', 'projet', 'ressource']:
                        self._creer_contenu(ligne, jours_map, type_ligne)
                        stats['nb_contenus'] += 1
                
                except Exception as e:
                    stats['erreurs'].append(f"Ligne {i}: {str(e)}")
            
            self.db.conn.commit()
            stats['succes'] = True
            
        except Exception as e:
            stats['erreurs'].append(f"Erreur générale: {str(e)}")
            self.db.conn.rollback()
        
        return stats
    
    def _creer_semaine(self, ligne, prog_id, semaines_map):
        """Crée une semaine"""
        numero = int(ligne[1])
        titre = ligne[3]
        objectif = ligne[4] if len(ligne) > 4 else ""
        
        sem_id = generate_id("sem", numero, prog_id)
        
        self.cursor.execute("""
            INSERT INTO semaines (id, programme_id, numero, titre, objectif, temps_quotidien, ordre)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sem_id, prog_id, numero, titre, objectif, "2h", numero))
        
        semaines_map[numero] = sem_id
    
    def _creer_jour(self, ligne, semaines_map, jours_map):
        """Crée un jour"""
        semaine_num = int(ligne[1])
        jour_num = int(ligne[2])
        nom_jour = f"jour_{jour_num}" if jour_num < 90 else "weekend"
        type_jour = ligne[4] if len(ligne) > 4 and ligne[4] else "normal"
        
        if semaine_num not in semaines_map:
            raise ValueError(f"Semaine {semaine_num} non trouvée")
        
        sem_id = semaines_map[semaine_num]
        jour_id = generate_id("jour", nom_jour, sem_id)
        
        self.cursor.execute("""
            INSERT INTO jours (id, semaine_id, nom, type, ordre)
            VALUES (?, ?, ?, ?, ?)
        """, (jour_id, sem_id, nom_jour, type_jour, jour_num))
        
        jours_map[(semaine_num, jour_num)] = jour_id
    
    def _creer_contenu(self, ligne, jours_map, type_contenu):
        """Crée un contenu"""
        semaine_num = int(ligne[1])
        jour_num = int(ligne[2])
        titre = ligne[3]
        description = ligne[4] if len(ligne) > 4 else ""
        enonce = ligne[5] if len(ligne) > 5 else ""
        indice = ligne[6] if len(ligne) > 6 else ""
        difficulte = int(ligne[7]) if len(ligne) > 7 and ligne[7] else 2
        temps_estime = int(ligne[8]) if len(ligne) > 8 and ligne[8] else 30
        
        if (semaine_num, jour_num) not in jours_map:
            raise ValueError(f"Jour {jour_num} de semaine {semaine_num} non trouvé")
        
        jour_id = jours_map[(semaine_num, jour_num)]
        
        # Compter l'ordre
        self.cursor.execute("""
            SELECT COUNT(*) FROM contenus WHERE jour_id = ?
        """, (jour_id,))
        ordre = self.cursor.fetchone()[0] + 1
        
        contenu_id = generate_id("cont", type_contenu, ordre, jour_id)
        
        self.cursor.execute("""
            INSERT INTO contenus (id, jour_id, type, titre, description, 
                                 enonce, indice, difficulte, temps_estime, ordre)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            contenu_id, jour_id, type_contenu, titre, description,
            enonce, indice, difficulte, temps_estime, ordre
        ))
    
    def generer_template_csv(self) -> str:
        """
        Génère un template CSV avec exemples
        
        Returns:
            Contenu CSV template
        """
        template = """Type,Semaine,Jour,Titre,Description,Enonce,Indice,Difficulte,TempsEstime
semaine,1,,Fondations JavaScript,Maîtriser les bases du langage,,,,
jour,1,1,,,,,
theorie,1,1,Variables : var let const,Comprendre les différences,,,,15
exercice,1,1,Déclarations de variables,Créer des variables,Créez 10 variables avec let et const,Utilisez console.log(),2,30
jour,1,2,,,,,
theorie,1,2,Fonctions,Créer et utiliser des fonctions,,,,20
exercice,1,2,Ma première fonction,Créer une fonction,Créez une fonction qui calcule le carré,function carre(n) { return n*n; },2,25
jour,1,99,,,,,
projet,1,99,Calculatrice JavaScript,Projet de weekend,Créez une calculatrice complète avec HTML/CSS/JS,,4,180

# INSTRUCTIONS:
# - Type: semaine, jour, theorie, exercice, projet, ressource
# - Semaine: Numéro de la semaine (1, 2, 3...)
# - Jour: Numéro du jour (1-5 pour jours normaux, 99 pour weekend)
# - Pour 'semaine': remplir Titre et Description
# - Pour 'jour': juste Semaine et Jour (crée la structure)
# - Pour contenus: tous les champs sauf Enonce (optionnel)
# - Difficulte: 1-5 (1=facile, 5=expert)
# - TempsEstime: en minutes
# - Lignes vides et commentaires (#) sont ignorés
"""
        return template


def generer_csv_depuis_programme_existant(db: DatabaseSchema, prog_id: str) -> str:
    """
    Exporte un programme existant en CSV pour le réutiliser comme template
    
    Args:
        db: Connexion base de données
        prog_id: ID du programme à exporter
    
    Returns:
        Contenu CSV
    """
    cursor = db.conn.cursor()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["Type", "Semaine", "Jour", "Titre", "Description", "Enonce", "Indice", "Difficulte", "TempsEstime"])
    
    # Programme
    cursor.execute("SELECT * FROM programmes WHERE id = ?", (prog_id,))
    prog = cursor.fetchone()
    if not prog:
        return "# Programme non trouvé"
    
    # Semaines
    cursor.execute("""
        SELECT * FROM semaines WHERE programme_id = ? ORDER BY ordre
    """, (prog_id,))
    
    for semaine in cursor.fetchall():
        writer.writerow(["semaine", semaine['numero'], "", semaine['titre'], semaine['objectif'], "", "", "", ""])
        
        # Jours de cette semaine
        cursor.execute("""
            SELECT * FROM jours WHERE semaine_id = ? ORDER BY ordre
        """, (semaine['id'],))
        
        for jour in cursor.fetchall():
            jour_num = 99 if jour['type'] == 'weekend' else jour['ordre']
            writer.writerow(["jour", semaine['numero'], jour_num, "", "", "", "", "", ""])
            
            # Contenus de ce jour
            cursor.execute("""
                SELECT * FROM contenus WHERE jour_id = ? ORDER BY ordre
            """, (jour['id'],))
            
            for contenu in cursor.fetchall():
                writer.writerow([
                    contenu['type'],
                    semaine['numero'],
                    jour_num,
                    contenu['titre'],
                    contenu['description'] or "",
                    contenu['enonce'] or "",
                    contenu['indice'] or "",
                    contenu['difficulte'] or "",
                    contenu['temps_estime'] or ""
                ])
    
    return output.getvalue()


def exporter_progression(db: DatabaseSchema, prog_id: str) -> str:
    """
    Exporte la progression d'un programme en JSON
    
    Args:
        db: Connexion base de données
        prog_id: ID du programme
    
    Returns:
        JSON string de la progression
    """
    cursor = db.conn.cursor()
    
    # Récupérer toutes les progressions pour ce programme
    cursor.execute("""
        SELECT 
            c.id as contenu_id,
            c.titre,
            c.type,
            p.statut,
            p.date_debut,
            p.date_completion,
            p.temps_passe,
            p.notes
        FROM contenus c
        JOIN jours j ON c.jour_id = j.id
        JOIN semaines s ON j.semaine_id = s.id
        LEFT JOIN progression p ON p.contenu_id = c.id
        WHERE s.programme_id = ?
          AND p.statut IS NOT NULL
        ORDER BY s.ordre, j.ordre, c.ordre
    """, (prog_id,))
    
    progressions = []
    for row in cursor.fetchall():
        progressions.append({
            'contenu_id': row['contenu_id'],
            'titre': row['titre'],
            'type': row['type'],
            'statut': row['statut'],
            'date_debut': row['date_debut'],
            'date_completion': row['date_completion'],
            'temps_passe': row['temps_passe'],
            'notes': row['notes']
        })
    
    export_data = {
        'programme_id': prog_id,
        'date_export': datetime.now().isoformat(),
        'nb_contenus': len(progressions),
        'progressions': progressions
    }
    
    return json.dumps(export_data, indent=2, ensure_ascii=False)


def importer_progression(db: DatabaseSchema, data: dict) -> dict:
    """
    Importe une progression depuis un JSON
    
    Args:
        db: Connexion base de données
        data: Données JSON de la progression
    
    Returns:
        Statistiques d'import
    """
    cursor = db.conn.cursor()
    
    stats = {
        'succes': False,
        'nb_importes': 0,
        'nb_ignores': 0,
        'erreurs': []
    }
    
    try:
        progressions = data.get('progressions', [])
        
        for prog in progressions:
            try:
                # Vérifier si le contenu existe
                cursor.execute("SELECT id FROM contenus WHERE id = ?", (prog['contenu_id'],))
                if not cursor.fetchone():
                    stats['nb_ignores'] += 1
                    stats['erreurs'].append(f"Contenu {prog['contenu_id']} introuvable")
                    continue
                
                # Insérer ou mettre à jour la progression
                cursor.execute("""
                    INSERT OR REPLACE INTO progression 
                    (contenu_id, statut, date_debut, date_completion, temps_passe, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    prog['contenu_id'],
                    prog['statut'],
                    prog.get('date_debut'),
                    prog.get('date_completion'),
                    prog.get('temps_passe', 0),
                    prog.get('notes', '')
                ))
                
                stats['nb_importes'] += 1
            
            except Exception as e:
                stats['erreurs'].append(f"Erreur sur {prog.get('titre', '?')}: {str(e)}")
        
        db.conn.commit()
        stats['succes'] = True
    
    except Exception as e:
        stats['erreurs'].append(f"Erreur générale: {str(e)}")
        db.conn.rollback()
    
    return stats
