import streamlit as st
import pandas as pd
import calendar
import random
import json
import copy
from datetime import date
import holidays
from github import Github

st.set_page_config(page_title="Turni Trust Pro - Cloud", layout="wide")
st.title("☁️ Turni Trust - Cloud Connected")

# ==============================================================================
# 1. GESTIONE CONNESSIONE GITHUB
# ==============================================================================

def get_github_data():
    """Scarica il config.json direttamente dal repository"""
    try:
        # Tenta di recuperare i secrets, gestisce il caso in cui non siano impostati
        if "GITHUB_TOKEN" not in st.secrets or "REPO_NAME" not in st.secrets:
            return None, None
            
        token = st.secrets["GITHUB_TOKEN"]
        repo_name = st.secrets["REPO_NAME"]
        g = Github(token)
        repo = g.get_repo(repo_name)
        contents = repo.get_contents("config.json")
        return json.loads(contents.decoded_content.decode()), contents.sha
    except Exception as e:
        st.error(f"Errore connessione GitHub: {e}")
        return None, None

def save_to_github(new_config, sha):
    """Salva le modifiche su GitHub"""
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo_name = st.secrets["REPO_NAME"]
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        repo.update_file(
            path="config.json",
            message="Aggiornamento automatico da App Turni",
            content=json.dumps(new_config, indent=4),
            sha=sha
        )
        return True
    except Exception as e:
        st.error(f"Errore salvataggio su GitHub: {e}")
        return False

# ==============================================================================
# 2. DATI DI DEFAULT (FALLBACK)
# ==============================================================================
# Usati se non c'è connessione a GitHub o config.json

