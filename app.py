"""
Interface Streamlit pour le programme d'apprentissage
Application web complète et interactive
"""

import streamlit as st
from database_schema import DatabaseSchema, format_duration
from programme_learning_v2 import ProgrammeService, ProgressionService
import os

# ============================================================================
# CONFIGURATION DE LA PAGE
# ============================================================================

st.set_page_config(
    page_title="Programme d'apprentissage Python",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# INITIALISATION
# ============================================================================

@st.cache_resource
def init_database():
    """Initialise la connexion à la base de données"""
    db_path = "learning_programme.db"
    
    # Si la DB n'existe pas, la créer et la peupler
    if not os.path.exists(db_path):
        st.warning("⚠️ Base de données non trouvée, création en cours...")
        from database_schema import DatabaseInitializer
        from migration_script import ProgrammeMigrator
        
        db = DatabaseInitializer.initialize_new_database(db_path)
        migrator = ProgrammeMigrator(db)
        migrator.migrate_all()
        st.success("✅ Base de données créée avec succès!")
    
    db = DatabaseSchema(db_path)
    db.connect()
    return db

# Initialiser les services avec session_state pour éviter les problèmes de connexion
if 'db' not in st.session_state:
    st.session_state.db = init_database()
    st.session_state.programme_service = ProgrammeService(st.session_state.db)
    st.session_state.progression_service = ProgressionService(st.session_state.db)

db = st.session_state.db
programme_service = st.session_state.programme_service
progression_service = st.session_state.progression_service

# ID du programme (à adapter si plusieurs programmes)
PROG_ID = "prog_python_30j"

# ============================================================================
# STYLE CSS PERSONNALISÉ
# ============================================================================

st.markdown("""
<style>
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .stat-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR : NAVIGATION
# ============================================================================

st.sidebar.title("📚 Navigation")

page = st.sidebar.radio(
    "Choisissez une page",
    [
        "🏠 Accueil",
        "📅 Semaines",
        "📊 Ma progression",
        "🔍 Recherche",
        "✅ Valider un contenu"
    ]
)

st.sidebar.markdown("---")

# Statistiques globales dans la sidebar
stats = progression_service.prog_dao.get_progression_programme(PROG_ID)
pourcentage = (stats['contenus_termines'] / stats['total_contenus'] * 100) if stats['total_contenus'] > 0 else 0

st.sidebar.markdown("### 📈 Progression globale")
st.sidebar.progress(pourcentage / 100)
st.sidebar.write(f"**{pourcentage:.0f}%** complété")
st.sidebar.write(f"{stats['contenus_termines']} / {stats['total_contenus']} contenus")

temps_h = (stats['temps_total_passe'] or 0) // 60
temps_m = (stats['temps_total_passe'] or 0) % 60
st.sidebar.write(f"⏱️ **{temps_h}h{temps_m:02d}** passées")

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
        # Métriques en colonnes
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
        st.subheader("📈 Votre progression")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.progress(pourcentage / 100)
        
        with col2:
            st.metric("Progression", f"{pourcentage:.1f}%")
        
        st.write(f"**{stats['contenus_termines']}** contenus terminés sur **{stats['total_contenus']}**")
        
        # Stats détaillées
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"🔄 **En cours**: {stats['contenus_en_cours']}")
        
        with col2:
            temps_passe = stats['temps_total_passe'] or 0
            st.info(f"⏱️ **Temps passé**: {format_duration(temps_passe)}")
        
        with col3:
            temps_estime = stats['temps_total_estime'] or 0
            st.info(f"📊 **Temps total**: {format_duration(temps_estime)}")
        
        st.markdown("---")
        
        # Suggestion de contenu
        st.subheader("💡 Prochain contenu suggéré")
        prochain = programme_service.suggerer_prochain_contenu(PROG_ID)
        
        if prochain:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### {prochain['titre']}")
                    
                    icone_type = {
                        'theorie': '📖',
                        'exercice': '✏️',
                        'projet': '🎯',
                        'ressource': '🔗'
                    }
                    
                    type_texte = prochain['type'].capitalize()
                    icone = icone_type.get(prochain['type'], '•')
                    
                    st.write(f"{icone} **Type**: {type_texte}")
                    
                    if prochain['difficulte']:
                        st.write(f"⭐ **Difficulté**: {'⭐' * prochain['difficulte']}")
                    
                    if prochain['temps_estime']:
                        st.write(f"⏱️ **Temps estimé**: {format_duration(prochain['temps_estime'])}")
                
                with col2:
                    if st.button("📖 Voir les détails", key="detail_prochain", use_container_width=True):
                        st.session_state['voir_detail_id'] = prochain['id']
                        st.rerun()
                
                if prochain['description']:
                    st.write(prochain['description'])
                
                # Afficher les détails si demandé
                if st.session_state.get('voir_detail_id') == prochain['id']:
                    with st.expander("📋 Détails complets", expanded=True):
                        if prochain['enonce']:
                            st.markdown("**Énoncé:**")
                            st.write(prochain['enonce'])
                        
                        if prochain['indice']:
                            if st.button("💡 Voir l'indice"):
                                st.info(f"💡 {prochain['indice']}")
                        
                        # Prérequis
                        prerequis = programme_service.contenu_dao.get_prerequis(prochain['id'])
                        if prerequis:
                            st.markdown("**🔗 Prérequis:**")
                            for prereq in prerequis:
                                prog_prereq = progression_service.prog_dao.get_progression(prereq['id'])
                                statut = "✅" if prog_prereq and prog_prereq['statut'] == 'termine' else "⚠️"
                                st.write(f"{statut} {prereq['titre']}")
        else:
            st.success("🎉 Félicitations ! Vous avez terminé tout le programme !")
            st.balloons()

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
        options=list(semaine_options.keys()),
        key="select_semaine"
    )
    
    if semaine_selectionnee:
        semaine = semaine_options[semaine_selectionnee]
        
        st.markdown(f"## Semaine {semaine['numero']} : {semaine['titre']}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**🎯 Objectif** : {semaine['objectif']}")
        
        with col2:
            st.markdown(f"**⏰ Temps quotidien** : {semaine['temps_quotidien']}")
        
        st.markdown("---")
        
        # Afficher les jours
        jours = programme_service.jour_dao.get_jours(semaine['id'])
        
        for jour in jours:
            # Calculer la progression du jour
            contenus = programme_service.contenu_dao.get_contenus(jour['id'])
            nb_termines = sum(1 for c in contenus 
                            if progression_service.prog_dao.get_progression(c['id']) 
                            and progression_service.prog_dao.get_progression(c['id'])['statut'] == 'termine')
            pct_jour = (nb_termines / len(contenus) * 100) if contenus else 0
            
            # Titre avec statut
            statut_emoji = "✅" if pct_jour == 100 else "🔄" if pct_jour > 0 else "⏳"
            titre_jour = f"{statut_emoji} {'🎮' if jour['type'] == 'weekend' else '📅'} {jour['nom'].replace('_', ' ').title()} ({nb_termines}/{len(contenus)})"
            
            with st.expander(titre_jour, expanded=(pct_jour > 0 and pct_jour < 100)):
                
                # Barre de progression du jour
                st.progress(pct_jour / 100)
                
                if contenus:
                    # Grouper par type
                    theories = [c for c in contenus if c['type'] == 'theorie']
                    exercices = [c for c in contenus if c['type'] == 'exercice']
                    projets = [c for c in contenus if c['type'] == 'projet']
                    ressources = [c for c in contenus if c['type'] == 'ressource']
                    
                    # Théorie
                    if theories:
                        st.markdown("#### 📖 Théorie")
                        for t in theories:
                            prog = progression_service.prog_dao.get_progression(t['id'])
                            statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                            temps = f"({format_duration(t['temps_estime'])})" if t['temps_estime'] else ""
                            st.write(f"{statut} {t['titre']} {temps}")
                    
                    # Exercices
                    if exercices:
                        st.markdown("#### ✏️ Exercices")
                        for e in exercices:
                            prog = progression_service.prog_dao.get_progression(e['id'])
                            statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                            difficulte = f"[{'⭐' * e['difficulte']}]" if e['difficulte'] else ""
                            temps = f"({format_duration(e['temps_estime'])})" if e['temps_estime'] else ""
                            st.write(f"{statut} {e['titre']} {difficulte} {temps}")
                            
                            # Description courte
                            if e['description'] and len(e['description']) < 100:
                                st.caption(f"└─ {e['description']}")
                    
                    # Projets
                    if projets:
                        st.markdown("#### 🎯 Projet")
                        for p in projets:
                            prog = progression_service.prog_dao.get_progression(p['id'])
                            statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                            difficulte = f"[{'⭐' * p['difficulte']}]" if p['difficulte'] else ""
                            temps = f"({format_duration(p['temps_estime'])})" if p['temps_estime'] else ""
                            st.write(f"{statut} **{p['titre']}** {difficulte} {temps}")
                            
                            if p['description']:
                                desc = p['description'][:150] + "..." if len(p['description']) > 150 else p['description']
                                st.caption(f"└─ {desc}")
                    
                    # Ressources
                    if ressources:
                        st.markdown("#### 🔗 Ressources")
                        for r in ressources:
                            prog = progression_service.prog_dao.get_progression(r['id'])
                            statut = "✅" if prog and prog['statut'] == 'termine' else "⬜"
                            st.write(f"{statut} {r['titre']}")
                    
                    # Résumé temps
                    temps_total = sum(c['temps_estime'] or 0 for c in contenus)
                    st.caption(f"⏱️ Temps total estimé : {format_duration(temps_total)}")

# ============================================================================
# PAGE : MA PROGRESSION
# ============================================================================

elif page == "📊 Ma progression":
    st.title("📊 Ma progression")
    
    # Vue d'ensemble
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Contenus terminés",
            f"{stats['contenus_termines']}/{stats['total_contenus']}",
            delta=f"{pourcentage:.1f}%"
        )
    
    with col2:
        st.metric("En cours", stats['contenus_en_cours'])
    
    with col3:
        temps_passe = stats['temps_total_passe'] or 0
        st.metric("Temps passé", format_duration(temps_passe))
    
    st.markdown("---")
    
    # Efficacité
    if stats['temps_total_passe'] and stats['temps_total_estime']:
        ratio = (stats['temps_total_passe'] / stats['temps_total_estime']) * 100
        
        st.subheader("⚡ Efficacité")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if ratio < 80:
                st.success(f"🚀 Excellent ! Vous êtes {100-ratio:.0f}% plus rapide que prévu")
            elif ratio < 120:
                st.info(f"✅ Bon rythme ! Vous êtes dans les temps ({ratio:.0f}%)")
            else:
                st.warning(f"⏰ Prenez votre temps, vous êtes à {ratio:.0f}% du temps estimé")
        
        with col2:
            st.metric("Ratio", f"{ratio:.0f}%")
    
    st.markdown("---")
    
    # Progression par semaine
    st.subheader("📚 Progression par semaine")
    
    cursor = db.conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                s.numero,
                s.titre,
                COUNT(c.id) as total,
                COUNT(CASE WHEN p.statut = 'termine' THEN 1 END) as termines,
                SUM(c.temps_estime) as temps_estime,
                SUM(CASE WHEN p.statut = 'termine' THEN p.temps_passe ELSE 0 END) as temps_passe
            FROM semaines s
            JOIN jours j ON j.semaine_id = s.id
            JOIN contenus c ON c.jour_id = j.id
            LEFT JOIN progression p ON p.contenu_id = c.id
            WHERE s.programme_id = ?
            GROUP BY s.id
            ORDER BY s.ordre
        """, (PROG_ID,))
        
        resultats = cursor.fetchall()
        
        for row in resultats:
            row = dict(row)
            pct = (row['termines'] / row['total'] * 100) if row['total'] > 0 else 0
            
            with st.container():
                col1, col2, col3 = st.columns([4, 1, 1])
                
                with col1:
                    st.write(f"**Semaine {row['numero']}**: {row['titre']}")
                    st.progress(pct / 100)
                
                with col2:
                    st.metric("Contenus", f"{row['termines']}/{row['total']}")
                
                with col3:
                    st.metric("Temps", format_duration(row['temps_passe'] or 0))
            
            st.markdown("")
    finally:
        cursor.close()
    
    st.markdown("---")
    
    # Conseils personnalisés
    st.subheader("💡 Conseils personnalisés")
    
    if pourcentage < 25:
        st.info("""
        🌱 **Vous débutez !**
        - Concentrez-vous sur les fondamentaux
        - Faites TOUS les exercices, ne sautez rien
        - Prenez le temps de bien comprendre
        """)
    elif pourcentage < 50:
        st.success("""
        🚀 **Bon rythme !**
        - Continuez ainsi
        - Revoyez les concepts pas encore maîtrisés
        - Commencez à créer vos propres petits projets
        """)
    elif pourcentage < 75:
        st.success("""
        ⭐ **Excellent progrès !**
        - Vous pouvez approfondir les concepts avancés
        - Challengez-vous avec des projets plus complexes
        - Explorez des bibliothèques tierces
        """)
    else:
        st.success("""
        🏆 **Bravo ! Vous maîtrisez les fondamentaux**
        - Prêt pour des projets ambitieux
        - Explorez des frameworks (Django, Flask, FastAPI)
        - Contribuez à des projets open source
        """)

# ============================================================================
# PAGE : RECHERCHE
# ============================================================================

elif page == "🔍 Recherche":
    st.title("🔍 Recherche de contenus")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        terme = st.text_input("🔎 Rechercher un contenu (titre ou description)", "", key="search")
    
    with col2:
        filtre_type = st.selectbox(
            "Type",
            ["Tous", "Théorie", "Exercice", "Projet", "Ressource"]
        )
    
    if terme:
        cursor = db.conn.cursor()
        
        try:
            # Construction de la requête selon le filtre
            type_condition = ""
            if filtre_type != "Tous":
                type_map = {
                    "Théorie": "theorie",
                    "Exercice": "exercice",
                    "Projet": "projet",
                    "Ressource": "ressource"
                }
                type_condition = f" AND type = '{type_map[filtre_type]}'"
            
            cursor.execute(f"""
                SELECT * FROM contenus
                WHERE (titre LIKE ? OR description LIKE ?)
                {type_condition}
                ORDER BY ordre
                LIMIT 20
            """, (f"%{terme}%", f"%{terme}%"))
            
            resultats = [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
        
        if resultats:
            st.success(f"✅ {len(resultats)} résultat(s) trouvé(s)")
            
            for contenu in resultats:
                with st.expander(
                    f"{'📖' if contenu['type'] == 'theorie' else '✏️' if contenu['type'] == 'exercice' else '🎯' if contenu['type'] == 'projet' else '🔗'} {contenu['titre']}"
                ):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        prog = progression_service.prog_dao.get_progression(contenu['id'])
                        
                        if prog and prog['statut'] == 'termine':
                            st.success("✅ Terminé")
                        elif prog and prog['statut'] == 'en_cours':
                            st.info("🔄 En cours")
                        else:
                            st.warning("⬜ Non commencé")
                        
                        if contenu['description']:
                            st.write(contenu['description'])
                        
                        if contenu['difficulte']:
                            st.write(f"**Difficulté**: {'⭐' * contenu['difficulte']}")
                        
                        if contenu['temps_estime']:
                            st.write(f"**Temps estimé**: {format_duration(contenu['temps_estime'])}")
                    
                    with col2:
                        if not prog or prog['statut'] != 'termine':
                            if st.button("✅ Valider", key=f"val_{contenu['id']}", use_container_width=True):
                                st.session_state['valider_contenu_id'] = contenu['id']
                                st.rerun()
        else:
            st.warning(f"Aucun résultat pour '{terme}'")

# ============================================================================
# PAGE : VALIDER UN CONTENU
# ============================================================================

elif page == "✅ Valider un contenu":
    st.title("✅ Valider un contenu")
    
    st.info("💡 Recherchez un contenu pour le marquer comme terminé")
    
    # Recherche
    terme = st.text_input("🔎 Rechercher", "", key="search_validation")
    
    if terme:
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT c.*
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
                format_func=lambda i: f"{'📖' if resultats[i]['type'] == 'theorie' else '✏️' if resultats[i]['type'] == 'exercice' else '🎯'} {resultats[i]['titre']}",
                key="select_contenu_validation"
            )
            
            contenu = resultats[contenu_selectionne]
            
            st.markdown("---")
            st.markdown(f"### {contenu['titre']}")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                if contenu['description']:
                    st.write(contenu['description'])
                
                if contenu['difficulte']:
                    st.write(f"**Difficulté**: {'⭐' * contenu['difficulte']}")
            
            with col2:
                if contenu['temps_estime']:
                    st.metric("⏱️ Temps estimé", format_duration(contenu['temps_estime']))
            
            # Vérifier prérequis
            prerequis_ok, messages = programme_service.verifier_prerequis(contenu['id'])
            
            if not prerequis_ok:
                st.warning("⚠️ Prérequis non validés")
                for msg in messages:
                    st.write(msg)
            
            # Formulaire de validation
            st.markdown("---")
            
            with st.form("validation_form"):
                st.subheader("📝 Valider le contenu")
                
                temps_passe = st.number_input(
                    "⏱️ Temps réellement passé (en minutes)",
                    min_value=1,
                    value=contenu['temps_estime'] or 30,
                    step=5
                )
                
                notes = st.text_area("📝 Notes personnelles (optionnel)", "", height=100)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    submitted = st.form_submit_button("✅ Valider ce contenu", use_container_width=True)
                
                with col2:
                    cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
                
                if submitted:
                    progression_service.prog_dao.marquer_termine(
                        contenu['id'],
                        temps_passe,
                        notes
                    )
                    st.success(f"🎉 '{contenu['titre']}' marqué comme terminé!")
                    st.balloons()
                    
                    # Afficher contenus débloqués
                    dependants = programme_service.contenu_dao.get_contenus_dependants(contenu['id'])
                    if dependants:
                        st.info(f"🔓 Vous avez débloqué {len(dependants)} nouveau(x) contenu(s) !")
                
                if cancel:
                    st.info("Validation annulée")
        else:
            st.warning("Aucun contenu non terminé trouvé pour cette recherche")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Fait avec ❤️ pour l'apprentissage | "
    "Powered by Streamlit 🎈"
    "</div>",
    unsafe_allow_html=True
)
