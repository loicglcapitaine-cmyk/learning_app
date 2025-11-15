"""
Interface Streamlit pour le programme d'apprentissage
"""

import streamlit as st
from database_schema import DatabaseSchema
from programme_learning_v2 import ProgrammeService, ProgressionService
import os

# Configuration de la page
st.set_page_config(
    page_title="Programme d'apprentissage Python",
    page_icon="📚",
    layout="wide"
)

# Initialisation de la base de données
@st.cache_resource
def init_database():
    """Initialise la connexion à la base de données"""
    db_path = "learning_programme.db"
    
    # Si la DB n'existe pas, la créer et la peupler
    if not os.path.exists(db_path):
        st.warning("Base de données non trouvée, création en cours...")
        from database_schema import DatabaseInitializer
        from migration_script import ProgrammeMigrator
        
        db = DatabaseInitializer.initialize_new_database(db_path)
        migrator = ProgrammeMigrator(db)
        migrator.migrate_all()
        st.success("Base de données créée avec succès!")
    
    db = DatabaseSchema(db_path)
    db.connect()
    return db

# Initialiser
db = init_database()
programme_service = ProgrammeService(db)
progression_service = ProgressionService(db)

# Identifiant du programme (à adapter si vous en avez plusieurs)
PROG_ID = "prog_python_30j"

# ============================================================================
# SIDEBAR : Navigation
# ============================================================================

