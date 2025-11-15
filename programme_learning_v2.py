"""
Programme d'apprentissage Python V2 - Avec base de données SQLite
Version flexible et maintenable avec séparation données/code
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from database_schema import DatabaseSchema, format_duration, parse_duration
import json


# ============================================================================
# COUCHE DAO (Data Access Objects)
# ============================================================================

class ProgrammeDAO:
    """Accès aux données des programmes"""
    
    def __init__(self, db: DatabaseSchema):
        self.db = db
    
    def _execute_query(self, query, params=()):
        """Exécute une requête de manière thread-safe"""
        cursor = self.db.conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    
    def _execute_one(self, query, params=()):
        """Exécute une requête et retourne un seul résultat"""
        cursor = self.db.conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            cursor.close()
    
    def get_programme(self, prog_id: str) -> Optional[Dict]:
        """Récupère un programme par ID"""
        row = self._execute_one("""
            SELECT * FROM programmes WHERE id = ? AND actif = 1
        """, (prog_id,))
        
        if row:
            return dict(row)
        return None
    
    def get_all_programmes(self) -> List[Dict]:
        """Récupère tous les programmes actifs"""
        rows = self._execute_query("""
            SELECT * FROM programmes WHERE actif = 1 ORDER BY date_creation DESC
        """)
        
        return [dict(row) for row in rows]
    
    def get_programme_with_stats(self, prog_id: str) -> Dict:
        """Récupère un programme avec ses statistiques"""
        prog = self.get_programme(prog_id)
        if not prog:
            return None
        
        # Compter semaines, jours, contenus
        stats_row = self._execute_one("""
            SELECT COUNT(DISTINCT s.id) as nb_semaines,
                   COUNT(DISTINCT j.id) as nb_jours,
                   COUNT(c.id) as nb_contenus
            FROM semaines s
            LEFT JOIN jours j ON j.semaine_id = s.id
            LEFT JOIN contenus c ON c.jour_id = j.id
            WHERE s.programme_id = ?
        """, (prog_id,))
        
        if stats_row:
            stats = dict(stats_row)
            prog.update(stats)
        
        return prog


class SemaineDAO:
    """Accès aux données des semaines"""
    
    def __init__(self, db: DatabaseSchema):
        self.db = db
    
    def _get_cursor(self):
        """Obtient un cursor frais"""
        return self.db.conn.cursor()
    
    def get_semaines(self, prog_id: str) -> List[Dict]:
        """Récupère toutes les semaines d'un programme"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM semaines 
            WHERE programme_id = ? 
            ORDER BY ordre, numero
        """, (prog_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_semaine(self, sem_id: str) -> Optional[Dict]:
        """Récupère une semaine par ID"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM semaines WHERE id = ?
        """, (sem_id,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


class JourDAO:
    """Accès aux données des jours"""
    
    def __init__(self, db: DatabaseSchema):
        self.db = db
    
    def _get_cursor(self):
        """Obtient un cursor frais"""
        return self.db.conn.cursor()
    
    def get_jours(self, sem_id: str) -> List[Dict]:
        """Récupère tous les jours d'une semaine"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM jours 
            WHERE semaine_id = ? 
            ORDER BY ordre, nom
        """, (sem_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_jour(self, jour_id: str) -> Optional[Dict]:
        """Récupère un jour par ID"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM jours WHERE id = ?
        """, (jour_id,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


class ContenuDAO:
    """Accès aux données des contenus"""
    
    def __init__(self, db: DatabaseSchema):
        self.db = db
    
    def _get_cursor(self):
        """Obtient un cursor frais"""
        return self.db.conn.cursor()
    
    def get_contenus(self, jour_id: str) -> List[Dict]:
        """Récupère tous les contenus d'un jour"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM contenus 
            WHERE jour_id = ? 
            ORDER BY ordre
        """, (jour_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_contenu(self, contenu_id: str) -> Optional[Dict]:
        """Récupère un contenu par ID"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM contenus WHERE id = ?
        """, (contenu_id,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_prerequis(self, contenu_id: str) -> List[Dict]:
        """Récupère les prérequis d'un contenu"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT c.*, p.obligatoire
            FROM prerequis p
            JOIN contenus c ON c.id = p.prerequis_contenu_id
            WHERE p.contenu_id = ?
        """, (contenu_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_contenus_dependants(self, contenu_id: str) -> List[Dict]:
        """Récupère les contenus qui dépendent de celui-ci"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT c.*, p.obligatoire
            FROM prerequis p
            JOIN contenus c ON c.id = p.contenu_id
            WHERE p.prerequis_contenu_id = ?
        """, (contenu_id,))
        
        return [dict(row) for row in cursor.fetchall()]


class ProgressionDAO:
    """Accès aux données de progression"""
    
    def __init__(self, db: DatabaseSchema):
        self.db = db
    
    def _get_cursor(self):
        """Obtient un cursor frais"""
        return self.db.conn.cursor()
    
    def get_progression(self, contenu_id: str) -> Optional[Dict]:
        """Récupère la progression d'un contenu"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM progression WHERE contenu_id = ?
        """, (contenu_id,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def marquer_commence(self, contenu_id: str):
        """Marque un contenu comme commencé"""
        cursor = self._get_cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO progression 
            (contenu_id, statut, date_debut)
            VALUES (?, 'en_cours', ?)
        """, (contenu_id, datetime.now()))
        
        self.db.conn.commit()
    
    def marquer_termine(self, contenu_id: str, temps_passe: int = 0, notes: str = ""):
        """Marque un contenu comme terminé"""
        # Récupérer la progression existante pour garder date_debut
        prog_existante = self.get_progression(contenu_id)
        
        cursor = self._get_cursor()
        if prog_existante:
            cursor.execute("""
                UPDATE progression 
                SET statut = 'termine', 
                    date_completion = ?,
                    temps_passe = ?,
                    notes = ?
                WHERE contenu_id = ?
            """, (datetime.now(), temps_passe, notes, contenu_id))
        else:
            cursor.execute("""
                INSERT INTO progression 
                (contenu_id, statut, date_debut, date_completion, temps_passe, notes)
                VALUES (?, 'termine', ?, ?, ?, ?)
            """, (contenu_id, datetime.now(), datetime.now(), temps_passe, notes))
        
        self.db.conn.commit()
    
    def get_progression_programme(self, prog_id: str) -> Dict:
        """Récupère les statistiques de progression d'un programme"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT c.id) as total_contenus,
                COUNT(DISTINCT CASE WHEN p.statut = 'termine' THEN c.id END) as contenus_termines,
                COUNT(DISTINCT CASE WHEN p.statut = 'en_cours' THEN c.id END) as contenus_en_cours,
                SUM(c.temps_estime) as temps_total_estime,
                SUM(CASE WHEN p.statut = 'termine' THEN p.temps_passe ELSE 0 END) as temps_total_passe
            FROM contenus c
            JOIN jours j ON c.jour_id = j.id
            JOIN semaines s ON j.semaine_id = s.id
            LEFT JOIN progression p ON p.contenu_id = c.id
            WHERE s.programme_id = ?
        """, (prog_id,))
        
        return dict(cursor.fetchone())