DEFAULT_CONFIG = {
    "OPERATORS": [
        "Gurpal S.", "Nicola T.", "Paolo G.", "Lorenzo T.", "Andrea V.",
        "Federico P.", "Erica B.", "Daniela C.", "Francesca F.", "Lorenza V.",
        "Daniela G.", "Katia B.", "Caterina B.", "Maria S."
    ],
    "SERVICES": {
        "FATTURAZIONE": {"color": "#4FFF81", "tasks": ["cc.fatturazione", "SDO", "PECMAN"]},
        "FIRMA": {"color": "#ffb74f", "tasks": ["cc.firma", "PECMAN/SDO"]},
        "SPID": {"color": "#549ff5", "tasks": ["cc.spid", "PECMAN/SDO"]},
        "PEC": {"color": "#FF5353", "tasks": ["reparto.pec", "Caselle attesa attivazione", "PECMAN/SDO escalation", "Caselle Occupate", "PECMAN/SDO MATTINA", "PECMAN/SDO POMERIGGIO"]}
    },
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

# ==============================================================================
# 3. LOGICA DI CARICAMENTO
# ==============================================================================

if 'config' not in st.session_state:
    data, sha = get_github_data()
    if data:
        st.session_state.config = data
        st.session_state.sha = sha
        st.toast("Dati caricati dal Cloud!", icon="☁️")
    else:
        st.warning("⚠️ Modalità Offline: impossibile connettersi a GitHub o Secrets non configurati. Uso dati locali.")
        st.session_state.config = copy.deepcopy(DEFAULT_CONFIG)
        st.session_state.sha = None

def save_state():
    if st.session_state.sha:
        with st.spinner("Salvataggio nel Cloud in corso..."):
            success = save_to_github(st.session_state.config, st.session_state.sha)
            if success:
                st.success("✅ Salvato! Ricarico...")
                _, new_sha = get_github_data()
                st.session_state.sha = new_sha
                st.rerun()
    else:
        st.error("Impossibile salvare: Connessione GitHub non attiva (mancano i Secrets?).")

CONFIG = st.session_state.config

# ==============================================================================
# 4. INTERFACCIA
# ==============================================================================

tab_gen, tab_settings = st.tabs(["🗓️ GENERAZIONE TURNI", "⚙️ IMPOSTAZIONI CLOUD"])

with tab_settings:
    st.header("Pannello di Controllo")
    
    # SERVIZI
    with st.expander("🎨 1. Servizi e Task", expanded=True):
        services = CONFIG["SERVICES"]
        c1, c2 = st.columns([3, 1])
        new_svc = c1.text_input("Nuovo Servizio")
        if c2.button("➕ Aggiungi") and new_svc:
            services[new_svc] = {"color": "#cccccc", "tasks": []}
            save_state()

        for s_name, s_data in services.items():
            c_col, c_name, c_del = st.columns([0.5, 3, 1])
            new_color = c_col.color_picker(f"Colore {s_name}", s_data["color"], key=f"c_{s_name}")
            c_name.markdown(f"**{s_name}**")
            
            if new_color != s_data["color"]:
                s_data["color"] = new_color
                # Nota: il colore si salva solo premendo un bottone di azione per non ricaricare continuamente
            
            tasks_str = "\n".join(s_data["tasks"])
            new_tasks = st.text_area(f"Task {s_name}", value=tasks_str, height=100, key=f"t_{s_name}")
            
            if st.button(f"💾 Aggiorna {s_name}"):
                s_data["tasks"] = [t.strip() for t in new_tasks.split("\n") if t.strip()]
                save_state()
            
            if c_del.button("🗑️", key=f"del_{s_name}"):
                del services[s_name]
                save_state()
            st.divider()

    # OPERATORI
    with st.expander("👥 2. Operatori", expanded=False):
        curr_ops = "\n".join(CONFIG["OPERATORS"])
        new_ops = st.text_area("Lista Operatori", value=curr_ops, height=200)
        if st.button("💾 Salva Operatori"):
            CONFIG["OPERATORS"] = [x.strip() for x in new_ops.split("\n") if x.strip()]
            save_state()

    # 3. MATRICE SKILL (FILTRATA PER SERVIZIO)
    with st.expander("🛠️ 3. Matrice Competenze (Filtrata)", expanded=False):
        st.info("Seleziona un servizio per modificare le competenze dei relativi task.")
        
        # 1. MENU A TENDINA PER SCEGLIERE IL SERVIZIO
        service_names = list(CONFIG["SERVICES"].keys())
        if not service_names:
            st.warning("Nessun servizio configurato.")
        else:
            selected_svc = st.selectbox("Filtra per Servizio:", service_names)
            
            # 2. RECUPERA SOLO I TASK DI QUEL SERVIZIO
            # Costruiamo i nomi completi (es. "FATTURAZIONE: PECMAN")
            tasks_of_service = CONFIG["SERVICES"][selected_svc]["tasks"]
            cols_to_show = [f"{selected_svc}: {t}" for t in tasks_of_service]
            
            if not cols_to_show:
                st.warning(f"Il servizio {selected_svc} non ha task configurati.")
            else:
                # 3. COSTRUISCI IL DATAFRAME FILTRATO
                rows = []
                for op in CONFIG["OPERATORS"]:
                    # Prendo le skill attuali dell'operatore
                    current_skills = CONFIG["SKILLS"].get(op, [])
                    row = {"Operatore": op}
                    
                    # Riempio le colonne (True/False) solo per i task visualizzati
                    for col in cols_to_show:
                        row[col] = col in current_skills
                    rows.append(row)
                
                df_filtered = pd.DataFrame(rows)
                df_filtered.set_index("Operatore", inplace=True)
                
                # 4. EDITOR INTERATTIVO
                edited_df = st.data_editor(
                    df_filtered, 
                    use_container_width=True, 
                    height=400,
                    key=f"editor_{selected_svc}" # Chiave unica per evitare conflitti
                )
                
                # 5. SALVATAGGIO INTELLIGENTE
                if st.button(f"💾 Salva Competenze ({selected_svc})"):
                    # Per ogni operatore, aggiorniamo SOLO le skill di questo servizio
                    for op, row in edited_df.iterrows():
                        # 1. Prendi tutte le skill che ha attualmente
                        old_skills = CONFIG["SKILLS"].get(op, [])
                        
                        # 2. Rimuovi da quella lista TUTTE le skill del servizio che stiamo modificando
                        # (Così puliamo il vecchio stato per questo servizio specifico)
                        skills_others = [s for s in old_skills if not s.startswith(f"{selected_svc}:")]
                        
                        # 3. Raccogli le nuove skill spuntate nella tabella
                        new_service_skills = [col for col in cols_to_show if row[col]]
                        
                        # 4. Unisci: Skill degli altri servizi + Nuove skill di questo servizio
                        CONFIG["SKILLS"][op] = skills_others + new_service_skills
                    
                    save_state()

    # TELEFONI E PAUSE
    with st.expander("☕ 4. Telefoni & Pause", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Orari Telefono**")
            ph_df = pd.DataFrame([{"Operatore": op, "Orario": CONFIG["TELEFONI"].get(op, "")} for op in CONFIG["OPERATORS"]])
            ed_ph = st.data_editor(ph_df, hide_index=True)
            if st.button("💾 Salva Telefoni"):
                CONFIG["TELEFONI"] = {r["Operatore"]: r["Orario"] for _, r in ed_ph.iterrows() if r["Orario"]}
                save_state()
        with c2:
            st.markdown("**Slot Pause**")
            slots = st.text_area("Slot", value="\n".join(CONFIG["PAUSE"]["SLOTS"]))
            if st.button("💾 Salva Slot"):
                CONFIG["PAUSE"]["SLOTS"] = [x.strip() for x in slots.split("\n") if x.strip()]
                save_state()

# GENERAZIONE
with tab_gen:
    st.header("Generazione Turni")
    c1, c2, c3 = st.columns(3)
    with c1:
        mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        mese_s = st.selectbox("Mese", mesi)
        mese_n = mesi.index(mese_s) + 1
    with c2:
        anno_s = st.number_input("Anno", 2024, 2030, 2026)
    with c3:
        max_tasks = st.slider("Max Task", 1, 6, 3)

    _, nd = calendar.monthrange(anno_s, mese_n)
    days = [date(anno_s, mese_n, x) for x in range(1, nd+1)]
    hols = holidays.IT(years=anno_s)
    cols = [f"{d.day:02d} {['Lun','Mar','Mer','Gio','Ven','Sab','Dom'][d.weekday()]}" for d in days]
    ops = CONFIG["OPERATORS"]
    
    st.markdown("### Assenze")
    df_base = pd.DataFrame(False, index=ops, columns=cols)
    for i, c in enumerate(cols):
        if days[i].weekday()>=5 or days[i] in hols: df_base[c] = True
    
    in_f = st.data_editor(df_base, key="abs")
    
    if st.button("🚀 GENERA", type="primary"):
        out = {}
        missing = {}
        cnt = {op: {} for op in ops}
        
        all_tasks = []
        col_map = {}
        for s, d in CONFIG["SERVICES"].items():
            for t in d["tasks"]:
                full = f"{s}: {t}"
                all_tasks.append(full)
                col_map[full] = d["color"]
        
        def scarcity(t): return sum(1 for op in ops if t in CONFIG["SKILLS"].get(op, []))
        all_tasks.sort(key=scarcity)
        
        for i, col in enumerate(cols):
            d_obj = days[i]
            if d_obj in hols:
                out[col] = {op: f"🎉 {hols[d_obj]}" for op in ops}
                continue
            if d_obj.weekday()>=5 and not any(in_f[col]):
                out[col] = {op: "" for op in ops}
                continue
            
            day_ass = {op: "" for op in ops}
            avail = []
            for op in ops:
                if in_f.at[op, col]: day_ass[op] = "FERIE"
                else: avail.append(op)
            
            day_tasks = copy.deepcopy(all_tasks)
            
            def load(op):
                if day_ass[op] == "FERIE": return 99
                if not day_ass[op]: return 0
                return day_ass[op].count('+') + 1

            for t in day_tasks:
                cands = [op for op in avail if t in CONFIG["SKILLS"].get(op, [])]
                if not cands:
                    if col not in missing: missing[col] = []
                    missing[col].append(t)
                    continue
                
                random.shuffle(cands)
                cands.sort(key=lambda x: (load(x), cnt[x].get(t, 0)))
                
                chosen = None
                for op in cands:
                    if load(op) < max_tasks: chosen = op; break
                
                if not chosen:
                    for op in cands:
                        if day_ass[op] != "FERIE": chosen = op; break
                
                if chosen:
                    if day_ass[chosen]: day_ass[chosen] += f" + {t}"
                    else: day_ass[chosen] = t
                    cnt[chosen][t] = cnt[chosen].get(t, 0) + 1
            
            # Pause & Telefoni
            slots = copy.deepcopy(CONFIG["PAUSE"]["SLOTS"])
            random.shuffle(slots)
            s_i = 0
            for op in avail:
                if day_ass[op] and day_ass[op] != "FERIE":
                    p = CONFIG["PAUSE"]["FISSI"].get(op)
                    if not p and slots: p = slots[s_i % len(slots)]; s_i += 1
                    if p: day_ass[op] += f"\n☕ {p}"
                    
                    tel = CONFIG["TELEFONI"].get(op)
                    if tel: day_ass[op] = f"☎️ {tel}\n" + day_ass[op]
            
            out[col] = day_ass
            
        res = pd.DataFrame(out)
        def styler(v):
            s = str(v)
            if "FERIE" in s: return "background-color: #e06666"
            if "🎉" in s: return "background-color: #f4cccc"
            for t, c in col_map.items():
                if t in s: return f"background-color: {c}"
            return ""
            
        st.dataframe(res.style.applymap(styler), use_container_width=True)
        if missing: st.warning("Task scoperti:"); st.json(missing)