st.sidebar.title("📚 Navigation")
page = st.sidebar.radio(
    "Choisissez une page",
    ["🏠 Accueil", "📅 Semaines", "📊 Ma progression", "🔍 Recherche", "✅ Valider un contenu"]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Astuce**: Explorez les différentes sections pour suivre votre progression!")

# ============================================================================
# PAGE : ACCUEIL
# ============================================================================

if page == "🏠 Accueil":
    st.title("📚 Programme d'apprentissage Python")
    st.markdown("### Apprenez Python en 30 jours avec un programme structuré")
    
    # Récupérer les infos du programme
    prog = programme_service.prog_dao.get_programme_with_stats(PROG_ID)
    
    if prog:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📅 Durée", f"{prog['duree_jours']} jours")
        
        with col2:
            st.metric("📚 Semaines", prog['nb_semaines'])
        
        with col3:
            st.metric("🗓️ Jours", prog['nb_jours'])
        
        with col4:
            st.metric("📝 Contenus", prog['nb_contenus'])
        
        st.markdown("---")
        
        # Statistiques de progression
        stats = progression_service.prog_dao.get_progression_programme(PROG_ID)
        pourcentage = (stats['contenus_termines'] / stats['total_contenus'] * 100) if stats['total_contenus'] > 0 else 0
        
        st.subheader("📈 Votre progression")
        st.progress(pourcentage / 100)
        st.write(f"**{stats['contenus_termines']} / {stats['total_contenus']}** contenus terminés ({pourcentage:.1f}%)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"🔄 En cours : {stats['contenus_en_cours']}")
        
        with col2:
            temps_passe = stats['temps_total_passe'] or 0
            st.info(f"⏱️ Temps passé : {temps_passe // 60}h{temps_passe % 60:02d}")
        
        st.markdown("---")
        
        # Suggestion de contenu
        st.subheader("💡 Prochain contenu suggéré")
        prochain = programme_service.suggerer_prochain_contenu(PROG_ID)
        
        if prochain:
            with st.container():
                st.markdown(f"### {prochain['titre']}")
                st.write(f"**Type**: {prochain['type']} | **Difficulté**: {'⭐' * (prochain['difficulte'] or 1)}")
                
                if prochain['description']:
                    st.write(prochain['description'])
                
                if st.button("📖 Voir les détails", key="detail_prochain"):
                    st.session_state['page_detail'] = prochain['id']
        else:
            st.success("🎉 Félicitations ! Vous avez terminé tout le programme !")

# ============================================================================
# PAGE : SEMAINES
# ============================================================================

elif page == "📅 Semaines":
    st.title("📅 Vue par semaines")
    
    # Sélecteur de semaine
    semaines = programme_service.sem_dao.get_semaines(PROG_ID)
    semaine_options = {f"Semaine {s['numero']} : {s['titre']}": s for s in semaines}
    
    semaine_selectionnee = st.selectbox(
        "Choisissez une semaine",
        options=list(semaine_options.keys())
    )
    
    if semaine_selectionnee:
        semaine = semaine_options[semaine_selectionnee]
        
        st.markdown(f"## Semaine {semaine['numero']} : {semaine['titre']}")
        st.markdown(f"**🎯 Objectif** : {semaine['objectif']}")
        st.markdown(f"**⏰ Temps quotidien** : {semaine['temps_quotidien']}")
        
        st.markdown("---")
        
        # Afficher les jours
        jours = programme_service.jour_dao.get_jours(semaine['id'])
        
        for jour in jours:
            with st.expander(f"{'🎮' if jour['type'] == 'weekend' else '📅'} {jour['nom'].replace('_', ' ').title()}", expanded=False):
                contenus = programme_service.contenu_dao.get_contenus(jour['id'])
                
                if contenus:
                    # Grouper par type
                    theories = [c for c in contenus if c['type'] == 'theorie']
                    exercices = [c for c in contenus if c['type'] == 'exercice']
                    projets = [c for c in contenus if c['type'] == 'projet']
                    
                    if theories:
                        st.markdown("#### 📖 Théorie")
                        for t in theories:
                            prog = progression_service.prog_dao.get_progression(t['id'])
                            statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                            st.write(f"{statut} {t['titre']}")
                    
                    if exercices:
                        st.markdown("#### ✏️ Exercices")
                        for e in exercices:
                            prog = progression_service.prog_dao.get_progression(e['id'])
                            statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                            difficulte = "⭐" * (e['difficulte'] or 1)
                            st.write(f"{statut} {e['titre']} [{difficulte}]")
                    
                    if projets:
                        st.markdown("#### 🎯 Projet")
                        for p in projets:
                            prog = progression_service.prog_dao.get_progression(p['id'])
                            statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                            st.write(f"{statut} **{p['titre']}**")
                            if p['description']:
                                st.caption(p['description'])

# ============================================================================
# PAGE : MA PROGRESSION
# ============================================================================

elif page == "📊 Ma progression":
    st.title("📊 Ma progression")
    
    stats = progression_service.prog_dao.get_progression_programme(PROG_ID)
    
    # Vue d'ensemble
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Contenus terminés",
            f"{stats['contenus_termines']}/{stats['total_contenus']}",
            delta=f"{(stats['contenus_termines']/stats['total_contenus']*100):.1f}%"
        )
    
    with col2:
        st.metric("En cours", stats['contenus_en_cours'])
    
    with col3:
        temps_h = (stats['temps_total_passe'] or 0) // 60
        temps_m = (stats['temps_total_passe'] or 0) % 60
        st.metric("Temps passé", f"{temps_h}h{temps_m:02d}")
    
    st.markdown("---")
    
    # Progression par semaine
    st.subheader("📚 Progression par semaine")
    
    cursor = db.conn.cursor()
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
    """, (PROG_ID,))
    
    for row in cursor.fetchall():
        row = dict(row)
        pct = (row['termines'] / row['total'] * 100) if row['total'] > 0 else 0
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.progress(pct / 100)
            st.caption(f"Semaine {row['numero']}: {row['titre']}")
        
        with col2:
            st.write(f"{row['termines']}/{row['total']}")

# ============================================================================
# PAGE : RECHERCHE
# ============================================================================

elif page == "🔍 Recherche":
    st.title("🔍 Recherche de contenus")
    
    terme = st.text_input("🔎 Rechercher un contenu (titre ou description)", "")
    
    if terme:
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT * FROM contenus
            WHERE titre LIKE ? OR description LIKE ?
            ORDER BY ordre
            LIMIT 20
        """, (f"%{terme}%", f"%{terme}%"))
        
        resultats = [dict(row) for row in cursor.fetchall()]
        
        if resultats:
            st.success(f"✅ {len(resultats)} résultat(s) trouvé(s)")
            
            for contenu in resultats:
                with st.expander(f"{'📖' if contenu['type'] == 'theorie' else '✏️' if contenu['type'] == 'exercice' else '🎯'} {contenu['titre']}"):
                    prog = progression_service.prog_dao.get_progression(contenu['id'])
                    statut = "✅ Terminé" if prog and prog['statut'] == 'termine' else "⬜ Non commencé"
                    
                    st.write(f"**Statut**: {statut}")
                    
                    if contenu['description']:
                        st.write(contenu['description'])
                    
                    if contenu['difficulte']:
                        st.write(f"**Difficulté**: {'⭐' * contenu['difficulte']}")
        else:
            st.warning(f"Aucun résultat pour '{terme}'")

# ============================================================================
# PAGE : VALIDER UN CONTENU
# ============================================================================

elif page == "✅ Valider un contenu":
    st.title("✅ Valider un contenu")
    
    st.info("💡 Recherchez un contenu pour le marquer comme terminé")
    
    # Recherche
    terme = st.text_input("🔎 Rechercher", "")
    
    if terme:
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT c.*, 
                   CASE WHEN p.statut = 'termine' THEN 1 ELSE 0 END as est_termine
            FROM contenus c
            LEFT JOIN progression p ON p.contenu_id = c.id
            WHERE (c.titre LIKE ? OR c.description LIKE ?)
              AND (p.statut IS NULL OR p.statut != 'termine')
            ORDER BY c.ordre
            LIMIT 10
        """, (f"%{terme}%", f"%{terme}%"))
        
        resultats = [dict(row) for row in cursor.fetchall()]
        
        if resultats:
            contenu_selectionne = st.selectbox(
                "Choisissez un contenu à valider",
                options=range(len(resultats)),
                format_func=lambda i: f"{'📖' if resultats[i]['type'] == 'theorie' else '✏️'} {resultats[i]['titre']}"
            )
            
            contenu = resultats[contenu_selectionne]
            
            st.markdown("---")
            st.markdown(f"### {contenu['titre']}")
            
            if contenu['description']:
                st.write(contenu['description'])