# ============================================================================
# COUCHE SERVICE (Logique métier)
# ============================================================================

class ProgrammeService:
    """Service de gestion des programmes"""
    
    def __init__(self, db: DatabaseSchema):
        self.db = db
        self.prog_dao = ProgrammeDAO(db)
        self.sem_dao = SemaineDAO(db)
        self.jour_dao = JourDAO(db)
        self.contenu_dao = ContenuDAO(db)
        self.prog_dao_user = ProgressionDAO(db)
    
    def afficher_programme_complet(self, prog_id: str):
        """Affiche la structure complète d'un programme"""
        prog = self.prog_dao.get_programme_with_stats(prog_id)
        
        if not prog:
            print("❌ Programme introuvable")
            return
        
        print(f"\n{'='*70}")
        print(f"📚 {prog['titre'].upper()}")
        print(f"{'='*70}")
        print(f"🎯 Sujet: {prog['sujet']} | Niveau: {prog['niveau']}")
        print(f"📅 Durée: {prog['duree_jours']} jours | Temps/jour: {prog['temps_quotidien']}h")
        print(f"📊 Structure: {prog['nb_semaines']} semaines, {prog['nb_jours']} jours, {prog['nb_contenus']} contenus")
        
        if prog['description']:
            print(f"\n💡 {prog['description']}")
        
        # Afficher progression
        stats = self.prog_dao_user.get_progression_programme(prog_id)
        pourcentage = (stats['contenus_termines'] / stats['total_contenus'] * 100) if stats['total_contenus'] > 0 else 0
        
        print(f"\n📈 Progression: {stats['contenus_termines']}/{stats['total_contenus']} ({pourcentage:.1f}%)")
        print(f"⏱️  Temps: {format_duration(stats['temps_total_passe'] or 0)} / {format_duration(stats['temps_total_estime'] or 0)}")
    
    def afficher_semaine(self, prog_id: str, numero_semaine: int):
        """Affiche le détail d'une semaine"""
        semaines = self.sem_dao.get_semaines(prog_id)
        semaine = next((s for s in semaines if s['numero'] == numero_semaine), None)
        
        if not semaine:
            print(f"❌ Semaine {numero_semaine} introuvable")
            return
        
        print(f"\n{'='*70}")
        print(f"📚 SEMAINE {semaine['numero']} : {semaine['titre'].upper()}")
        print(f"{'='*70}")
        print(f"🎯 Objectif : {semaine['objectif']}")
        print(f"⏰ Temps quotidien : {semaine['temps_quotidien']}")
        
        # Afficher les jours avec tous leurs contenus
        jours = self.jour_dao.get_jours(semaine['id'])
        
        for jour in jours:
            self._afficher_jour_complet_dans_semaine(jour)
    
    def _afficher_jour_complet_dans_semaine(self, jour: Dict):
        """Affiche un jour avec TOUS ses contenus détaillés"""
        print(f"\n{'-'*70}")
        
        if jour['type'] == 'weekend':
            print(f"🎮 {jour['nom'].upper().replace('_', ' ')}")
        else:
            print(f"📅 {jour['nom'].upper().replace('_', ' ')}")
        
        print(f"{'-'*70}")
        
        contenus = self.contenu_dao.get_contenus(jour['id'])
        
        if not contenus:
            print("   (Aucun contenu)")
            return
        
        # Grouper par type pour un affichage organisé
        theories = [c for c in contenus if c['type'] == 'theorie']
        exercices = [c for c in contenus if c['type'] == 'exercice']
        projets = [c for c in contenus if c['type'] == 'projet']
        ressources = [c for c in contenus if c['type'] == 'ressource']
        
        # Afficher la théorie
        if theories:
            print(f"\n   📖 THÉORIE ({len(theories)} concepts):")
            for i, contenu in enumerate(theories, 1):
                prog = self.prog_dao_user.get_progression(contenu['id'])
                statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                temps = f"({format_duration(contenu['temps_estime'])})" if contenu['temps_estime'] else ""
                print(f"      {statut} {i}. {contenu['titre']} {temps}")
        
        # Afficher les exercices
        if exercices:
            print(f"\n   ✏️  EXERCICES ({len(exercices)}):")
            for i, contenu in enumerate(exercices, 1):
                prog = self.prog_dao_user.get_progression(contenu['id'])
                statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                
                # Difficulté
                difficulte = ""
                if contenu['difficulte']:
                    difficulte = f"[{'⭐' * contenu['difficulte']}]"
                
                temps = f"({format_duration(contenu['temps_estime'])})" if contenu['temps_estime'] else ""
                
                print(f"      {statut} {i}. {contenu['titre']} {difficulte} {temps}")
                
                # Afficher la description courte si disponible
                if contenu['description'] and len(contenu['description']) < 100:
                    print(f"         └─ {contenu['description']}")
        
        # Afficher les projets
        if projets:
            print(f"\n   🎯 PROJET:")
            for contenu in projets:
                prog = self.prog_dao_user.get_progression(contenu['id'])
                statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                
                temps = f"({format_duration(contenu['temps_estime'])})" if contenu['temps_estime'] else ""
                difficulte = f"[{'⭐' * contenu['difficulte']}]" if contenu['difficulte'] else ""
                
                print(f"      {statut} {contenu['titre']} {difficulte} {temps}")
                
                if contenu['description']:
                    # Afficher description tronquée si trop longue
                    desc = contenu['description']
                    if len(desc) > 150:
                        desc = desc[:150] + "..."
                    print(f"         └─ {desc}")
        
        # Afficher les ressources
        if ressources:
            print(f"\n   🔗 RESSOURCES ({len(ressources)}):")
            for i, contenu in enumerate(ressources, 1):
                prog = self.prog_dao_user.get_progression(contenu['id'])
                statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                print(f"      {statut} {i}. {contenu['titre']}")
        
        # Résumé du jour
        temps_total = sum(c['temps_estime'] or 0 for c in contenus)
        termines = sum(1 for c in contenus if self.prog_dao_user.get_progression(c['id']) and 
                      self.prog_dao_user.get_progression(c['id'])['statut'] == 'termine')
        pourcentage = (termines / len(contenus) * 100) if contenus else 0
        
        print(f"\n   📊 Résumé: {termines}/{len(contenus)} terminés ({pourcentage:.0f}%) | ⏱️  {format_duration(temps_total)} estimé")
    
    def _afficher_jour_resume(self, jour: Dict):
        """Affiche un résumé d'un jour (version courte - gardée pour compatibilité)"""
        print(f"\n{'-'*70}")
        
        if jour['type'] == 'weekend':
            print(f"🎮 {jour['nom'].upper().replace('_', ' ')}")
        else:
            print(f"📅 {jour['nom'].upper().replace('_', ' ')}")
        
        contenus = self.contenu_dao.get_contenus(jour['id'])
        
        # Compter par type
        theories = [c for c in contenus if c['type'] == 'theorie']
        exercices = [c for c in contenus if c['type'] == 'exercice']
        projets = [c for c in contenus if c['type'] == 'projet']
        
        if theories:
            print(f"   📖 Théorie: {len(theories)} concepts")
        if exercices:
            print(f"   ✏️  Exercices: {len(exercices)}")
        if projets:
            print(f"   🎯 Projet: {projets[0]['titre']}")
        
        # Temps estimé total
        temps_total = sum(c['temps_estime'] or 0 for c in contenus)
        print(f"   ⏱️  Temps estimé: {format_duration(temps_total)}")
        
        # Progression
        termines = sum(1 for c in contenus if self.prog_dao_user.get_progression(c['id']) and 
                      self.prog_dao_user.get_progression(c['id'])['statut'] == 'termine')
        pourcentage = (termines / len(contenus) * 100) if contenus else 0
        
        statut = "✅" if termines == len(contenus) else "🔄" if termines > 0 else "⏳"
        print(f"   {statut} Progression: {termines}/{len(contenus)} ({pourcentage:.0f}%)")
    
    def afficher_jour_detaille(self, jour_id: str):
        """Affiche le détail complet d'un jour"""
        jour = self.jour_dao.get_jour(jour_id)
        
        if not jour:
            print("❌ Jour introuvable")
            return
        
        print(f"\n{'='*70}")
        print(f"📅 {jour['nom'].upper().replace('_', ' ')}")
        print(f"{'='*70}")
        
        contenus = self.contenu_dao.get_contenus(jour_id)
        
        for i, contenu in enumerate(contenus, 1):
            self._afficher_contenu(contenu, i)
        
        # Résumé
        temps_total = sum(c['temps_estime'] or 0 for c in contenus)
        print(f"\n{'-'*70}")
        print(f"⏱️  Temps total estimé: {format_duration(temps_total)}")
        print(f"📊 {len(contenus)} contenus")
    
    def _afficher_contenu(self, contenu: Dict, numero: int = None):
        """Affiche un contenu avec tous ses détails"""
        # Icône selon type
        icones = {
            'theorie': '📖',
            'exercice': '✏️',
            'projet': '🎯',
            'ressource': '🔗'
        }
        
        icone = icones.get(contenu['type'], '•')
        
        # Statut de progression
        prog = self.prog_dao_user.get_progression(contenu['id'])
        
        if prog:
            if prog['statut'] == 'termine':
                statut = "✅"
            elif prog['statut'] == 'en_cours':
                statut = "🔄"
            else:
                statut = "⬜"
        else:
            statut = "⬜"
        
        # Affichage
        numero_str = f"{numero}. " if numero else ""
        print(f"\n{statut} {icone} {numero_str}{contenu['titre']}")
        
        # Détails
        infos = []
        if contenu['difficulte']:
            etoiles = "⭐" * contenu['difficulte']
            infos.append(f"Difficulté: {etoiles}")
        
        if contenu['temps_estime']:
            infos.append(f"Temps: {format_duration(contenu['temps_estime'])}")
        
        if infos:
            print(f"   {' | '.join(infos)}")
        
        # Prérequis
        prerequis = self.contenu_dao.get_prerequis(contenu['id'])
        if prerequis:
            print(f"   🔗 Prérequis: {len(prerequis)} concept(s)")
            for prereq in prerequis:
                prereq_prog = self.prog_dao_user.get_progression(prereq['id'])
                prereq_status = "✅" if prereq_prog and prereq_prog['statut'] == 'termine' else "⚠️"
                obligatoire = "obligatoire" if prereq['obligatoire'] else "recommandé"
                print(f"      {prereq_status} {prereq['titre']} ({obligatoire})")
        
        # Description si exercice ou projet
        if contenu['type'] in ['exercice', 'projet'] and contenu['description']:
            print(f"   📝 {contenu['description']}")
    
    def verifier_prerequis(self, contenu_id: str) -> Tuple[bool, List[str]]:
        """
        Vérifie si les prérequis d'un contenu sont satisfaits
        
        Returns:
            (True/False, liste des messages d'avertissement)
        """
        prerequis = self.contenu_dao.get_prerequis(contenu_id)
        
        if not prerequis:
            return True, []
        
        messages = []
        prerequis_non_valides = []
        
        for prereq in prerequis:
            prog = self.prog_dao_user.get_progression(prereq['id'])
            
            if not prog or prog['statut'] != 'termine':
                type_prereq = "obligatoire" if prereq['obligatoire'] else "recommandé"
                prerequis_non_valides.append(f"• {prereq['titre']} ({type_prereq})")
        
        if prerequis_non_valides:
            messages.append("⚠️  PRÉREQUIS NON VALIDÉS:")
            messages.extend(prerequis_non_valides)
            messages.append("")
            messages.append("Il est recommandé de valider ces concepts d'abord.")
            return False, messages
        
        return True, ["✅ Tous les prérequis sont validés"]
    
    def suggerer_prochain_contenu(self, prog_id: str) -> Optional[Dict]:
        """Suggère le prochain contenu à étudier"""
        cursor = self.db.conn.cursor()  # ✅ Créer un nouveau cursor
        
        # Trouver les contenus non commencés avec prérequis validés
        cursor.execute("""
            SELECT c.*
            FROM contenus c
            JOIN jours j ON c.jour_id = j.id
            JOIN semaines s ON j.semaine_id = s.id
            LEFT JOIN progression p ON p.contenu_id = c.id
            WHERE s.programme_id = ?
              AND (p.statut IS NULL OR p.statut = 'non_commence')
            ORDER BY s.ordre, j.ordre, c.ordre
            LIMIT 10
        """, (prog_id,))
        
        candidats = [dict(row) for row in cursor.fetchall()]
        cursor.close()  # ✅ Fermer le cursor
        
        # Trouver le premier avec tous les prérequis validés
        for contenu in candidats:
            prerequis_ok, _ = self.verifier_prerequis(contenu['id'])
            if prerequis_ok or not self.contenu_dao.get_prerequis(contenu['id']):
                return contenu
        
        # Si aucun trouvé, retourner le premier quand même
        return candidats[0] if candidats else None


