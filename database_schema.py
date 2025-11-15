"""
Schéma de base de données SQLite pour l'application d'apprentissage
Gère les programmes, semaines, jours, contenus, prérequis et progression
"""

import sqlite3
from datetime import datetime
from typing import Optional
import os


class DatabaseSchema:
    """
    Gère la création et l'initialisation de la base de données
    """
    
    def __init__(self, db_path: str = "learning_programme.db"):
        """
        Initialise la connexion à la base de données
        
        Args:
            db_path: Chemin vers le fichier de base de données
        """
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """Établit la connexion à la base de données"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
        # Active les clés étrangères (désactivées par défaut dans SQLite)
        self.conn.execute("PRAGMA foreign_keys = ON")
        return self.conn
    
    def disconnect(self):
        """Ferme la connexion à la base de données"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def create_tables(self):
        """
        Crée toutes les tables de la base de données
        """
        cursor = self.conn.cursor()
        
        # Table 1 : PROGRAMMES
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS programmes (
                id TEXT PRIMARY KEY,
                titre TEXT NOT NULL,
                sujet TEXT NOT NULL,
                duree_jours INTEGER,
                niveau TEXT,
                temps_quotidien INTEGER,
                description TEXT,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                actif INTEGER DEFAULT 1
            )
        """)
        
        # Table 2 : SEMAINES
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semaines (
                id TEXT PRIMARY KEY,
                programme_id TEXT NOT NULL,
                numero INTEGER NOT NULL,
                titre TEXT NOT NULL,
                objectif TEXT,
                temps_quotidien TEXT,
                ordre INTEGER,
                FOREIGN KEY (programme_id) REFERENCES programmes(id) ON DELETE CASCADE
            )
        """)
        
        # Table 3 : JOURS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jours (
                id TEXT PRIMARY KEY,
                semaine_id TEXT NOT NULL,
                nom TEXT NOT NULL,
                type TEXT DEFAULT 'normal',
                ordre INTEGER,
                FOREIGN KEY (semaine_id) REFERENCES semaines(id) ON DELETE CASCADE
            )
        """)
        
        # Table 4 : CONTENUS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contenus (
                id TEXT PRIMARY KEY,
                jour_id TEXT NOT NULL,
                type TEXT NOT NULL,
                titre TEXT NOT NULL,
                description TEXT,
                enonce TEXT,
                indice TEXT,
                difficulte INTEGER,
                temps_estime INTEGER,
                ordre INTEGER,
                FOREIGN KEY (jour_id) REFERENCES jours(id) ON DELETE CASCADE
            )
        """)
        
        # Table 5 : PREREQUIS (relation many-to-many)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prerequis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contenu_id TEXT NOT NULL,
                prerequis_contenu_id TEXT NOT NULL,
                obligatoire INTEGER DEFAULT 1,
                FOREIGN KEY (contenu_id) REFERENCES contenus(id) ON DELETE CASCADE,
                FOREIGN KEY (prerequis_contenu_id) REFERENCES contenus(id) ON DELETE CASCADE,
                UNIQUE(contenu_id, prerequis_contenu_id)
            )
        """)
        
        # Table 6 : PROGRESSION
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS progression (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contenu_id TEXT NOT NULL,
                statut TEXT DEFAULT 'non_commence',
                date_debut TIMESTAMP,
                date_completion TIMESTAMP,
                notes TEXT,
                temps_passe INTEGER DEFAULT 0,
                FOREIGN KEY (contenu_id) REFERENCES contenus(id) ON DELETE CASCADE,
                UNIQUE(contenu_id)
            )
        """)
        
        # Index pour optimiser les requêtes fréquentes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_semaines_programme ON semaines(programme_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jours_semaine ON jours(semaine_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contenus_jour ON contenus(jour_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prerequis_contenu ON prerequis(contenu_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_progression_contenu ON progression(contenu_id)")
        
        self.conn.commit()
        print("✅ Tables créées avec succès")
    
    def drop_all_tables(self):
        """
        Supprime toutes les tables (ATTENTION : perte de données)
        Utilisé principalement pour les tests ou réinitialisation complète
        """
        cursor = self.conn.cursor()
        
        tables = ['progression', 'prerequis', 'contenus', 'jours', 'semaines', 'programmes']
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        
        self.conn.commit()
        print("⚠️  Toutes les tables ont été supprimées")
    
    def verify_schema(self) -> bool:
        """
        Vérifie que toutes les tables existent
        
        Returns:
            True si toutes les tables existent, False sinon
        """
        cursor = self.conn.cursor()
        
        expected_tables = ['programmes', 'semaines', 'jours', 'contenus', 'prerequis', 'progression']
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = set(expected_tables) - set(existing_tables)
        
        if missing_tables:
            print(f"❌ Tables manquantes: {missing_tables}")
            return False
        
        print("✅ Toutes les tables existent")
        return True
    
    def get_statistics(self) -> dict:
        """
        Retourne des statistiques sur la base de données
        
        Returns:
            Dictionnaire avec le nombre d'enregistrements par table
        """
        cursor = self.conn.cursor()
        
        stats = {}
        tables = ['programmes', 'semaines', 'jours', 'contenus', 'prerequis', 'progression']
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            stats[table] = count
        
        return stats
    
    def export_schema_info(self) -> str:
        """
        Exporte les informations du schéma pour documentation
        
        Returns:
            String formaté avec les informations de schéma
        """
        cursor = self.conn.cursor()
        
        info = []
        info.append("="*70)
        info.append("SCHÉMA DE BASE DE DONNÉES")
        info.append("="*70)
        
        tables = ['programmes', 'semaines', 'jours', 'contenus', 'prerequis', 'progression']
        
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            info.append(f"\n📋 Table: {table.upper()}")
            info.append("-" * 70)
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                not_null = "NOT NULL" if col[3] else ""
                primary_key = "PRIMARY KEY" if col[5] else ""
                info.append(f"  • {col_name:25} {col_type:15} {not_null:10} {primary_key}")
        
        info.append("\n" + "="*70)
        
        return "\n".join(info)


