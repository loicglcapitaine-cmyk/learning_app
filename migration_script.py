"""
Script de migration des données du programme Python
Migre depuis la structure Python hardcodée vers la base de données SQLite
"""

import json
import os
from datetime import datetime
from database_schema import DatabaseSchema, DatabaseInitializer, generate_id, parse_duration


class ProgrammeMigrator:
    """
    Gère la migration des données du programme Python vers SQLite
    """
    
    def __init__(self, db: DatabaseSchema):
        """
        Args:
            db: Instance de DatabaseSchema connectée
        """
        self.db = db
        self.cursor = db.conn.cursor()
        self.contenu_ids_map = {}  # Pour mapping contenu -> ID
    
    def migrate_all(self):
        """
        Exécute la migration complète
        """
        print("\n" + "="*70)
        print("🚀 DÉBUT DE LA MIGRATION")
        print("="*70 + "\n")
        
        # 1. Créer le programme
        prog_id = self._create_programme()
        
        # 2. Créer les semaines, jours et contenus
        self._create_structure(prog_id)
        
        # 3. Créer les prérequis logiques
        self._create_prerequis()
        
        # 4. Migrer la progression existante
        self._migrate_progression()
        
        # 5. Statistiques finales
        self._show_statistics()
        
        print("\n" + "="*70)
        print("✅ MIGRATION TERMINÉE AVEC SUCCÈS")
        print("="*70 + "\n")
    
    def _create_programme(self) -> str:
        """
        Crée l'enregistrement du programme principal
        
        Returns:
            ID du programme créé
        """
        prog_id = generate_id("prog", "python", "30j")
        
        self.cursor.execute("""
            INSERT INTO programmes (id, titre, sujet, duree_jours, niveau, temps_quotidien, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            prog_id,
            "Apprentissage Python en 30 jours",
            "Python",
            30,
            "débutant",
            2,
            "Programme complet pour apprendre Python de zéro en 1 mois avec pratique intensive"
        ))
        
        self.db.conn.commit()
        print(f"✅ Programme créé: {prog_id}")
        return prog_id
    
    def _create_structure(self, prog_id: str):
        """
        Crée toute la structure hiérarchique (semaines, jours, contenus)
        """
        print("\n📚 Création de la structure du programme...")
        
        # Données du programme Python (structure complète)
        structure = self._get_programme_data()
        
        for sem_num, sem_data in structure.items():
            sem_id = self._create_semaine(prog_id, sem_num, sem_data)
            
            for jour_nom, jour_data in sem_data['jours'].items():
                jour_id = self._create_jour(sem_id, jour_nom, jour_data)
                self._create_contenus(jour_id, jour_nom, jour_data)
        
        self.db.conn.commit()
        print("✅ Structure créée avec succès")
    
    def _create_semaine(self, prog_id: str, sem_num: str, sem_data: dict) -> str:
        """
        Crée une semaine
        """
        numero = int(sem_num.split('_')[1])
        sem_id = generate_id("sem", numero, prog_id)
        
        self.cursor.execute("""
            INSERT INTO semaines (id, programme_id, numero, titre, objectif, temps_quotidien, ordre)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            sem_id,
            prog_id,
            numero,
            sem_data['titre'],
            sem_data['objectif'],
            sem_data['temps_quotidien'],
            numero
        ))
        
        return sem_id
    
    def _create_jour(self, sem_id: str, jour_nom: str, jour_data: dict) -> str:
        """
        Crée un jour
        """
        jour_id = generate_id("jour", jour_nom, sem_id)
        
        # Déterminer le type et l'ordre
        if jour_nom == "weekend":
            type_jour = "weekend"
            ordre = 99  # Toujours à la fin
        elif "jour_" in jour_nom:
            type_jour = "normal"
            ordre = int(jour_nom.split('_')[1])
        else:
            type_jour = "revision"
            ordre = 98
        
        self.cursor.execute("""
            INSERT INTO jours (id, semaine_id, nom, type, ordre)
            VALUES (?, ?, ?, ?, ?)
        """, (
            jour_id,
            sem_id,
            jour_nom,
            type_jour,
            ordre
        ))
        
        return jour_id
    
    def _create_contenus(self, jour_id: str, jour_nom: str, jour_data: dict):
        """
        Crée tous les contenus d'un jour
        """
        ordre = 0
        
        # Contenus théoriques (matin)
        if 'matin' in jour_data:
            for concept in jour_data['matin']:
                ordre += 1
                contenu_id = self._insert_contenu(
                    jour_id, 'theorie', concept, concept, 
                    None, None, 1, 15, ordre
                )
        
        # Exercices
        if 'exercices' in jour_data:
            for exercice in jour_data['exercices']:
                ordre += 1
                
                if isinstance(exercice, dict):
                    # Format détaillé
                    contenu_id = self._insert_contenu(
                        jour_id, 'exercice', 
                        exercice['titre'],
                        exercice['titre'],
                        exercice['enonce'],
                        exercice.get('indice'),
                        2,  # Difficulté moyenne par défaut
                        30,  # 30 min par défaut
                        ordre
                    )
                else:
                    # Format simple (string)
                    contenu_id = self._insert_contenu(
                        jour_id, 'exercice', exercice, exercice,
                        None, None, 2, 30, ordre
                    )
        
        # Projets weekend
        if jour_nom == "weekend" and 'projet' in jour_data:
            ordre += 1
            
            description = jour_data.get('description', '')
            enonce = jour_data.get('enonce_complet', description)
            
            contenu_id = self._insert_contenu(
                jour_id, 'projet',
                jour_data['projet'],
                description,
                enonce,
                None,
                4,  # Difficulté élevée
                180,  # 3 heures
                ordre
            )
        
        # Ressources
        if 'ressources' in jour_data:
            for ressource in jour_data['ressources']:
                ordre += 1
                contenu_id = self._insert_contenu(
                    jour_id, 'ressource', ressource, ressource,
                    None, None, 1, 10, ordre
                )
    
    def _insert_contenu(self, jour_id: str, type_contenu: str, titre: str,
                       description: str, enonce: str, indice: str,
                       difficulte: int, temps_estime: int, ordre: int) -> str:
        """
        Insère un contenu et retourne son ID
        """
        contenu_id = generate_id("cont", type_contenu, ordre, jour_id)
        
        self.cursor.execute("""
            INSERT INTO contenus (id, jour_id, type, titre, description, 
                                 enonce, indice, difficulte, temps_estime, ordre)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            contenu_id, jour_id, type_contenu, titre, description,
            enonce, indice, difficulte, temps_estime, ordre
        ))
        
        # Stocker dans le mapping pour les prérequis
        key = f"{jour_id}_{type_contenu}_{titre[:20]}"
        self.contenu_ids_map[key] = contenu_id
        
        return contenu_id
    
    def _create_prerequis(self):
        """
        Crée les prérequis logiques entre contenus
        """
        print("\n🔗 Création des prérequis logiques...")
        
        prerequis = [
            # Semaine 1
            ("Variables", ["Installation Python"]),
            ("Opérateurs", ["Variables"]),
            ("Conditions", ["Opérateurs"]),
            ("Boucles", ["Conditions"]),
            ("Listes", ["Boucles"]),
            
            # Semaine 2
            ("Dictionnaires", ["Listes"]),
            ("Sets", ["Dictionnaires"]),
            ("Fonctions", ["Listes", "Dictionnaires"]),
            ("Arguments *args", ["Fonctions"]),
            ("Modules", ["Fonctions"]),
            
            # Semaine 3
            ("Classes et objets", ["Fonctions"]),
            ("Héritage", ["Classes et objets"]),
            ("Fichiers", ["Classes et objets"]),
            ("JSON", ["Fichiers"]),
            ("Exceptions", ["Fichiers"]),
            
            # Semaine 4
            ("Comprehensions avancées", ["Listes", "Dictionnaires"]),
            ("Décorateurs", ["Fonctions"]),
            ("Tests unitaires", ["Fonctions", "Classes et objets"]),
        ]
        
        count = 0
        for contenu_titre, prerequis_titres in prerequis:
            contenu_id = self._find_contenu_by_titre_partial(contenu_titre)
            
            if contenu_id:
                for prereq_titre in prerequis_titres:
                    prereq_id = self._find_contenu_by_titre_partial(prereq_titre)
                    
                    if prereq_id and contenu_id != prereq_id:
                        try:
                            self.cursor.execute("""
                                INSERT INTO prerequis (contenu_id, prerequis_contenu_id, obligatoire)
                                VALUES (?, ?, ?)
                            """, (contenu_id, prereq_id, 1))
                            count += 1
                        except:
                            pass  # Ignore doublons
        
        self.db.conn.commit()
        print(f"✅ {count} prérequis créés")
    
    def _find_contenu_by_titre_partial(self, titre_partial: str) -> str:
        """
        Trouve un contenu par titre partiel (recherche LIKE)
        """
        self.cursor.execute("""
            SELECT id FROM contenus 
            WHERE titre LIKE ? 
            ORDER BY ordre 
            LIMIT 1
        """, (f"%{titre_partial}%",))
        
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def _migrate_progression(self):
        """
        Migre la progression depuis ma_progression.json
        """
        print("\n📊 Migration de la progression existante...")
        
        progression_file = "ma_progression.json"
        
        if not os.path.exists(progression_file):
            print("ℹ️  Aucune progression existante à migrer")
            return
        
        try:
            with open(progression_file, 'r', encoding='utf-8') as f:
                progression_data = json.load(f)
            
            count = 0
            
            for key, indices in progression_data.items():
                # key format: "semaine_1_jour_1"
                parts = key.split('_')
                
                if len(parts) >= 4:
                    semaine = f"{parts[0]}_{parts[1]}"
                    jour = f"{parts[2]}_{parts[3]}" if parts[2] != "weekend" else "weekend"
                    
                    # Récupérer les contenus de ce jour
                    jour_id_partial = f"jour_{jour}"
                    
                    self.cursor.execute("""
                        SELECT c.id 
                        FROM contenus c
                        JOIN jours j ON c.jour_id = j.id
                        WHERE j.nom LIKE ?
                        ORDER BY c.ordre
                    """, (f"%{jour}%",))
                    
                    contenus = self.cursor.fetchall()
                    
                    # Marquer comme terminé les contenus validés
                    for index in indices:
                        if index < len(contenus):
                            contenu_id = contenus[index][0]
                            
                            self.cursor.execute("""
                                INSERT OR IGNORE INTO progression 
                                (contenu_id, statut, date_completion)
                                VALUES (?, ?, ?)
                            """, (contenu_id, 'termine', datetime.now()))
                            
                            count += 1
            
            self.db.conn.commit()
            print(f"✅ {count} éléments de progression migrés")
            
        except Exception as e:
            print(f"⚠️  Erreur lors de la migration: {e}")
    
    def _show_statistics(self):
        """
        Affiche les statistiques de la migration
        """
        print("\n📊 STATISTIQUES DE LA MIGRATION:")
        
        stats = self.db.get_statistics()
        
        for table, count in stats.items():
            emoji = {
                'programmes': '📚',
                'semaines': '📅',
                'jours': '🗓️',
                'contenus': '📝',
                'prerequis': '🔗',
                'progression': '✅'
            }.get(table, '•')
            
            print(f"  {emoji} {table.capitalize():20} {count:5} enregistrements")
    
    def _get_programme_data(self) -> dict:
        """
        Retourne la structure complète du programme Python
        (Reproduit les données du programme original)
        """
        return {
            "semaine_1": {
                "titre": "Fondations et syntaxe de base",
                "objectif": "Maîtriser les bases du langage",
                "temps_quotidien": "2h",
                "jours": {
                    "jour_1": {
                        "matin": [
                            "Installation Python + VSCode/PyCharm",
                            "Premier programme : print('Hello World')",
                            "Variables et types de données (int, float, str, bool)"
                        ],
                        "exercices": [
                            {
                                "titre": "Créer 10 variables de types différents",
                                "enonce": "Créez un programme qui déclare et affiche 10 variables...",
                                "indice": "Utilisez print(f'Variable: {ma_var}, Type: {type(ma_var)}')"
                            },
                            {
                                "titre": "Calculatrice simple",
                                "enonce": "Créez un programme qui demande deux nombres...",
                                "indice": "Utilisez input() puis float() pour convertir"
                            },
                            {
                                "titre": "Message personnalisé",
                                "enonce": "Demandez nom, prénom, âge, ville...",
                                "indice": "Utilisez les f-strings"
                            }
                        ],
                        "ressources": ["Documentation Python officielle"]
                    },
                    "jour_2": {
                        "matin": [
                            "Opérateurs (arithmétiques, comparaison, logiques)",
                            "Input utilisateur et conversion de types",
                            "Formatage de strings (f-strings)"
                        ],
                        "exercices": [
                            {
                                "titre": "Convertisseur température",
                                "enonce": "Créez un convertisseur Celsius/Fahrenheit...",
                                "indice": "Utilisez if/else pour choisir la formule"
                            },
                            {
                                "titre": "Calculateur IMC",
                                "enonce": "Calculez l'IMC avec interprétation...",
                                "indice": "Utilisez round(nombre, 2)"
                            }
                        ]
                    },
                    "jour_3": {
                        "matin": [
                            "Structures conditionnelles (if/elif/else)",
                            "Opérateurs logiques combinés",
                            "Conditions imbriquées"
                        ],
                        "exercices": [
                            {
                                "titre": "Pierre-Papier-Ciseaux",
                                "enonce": "Créez le jeu complet...",
                                "indice": "import random"
                            }
                        ]
                    },
                    "jour_4": {
                        "matin": [
                            "Boucles while et for",
                            "Range et énumération",
                            "Break et continue"
                        ],
                        "exercices": [
                            {
                                "titre": "Table de multiplication",
                                "enonce": "Affichez la table de multiplication...",
                                "indice": "Utilisez range(1, 11)"
                            }
                        ]
                    },
                    "jour_5": {
                        "matin": [
                            "Listes : création, manipulation",
                            "Indexation et slicing",
                            "List comprehension"
                        ],
                        "exercices": [
                            {
                                "titre": "Gestionnaire de tâches",
                                "enonce": "Créez un menu avec ajout/suppression...",
                                "indice": "taches = []; taches.append()"
                            }
                        ]
                    },
                    "weekend": {
                        "projet": "Jeu du Pendu",
                        "description": "Intègre listes, boucles, conditions",
                        "enonce_complet": "Créez un jeu du pendu complet avec liste de mots..."
                    }
                }
            },
            "semaine_2": {
                "titre": "Structures de données et fonctions",
                "objectif": "Organiser et réutiliser le code",
                "temps_quotidien": "2h",
                "jours": {
                    "jour_1": {
                        "matin": [
                            "Tuples et leurs utilisations",
                            "Dictionnaires : création et manipulation",
                            "Méthodes des dictionnaires"
                        ],
                        "exercices": []
                    },
                    "jour_2": {
                        "matin": [
                            "Sets : unicité et opérations",
                            "Opérations sur ensembles"
                        ],
                        "exercices": []
                    },
                    "jour_3": {
                        "matin": [
                            "Fonctions : définition et appel",
                            "Paramètres et arguments",
                            "Return et portée"
                        ],
                        "exercices": []
                    },
                    "jour_4": {
                        "matin": [
                            "Arguments *args et **kwargs",
                            "Fonctions lambda"
                        ],
                        "exercices": []
                    },
                    "jour_5": {
                        "matin": [
                            "Modules : import et création",
                            "Packages"
                        ],
                        "exercices": []
                    },
                    "weekend": {
                        "projet": "Gestionnaire de budget",
                        "description": "Application complète"
                    }
                }
            },
            "semaine_3": {
                "titre": "Programmation orientée objet",
                "objectif": "Structurer des programmes complexes",
                "temps_quotidien": "2h",
                "jours": {
                    "jour_1": {
                        "matin": [
                            "Classes et objets : concepts",
                            "__init__ et self"
                        ],
                        "exercices": []
                    },
                    "jour_2": {
                        "matin": [
                            "Encapsulation",
                            "Héritage simple"
                        ],
                        "exercices": []
                    },
                    "jour_3": {
                        "matin": [
                            "Lecture de fichiers texte",
                            "Écriture dans fichiers"
                        ],
                        "exercices": []
                    },
                    "jour_4": {
                        "matin": [
                            "JSON : lecture et écriture",
                            "CSV : manipulation"
                        ],
                        "exercices": []
                    },
                    "jour_5": {
                        "matin": [
                            "Gestion des exceptions",
                            "Try/except/finally"
                        ],
                        "exercices": []
                    },
                    "weekend": {
                        "projet": "Système de bibliothèque",
                        "description": "POO complète"
                    }
                }
            },
            "semaine_4": {
                "titre": "Concepts avancés",
                "objectif": "Consolider et créer un projet",
                "temps_quotidien": "2-3h",
                "jours": {
                    "jour_1": {
                        "matin": [
                            "List/Dict/Set comprehensions avancées",
                            "Générateurs et yield"
                        ],
                        "exercices": []
                    },
                    "jour_2": {
                        "matin": [
                            "Décorateurs : création",
                            "Fonctions de haut niveau"
                        ],
                        "exercices": []
                    },
                    "jour_3": {
                        "matin": [
                            "Introduction aux tests (unittest)",
                            "Tests unitaires simples"
                        ],
                        "exercices": []
                    },
                    "jour_4": {
                        "matin": [
                            "Révision générale",
                            "Refactorisation"
                        ],
                        "exercices": []
                    },
                    "jour_5": {
                        "matin": [
                            "Consolidation concepts",
                            "Antisèche personnelle"
                        ],
                        "exercices": []
                    },
                    "weekend": {
                        "projet": "Projet final",
                        "description": "Application complète professionnelle"
                    }
                }
            }
        }


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

def main():
    """
    Fonction principale de migration
    """
    print("\n" + "="*70)
    print("🔄 SCRIPT DE MIGRATION - PROGRAMME PYTHON → SQLITE")
    print("="*70)
    
    # Demander confirmation
    print("\n⚠️  ATTENTION:")
    print("  • Ce script va créer/réinitialiser la base de données")
    print("  • Une sauvegarde sera créée si la DB existe déjà")
    print("  • La progression existante (ma_progression.json) sera migrée")
    
    reponse = input("\nContinuer ? (oui/non): ").strip().lower()
    
    if reponse != "oui":
        print("\n❌ Migration annulée")
        return
    
    # Créer sauvegarde si la DB existe
    db_path = "learning_programme.db"
    if os.path.exists(db_path):
        DatabaseInitializer.create_backup(db_path)
    
    # Initialiser la base de données
    db = DatabaseInitializer.initialize_new_database(db_path, force=True)
    
    # Exécuter la migration
    migrator = ProgrammeMigrator(db)
    migrator.migrate_all()
    
    # Fermer la connexion
    db.disconnect()
    
    print("\n💡 PROCHAINES ÉTAPES:")
    print("  1. Vérifiez la base de données: learning_programme.db")
    print("  2. Lancez le programme principal: programme_learning_v2.py")
    print("  3. Votre progression a été préservée!")


if __name__ == "__main__":
    main()