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
# 1. CONFIGURAZIONE INIZIALE (I TUOI DATI)
# ==============================================================================
# Questa configurazione viene caricata se non ci sono salvataggi precedenti.

DEFAULT_CONFIG = {
    "OPERATORS": [
        "Gurpal S.", "Nicola T.", "Paolo G.", "Lorenzo T.", "Andrea V.",
        "Federico P.", "Erica B.", "Daniela C.", "Francesca F.", "Lorenza V.",
        "Daniela G.", "Katia B.", "Caterina B.", "Maria S."
    ],
    
    # Struttura Servizi e Task
    "SERVICES": {
        "FATTURAZIONE": {"color": "#4FFF81", "tasks": ["cc.fatturazione", "SDO", "PECMAN"]},
        "FIRMA": {"color": "#ffb74f", "tasks": ["cc.firma", "PECMAN/SDO"]},
        "SPID": {"color": "#549ff5", "tasks": ["cc.spid", "PECMAN/SDO"]},
        "PEC": {"color": "#FF5353", "tasks": ["reparto.pec", "Caselle attesa attivazione", "PECMAN/SDO escalation", "Caselle Occupate", "PECMAN/SDO MATTINA", "PECMAN/SDO POMERIGGIO"]}
    },
    
    # Competenze (Mappate direttamente sui nomi completi "SERVIZIO: Task")
    "SKILLS": {
        "Gurpal S.": ["FATTURAZIONE: cc.fatturazione", "FATTURAZIONE: SDO", "FATTURAZIONE: PECMAN"],
        "Nicola T.": ["SPID: PECMAN/SDO", "SPID: cc.spid", "PEC: reparto.pec", "PEC: Caselle attesa attivazione", "PEC: PECMAN/SDO escalation"],
        "Paolo G.": ["PEC: reparto.pec", "PEC: Caselle attesa attivazione", "PEC: PECMAN/SDO escalation"],
        "Lorenzo T.": ["PEC: reparto.pec", "PEC: Caselle attesa attivazione", "PEC: PECMAN/SDO escalation"],
        "Andrea V.": ["FIRMA: cc.firma", "FIRMA: PECMAN/SDO"],
        "Federico P.": ["FIRMA: cc.firma", "FIRMA: PECMAN/SDO", "PEC: reparto.pec", "PEC: Caselle attesa attivazione", "PEC: PECMAN/SDO escalation"],
        "Erica B.": ["PEC: Caselle Occupate", "PEC: PECMAN/SDO MATTINA", "PEC: PECMAN/SDO POMERIGGIO"],
        "Daniela C.": ["FATTURAZIONE: SDO", "FATTURAZIONE: PECMAN", "PEC: Caselle Occupate", "PEC: PECMAN/SDO MATTINA", "PEC: PECMAN/SDO POMERIGGIO"],
        "Francesca F.": ["FATTURAZIONE: SDO", "FATTURAZIONE: PECMAN", "PEC: Caselle Occupate", "PEC: PECMAN/SDO MATTINA", "PEC: PECMAN/SDO POMERIGGIO"],
        "Lorenza V.": ["FATTURAZIONE: SDO", "FATTURAZIONE: PECMAN", "SPID: PECMAN/SDO", "SPID: cc.spid"],
        "Daniela G.": ["SPID: PECMAN/SDO", "SPID: cc.spid", "PEC: Caselle Occupate", "PEC: PECMAN/SDO MATTINA", "PEC: PECMAN/SDO POMERIGGIO"],
        "Katia B.": ["FATTURAZIONE: cc.fatturazione", "FATTURAZIONE: SDO", "FATTURAZIONE: PECMAN", "PEC: Caselle Occupate", "PEC: PECMAN/SDO MATTINA", "PEC: PECMAN/SDO POMERIGGIO"],
        "Caterina B.": ["FATTURAZIONE: cc.fatturazione", "FATTURAZIONE: SDO", "FATTURAZIONE: PECMAN"],
        "Maria S.": []
    },

    "PAUSE": {
        "FISSI": {
            "Nicola T.": "13:00 - 14:30", "Paolo G.": "13:30 - 15:00", "Lorenzo T.": "13:00 - 14:30",
            "Andrea V.": "13:00 - 14:30", "Federico P.": "13:00 - 14:30", "Erica B.": "13:00 - 14:30",
            "Daniela C.": "13:30 - 15:00", "Francesca F.": "13:00 - 14:30", "Lorenza V.": "13:00 - 14:30",
            "Daniela G.": "13:00 - 14:30", "Caterina B.": "13:00 - 14:30", "Maria S.": "13:00 - 14:30"
        },
        "SLOTS": ["12:30 - 14:00", "13:00 - 14:30", "13:30 - 15:00"]
    },
    
    "TELEFONI": {
        "Gurpal S.": "11:00 - 12:00", "Nicola T.": "11:00 - 12:00", "Paolo G.": "12:00 - 13:00",
        "Lorenzo T.": "09:00 - 10:00", "Andrea V.": "10:00 - 11:00", "Federico P.": "11:00 - 12:00",
        "Erica B.": "10:00 - 11:00", "Daniela C.": "15:00 - 16:00", "Francesca F.": "10:00 - 11:00",
        "Katia B.": "10:00 - 11:00"
    }
}

