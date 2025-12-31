import streamlit as st
import pandas as pd
import calendar
import random
import json
import copy
from datetime import date
import holidays

st.set_page_config(page_title="Turni Trust Pro - TEST", layout="wide")

# ==============================================================================
# 1. GESTIONE STATO E CONFIGURAZIONE DI DEFAULT
# ==============================================================================

# Configurazione di base (Fallback se non carichi nulla)
DEFAULT_CONFIG = {
    "OPERATORS": ["Operatore 1", "Operatore 2"],
    "SERVICES": {
        "FATTURAZIONE": {"color": "#4FFF81", "tasks": ["cc.fatturazione", "SDO", "PECMAN"]},
        "FIRMA": {"color": "#ffb74f", "tasks": ["cc.firma", "PECMAN/SDO (Firma)"]},
        "SPID": {"color": "#549ff5", "tasks": ["cc.spid", "PECMAN/SDO (SPID)"]},
        "PEC": {"color": "#FF5353", "tasks": ["reparto.pec", "Caselle attesa attivazione", "Escalation"]}
    },
    "SKILLS": {
        "Operatore 1": ["cc.fatturazione"],
        "Operatore 2": ["reparto.pec"]
    },
    "PAUSE": {
        "FISSI": {},
        "SLOTS": ["12:30 - 13:00", "13:00 - 13:30", "13:30 - 14:00"]
    },
    "TELEFONI": {}
}

# Inizializzazione Session State
if 'config' not in st.session_state:
    st.session_state.config = copy.deepcopy(DEFAULT_CONFIG)

def update_config(key, value):
    st.session_state.config[key] = value

# ==============================================================================
# 2. INTERFACCIA UTENTE
# ==============================================================================

st.title("🧩 Turni Trust - Pannello di Controllo")

# Sidebar per Caricamento/Salvataggio Configurazione
with st.sidebar:
    st.header("💾 Memoria Dati")
    st.info("Configura l'app dalla tab 'Impostazioni', poi scarica il file per non perdere le modifiche.")
    
    # Upload
    uploaded_file = st.file_uploader("📂 Carica Configurazione (JSON)", type="json")
    if uploaded_file is not None:
        try:
            loaded_json = json.load(uploaded_file)
            st.session_state.config = loaded_json
            st.success("Configurazione caricata!")
        except Exception as e:
            st.error(f"Errore caricamento: {e}")

    # Download
    config_json = json.dumps(st.session_state.config, indent=4)
    st.download_button(
        label="📥 Scarica Configurazione Attuale",
        data=config_json,
        file_name="configurazione_turni.json",
        mime="application/json"
    )
    st.divider()

# TAB PRINCIPALI
tab_gen, tab_settings = st.tabs(["🗓️ GENERAZIONE TURNI", "⚙️ IMPOSTAZIONI AVANZATE"])