class DatabaseInitializer:
    """
    Classe utilitaire pour initialiser une nouvelle base de données
    """
    
    @staticmethod
    def initialize_new_database(db_path: str = "learning_programme.db", 
                               force: bool = False) -> DatabaseSchema:
        """
        Initialise une nouvelle base de données
        
        Args:
            db_path: Chemin vers le fichier de base de données
            force: Si True, supprime la DB existante avant de créer
        
        Returns:
            Instance de DatabaseSchema connectée
        """
        if force and os.path.exists(db_path):
            os.remove(db_path)
            print(f"🗑️  Base de données existante supprimée: {db_path}")
        
        db = DatabaseSchema(db_path)
        db.connect()
        db.create_tables()
        
        if db.verify_schema():
            print(f"✅ Base de données initialisée: {db_path}")
        else:
            print(f"❌ Erreur lors de l'initialisation de la base de données")
        
        return db
    
    @staticmethod
    def create_backup(source_db: str, backup_path: Optional[str] = None):
        """
        Crée une sauvegarde de la base de données
        
        Args:
            source_db: Chemin de la DB source
            backup_path: Chemin de sauvegarde (auto-généré si None)
        """
        import shutil
        
        if not os.path.exists(source_db):
            print(f"❌ Base de données source introuvable: {source_db}")
            return
        
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{source_db}.backup_{timestamp}"
        
        shutil.copy2(source_db, backup_path)
        print(f"💾 Sauvegarde créée: {backup_path}")


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def generate_id(prefix: str, *parts) -> str:
    """
    Génère un ID lisible pour les entités
    
    Args:
        prefix: Préfixe de l'ID (prog, sem, jour, cont)
        parts: Parties à inclure dans l'ID
    
    Returns:
        ID formaté (ex: "prog_python_30j", "sem_1_prog_python")
    
    Exemples:
        >>> generate_id("prog", "python", "30j")
        'prog_python_30j'
        >>> generate_id("sem", "1", "prog_python_30j")
        'sem_1_prog_python_30j'
    """
    parts_clean = [str(p).lower().replace(" ", "_") for p in parts]
    return f"{prefix}_{'_'.join(parts_clean)}"