class ProgressionService:
    """Service de gestion de la progression"""
    
    def __init__(self, db: DatabaseSchema):
        self.db = db
        self.prog_dao = ProgressionDAO(db)
        self.contenu_dao = ContenuDAO(db)
        self.programme_service = ProgrammeService(db)
    
    def valider_contenu_interactif(self, contenu_id: str):
        """Marque un contenu comme validé avec saisie interactive"""
        contenu = self.contenu_dao.get_contenu(contenu_id)
        
        if not contenu:
            print("❌ Contenu introuvable")
            return
        
        print(f"\n{'='*70}")
        print(f"✅ Validation de: {contenu['titre']}")
        print(f"{'='*70}")
        
        # Vérifier prérequis
        prerequis_ok, messages = self.programme_service.verifier_prerequis(contenu_id)
        
        if not prerequis_ok:
            for msg in messages:
                print(msg)
            
            continuer = input("\nValider quand même ? (oui/non): ").strip().lower()
            if continuer != 'oui':
                print("❌ Validation annulée")
                return
        
        # Demander le temps passé
        temps_estime = contenu['temps_estime'] or 0
        print(f"\n⏱️  Temps estimé: {format_duration(temps_estime)}")
        
        temps_str = input("Temps réellement passé (ex: 45min, 1h30) [Entrée = estimé]: ").strip()
        
        if temps_str:
            try:
                temps_passe = parse_duration(temps_str)
            except:
                print("⚠️  Format invalide, utilisation du temps estimé")
                temps_passe = temps_estime
        else:
            temps_passe = temps_estime
        
        # Notes optionnelles
        notes = input("Notes personnelles (optionnel): ").strip()
        
        # Marquer comme terminé
        self.prog_dao.marquer_termine(contenu_id, temps_passe, notes)
        
        print(f"\n✅ Contenu validé avec succès!")
        print(f"⏱️  Temps enregistré: {format_duration(temps_passe)}")
        
        # Montrer les contenus débloqués
        dependants = self.contenu_dao.get_contenus_dependants(contenu_id)
        if dependants:
            print(f"\n🔓 Contenus débloqués ({len(dependants)}):")
            for dep in dependants[:3]:  # Montrer les 3 premiers
                print(f"   • {dep['titre']}")
    
    def generer_rapport(self, prog_id: str):
        """Génère un rapport détaillé de progression"""
        print(f"\n{'='*70}")
        print(f"📊 RAPPORT DE PROGRESSION")
        print(f"{'='*70}")
        
        stats = self.prog_dao.get_progression_programme(prog_id)
        
        # Statistiques globales
        pourcentage = (stats['contenus_termines'] / stats['total_contenus'] * 100) if stats['total_contenus'] > 0 else 0
        
        print(f"\n🎯 VUE D'ENSEMBLE:")
        print(f"   Contenus terminés: {stats['contenus_termines']}/{stats['total_contenus']} ({pourcentage:.1f}%)")
        print(f"   En cours: {stats['contenus_en_cours']}")
        print(f"   Temps passé: {format_duration(stats['temps_total_passe'] or 0)}")
        print(f"   Temps estimé total: {format_duration(stats['temps_total_estime'] or 0)}")
        
        # Efficacité
        if stats['temps_total_passe'] and stats['temps_total_estime']:
            ratio = (stats['temps_total_passe'] / stats['temps_total_estime']) * 100
            print(f"   Efficacité: {ratio:.0f}% du temps estimé")
        
        # Progression par semaine
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT 
                s.numero,
                s.titre,
                COUNT(c.id) as total,
                COUNT(CASE WHEN p.statut = 'termine' THEN 1 END) as termines
            FROM semaines s
            JOIN jours j ON j.semaine_id = s.id
            JOIN contenus c ON c.jour_id = j.id
            LEFT JOIN progression p ON p.contenu_id = c.id
            WHERE s.programme_id = ?
            GROUP BY s.id
            ORDER BY s.ordre
        """, (prog_id,))
        
        print(f"\n📚 PAR SEMAINE:")
        for row in cursor.fetchall():
            row = dict(row)
            pct = (row['termines'] / row['total'] * 100) if row['total'] > 0 else 0
            statut = "✅" if row['termines'] == row['total'] else "🔄" if row['termines'] > 0 else "⏳"
            print(f"   {statut} Semaine {row['numero']}: {row['termines']}/{row['total']} ({pct:.0f}%)")
        
        # Suggestions
        print(f"\n💡 SUGGESTIONS:")
        prochain = self.programme_service.suggerer_prochain_contenu(prog_id)
        if prochain:
            print(f"   ➤ Prochain contenu suggéré: {prochain['titre']}")
            print(f"      Type: {prochain['type']} | Temps: {format_duration(prochain['temps_estime'] or 0)}")
        
        # Conseils selon progression
        if pourcentage < 25:
            print("\n   📌 Vous débutez! Concentrez-vous sur les fondamentaux")
            print("   📌 Faites tous les exercices, ne sautez rien")
        elif pourcentage < 50:
            print("\n   📌 Bon rythme! Continuez ainsi")
            print("   📌 Revoyez les concepts non maîtrisés")
        elif pourcentage < 75:
            print("\n   📌 Excellent progrès!")
            print("   📌 Vous pouvez approfondir les concepts avancés")
        else:
            print("\n   📌 Bravo! Vous maîtrisez les fondamentaux")
            print("   📌 Prêt pour des projets plus ambitieux")


# ============================================================================
# INTERFACE UTILISATEUR (Menu)
# ============================================================================

class MenuPrincipal:
    """Menu principal de l'application"""
    
    def __init__(self):
        self.db = DatabaseSchema("learning_programme.db")
        self.db.connect()
        self.programme_service = ProgrammeService(self.db)
        self.progression_service = ProgressionService(self.db)
        self.prog_id = "prog_python_30j"  # Programme par défaut
    
    def run(self):
        """Lance le menu principal"""
        while True:
            self._afficher_menu()
            
            choix = input("\n➤ Votre choix: ").strip()
            
            if choix == "0":
                print("\n👋 À bientôt! Bon apprentissage!")
                break
            
            self._traiter_choix(choix)
            
            input("\n[Appuyez sur Entrée pour continuer]")
    
    def _afficher_menu(self):
        """Affiche le menu"""
        print(f"\n{'='*70}")
        print("📚 PROGRAMME D'APPRENTISSAGE PYTHON")
        print(f"{'='*70}")
        print("1. Vue d'ensemble du programme")
        print("2. Afficher une semaine")
        print("3. Afficher un jour en détail")
        print("4. Valider un contenu")
        print("5. Voir mon rapport de progression")
        print("6. Suggestion: prochain contenu")
        print("7. Rechercher un contenu")
        print("0. Quitter")
        print(f"{'='*70}")
    
    def _traiter_choix(self, choix: str):
        """Traite le choix de l'utilisateur"""
        if choix == "1":
            self.programme_service.afficher_programme_complet(self.prog_id)
        
        elif choix == "2":
            try:
                num = int(input("Numéro de la semaine (1-4): "))
                self.programme_service.afficher_semaine(self.prog_id, num)
            except ValueError:
                print("❌ Numéro invalide")
        
        elif choix == "3":
            self._menu_afficher_jour()
        
        elif choix == "4":
            self._menu_valider_contenu()
        
        elif choix == "5":
            self.progression_service.generer_rapport(self.prog_id)
        
        elif choix == "6":
            prochain = self.programme_service.suggerer_prochain_contenu(self.prog_id)
            if prochain:
                print(f"\n💡 PROCHAIN CONTENU SUGGÉRÉ:")
                self.programme_service._afficher_contenu(prochain)
                
                commencer = input("\nAfficher les détails complets? (oui/non): ").strip().lower()
                if commencer == 'oui':
                    self._afficher_contenu_complet(prochain['id'])
            else:
                print("\n✅ Félicitations! Vous avez terminé tout le programme!")
        
        elif choix == "7":
            self._menu_recherche()
        
        else:
            print("❌ Choix invalide")
    
    def _menu_afficher_jour(self):
        """Menu pour afficher un jour"""
        print("\n📅 SÉLECTION D'UN JOUR:")
        
        try:
            num_sem = int(input("Semaine (1-4): "))
            
            # Récupérer la semaine
            semaines = self.programme_service.sem_dao.get_semaines(self.prog_id)
            semaine = next((s for s in semaines if s['numero'] == num_sem), None)
            
            if not semaine:
                print(f"❌ Semaine {num_sem} introuvable")
                return
            
            # Afficher les jours disponibles
            jours = self.programme_service.jour_dao.get_jours(semaine['id'])
            
            print(f"\nJours disponibles:")
            for i, jour in enumerate(jours, 1):
                print(f"   {i}. {jour['nom'].replace('_', ' ')}")
            
            num_jour = int(input("\nNuméro du jour: "))
            
            if 1 <= num_jour <= len(jours):
                self.programme_service.afficher_jour_detaille(jours[num_jour-1]['id'])
            else:
                print("❌ Numéro de jour invalide")
                
        except ValueError:
            print("❌ Entrée invalide")
    
    def _menu_valider_contenu(self):
        """Menu pour valider un contenu"""
        print("\n✅ VALIDATION D'UN CONTENU:")
        print("Vous pouvez:")
        print("1. Chercher par titre")
        print("2. Naviguer par semaine/jour")
        
        choix = input("\nVotre choix: ").strip()
        
        if choix == "1":
            titre = input("Entrez une partie du titre: ").strip()
            contenus = self._rechercher_contenus(titre)
            
            if not contenus:
                print("❌ Aucun contenu trouvé")
                return
            
            print(f"\n{len(contenus)} résultat(s):")
            for i, contenu in enumerate(contenus, 1):
                prog = self.progression_service.prog_dao.get_progression(contenu['id'])
                statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                print(f"   {i}. {statut} {contenu['titre']}")
            
            try:
                num = int(input("\nNuméro à valider (0 pour annuler): "))
                if num > 0 and num <= len(contenus):
                    self.progression_service.valider_contenu_interactif(contenus[num-1]['id'])
            except ValueError:
                print("❌ Numéro invalide")
        
        elif choix == "2":
            try:
                num_sem = int(input("Semaine (1-4): "))
                semaines = self.programme_service.sem_dao.get_semaines(self.prog_id)
                semaine = next((s for s in semaines if s['numero'] == num_sem), None)
                
                if not semaine:
                    print(f"❌ Semaine {num_sem} introuvable")
                    return
                
                jours = self.programme_service.jour_dao.get_jours(semaine['id'])
                print(f"\nJours disponibles:")
                for i, jour in enumerate(jours, 1):
                    print(f"   {i}. {jour['nom'].replace('_', ' ')}")
                
                num_jour = int(input("\nNuméro du jour: "))
                
                if 1 <= num_jour <= len(jours):
                    contenus = self.programme_service.contenu_dao.get_contenus(jours[num_jour-1]['id'])
                    
                    print(f"\nContenus:")
                    for i, contenu in enumerate(contenus, 1):
                        prog = self.progression_service.prog_dao.get_progression(contenu['id'])
                        statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                        print(f"   {i}. {statut} {contenu['titre']}")
                    
                    num_cont = int(input("\nNuméro à valider (0 pour annuler): "))
                    if num_cont > 0 and num_cont <= len(contenus):
                        self.progression_service.valider_contenu_interactif(contenus[num_cont-1]['id'])
                
            except ValueError:
                print("❌ Entrée invalide")
    
    def _menu_recherche(self):
        """Menu de recherche de contenus"""
        print("\n🔍 RECHERCHE DE CONTENUS:")
        
        terme = input("Entrez un mot-clé (titre ou description): ").strip()
        
        if not terme:
            return
        
        contenus = self._rechercher_contenus(terme)
        
        if not contenus:
            print(f"\n❌ Aucun résultat pour '{terme}'")
            return
        
        print(f"\n✅ {len(contenus)} résultat(s) trouvé(s):\n")
        
        for i, contenu in enumerate(contenus, 1):
            self.programme_service._afficher_contenu(contenu, i)
        
        # Option pour afficher les détails d'un contenu
        voir_details = input("\nVoir les détails d'un contenu? (numéro ou 0 pour annuler): ").strip()
        
        try:
            num = int(voir_details)
            if num > 0 and num <= len(contenus):
                self._afficher_contenu_complet(contenus[num-1]['id'])
        except ValueError:
            pass
    
    def _rechercher_contenus(self, terme: str) -> List[Dict]:
        """Recherche des contenus par terme"""
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM contenus
            WHERE titre LIKE ? OR description LIKE ?
            ORDER BY ordre
        """, (f"%{terme}%", f"%{terme}%"))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def _afficher_contenu_complet(self, contenu_id: str):
        """Affiche tous les détails d'un contenu"""
        contenu = self.programme_service.contenu_dao.get_contenu(contenu_id)
        
        if not contenu:
            print("❌ Contenu introuvable")
            return
        
        print(f"\n{'='*70}")
        print(f"📝 {contenu['titre'].upper()}")
        print(f"{'='*70}")
        
        # Informations générales
        print(f"\n📌 Type: {contenu['type']}")
        
        if contenu['difficulte']:
            print(f"⭐ Difficulté: {'⭐' * contenu['difficulte']}")
        
        if contenu['temps_estime']:
            print(f"⏱️  Temps estimé: {format_duration(contenu['temps_estime'])}")
        
        # Description
        if contenu['description']:
            print(f"\n📖 Description:")
            print(f"   {contenu['description']}")
        
        # Énoncé (pour exercices et projets)
        if contenu['enonce']:
            print(f"\n📋 Énoncé:")
            print(f"{contenu['enonce']}")
        
        # Indice
        if contenu['indice']:
            voir_indice = input("\n💡 Un indice est disponible. L'afficher? (oui/non): ").strip().lower()
            if voir_indice == 'oui':
                print(f"\n💡 Indice: {contenu['indice']}")
        
        # Prérequis
        prerequis = self.programme_service.contenu_dao.get_prerequis(contenu_id)
        if prerequis:
            print(f"\n🔗 PRÉREQUIS:")
            for prereq in prerequis:
                prog = self.progression_service.prog_dao.get_progression(prereq['id'])
                statut = "✅" if prog and prog['statut'] == 'termine' else "⚠️"
                obligatoire = "obligatoire" if prereq['obligatoire'] else "recommandé"
                print(f"   {statut} {prereq['titre']} ({obligatoire})")
        
        # Progression
        prog = self.progression_service.prog_dao.get_progression(contenu_id)
        
        print(f"\n{'='*70}")
        print(f"📊 PROGRESSION:")
        
        if prog:
            print(f"   Statut: {prog['statut']}")
            
            if prog['date_debut']:
                print(f"   Débuté le: {prog['date_debut']}")
            
            if prog['statut'] == 'termine':
                print(f"   ✅ Terminé le: {prog['date_completion']}")
                if prog['temps_passe']:
                    print(f"   ⏱️  Temps passé: {format_duration(prog['temps_passe'])}")
                if prog['notes']:
                    print(f"   📝 Notes: {prog['notes']}")
        else:
            print(f"   ⬜ Non commencé")
        
        print(f"{'='*70}")
        
        # Actions possibles
        if not prog or prog['statut'] != 'termine':
            valider = input("\n➤ Marquer comme terminé? (oui/non): ").strip().lower()
            if valider == 'oui':
                self.progression_service.valider_contenu_interactif(contenu_id)
    
    def cleanup(self):
        """Nettoie les ressources"""
        if self.db:
            self.db.disconnect()


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

def main():
    """
    Fonction principale
    """
    # Vérifier que la base de données existe
    if not os.path.exists("learning_programme.db"):
        print("\n❌ ERREUR: Base de données introuvable!")
        print("\n📋 Veuillez d'abord exécuter:")
        print("   1. python database_schema.py (créer le schéma)")
        print("   2. python migration_script.py (migrer les données)")
        print("\nPuis relancez ce programme.")
        return
    
    # Lancer le menu
    menu = MenuPrincipal()
    
    try:
        menu.run()
    except KeyboardInterrupt:
        print("\n\n👋 Programme interrompu")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        menu.cleanup()


if __name__ == "__main__":
    import os
    main()