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
                                "enonce": """**Objectif**: Maîtriser la déclaration de variables et les types de données en Python.

**Instructions détaillées**:

1. **Variables numériques entières (int)** :
   - Créez `age` = votre âge
   - Créez `annee_naissance` = année de votre naissance
   - Créez `nombre_freres_soeurs` = nombre de frères et sœurs

2. **Variables numériques décimales (float)** :
   - Créez `taille` = votre taille en mètres (ex: 1.75)
   - Créez `temperature` = température actuelle (ex: 22.5)

3. **Variables textuelles (str)** :
   - Créez `prenom` = votre prénom
   - Créez `ville` = votre ville
   - Créez `citation` = une citation que vous aimez

4. **Variables booléennes (bool)** :
   - Créez `est_majeur` = True ou False selon votre âge
   - Créez `aime_python` = True

**Bonus** :
Pour chaque variable, affichez :
```python
print(f"Variable: {ma_variable}, Type: {type(ma_variable)}, Valeur: {ma_variable}")
```

**Résultat attendu** :
```
Variable: age, Type: <class 'int'>, Valeur: 25
Variable: taille, Type: <class 'float'>, Valeur: 1.75
Variable: prenom, Type: <class 'str'>, Valeur: Jean
...
```

**Critères de réussite** :
✅ 10 variables créées de types variés
✅ Affichage du type de chaque variable
✅ Code exécutable sans erreur""",
                                "indice": "Utilisez print(f'Variable: {ma_var}, Type: {type(ma_var)}')"
                            },
                            {
                                "titre": "Calculatrice simple",
                                "enonce": """**Objectif**: Créer une calculatrice interactive qui demande deux nombres et effectue les 4 opérations de base.

**Spécifications** :

1. **Demander les nombres** :
   - Demandez le premier nombre à l'utilisateur
   - Demandez le deuxième nombre à l'utilisateur
   - Convertissez-les en `float` pour accepter les décimales

2. **Effectuer les calculs** :
   - Addition : `nombre1 + nombre2`
   - Soustraction : `nombre1 - nombre2`
   - Multiplication : `nombre1 * nombre2`
   - Division : `nombre1 / nombre2`

3. **Afficher les résultats** :
   Format attendu :
   ```
   Premier nombre: 10
   Deuxième nombre: 3
   
   === RÉSULTATS ===
   10 + 3 = 13
   10 - 3 = 7
   10 * 3 = 30
   10 / 3 = 3.33
   ```

**Code de base** :
```python
# Demander les nombres
nombre1 = float(input("Premier nombre: "))
nombre2 = float(input("Deuxième nombre: "))

# À vous de jouer !
```

**Bonus** :
- Ajoutez la division entière : `nombre1 // nombre2`
- Ajoutez le modulo (reste) : `nombre1 % nombre2`
- Ajoutez la puissance : `nombre1 ** nombre2`
- Gérez le cas de la division par zéro

**Critères de réussite** :
✅ Programme demande bien 2 nombres
✅ Les 4 opérations sont calculées
✅ Affichage clair et formaté
✅ Fonctionne avec des décimales""",
                                "indice": "Utilisez float(input()) pour convertir l'entrée utilisateur en nombre"
                            },
                            {
                                "titre": "Message personnalisé",
                                "enonce": """**Objectif**: Créer un programme qui collecte des informations personnelles et génère un message de bienvenue personnalisé.

**Étape 1 : Collecter les informations**
Demandez à l'utilisateur :
- Son prénom
- Son nom de famille
- Son âge
- Sa ville de résidence

**Étape 2 : Créer le message**
Générez un message qui contient toutes ces informations de manière naturelle.

**Exemple d'exécution** :
```
=== FORMULAIRE D'INSCRIPTION ===
Prénom: Jean
Nom: Dupont
Âge: 25
Ville: Paris

=== MESSAGE DE BIENVENUE ===
Bonjour Jean Dupont !
Vous avez 25 ans et habitez à Paris.
Bienvenue dans notre programme d'apprentissage Python !
```

**Structure recommandée** :
```python
# Collecte des informations
prenom = input("Prénom: ")
# ... à compléter

# Génération du message
message = f"Bonjour {prenom} {nom} !"
# ... à compléter

print(message)
```

**Bonus** :
- Ajoutez une vérification : si l'âge < 18, ajoutez "Tu es mineur(e)"
- Mettez la première lettre en majuscule même si l'utilisateur écrit en minuscules
- Ajoutez une question "Êtes-vous étudiant ? (oui/non)" et adaptez le message
- Calculez l'année de naissance à partir de l'âge

**Critères de réussite** :
✅ 4 informations collectées
✅ Message personnalisé et formaté
✅ Utilisation des f-strings
✅ Affichage professionnel""",
                                "indice": "Utilisez les f-strings : f'Bonjour {prenom} {nom}!'"
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
                                "enonce": """**Objectif**: Créer un convertisseur bidirectionnel Celsius ↔ Fahrenheit

**Contexte** :
Les formules de conversion sont :
- **Celsius → Fahrenheit** : (C × 9/5) + 32
- **Fahrenheit → Celsius** : (F - 32) × 5/9

**Spécifications** :

1. **Menu de choix** :
   ```
   === CONVERTISSEUR DE TEMPÉRATURE ===
   1. Celsius vers Fahrenheit
   2. Fahrenheit vers Celsius
   Votre choix (1 ou 2): _
   ```

2. **Demander la température** :
   - Demander la valeur à convertir
   - Afficher le résultat avec 2 décimales

**Exemple d'exécution 1** :
```
Votre choix: 1
Température en Celsius: 25
25°C = 77.0°F
```

**Exemple d'exécution 2** :
```
Votre choix: 2
Température en Fahrenheit: 77
77°F = 25.0°C
```

**Structure de base** :
```python
print("=== CONVERTISSEUR DE TEMPÉRATURE ===")
print("1. Celsius vers Fahrenheit")
print("2. Fahrenheit vers Celsius")

choix = input("Votre choix (1 ou 2): ")

if choix == "1":
    celsius = float(input("Température en Celsius: "))
    # Votre code ici
    
elif choix == "2":
    fahrenheit = float(input("Température en Fahrenheit: "))
    # Votre code ici
```

**Bonus** :
- Ajoutez la conversion vers Kelvin
- Ajoutez des validations (température > -273.15°C)
- Créez une boucle pour refaire des conversions
- Affichez des messages selon la température (chaud/froid)

**Critères de réussite** :
✅ Menu de choix fonctionnel
✅ Les deux conversions fonctionnent
✅ Résultats affichés avec 2 décimales
✅ Symboles °C et °F affichés""",
                                "indice": "Utilisez if/elif pour choisir la formule selon le choix"
                            },
                            {
                                "titre": "Calculateur IMC",
                                "enonce": """**Objectif**: Calculer l'Indice de Masse Corporelle et donner une interprétation médicale

**Contexte** :
L'IMC (Indice de Masse Corporelle) est calculé par : **IMC = poids / (taille²)**
- Poids en kilogrammes
- Taille en mètres

**Classification OMS** :
- IMC < 18.5 : Insuffisance pondérale
- IMC 18.5-24.9 : Poids normal
- IMC 25-29.9 : Surpoids
- IMC ≥ 30 : Obésité

**Spécifications** :

1. **Collecte des données** :
   ```
   === CALCULATEUR D'IMC ===
   Entrez votre poids (kg): 70
   Entrez votre taille (m): 1.75
   ```

2. **Calcul et affichage** :
   ```
   Votre IMC: 22.86
   Interprétation: Poids normal
   Vous êtes dans une fourchette de poids santé.
   ```

**Structure complète** :
```python
print("=== CALCULATEUR D'IMC ===")

# 1. Demander les données
poids = float(input("Entrez votre poids (kg): "))
taille = float(input("Entrez votre taille (m): "))

# 2. Calculer l'IMC
imc = poids / (taille ** 2)
imc_arrondi = round(imc, 2)

# 3. Interpréter
if imc < 18.5:
    categorie = "Insuffisance pondérale"
    message = "Vous pourriez avoir besoin de prendre du poids."
elif imc < 25:
    categorie = "Poids normal"
    message = "Vous êtes dans une fourchette de poids santé."
# À compléter...

# 4. Afficher
print(f"Votre IMC: {imc_arrondi}")
print(f"Interprétation: {categorie}")
print(message)
```

**Bonus** :
- Ajoutez des emoji selon la catégorie (😊 pour normal, ⚠️ pour les autres)
- Calculez le poids idéal pour un IMC de 22
- Ajoutez une validation (poids et taille > 0)
- Créez un graphique ASCII montrant la position sur l'échelle

**Critères de réussite** :
✅ IMC calculé correctement
✅ Résultat arrondi à 2 décimales
✅ Interprétation selon les 4 catégories
✅ Message personnalisé affiché""",
                                "indice": "Utilisez round(nombre, 2) pour arrondir à 2 décimales"
                            },
                            {
                                "titre": "Vérificateur de nombre",
                                "enonce": """**Objectif**: Analyser un nombre et déterminer ses propriétés mathématiques

**Spécifications** :

Créez un programme qui demande un nombre entier et vérifie :
1. S'il est **pair** ou **impair**
2. S'il est **divisible par 3**
3. S'il est **divisible par 5**
4. S'il est **divisible par 7**

**Exemple d'exécution 1** :
```
Entrez un nombre: 15

Analyse du nombre 15:
✓ Nombre impair
✓ Divisible par 3
✓ Divisible par 5
✗ Non divisible par 7
```

**Exemple d'exécution 2** :
```
Entrez un nombre: 14

Analyse du nombre 14:
✓ Nombre pair
✗ Non divisible par 3
✗ Non divisible par 5
✓ Divisible par 7
```

**Rappels mathématiques** :
- Un nombre est **pair** si `nombre % 2 == 0`
- Un nombre est **divisible par N** si `nombre % N == 0`

**Structure recommandée** :
```python
nombre = int(input("Entrez un nombre: "))

print(f"\\nAnalyse du nombre {nombre}:")

# Pair ou impair
if nombre % 2 == 0:
    print("✓ Nombre pair")
else:
    print("✗ Nombre impair")

# Divisible par 3
if nombre % 3 == 0:
    print("✓ Divisible par 3")
else:
    print("✗ Non divisible par 3")

# À compléter pour 5 et 7...
```

**Bonus** :
- Ajoutez la vérification de divisibilité par 10
- Si divisible par 3 ET 5, affichez "Divisible par 15 !"
- Vérifiez si c'est un nombre premier
- Affichez tous les diviseurs du nombre
- Ajoutez des couleurs (si vous utilisez colorama)

**Critères de réussite** :
✅ Vérification pair/impair
✅ Vérification divisibilité par 3, 5, 7
✅ Affichage clair avec ✓ et ✗
✅ Fonctionne avec n'importe quel nombre entier""",
                                "indice": "L'opérateur modulo % donne le reste : 15 % 3 = 0 donc divisible"
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