def format_duration(minutes: int) -> str:
    """
    Formate une durée en minutes vers un format lisible
    
    Args:
        minutes: Durée en minutes
    
    Returns:
        Chaîne formatée (ex: "2h30", "45min")
    
    Exemples:
        >>> format_duration(30)
        '30min'
        >>> format_duration(150)
        '2h30'
    """
    if minutes < 60:
        return f"{minutes}min"
    
    hours = minutes // 60
    mins = minutes % 60
    
    if mins == 0:
        return f"{hours}h"
    
    return f"{hours}h{mins:02d}"


def parse_duration(duration_str: str) -> int:
    """
    Parse une chaîne de durée vers des minutes
    
    Args:
        duration_str: Chaîne de durée ("2h", "30min", "2h30")
    
    Returns:
        Durée en minutes
    
    Exemples:
        >>> parse_duration("2h")
        120
        >>> parse_duration("30min")
        30
        >>> parse_duration("2h30")
        150
    """
    duration_str = duration_str.lower().strip()
    
    total_minutes = 0
    
    # Heures
    if 'h' in duration_str:
        parts = duration_str.split('h')
        hours = int(parts[0])
        total_minutes += hours * 60
        
        # Minutes après 'h'
        if len(parts) > 1 and parts[1]:
            mins_part = parts[1].replace('min', '').strip()
            if mins_part:
                total_minutes += int(mins_part)
    
    # Minutes seules
    elif 'min' in duration_str:
        minutes = int(duration_str.replace('min', '').strip())
        total_minutes = minutes
    
    return total_minutes


# ============================================================================
# SCRIPT DE TEST
# ============================================================================

def main():
    """
    Fonction de test pour vérifier le schéma
    """
    print("\n" + "="*70)
    print("TEST DU SCHÉMA DE BASE DE DONNÉES")
    print("="*70 + "\n")
    
    # Initialiser une nouvelle DB de test
    db = DatabaseInitializer.initialize_new_database("test_learning.db", force=True)
    
    # Afficher les informations du schéma
    print("\n" + db.export_schema_info())
    
    # Afficher les statistiques (devrait être vide)
    stats = db.get_statistics()
    print("\n📊 STATISTIQUES DE LA BASE:")
    for table, count in stats.items():
        print(f"  • {table:20} {count:5} enregistrements")
    
    # Test des fonctions utilitaires
    print("\n🧪 TEST DES FONCTIONS UTILITAIRES:")
    
    # Test generate_id
    prog_id = generate_id("prog", "python", "30j")
    print(f"  • ID programme: {prog_id}")
    
    sem_id = generate_id("sem", "1", prog_id)
    print(f"  • ID semaine: {sem_id}")
    
    # Test format_duration
    print(f"  • 45 minutes: {format_duration(45)}")
    print(f"  • 120 minutes: {format_duration(120)}")
    print(f"  • 150 minutes: {format_duration(150)}")
    
    # Test parse_duration
    print(f"  • '2h' = {parse_duration('2h')} minutes")
    print(f"  • '30min' = {parse_duration('30min')} minutes")
    print(f"  • '2h30' = {parse_duration('2h30')} minutes")
    
    # Créer une sauvegarde
    print("\n💾 TEST DE SAUVEGARDE:")
    DatabaseInitializer.create_backup("test_learning.db")
    
    # Nettoyer
    db.disconnect()
    print("\n✅ Tests terminés avec succès!")
    print("\nℹ️  Fichiers créés:")
    print("  • test_learning.db (base de données de test)")
    print("  • test_learning.db.backup_* (sauvegarde)")
    print("\nVous pouvez les supprimer si nécessaire.")


if __name__ == "__main__":
    main()