import streamlit as st
import pandas as pd
import calendar
import random
import copy
from datetime import date
import holidays

st.set_page_config(page_title="Turni Trust Pro", layout="wide")
st.title("🧩 Turni Trust - All In One Version")

# ==============================================================================
# 1. CONFIGURAZIONE DATI
# ==============================================================================
# Inserisci qui i dati. Quando salvi questo file, l'app si aggiorna in tempo reale.

CONFIG = {
    "OPERATORS": [
        "Gurpal S.", "Nicola T.", "Paolo G.", "Lorenzo T.", "Andrea V.",
        "Federico P.", "Erica B.", "Daniela C.", "Francesca F.", "Lorenza V.",
        "Daniela G.", "Katia B.", "Caterina B.", "Maria S."
    ],
    
    # COMPETENZE CON LA NOMENCLATURA RICHIESTA (Prefisso SERVIZIO:)
    "OPERATOR_SKILLS": {
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

    # ORARI TELEFONO
    "TURNI_TELEFONO_FISSI": {
        "Gurpal S.": "11:00 - 12:00",
        "Nicola T.": "11:00 - 12:00",
        "Paolo G.": "12:00 - 13:00",
        "Lorenzo T.": "09:00 - 10:00",
        "Andrea V.": "10:00 - 11:00",
        "Federico P.": "11:00 - 12:00",
        "Erica B.": "10:00 - 11:00",
        "Daniela C.": "15:00 - 16:00",
        "Francesca F.": "10:00 - 11:00",
        "Katia B.": "10:00 - 11:00"
    },

    # PAUSE PRANZO
    "PAUSE_PRANZO": {
        "FISSI": {
            "Nicola T.": "13:00 - 14:30", "Paolo G.": "13:30 - 15:00", "Lorenzo T.": "13:00 - 14:30",
            "Andrea V.": "13:00 - 14:30", "Federico P.": "13:00 - 14:30", "Erica B.": "13:00 - 14:30",
            "Daniela C.": "13:30 - 15:00", "Francesca F.": "13:00 - 14:30", "Lorenza V.": "13:00 - 14:30",
            "Daniela G.": "13:00 - 14:30", "Caterina B.": "13:00 - 14:30", "Maria S.": "13:00 - 14:30"
        },
        "SLOT_ROTAZIONE": ["12:30 - 14:00", "13:30 - 15:00"]
    },

    # GIORNATA TIPO (Deve combaciare esattamente con le skill sopra)
    "GIORNATA_TIPO": [
        {"nome": "FATTURAZIONE: cc.fatturazione", "skill_richiesta": "FATTURAZIONE: cc.fatturazione", "qty": 1, "colore": "#4FFF81"},
        {"nome": "FATTURAZIONE: SDO", "skill_richiesta": "FATTURAZIONE: SDO", "qty": 1, "colore": "#4FFF81"},
        {"nome": "FATTURAZIONE: PECMAN", "skill_richiesta": "FATTURAZIONE: PECMAN", "qty": 1, "colore": "#4FFF81"},
        {"nome": "FIRMA: PECMAN/SDO", "skill_richiesta": "FIRMA: PECMAN/SDO", "qty": 1, "colore": "#ffb74f"},
        {"nome": "FIRMA: cc.firma", "skill_richiesta": "FIRMA: cc.firma", "qty": 1, "colore": "#ffb74f"},
        {"nome": "SPID: cc.spid", "skill_richiesta": "SPID: cc.spid", "qty": 1, "colore": "#549ff5"},
        {"nome": "SPID: PECMAN/SDO", "skill_richiesta": "SPID: PECMAN/SDO", "qty": 1, "colore": "#549ff5"},
        {"nome": "PEC: reparto.tecnico", "skill_richiesta": "PEC: reparto.pec", "qty": 1, "colore": "#FF5353"},
        {"nome": "PEC: Escalation SDO/PECMAN", "skill_richiesta": "PEC: PECMAN/SDO escalation", "qty": 1, "colore": "#FF5353"},
        {"nome": "PEC: Caselle Occupate", "skill_richiesta": "PEC: Caselle Occupate", "qty": 1, "colore": "#FF9696"},
        {"nome": "PEC: PECMAN Mattina", "skill_richiesta": "PEC: PECMAN/SDO MATTINA", "qty": 1, "colore": "#FF9696"},
        {"nome": "PEC: PECMAN Pomeriggio", "skill_richiesta": "PEC: PECMAN/SDO POMERIGGIO", "qty": 1, "colore": "#FF9696"}
    ],
    
    # SCHEMA SERVIZI (Per visualizzazione Matrice - Aggiornato con i nomi completi)
    "SERVICES_SCHEMA": {
        "FATTURAZIONE": ["FATTURAZIONE: cc.fatturazione", "FATTURAZIONE: SDO", "FATTURAZIONE: PECMAN"],
        "FIRMA": ["FIRMA: cc.firma", "FIRMA: PECMAN/SDO"],
        "SPID": ["SPID: cc.spid", "SPID: PECMAN/SDO"],
        "PEC": ["PEC: reparto.pec", "PEC: Caselle attesa attivazione", "PEC: PECMAN/SDO escalation", "PEC: Caselle Occupate", "PEC: PECMAN/SDO MATTINA", "PEC: PECMAN/SDO POMERIGGIO"]
    }
}

# ==============================================================================
# 2. LOGICA APPLICATIVA
# ==============================================================================

if 'presenze_db' not in st.session_state:
    st.session_state.presenze_db = {}

# --- INTERFACCIA ---
main_tab1, main_tab2, main_tab3 = st.tabs(["🗓️ GENERAZIONE TURNI", "🛠️ VISUALIZZA MATRICE", "ℹ️ ISTRUZIONI"])

with main_tab3:
    st.header("Configurazione Attuale")
    st.info("Per modificare permanentemente questi dati, edita il file app.py su GitHub.")
    st.json(CONFIG)

with main_tab2:
    st.header("Matrice Competenze (Sola Lettura)")
    st.caption("Verifica qui chi sa fare cosa. Per modifiche, edita CONFIG in app.py")
    
    # Costruzione tabella usando i nomi ESATTI senza manipolazioni
    all_skill_cols = []
    # Prima raccogliamo le skill definite nello schema
    for service, tasks in CONFIG["SERVICES_SCHEMA"].items():
        for t in tasks:
            if t not in all_skill_cols: all_skill_cols.append(t)
            
    # Poi aggiungiamo eventuali skill orfane dalla Giornata Tipo
    for t in CONFIG["GIORNATA_TIPO"]:
        skill = t["skill_richiesta"]
        if skill not in all_skill_cols:
            all_skill_cols.append(skill)

    rows = []
    for op in CONFIG["OPERATORS"]:
        r = {"Operatore": op}
        my_s = CONFIG["OPERATOR_SKILLS"].get(op, [])
        for col in all_skill_cols:
            # Controllo ESATTO della stringa
            r[col] = "✅" if col in my_s else ""
        rows.append(r)
        
    df_m = pd.DataFrame(rows).set_index("Operatore")
    st.dataframe(df_m, use_container_width=True, height=600)

with main_tab1:
    mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    
    st.sidebar.header("Impostazioni")
    mese_s = st.sidebar.selectbox("Mese", mesi)
    anno_s = st.sidebar.number_input("Anno", 2024, 2030, 2026)
    st.sidebar.divider()
    modo = st.sidebar.radio("Modalità Rotazione", ["Giornaliera", "Settimanale"], index=0)
    st.sidebar.markdown("---")
    max_tasks = st.sidebar.slider("Max Lavorazioni/giorno", 1, 6, 3)
    
    mese_n = mesi.index(mese_s) + 1
    _, nd = calendar.monthrange(anno_s, mese_n)
    days = [date(anno_s, mese_n, x) for x in range(1, nd+1)]
    hols = holidays.IT(years=anno_s)
    cols = [f"{d.day:02d} {['Lun','Mar','Mer','Gio','Ven','Sab','Dom'][d.weekday()]}" for d in days]
    mask = [(d.weekday()>=5 or d in hols) for d in days]
    ops = CONFIG["OPERATORS"]
    
    st.subheader(f"Piano Turni: {mese_s} {anno_s}")
    st.warning("⚠️ Nota: Le assenze inserite qui si resettano se ricarichi la pagina.")
    
    df_base = pd.DataFrame(False, index=ops, columns=cols)
    for i, c in enumerate(cols): 
        if mask[i]: df_base[c] = True 
    
    t1, t2, t3 = st.tabs(["FERIE", "P.MATTINA", "P.POMERIGGIO"])
    with t1: in_f = st.data_editor(df_base.copy(), key="f", height=200)
    with t2: in_pm = st.data_editor(pd.DataFrame(False, index=ops, columns=cols), key="pm", height=200)
    with t3: in_pp = st.data_editor(pd.DataFrame(False, index=ops, columns=cols), key="pp", height=200)

    st.divider()

    if st.button("🚀 GENERA TURNI", type="primary"):
        out_sched = {}
        missing = {}
        history_cnt = {op: {} for op in ops}
        
        # PREPARAZIONE TASK E ORDINAMENTO PER SCARSITÀ
        tasks_base = []
        for t in CONFIG["GIORNATA_TIPO"]:
            for _ in range(int(t.get("qty", 1))): tasks_base.append(copy.deepcopy(t))
            
        def count_capable(task_name):
            # Trova la skill richiesta per questo task
            task_info = next((t for t in CONFIG["GIORNATA_TIPO"] if t["nome"] == task_name), None)
            if not task_info: return 999
            needed_skill = task_info["skill_richiesta"]
            # Conta quanti operatori hanno ESATTAMENTE quella stringa skill
            return sum(1 for op in ops if needed_skill in CONFIG["OPERATOR_SKILLS"].get(op, []))
        
        # Ordina: prima i task che sanno fare in pochi
        tasks_base.sort(key=lambda t: count_capable(t["nome"]))
        
        weekly_sticky = {}

        for i, day_col in enumerate(cols):
            curr_date = days[i]
            
            # GESTIONE FESTIVI E WEEKEND
            if curr_date in hols:
                out_sched[day_col] = {op: f"🎉 {hols.get(curr_date)}" for op in ops}
                continue
            if curr_date.weekday() >= 5 and not any(in_f[day_col]):
                out_sched[day_col] = {op: "" for op in ops}
                continue

            if curr_date.weekday() == 0: weekly_sticky = {} 

            day_assign = {op: "" for op in ops}
            available_ops = []
            
            # CHECK DISPONIBILITÀ
            for op in ops:
                if in_f.at[op, day_col]: day_assign[op] = "FERIE"
                elif in_pm.at[op, day_col]: day_assign[op] = "P.MATT"; available_ops.append(op)
                elif in_pp.at[op, day_col]: day_assign[op] = "P.POM"; available_ops.append(op)
                else: available_ops.append(op)
            
            todays_tasks = copy.deepcopy(tasks_base)
            
            # FUNZIONE ASSEGNAZIONE
            def get_load(op):
                if day_assign[op] in ["FERIE", "P.MATT", "P.POM"]: return 99
                if not day_assign[op]: return 0
                return day_assign[op].count('+') + 1

            def try_assign(task_list, mode_sticky=False):
                remaining = []
                for t in task_list:
                    assigned = False
                    candidates = []
                    for op in available_ops:
                        op_skills = CONFIG["OPERATOR_SKILLS"].get(op, [])
                        # Match ESATTO della stringa
                        if t["skill_richiesta"] in op_skills:
                            candidates.append(op)
                    
                    if not candidates:
                        remaining.append(t); continue

                    random.shuffle(candidates)
                    # EQUITÀ: Prima chi è più scarico oggi, poi chi l'ha fatto meno nel mese
                    candidates.sort(key=lambda x: (get_load(x), history_cnt[x].get(t["nome"], 0)))

                    chosen_one = None
                    for op in candidates:
                        if mode_sticky and t["nome"] not in weekly_sticky.get(op, []): continue
                        if get_load(op) < max_tasks:
                            if day_assign[op] and "P." not in day_assign[op] and "+" not in day_assign[op] and max_tasks == 1: continue
                            if day_assign[op] in ["FERIE"]: continue 
                            chosen_one = op; break
                    
                    # Force assign se necessario
                    if not chosen_one and not mode_sticky:
                        for op in candidates:
                            if day_assign[op] in ["FERIE", "P.MATT", "P.POM"]: continue 
                            chosen_one = op; break 

                    if chosen_one:
                        op = chosen_one
                        prefix = f"({day_assign[op]}) " if "P." in day_assign[op] else ""
                        if day_assign[op] and "P." not in day_assign[op]: day_assign[op] += f" + {t['nome']}"
                        else: day_assign[op] = prefix + t["nome"]
                        history_cnt[op][t["nome"]] = history_cnt[op].get(t["nome"], 0) + 1
                        assigned = True
                        if modo == "Settimanale":
                            if op not in weekly_sticky: weekly_sticky[op] = []
                            weekly_sticky[op].append(t["nome"])
                    
                    if not assigned: remaining.append(t)
                return remaining

            if modo == "Settimanale":
                todays_tasks = try_assign(todays_tasks, mode_sticky=True)
            
            final_rem = try_assign(todays_tasks, mode_sticky=False)
            if final_rem: missing[day_col] = [t["nome"] for t in final_rem]

            # PRANZI
            rotation_slots = CONFIG["PAUSE_PRANZO"]["SLOT_ROTAZIONE"]
            fixed_lunches = CONFIG["PAUSE_PRANZO"]["FISSI"]
            daily_lunch_slots = copy.deepcopy(rotation_slots)
            random.shuffle(daily_lunch_slots)
            lunch_idx = 0
            
            for op in ops:
                is_working = day_assign[op] not in ["FERIE"] and "🎉" not in day_assign[op]
                if is_working and day_assign[op] and day_assign[op] not in ["P.MATT", "P.POM"]:
                    lunch_time = ""
                    if op in fixed_lunches: lunch_time = fixed_lunches[op]
                    elif daily_lunch_slots:
                        lunch_time = daily_lunch_slots[lunch_idx % len(daily_lunch_slots)]
                        lunch_idx += 1
                    if lunch_time: day_assign[op] += f"\n🥘 {lunch_time}"

            out_sched[day_col] = day_assign

        # OUTPUT
        res_df = pd.DataFrame(out_sched)
        new_index = []
        for op in res_df.index:
            ph = CONFIG["TURNI_TELEFONO_FISSI"].get(op)
            if ph: new_index.append(f"{op}\n☎️ {ph}")
            else: new_index.append(op)
        res_df.index = new_index

        task_colors = {t["nome"]: t.get("colore", "#fff") for t in CONFIG["GIORNATA_TIPO"]}
        def colora(val):
            s = str(val); bg = ""
            if "🎉" in s: bg = "#f4cccc"
            elif "FERIE" in s: bg = "#e06666"
            elif "P." in s: bg = "#ffd966"
            else:
                for k, c in task_colors.items():
                    if k in s: bg = c; break
            return f'background-color: {bg}' if bg else ''

        st.success("Turni Generati con successo!")

        weeks = []
        curr_week = []
        for col in res_df.columns:
            if "Lun" in col and curr_week: weeks.append(curr_week); curr_week = []
            curr_week.append(col)
        if curr_week: weeks.append(curr_week)

        for i, w_cols in enumerate(weeks):
            working_cols = []
            for c in w_cols:
                is_weekend = "Sab" in c or "Dom" in c
                if not is_weekend: working_cols.append(c)

            if working_cols:
                st.markdown(f"### 📅 Settimana {i+1}")
                st.dataframe(res_df[working_cols].style.applymap(colora), use_container_width=True)
                
                week_errors = []
                for day in working_cols:
                    if day in missing and missing[day]:
                        tasks_str = ", ".join(missing[day])
                        week_errors.append(f"**{day}**: {tasks_str}")
                if week_errors:
                    st.error("⚠️ Task scoperti (Mancanza skill o operatori):")
                    for err in week_errors: st.markdown(f"- {err}")
                
                with st.expander(f"📋 Copia Dati Settimana {i+1}"):
                    st.code(res_df[working_cols].to_csv(sep='\t'), language='text')
                st.markdown("---")
        
        st.subheader("📋 Export Mese Completo")
        st.download_button("Scarica CSV", res_df.to_csv(sep=';').encode('utf-8'), f'Turni_{mese_s}.csv', 'text/csv')