# ------------------------------------------------------------------------------
# TAB IMPOSTAZIONI (IL CUORE DELLE MODIFICHE)
# ------------------------------------------------------------------------------
with tab_settings:
    st.header("Pannello di Configurazione")
    
    # 1. GESTIONE SERVIZI E COLORI
    with st.expander("🎨 1. Servizi, Colori e Sottolavorazioni", expanded=True):
        col_s1, col_s2 = st.columns([1, 2])
        
        with col_s1:
            st.subheader("Aggiungi Servizio")
            new_service = st.text_input("Nome Servizio (es. PEC)")
            new_color = st.color_picker("Colore Servizio", "#00f900")
            if st.button("➕ Crea Servizio"):
                if new_service and new_service not in st.session_state.config["SERVICES"]:
                    st.session_state.config["SERVICES"][new_service] = {"color": new_color, "tasks": []}
                    st.rerun()
        
        with col_s2:
            st.subheader("Gestione Sottolavorazioni")
            services = st.session_state.config["SERVICES"]
            
            for s_name, s_data in services.items():
                c1, c2, c3 = st.columns([0.5, 2, 1])
                c1.color_picker("", s_data["color"], key=f"col_{s_name}", disabled=True)
                c2.markdown(f"**{s_name}**")
                
                # Gestione Task
                current_tasks = s_data.get("tasks", [])
                tasks_text = st.text_area(f"Task per {s_name} (uno per riga)", value="\n".join(current_tasks), key=f"txt_{s_name}", height=68)
                
                # Aggiorna Task
                if st.button(f"💾 Salva Task {s_name}", key=f"btn_{s_name}"):
                    new_task_list = [t.strip() for t in tasks_text.split("\n") if t.strip()]
                    st.session_state.config["SERVICES"][s_name]["tasks"] = new_task_list
                    st.session_state.config["SERVICES"][s_name]["color"] = s_data["color"] # (Placeholder per editing colore futuro)
                    st.toast(f"Task {s_name} aggiornati")
                    st.rerun()
                
                if st.button(f"🗑️ Elimina Servizio {s_name}", key=f"del_{s_name}"):
                    del st.session_state.config["SERVICES"][s_name]
                    st.rerun()
                st.divider()

    # 2. GESTIONE OPERATORI
    with st.expander("👥 2. Gestione Operatori", expanded=False):
        current_ops = st.session_state.config["OPERATORS"]
        text_ops = st.text_area("Lista Operatori (uno per riga)", value="\n".join(current_ops), height=150)
        if st.button("💾 Aggiorna Lista Operatori"):
            new_ops_list = [x.strip() for x in text_ops.split("\n") if x.strip()]
            st.session_state.config["OPERATORS"] = new_ops_list
            # Pulisci skill orfane
            clean_skills = {op: st.session_state.config["SKILLS"].get(op, []) for op in new_ops_list}
            st.session_state.config["SKILLS"] = clean_skills
            st.toast("Lista operatori salvata!")
            st.rerun()

    # 3. MATRICE SKILL
    with st.expander("🛠️ 3. Matrice Competenze (Chi sa fare cosa)", expanded=False):
        st.info("Spunta le caselle per assegnare le skill.")
        
        # Costruzione colonne dinamica
        all_tasks_cols = []
        task_to_service_map = {} # Per ritrovare il padre
        
        for s_name, s_data in st.session_state.config["SERVICES"].items():
            for t in s_data["tasks"]:
                full_name = f"{s_name} > {t}"
                all_tasks_cols.append(full_name)
                task_to_service_map[full_name] = t # Mappa nome visualizzato -> nome reale
        
        # Costruzione DataFrame per editor
        rows = []
        for op in st.session_state.config["OPERATORS"]:
            op_skills = st.session_state.config["SKILLS"].get(op, [])
            row = {"Operatore": op}
            for col in all_tasks_cols:
                real_task_name = task_to_service_map[col]
                row[col] = real_task_name in op_skills
            rows.append(row)
            
        df_skills = pd.DataFrame(rows)
        if not df_skills.empty:
            df_skills.set_index("Operatore", inplace=True)
            edited_df = st.data_editor(df_skills, use_container_width=True, height=500)
            
            if st.button("💾 Salva Matrice Competenze"):
                new_skill_dict = {}
                for op, row in edited_df.iterrows():
                    skills = []
                    for col in all_tasks_cols:
                        if row[col]:
                            skills.append(task_to_service_map[col])
                    new_skill_dict[op] = skills
                st.session_state.config["SKILLS"] = new_skill_dict
                st.success("Matrice salvata in memoria! Ricordati di scaricare il JSON.")

    # 4. GESTIONE PAUSE E TELEFONI
    with st.expander("☕ 4. Gestione Pause e Telefoni", expanded=False):
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            st.subheader("Slot Rotazione Pause")
            current_slots = st.session_state.config["PAUSE"].get("SLOTS", [])
            slots_txt = st.text_area("Orari slot (uno per riga)", value="\n".join(current_slots))
            if st.button("💾 Salva Slot"):
                st.session_state.config["PAUSE"]["SLOTS"] = [x.strip() for x in slots_txt.split("\n") if x.strip()]
                st.toast("Slot salvati")
        
        with c_p2:
            st.subheader("Pause Fisse (Eccezioni)")
            fixed_df = pd.DataFrame([
                {"Operatore": op, "Orario": st.session_state.config["PAUSE"]["FISSI"].get(op, "")}
                for op in st.session_state.config["OPERATORS"]
            ])
            edited_fixed = st.data_editor(fixed_df, key="fixed_pause_editor", hide_index=True)
            if st.button("💾 Salva Pause Fisse"):
                new_fixed = {row["Operatore"]: row["Orario"] for _, row in edited_fixed.iterrows() if row["Orario"]}
                st.session_state.config["PAUSE"]["FISSI"] = new_fixed
                st.toast("Pause fisse salvate")

