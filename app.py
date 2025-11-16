"""
Interface Streamlit pour le programme d'apprentissage
Version améliorée avec thème sombre et nouvelles fonctionnalités
"""

import streamlit as st
from database_schema import DatabaseSchema, format_duration
from programme_learning_v2 import ProgrammeService, ProgressionService
from import_programme import exporter_progression
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
# STYLE CSS PERSONNALISÉ - THÈME SOMBRE
# ============================================================================

st.markdown("""
<style>
    /* Thème sombre général */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Cartes de contenu */
    .content-card {
        background: linear-gradient(135deg, #1e2530 0%, #2d3748 100%);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #4a5568;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    }
    
    .content-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
    }
    
    /* Badges de statut */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin: 5px;
    }
    
    .status-termine {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
    }
    
    .status-en-cours {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
    }
    
    .status-non-commence {
        background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
        color: white;
    }
    
    /* Boutons personnalisés */
    .custom-button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        padding: 10px 20px;
        border-radius: 10px;
        border: none;
        cursor: pointer;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .custom-button:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    
    /* Progress bars */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
    }
    
    /* Titres avec gradient */
    .gradient-title {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
        font-size: 2em;
    }
    
    /* Cartes métriques */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        border: 1px solid #475569;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border-radius: 10px;
        font-weight: 600;
    }
    
    /* Icônes de difficulté */
    .difficulty-stars {
        color: #fbbf24;
        font-size: 18px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# INITIALISATION
# ============================================================================

def init_database():
    """Initialise la connexion à la base de données (sans cache)"""
    db_path = "learning_programme.db"
    
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

# Initialiser
db = init_database()
programme_service = ProgrammeService(db)
progression_service = ProgressionService(db)

PROG_ID = "prog_python_30j"

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def get_status_badge(statut):
    """Retourne un badge HTML selon le statut"""
    if statut == 'termine':
        return '<span class="status-badge status-termine">✅ Terminé</span>'
    elif statut == 'en_cours':
        return '<span class="status-badge status-en-cours">🔄 En cours</span>'
    else:
        return '<span class="status-badge status-non-commence">⏳ Non commencé</span>'

def marquer_en_cours(contenu_id):
    """Marque un contenu comme en cours"""
    progression_service.prog_dao.marquer_commence(contenu_id)
    st.success("📝 Marqué comme en cours !")
    st.rerun()

# ============================================================================
# SIDEBAR : Navigation
# ============================================================================

st.sidebar.markdown('<p class="gradient-title">📚 Navigation</p>', unsafe_allow_html=True)

page = st.sidebar.radio(
    "",
    [
        "🏠 Accueil",
        "📅 Semaines",
        "📊 Ma progression",
        "🔍 Recherche",
        "✅ Valider un contenu",
        "📥 Importer un programme"
    ],
    label_visibility="collapsed"
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
st.sidebar.info("💡 **Astuce**: Marquez les contenus comme 'en cours' avant de les valider!")

# ============================================================================
# PAGE : ACCUEIL
# ============================================================================

if page == "🏠 Accueil":
    st.markdown('<h1 class="gradient-title">📚 Programme d\'apprentissage Python</h1>', unsafe_allow_html=True)
    st.markdown("### Apprenez Python en 30 jours avec un programme structuré")
    
    prog = programme_service.prog_dao.get_programme_with_stats(PROG_ID)
    
    if prog:
        # Métriques en colonnes
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("📅 Durée", f"{prog['duree_jours']} jours")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("📚 Semaines", prog['nb_semaines'])
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("🗓️ Jours", prog['nb_jours'])
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("📝 Contenus", prog['nb_contenus'])
            st.markdown('</div>', unsafe_allow_html=True)
        
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
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.markdown(f"### 🔄 En cours\n**{stats['contenus_en_cours']}** contenus")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            temps_passe = stats['temps_total_passe'] or 0
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.markdown(f"### ⏱️ Temps passé\n**{format_duration(temps_passe)}**")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            temps_estime = stats['temps_total_estime'] or 0
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.markdown(f"### 📊 Temps total\n**{format_duration(temps_estime)}**")
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Suggestion de contenu
        st.subheader("💡 Prochain contenu suggéré")
        prochain = programme_service.suggerer_prochain_contenu(PROG_ID)
        
        if prochain:
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {prochain['titre']}")
                
                icone_type = {
                    'theorie': '📖 Théorie',
                    'exercice': '✏️ Exercice',
                    'projet': '🎯 Projet',
                    'ressource': '🔗 Ressource'
                }
                
                type_texte = icone_type.get(prochain['type'], prochain['type'])
                st.write(f"**{type_texte}**")
                
                if prochain['difficulte']:
                    st.markdown(f'<span class="difficulty-stars">{"⭐" * prochain['difficulte']}</span>', unsafe_allow_html=True)
                
                if prochain['temps_estime']:
                    st.write(f"⏱️ **Temps estimé**: {format_duration(prochain['temps_estime'])}")
            
            with col2:
                # Vérifier le statut actuel
                prog_actuelle = progression_service.prog_dao.get_progression(prochain['id'])
                
                if not prog_actuelle or prog_actuelle['statut'] == 'non_commence':
                    if st.button("📝 Commencer", key="start_prochain", use_container_width=True):
                        marquer_en_cours(prochain['id'])
                
                if st.button("📖 Voir détails", key="detail_prochain", use_container_width=True):
                    st.session_state['voir_detail_id'] = prochain['id']
                    st.rerun()
            
            if prochain['description']:
                st.write(prochain['description'])
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Afficher les détails si demandé
            if st.session_state.get('voir_detail_id') == prochain['id']:
                with st.expander("📋 Énoncé complet", expanded=True):
                    if prochain['enonce']:
                        st.markdown("**Énoncé détaillé:**")
                        st.write(prochain['enonce'])
                    else:
                        st.info("Aucun énoncé détaillé disponible pour ce contenu.")
                    
                    if prochain['indice']:
                        if st.button("💡 Afficher l'indice"):
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
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.success("🎉 Félicitations ! Vous avez terminé tout le programme !")
            st.balloons()
            st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# PAGE : SEMAINES
# ============================================================================

elif page == "📅 Semaines":
    st.markdown('<h1 class="gradient-title">📅 Vue par semaines</h1>', unsafe_allow_html=True)
    
    # Sélecteur de semaine avec menu déroulant
    semaines = programme_service.sem_dao.get_semaines(PROG_ID)
    semaine_options = {f"Semaine {s['numero']} : {s['titre']}": s for s in semaines}
    
    semaine_selectionnee = st.selectbox(
        "Choisissez une semaine",
        options=list(semaine_options.keys()),
        key="select_semaine"
    )
    
    if semaine_selectionnee:
        semaine = semaine_options[semaine_selectionnee]
        
        st.markdown(f"## {semaine['titre']}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**🎯 Objectif** : {semaine['objectif']}")
        
        with col2:
            st.markdown(f"**⏰ Temps quotidien** : {semaine['temps_quotidien']}")
        
        st.markdown("---")
        
        # Afficher les jours
        jours = programme_service.jour_dao.get_jours(semaine['id'])
        
        for jour in jours:
            contenus = programme_service.contenu_dao.get_contenus(jour['id'])
            nb_termines = sum(1 for c in contenus 
                            if progression_service.prog_dao.get_progression(c['id']) 
                            and progression_service.prog_dao.get_progression(c['id'])['statut'] == 'termine')
            pct_jour = (nb_termines / len(contenus) * 100) if contenus else 0
            
            statut_emoji = "✅" if pct_jour == 100 else "🔄" if pct_jour > 0 else "⏳"
            titre_jour = f"{statut_emoji} {'🎮' if jour['type'] == 'weekend' else '📅'} {jour['nom'].replace('_', ' ').title()} ({nb_termines}/{len(contenus)})"
            
            with st.expander(titre_jour, expanded=(pct_jour > 0 and pct_jour < 100)):
                st.progress(pct_jour / 100)
                
                if contenus:
                    theories = [c for c in contenus if c['type'] == 'theorie']
                    exercices = [c for c in contenus if c['type'] == 'exercice']
                    projets = [c for c in contenus if c['type'] == 'projet']
                    ressources = [c for c in contenus if c['type'] == 'ressource']
                    
                    if theories:
                        st.markdown("#### 📖 Théorie")
                        for t in theories:
                            prog = progression_service.prog_dao.get_progression(t['id'])
                            if prog:
                                badge = get_status_badge(prog['statut'])
                            else:
                                badge = get_status_badge('non_commence')
                            
                            temps = f"({format_duration(t['temps_estime'])})" if t['temps_estime'] else ""
                            st.markdown(f"{badge} {t['titre']} {temps}", unsafe_allow_html=True)
                    
                    if exercices:
                        st.markdown("#### ✏️ Exercices")
                        for e in exercices:
                            prog = progression_service.prog_dao.get_progression(e['id'])
                            if prog:
                                badge = get_status_badge(prog['statut'])
                            else:
                                badge = get_status_badge('non_commence')
                            
                            difficulte = f'<span class="difficulty-stars">{"⭐" * e["difficulte"]}</span>' if e['difficulte'] else ""
                            temps = f"({format_duration(e['temps_estime'])})" if e['temps_estime'] else ""
                            
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.markdown(f"{badge} {e['titre']} {difficulte} {temps}", unsafe_allow_html=True)
                                if e['description'] and len(e['description']) < 100:
                                    st.caption(f"└─ {e['description']}")
                            with col2:
                                if not prog or prog['statut'] == 'non_commence':
                                    if st.button("▶️", key=f"start_{e['id']}", help="Commencer"):
                                        marquer_en_cours(e['id'])
                    
                    if projets:
                        st.markdown("#### 🎯 Projet")
                        for p in projets:
                            prog = progression_service.prog_dao.get_progression(p['id'])
                            if prog:
                                badge = get_status_badge(prog['statut'])
                            else:
                                badge = get_status_badge('non_commence')
                            
                            difficulte = f'<span class="difficulty-stars">{"⭐" * p["difficulte"]}</span>' if p['difficulte'] else ""
                            temps = f"({format_duration(p['temps_estime'])})" if p['temps_estime'] else ""
                            st.markdown(f"{badge} **{p['titre']}** {difficulte} {temps}", unsafe_allow_html=True)
                            
                            if p['description']:
                                desc = p['description'][:150] + "..." if len(p['description']) > 150 else p['description']
                                st.caption(f"└─ {desc}")
                    
                    if ressources:
                        st.markdown("#### 🔗 Ressources")
                        for r in ressources:
                            prog = progression_service.prog_dao.get_progression(r['id'])
                            if prog:
                                badge = get_status_badge(prog['statut'])
                            else:
                                badge = get_status_badge('non_commence')
                            st.markdown(f"{badge} {r['titre']}", unsafe_allow_html=True)
                    
                    temps_total = sum(c['temps_estime'] or 0 for c in contenus)
                    st.caption(f"⏱️ Temps total estimé : {format_duration(temps_total)}")

# Les autres pages restent identiques pour l'instant...
# (Ma progression, Recherche améliorée, Valider, Importer)

# Je vais créer les pages manquantes dans la prochaine partie

elif page == "📊 Ma progression":
    st.markdown('<h1 class="gradient-title">📊 Ma progression</h1>', unsafe_allow_html=True)
    
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
    
    # Export/Import de progression
    st.subheader("💾 Sauvegarder ma progression")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Exporter la progression"):
            try:
                # Appel de la fonction
                json_data = exporter_progression(db, PROG_ID)
        
                # Bouton de téléchargement
                st.download_button(
                    label="💾 Télécharger le fichier JSON",
                    data=json_data,
                    file_name=f"progression_{PROG_ID}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
        
                 st.success(f"✅ Export réussi !")
        
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")
    
    with col2:
        fichier_import = st.file_uploader("📤 Importer une progression", type=['json'])
        if fichier_import:
            if st.button("🔄 Importer", use_container_width=True):
                from import_programme import importer_progression
                import json as json_lib
                
                try:
                    data = json_lib.load(fichier_import)
                    stats_import = importer_progression(db, data)
                    st.success(f"✅ {stats_import['nb_importes']} progressions importées !")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'import : {e}")
    
    st.info("💡 **Astuce** : Exportez votre progression avant de changer de programme ou de réinitialiser la base de données")
    
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
    st.markdown('<h1 class="gradient-title">🔍 Recherche</h1>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        terme = st.text_input("🔎 Rechercher un contenu (titre ou description)", "", key="search")
    
    with col2:
        filtre_type = st.selectbox(
            "Type",
            ["Tous", "Théorie", "Exercice", "Projet", "Ressource"],
            key="filter_type"
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
                        
                        if prog:
                            badge = get_status_badge(prog['statut'])
                        else:
                            badge = get_status_badge('non_commence')
                        
                        st.markdown(badge, unsafe_allow_html=True)
                        
                        if contenu['description']:
                            st.write(contenu['description'])
                        
                        if contenu['difficulte']:
                            st.markdown(f'**Difficulté**: <span class="difficulty-stars">{"⭐" * contenu["difficulte"]}</span>', unsafe_allow_html=True)
                        
                        if contenu['temps_estime']:
                            st.write(f"**Temps estimé**: {format_duration(contenu['temps_estime'])}")
                    
                    with col2:
                        if not prog or prog['statut'] != 'termine':
                            if not prog or prog['statut'] == 'non_commence':
                                if st.button("▶️ Commencer", key=f"start_{contenu['id']}", use_container_width=True):
                                    marquer_en_cours(contenu['id'])
                            if st.button("✅ Valider", key=f"val_{contenu['id']}", use_container_width=True):
                                st.session_state['valider_contenu_id'] = contenu['id']
                                st.rerun()
        else:
            st.warning(f"Aucun résultat pour '{terme}'")

# ============================================================================
# PAGE : VALIDER UN CONTENU
# ============================================================================

elif page == "✅ Valider un contenu":
    st.markdown('<h1 class="gradient-title">✅ Valider un contenu</h1>', unsafe_allow_html=True)
    
    st.info("💡 Recherchez un contenu pour le marquer comme terminé")
    
    # Recherche avec menu déroulant
    col1, col2 = st.columns([3, 1])
    
    with col1:
        terme = st.text_input("🔎 Rechercher", "", key="search_validation")
    
    with col2:
        filtre_validation = st.selectbox(
            "Type",
            ["Tous", "Théorie", "Exercice", "Projet"],
            key="filter_validation"
        )
    
    if terme:
        cursor = db.conn.cursor()
        
        try:
            type_condition = ""
            if filtre_validation != "Tous":
                type_map = {
                    "Théorie": "theorie",
                    "Exercice": "exercice",
                    "Projet": "projet"
                }
                type_condition = f" AND c.type = '{type_map[filtre_validation]}'"
            
            cursor.execute(f"""
                SELECT c.*
                FROM contenus c
                LEFT JOIN progression p ON p.contenu_id = c.id
                WHERE (c.titre LIKE ? OR c.description LIKE ?)
                  AND (p.statut IS NULL OR p.statut != 'termine')
                {type_condition}
                ORDER BY c.ordre
                LIMIT 10
            """, (f"%{terme}%", f"%{terme}%"))
            
            resultats = [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
        
        if resultats:
            # Menu déroulant pour sélectionner
            options = [f"{'📖' if r['type'] == 'theorie' else '✏️' if r['type'] == 'exercice' else '🎯'} {r['titre']}" for r in resultats]
            
            contenu_selectionne_idx = st.selectbox(
                "Choisissez un contenu à valider",
                options=range(len(options)),
                format_func=lambda i: options[i],
                key="select_contenu_validation"
            )
            
            contenu = resultats[contenu_selectionne_idx]
            
            st.markdown("---")
            st.markdown(f"### {contenu['titre']}")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                if contenu['description']:
                    st.write(contenu['description'])
                
                if contenu['difficulte']:
                    st.markdown(f'**Difficulté**: <span class="difficulty-stars">{"⭐" * contenu["difficulte"]}</span>', unsafe_allow_html=True)
            
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
                    
                    # Afficher contenus débloqués
                    dependants = programme_service.contenu_dao.get_contenus_dependants(contenu['id'])
                    if dependants:
                        st.info(f"🔓 Vous avez débloqué {len(dependants)} nouveau(x) contenu(s) !")
                
                if cancel:
                    st.info("Validation annulée")
        else:
            st.warning("Aucun contenu non terminé trouvé pour cette recherche")

# ============================================================================
# PAGE : IMPORTER UN PROGRAMME
# ============================================================================

elif page == "📥 Importer un programme":
    st.markdown('<h1 class="gradient-title">📥 Importer un nouveau programme</h1>', unsafe_allow_html=True)
    
    st.write("""
    Importez facilement un nouveau programme d'apprentissage depuis un fichier CSV.
    Le format CSV permet de créer des programmes dans Excel, Google Sheets ou tout éditeur de texte.
    """)
    
    # Onglets
    tab1, tab2, tab3 = st.tabs(["📤 Importer", "📋 Template", "📖 Documentation"])
    
    with tab1:
        st.subheader("Importer un programme CSV")
        
        fichier_csv = st.file_uploader(
            "Choisissez un fichier CSV",
            type=['csv'],
            help="Format: Type,Semaine,Jour,Titre,Description,Enonce,Indice,Difficulte,TempsEstime"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            nom_programme = st.text_input(
                "Nom du programme",
                placeholder="Ex: JavaScript 30 jours",
                help="Nom qui apparaîtra dans l'application"
            )
        
        with col2:
            sujet_programme = st.text_input(
                "Sujet",
                placeholder="Ex: JavaScript",
                help="Catégorie du programme"
            )
        
        if fichier_csv and nom_programme and sujet_programme:
            if st.button("🚀 Importer le programme", type="primary", use_container_width=True):
                from import_programme import ProgrammeImporter
                import io
                
                try:
                    # Lire le CSV
                    content = fichier_csv.getvalue().decode('utf-8')
                    csv_file = io.StringIO(content)
                    
                    # Importer
                    importer = ProgrammeImporter(db)
                    stats = importer.importer_depuis_csv(csv_file, nom_programme, sujet_programme)
                    
                    if stats['succes']:
                        st.success(f"""
                        ✅ **Import réussi !**
                        
                        - Programme ID: `{stats['programme_id']}`
                        - {stats['nb_semaines']} semaines créées
                        - {stats['nb_jours']} jours créés
                        - {stats['nb_contenus']} contenus créés
                        """)
                        
                        if stats['erreurs']:
                            with st.expander("⚠️ Avertissements", expanded=False):
                                for err in stats['erreurs']:
                                    st.warning(err)
                        
                        st.info("💡 Redémarrez l'application pour voir le nouveau programme")
                    else:
                        st.error("❌ Échec de l'import")
                        for err in stats['erreurs']:
                            st.error(err)
                
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")
    
    with tab2:
        st.subheader("Télécharger un template")
        
        st.write("""
        Téléchargez un template CSV pour créer votre propre programme.
        Deux options disponibles :
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📄 Template vide")
            if st.button("⬇️ Télécharger template vide", use_container_width=True):
                from import_programme import ProgrammeImporter
                importer = ProgrammeImporter(db)
                template = importer.generer_template_csv()
                
                st.download_button(
                    label="💾 Télécharger",
                    data=template,
                    file_name="template_programme.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col2:
            st.markdown("### 📚 Programme Python complet")
            st.info("Template avec la semaine 1 complète du programme Python")
            # Vous pouvez ajouter le téléchargement du CSV Python complet ici
    
    with tab3:
        st.subheader("📖 Format du fichier CSV")
        
        st.markdown("""
        ### Structure du CSV
        
        Le fichier CSV doit contenir ces colonnes (dans cet ordre) :
        
        | Colonne | Description | Obligatoire | Exemple |
        |---------|-------------|-------------|---------|
        | **Type** | Type de ligne | ✅ | `semaine`, `jour`, `theorie`, `exercice`, `projet` |
        | **Semaine** | Numéro de semaine | ✅ | `1`, `2`, `3`... |
        | **Jour** | Numéro du jour | Pour contenus | `1`, `2`, `3`, `99` (weekend) |
        | **Titre** | Titre du contenu | ✅ | `Variables et types` |
        | **Description** | Description courte | ❌ | `Introduction aux variables` |
        | **Enonce** | Énoncé détaillé | Pour exercices | `**Objectif**: Créer...` |
        | **Indice** | Aide pour l'exercice | ❌ | `Utilisez print()` |
        | **Difficulte** | Niveau 1-5 | ❌ | `2` |
        | **TempsEstime** | En minutes | ❌ | `30` |
        
        ### Exemple complet
        
        ```csv
Type,Semaine,Jour,Titre,Description,Enonce,Indice,Difficulte,TempsEstime
semaine,1,,Fondations,Maîtriser les bases,,,,
jour,1,1,,,,,,,
theorie,1,1,Variables,Introduction,,,,15
exercice,1,1,Exercice 1,Créer variables,"Objectif: ...",Indice,2,30
        ```
        
        ### Conseils
        
        - ✅ Créez d'abord les semaines, puis les jours, puis les contenus
        - ✅ Utilisez `99` pour le jour weekend
        - ✅ Encodage UTF-8 obligatoire
        - ✅ Les lignes vides et commentaires (#) sont ignorés
        - ✅ Testez avec un petit programme d'abord
        """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Fait avec ❤️ pour l'apprentissage | "
    "Powered by Streamlit 🎈"
    "</div>",
    unsafe_allow_html=True
)