# Inizializzazione Session State
if 'config' not in st.session_state:
    st.session_state.config = copy.deepcopy(DEFAULT_CONFIG)

# ==============================================================================
# 2. INTERFACCIA UTENTE
# ==============================================================================

st.title("🧩 Turni Trust - Pannello di Controllo (TEST)")

# Sidebar per Caricamento/Salvataggio Configurazione
with st.sidebar:
    st.header("💾 Memoria Dati")
    st.info("Qui puoi salvare le tue configurazioni.")
    
    uploaded_file = st.file_uploader("📂 Carica Configurazione (JSON)", type="json")
    if uploaded_file is not None:
        try:
            loaded_json = json.load(uploaded_file)
            st.session_state.config = loaded_json
            st.success("Configurazione caricata!")
            st.rerun()
        except Exception as e:
            st.error(f"Errore caricamento: {e}")

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
# TAB IMPOSTAZIONI
# ------------------------------------------------------------------------------
with tab_settings:
    st.header("Pannello di Configurazione")
    
    # 1. GESTIONE SERVIZI
    with st.expander("🎨 1. Servizi e Task", expanded=True):
        services = st.session_state.config["SERVICES"]
        
        # Aggiunta nuovo servizio
        c_add1, c_add2 = st.columns([2, 1])
        new_svc = c_add1.text_input("Nuovo Servizio")
        if c_add2.button("➕ Aggiungi"):
            if new_svc and new_svc not in services:
                services[new_svc] = {"color": "#cccccc", "tasks": []}
                st.rerun()

        for s_name, s_data in services.items():
            c1, c2, c3 = st.columns([0.5, 3, 1])
            new_col = c1.color_picker(f"Colore {s_name}", s_data["color"], key=f"c_{s_name}")
            if new_col != s_data["color"]:
                s_data["color"] = new_col
                st.rerun()
                
            c2.markdown(f"### {s_name}")
            
            tasks_text = c2.text_area(f"Task per {s_name}", value="\n".join(s_data["tasks"]), key=f"t_{s_name}", height=100)
            if c2.button(f"Salva Task {s_name}"):
                s_data["tasks"] = [t.strip() for t in tasks_text.split("\n") if t.strip()]
                st.toast("Task aggiornati")
                st.rerun()
            
            if c3.button("🗑️ Elimina", key=f"d_{s_name}"):
                del services[s_name]
                st.rerun()
            st.divider()

    # 2. OPERATORI
    with st.expander("👥 2. Gestione Operatori", expanded=False):
        current_ops = st.session_state.config["OPERATORS"]
        text_ops = st.text_area("Lista Operatori (uno per riga)", value="\n".join(current_ops), height=150)
        if st.button("💾 Aggiorna Lista Operatori"):
            new_ops_list = [x.strip() for x in text_ops.split("\n") if x.strip()]
            st.session_state.config["OPERATORS"] = new_ops_list
            # Pulisci skill orfane
            clean_skills = {op: st.session_state.config["SKILLS"].get(op, []) for op in new_ops_list}
            st.session_state.config["SKILLS"] = clean_skills
            st.toast("Lista salvata!")
            st.rerun()

    # 3. MATRICE SKILL
    with st.expander("🛠️ 3. Matrice Competenze", expanded=False):
        # Costruzione colonne dinamica basata sui servizi
        all_tasks_cols = []
        
        for s_name, s_data in st.session_state.config["SERVICES"].items():
            for t in s_data["tasks"]:
                # Qui usiamo la nomenclatura SERVIZIO: Task
                full_name = f"{s_name}: {t}"
                all_tasks_cols.append(full_name)
        
        rows = []
        for op in st.session_state.config["OPERATORS"]:
            op_skills = st.session_state.config["SKILLS"].get(op, [])
            row = {"Operatore": op}
            for col in all_tasks_cols:
                row[col] = col in op_skills
            rows.append(row)
            
        df_skills = pd.DataFrame(rows)
        if not df_skills.empty:
            df_skills.set_index("Operatore", inplace=True)
            edited_df = st.data_editor(df_skills, use_container_width=True, height=500)
            
            if st.button("💾 Salva Matrice"):
                new_skill_dict = {}
                for op, row in edited_df.iterrows():
                    skills = []
                    for col in all_tasks_cols:
                        if row[col]:
                            skills.append(col)
                    new_skill_dict[op] = skills
                st.session_state.config["SKILLS"] = new_skill_dict
                st.success("Matrice salvata!")

    # 4. PAUSE E TELEFONI
    with st.expander("☕ 4. Pause e Telefoni", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Slot Rotazione Pause**")
            slots_txt = st.text_area("Slot", value="\n".join(st.session_state.config["PAUSE"]["SLOTS"]))
            if st.button("Salva Slot"):
                st.session_state.config["PAUSE"]["SLOTS"] = [x.strip() for x in slots_txt.split("\n") if x.strip()]
                st.rerun()
        with c2:
            st.markdown("**Telefoni Fissi**")
            phones_df = pd.DataFrame([{"Operatore": op, "Telefono": st.session_state.config["TELEFONI"].get(op, "")} for op in st.session_state.config["OPERATORS"]])
            ed_ph = st.data_editor(phones_df, hide_index=True)
            if st.button("Salva Telefoni"):
                st.session_state.config["TELEFONI"] = {r["Operatore"]: r["Telefono"] for _, r in ed_ph.iterrows() if r["Telefono"]}
                st.rerun()

# ------------------------------------------------------------------------------
# TAB GENERAZIONE
# ------------------------------------------------------------------------------
with tab_gen:
    st.header("Generazione Turni")
    
    col_set1, col_set2, col_set3 = st.columns(3)
    with col_set1:
        mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        mese_s = st.selectbox("Mese", mesi)
        mese_n = mesi.index(mese_s) + 1
    with col_set2:
        anno_s = st.number_input("Anno", 2024, 2030, 2026)
    with col_set3:
        max_tasks = st.slider("Max Task/Giorno", 1, 6, 3)

    _, nd = calendar.monthrange(anno_s, mese_n)
    days = [date(anno_s, mese_n, x) for x in range(1, nd+1)]
    hols = holidays.IT(years=anno_s)
    cols = [f"{d.day:02d} {['Lun','Mar','Mer','Gio','Ven','Sab','Dom'][d.weekday()]}" for d in days]
    ops = st.session_state.config["OPERATORS"]
    
    st.markdown("### Assenze (Non salvate)")
    df_base = pd.DataFrame(False, index=ops, columns=cols)
    mask = [(d.weekday()>=5 or d in hols) for d in days]
    for i, c in enumerate(cols): 
        if mask[i]: df_base[c] = True 
    
    edited_absence = st.data_editor(df_base, key="absences_editor")
    
    if st.button("🚀 GENERA PIANO TURNI", type="primary"):
        out_sched = {}
        missing = {}
        history_cnt = {op: {} for op in ops}
        
        # Costruzione lista task piatta
        all_tasks_flat = []
        task_color_map = {}
        
        for s_name, s_data in st.session_state.config["SERVICES"].items():
            for t in s_data["tasks"]:
                full_name = f"{s_name}: {t}"
                all_tasks_flat.append(full_name)
                task_color_map[full_name] = s_data["color"]
        
        # Funzione Scarsità (conta quanti operatori hanno la skill)
        def count_capable(task_full_name):
            return sum(1 for op in ops if task_full_name in st.session_state.config["SKILLS"].get(op, []))
        
        # Ordina task per difficoltà
        all_tasks_flat.sort(key=lambda t: count_capable(t))
        
        for i, day_col in enumerate(cols):
            curr_date = days[i]
            
            if curr_date in hols:
                out_sched[day_col] = {op: f"🎉 {hols.get(curr_date)}" for op in ops}
                continue
            # Se weekend e non lavorativo
            if curr_date.weekday() >= 5 and not any(edited_absence[day_col]): 
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
            
            # Pause
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
            
            # Telefoni
            tel = st.session_state.config["TELEFONI"].get(op)
            if tel: day_assign[op] = f"☎️ {tel}\n" + day_assign[op]

            out_sched[day_col] = day_assign

        res_df = pd.DataFrame(out_sched)
        
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
            st.error("Alcuni task non sono stati assegnati:")
            st.json(missing)