# ------------------------------------------------------------------------------
# TAB GENERAZIONE TURNI (LOGICA OPERATIVA)
# ------------------------------------------------------------------------------
with tab_gen:
    st.header("Generazione Turni")
    
    # Sidebar impostazioni locali
    col_set1, col_set2, col_set3 = st.columns(3)
    with col_set1:
        mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        mese_s = st.selectbox("Mese", mesi)
        mese_n = mesi.index(mese_s) + 1
    with col_set2:
        anno_s = st.number_input("Anno", 2024, 2030, 2026)
    with col_set3:
        max_tasks = st.slider("Max Task/Giorno", 1, 5, 3)

    # Preparazione Calendario
    _, nd = calendar.monthrange(anno_s, mese_n)
    days = [date(anno_s, mese_n, x) for x in range(1, nd+1)]
    hols = holidays.IT(years=anno_s)
    cols = [f"{d.day:02d} {['Lun','Mar','Mer','Gio','Ven','Sab','Dom'][d.weekday()]}" for d in days]
    ops = st.session_state.config["OPERATORS"]
    
    # Tabella Presenze Temporanea
    st.markdown("### 1. Inserisci Assenze (Ferie/Permessi)")
    df_base = pd.DataFrame(False, index=ops, columns=cols)
    
    # Pre-fill weekend
    mask = [(d.weekday()>=5 or d in hols) for d in days]
    for i, c in enumerate(cols): 
        if mask[i]: df_base[c] = True 
    
    edited_absence = st.data_editor(df_base, key="absences_editor")
    
    if st.button("🚀 GENERA PIANO TURNI", type="primary"):
        # Logica di generazione
        out_sched = {}
        missing = {}
        history_cnt = {op: {} for op in ops}
        
        # Costruzione lista task piatta
        all_tasks_flat = []
        task_color_map = {}
        task_skill_map = {} # Nome Task -> Skill richiesta (in questo caso coincidono, ma per struttura futura)
        
        for s_name, s_data in st.session_state.config["SERVICES"].items():
            for t in s_data["tasks"]:
                all_tasks_flat.append(t)
                task_color_map[t] = s_data["color"]
                task_skill_map[t] = t # La skill richiesta è il nome stesso del task
        
        # Funzione Scarsità
        def count_capable(task_name):
            return sum(1 for op in ops if task_name in st.session_state.config["SKILLS"].get(op, []))
        
        # Ordina task per difficoltà (chi li sa fare in pochi viene assegnato prima)
        all_tasks_flat.sort(key=lambda t: count_capable(t))
        
        # Ciclo Giorni
        for i, day_col in enumerate(cols):
            curr_date = days[i]
            
            # Skip Festivi/Weekend se non lavorativi
            if curr_date in hols:
                out_sched[day_col] = {op: f"🎉 {hols.get(curr_date)}" for op in ops}
                continue
            if curr_date.weekday() >= 5 and not any(edited_absence[day_col]): # Se weekend e nessuno ha tolto la spunta (che qui significa ferie forzata)
                 # Nota: logica inversa weekend. Se è spuntato = NON lavora.
                 out_sched[day_col] = {op: "" for op in ops}
                 continue

            day_assign = {op: "" for op in ops}
            available_ops = []
            
            for op in ops:
                if edited_absence.at[op, day_col]: 
                    day_assign[op] = "FERIE"
                else:
                    available_ops.append(op)
            
            todays_tasks = copy.deepcopy(all_tasks_flat)
            
            # Assegnazione
            def get_load(op):
                if day_assign[op] == "FERIE": return 99
                if not day_assign[op]: return 0
                return day_assign[op].count('+') + 1

            for t in todays_tasks:
                candidates = [op for op in available_ops if t in st.session_state.config["SKILLS"].get(op, [])]
                
                if not candidates:
                    if day_col not in missing: missing[day_col] = []
                    missing[day_col].append(t)
                    continue

                random.shuffle(candidates)
                # Sort: 1. Carico oggi, 2. Storico
                candidates.sort(key=lambda x: (get_load(x), history_cnt[x].get(t, 0)))
                
                chosen = None
                for op in candidates:
                    if get_load(op) < max_tasks:
                        chosen = op
                        break
                
                if chosen:
                    if day_assign[chosen]: day_assign[chosen] += f" + {t}"
                    else: day_assign[chosen] = t
                    history_cnt[chosen][t] = history_cnt[chosen].get(t, 0) + 1
            
            # Assegnazione Pause
            slots = copy.deepcopy(st.session_state.config["PAUSE"]["SLOTS"])
            random.shuffle(slots)
            slot_idx = 0
            fixed_pause = st.session_state.config["PAUSE"]["FISSI"]
            
            for op in available_ops:
                if day_assign[op] and day_assign[op] != "FERIE":
                    p_time = fixed_pause.get(op)
                    if not p_time and slots:
                        p_time = slots[slot_idx % len(slots)]
                        slot_idx += 1
                    if p_time: day_assign[op] += f"\n☕ {p_time}"
            
            out_sched[day_col] = day_assign

        # Visualizzazione
        res_df = pd.DataFrame(out_sched)
        
        # Funzione Colori
        def style_map(val):
            s = str(val)
            if "FERIE" in s: return "background-color: #e06666"
            if "🎉" in s: return "background-color: #f4cccc"
            for t, color in task_color_map.items():
                if t in s: return f"background-color: {color}"
            return ""

        st.success("Generazione Completata!")
        st.dataframe(res_df.style.applymap(style_map), use_container_width=True, height=600)
        
        if missing:
            st.error("Alcuni task non sono stati assegnati per mancanza di operatori disponibili:")
            st.json(missing)
            
        st.download_button("Scarica CSV Turni", res_df.to_csv(sep=";").encode("utf-8"), "turni.csv")
