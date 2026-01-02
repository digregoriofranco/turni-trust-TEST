import streamlit as st
import pandas as pd
import calendar
import random
import json
import copy
from datetime import date
import holidays
from github import Github, GithubException

st.set_page_config(page_title="Turni Trust Pro - Cloud", layout="wide")
st.title("☁️ Turni Trust - Cloud Connected")

# ==============================================================================
# 1. GESTIONE CONNESSIONE GITHUB
# ==============================================================================

def get_file_from_github(filename):
    """Scarica un file specifico dal repository"""
    try:
        if "GITHUB_TOKEN" not in st.secrets or "REPO_NAME" not in st.secrets:
            return None, None
        token = st.secrets["GITHUB_TOKEN"]
        repo_name = st.secrets["REPO_NAME"]
        g = Github(token)
        repo = g.get_repo(repo_name)
        try:
            contents = repo.get_contents(filename)
            return json.loads(contents.decoded_content.decode()), contents.sha
        except:
            return {}, None
    except Exception as e:
        st.error(f"Errore lettura {filename}: {e}")
        return None, None

def save_file_to_github(filename, content, sha):
    """Salva un file su GitHub gestendo i conflitti (Errore 409)"""
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo_name = st.secrets["REPO_NAME"]
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        if sha is None:
            try:
                contents = repo.get_contents(filename)
                sha = contents.sha
            except:
                repo.create_file(filename, f"Create {filename}", json.dumps(content, indent=4))
                return True, None

        update_result = repo.update_file(
            path=filename,
            message=f"Update {filename}",
            content=json.dumps(content, indent=4),
            sha=sha
        )
        return True, update_result['content'].sha

    except GithubException as e:
        if e.status == 409:
            try:
                contents = repo.get_contents(filename)
                new_sha = contents.sha
                update_result = repo.update_file(
                    path=filename,
                    message=f"Update {filename} (Retry)",
                    content=json.dumps(content, indent=4),
                    sha=new_sha
                )
                return True, update_result['content'].sha
            except Exception as e2:
                st.error(f"Errore durante il retry automatico: {e2}")
                return False, None
        else:
            st.error(f"Errore salvataggio {filename}: {e}")
            return False, None

# ==============================================================================
# 2. CARICAMENTO DATI
# ==============================================================================

if 'config' not in st.session_state:
    cfg_data, cfg_sha = get_file_from_github("config.json")
    if cfg_data and "SERVICES" in cfg_data:
        st.session_state.config = cfg_data
        st.session_state.config_sha = cfg_sha
    else:
        st.error("Errore critico: config.json mancante o non valido. Controlla GitHub.")
        st.stop()
    
    leaves_data, leaves_sha = get_file_from_github("leaves.json")
    st.session_state.leaves = leaves_data if leaves_data else {}
    st.session_state.leaves_sha = leaves_sha
    
    st.toast("Dati sincronizzati col Cloud!", icon="☁️")

CONFIG = st.session_state.config

# ==============================================================================
# 3. INTERFACCIA
# ==============================================================================

tab_gen, tab_settings = st.tabs(["🗓️ GENERAZIONE TURNI", "⚙️ IMPOSTAZIONI"])

# ------------------------------------------------------------------------------
# TAB IMPOSTAZIONI
# ------------------------------------------------------------------------------
with tab_settings:
    st.header("⚙️ Configurazione")

    # 1. SERVIZI
    with st.expander("🎨 1. Servizi e Colori", expanded=True):
        services = CONFIG["SERVICES"]
        
        # Aggiungi
        st.markdown("#### ➕ Crea Nuovo Servizio")
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            new_svc = c1.text_input("Nome nuovo servizio")
            if c2.button("Aggiungi Servizio"):
                if new_svc and new_svc not in services:
                    services[new_svc] = {"color": "#cccccc", "tasks": []}
                    save_file_to_github("config.json", CONFIG, st.session_state.config_sha)
                    st.rerun()
        
        st.divider()
        st.markdown("#### ✏️ Modifica Servizi")

        for s_name, s_data in services.items():
            c_col, c_name, c_del = st.columns([0.5, 3, 1])
            new_color = c_col.color_picker(f"Colore {s_name}", s_data["color"], key=f"c_{s_name}")
            c_name.markdown(f"**{s_name}**")
            
            if new_color != s_data["color"]:
                s_data["color"] = new_color
            
            tasks_str = "\n".join(s_data["tasks"])
            new_tasks = st.text_area(f"Task {s_name}", value=tasks_str, height=100, key=f"t_{s_name}")
            
            cb1, cb2 = st.columns([1, 5])
            if cb1.button(f"💾 Salva {s_name}"):
                s_data["tasks"] = [t.strip() for t in new_tasks.split("\n") if t.strip()]
                save_file_to_github("config.json", CONFIG, st.session_state.config_sha)
                st.rerun()
            
            if c_del.button("🗑️ Elimina", key=f"del_{s_name}"):
                del services[s_name]
                save_file_to_github("config.json", CONFIG, st.session_state.config_sha)
                st.rerun()
            st.divider()

    # 2. OPERATORI
    with st.expander("👥 2. Operatori", expanded=False):
        curr_ops = "\n".join(CONFIG["OPERATORS"])
        new_ops = st.text_area("Lista Operatori", value=curr_ops, height=200)
        if st.button("💾 Salva Operatori"):
            CONFIG["OPERATORS"] = [x.strip() for x in new_ops.split("\n") if x.strip()]
            CONFIG["SKILLS"] = {op: CONFIG["SKILLS"].get(op, []) for op in CONFIG["OPERATORS"]}
            save_file_to_github("config.json", CONFIG, st.session_state.config_sha)
            st.rerun()

    # 3. MATRICE
    with st.expander("🛠️ 3. Matrice Competenze", expanded=False):
        svc_names = list(CONFIG["SERVICES"].keys())
        if svc_names:
            sel_svc = st.selectbox("Filtra per Servizio:", svc_names)
            svc_tasks = CONFIG["SERVICES"][sel_svc]["tasks"]
            cols_show = [f"{sel_svc}: {t}" for t in svc_tasks]
            
            rows = []
            for op in CONFIG["OPERATORS"]:
                curr = CONFIG["SKILLS"].get(op, [])
                r = {"Operatore": op}
                for c in cols_show: r[c] = c in curr
                rows.append(r)
            
            df_sk = pd.DataFrame(rows).set_index("Operatore")
            ed_sk = st.data_editor(df_sk, use_container_width=True, key=f"ed_{sel_svc}")
            
            if st.button(f"💾 Salva Competenze ({sel_svc})"):
                for op, row in ed_sk.iterrows():
                    old = CONFIG["SKILLS"].get(op, [])
                    others = [s for s in old if not s.startswith(f"{sel_svc}:")]
                    new_sel = [c for c in cols_show if row[c]]
                    CONFIG["SKILLS"][op] = others + new_sel
                save_file_to_github("config.json", CONFIG, st.session_state.config_sha)
                st.success("Salvato!")

    # 4. PAUSE
    with st.expander("☕ 4. Telefoni & Pause", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Orari Telefono**")
            ph_df = pd.DataFrame([{"Operatore": op, "Orario": CONFIG["TELEFONI"].get(op, "")} for op in CONFIG["OPERATORS"]])
            ed_ph = st.data_editor(ph_df, hide_index=True)
            if st.button("💾 Salva Telefoni"):
                CONFIG["TELEFONI"] = {r["Operatore"]: r["Orario"] for _, r in ed_ph.iterrows() if r["Orario"]}
                save_file_to_github("config.json", CONFIG, st.session_state.config_sha)
        with c2:
            st.markdown("**Slot Pause**")
            slots = st.text_area("Slot", value="\n".join(CONFIG["PAUSE"]["SLOTS"]))
            if st.button("💾 Salva Slot"):
                CONFIG["PAUSE"]["SLOTS"] = [x.strip() for x in slots.split("\n") if x.strip()]
                save_file_to_github("config.json", CONFIG, st.session_state.config_sha)

# ------------------------------------------------------------------------------
# TAB GENERAZIONE
# ------------------------------------------------------------------------------
with tab_gen:
    st.header("Gestione Turni")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        mese_s = st.selectbox("Mese", mesi)
        mese_n = mesi.index(mese_s) + 1
    with c2:
        anno_s = st.number_input("Anno", 2024, 2030, 2026)
    with c3:
        max_tasks = st.slider("Max Task Simultanei", 1, 6, 3)

    LEAVES_KEY = f"{anno_s}_{mese_n}"
    _, nd = calendar.monthrange(anno_s, mese_n)
    days = [date(anno_s, mese_n, x) for x in range(1, nd+1)]
    hols = holidays.IT(years=anno_s)
    # Colonne totali (per input assenze)
    cols = [f"{d.day:02d} {['Lun','Mar','Mer','Gio','Ven','Sab','Dom'][d.weekday()]}" for d in days]
    ops = CONFIG["OPERATORS"]
    
    st.divider()
    
    # ASSENZE
    current_leaves = st.session_state.leaves.get(LEAVES_KEY, {"ferie": {}, "p_matt": {}, "p_pom": {}})
    
    def create_bool_df(saved_dict, prefill_weekends=False):
        df = pd.DataFrame(False, index=ops, columns=cols)
        if prefill_weekends and not saved_dict:
            for i, c in enumerate(cols):
                if days[i].weekday() >= 5 or days[i] in hols: df[c] = True
        if saved_dict:
            temp_df = pd.DataFrame(saved_dict)
            df.update(temp_df)
            df = df.fillna(False).astype(bool)
        return df

    t1, t2, t3 = st.tabs(["🔴 FERIE", "🟡 P. MATTINA", "🟠 P. POMERIGGIO"])
    with t1:
        st.caption("Spunta i giorni di assenza completa.")
        df_ferie = create_bool_df(current_leaves.get("ferie"), prefill_weekends=True)
        in_ferie = st.data_editor(df_ferie, key="ed_ferie", height=250)
    with t2:
        df_pm = create_bool_df(current_leaves.get("p_matt"))
        in_pm = st.data_editor(df_pm, key="ed_pm", height=250)
    with t3:
        df_pp = create_bool_df(current_leaves.get("p_pom"))
        in_pp = st.data_editor(df_pp, key="ed_pp", height=250)

    if st.button("💾 SALVA ASSENZE SU CLOUD", type="secondary"):
        with st.spinner("Salvataggio..."):
            st.session_state.leaves[LEAVES_KEY] = {
                "ferie": in_ferie.to_dict(),
                "p_matt": in_pm.to_dict(),
                "p_pom": in_pp.to_dict()
            }
            res, new_sha = save_file_to_github("leaves.json", st.session_state.leaves, st.session_state.leaves_sha)
            if res:
                st.session_state.leaves_sha = new_sha
                st.success("Salvataggio riuscito!")

    st.divider()

    # GENERAZIONE
    if st.button("🚀 CALCOLA TURNI (SETTIMANALI)", type="primary"):
        out = {}
        missing = {}
        cnt = {op: {} for op in ops}
        
        # Mappa colori e lista task completa
        all_tasks = []
        col_map = {}
        for s, d in CONFIG["SERVICES"].items():
            for t in d["tasks"]:
                full = f"{s}: {t}"
                all_tasks.append(full)
                col_map[full] = d["color"]
        
        def scarcity(t): return sum(1 for op in ops if t in CONFIG["SKILLS"].get(op, []))
        all_tasks.sort(key=scarcity)
        
        # MEMORIA SETTIMANALE ("Master Plan")
        weekly_assignments = {} # {Op: [Task1, Task2]}
        weekly_lunches = {}     # {Op: "13:00"}
        
        # Iterazione giorni
        for i, col in enumerate(cols):
            d_obj = days[i]
            
            # Reset del piano settimanale se è Lunedì
            if d_obj.weekday() == 0:
                weekly_assignments = {}
                weekly_lunches = {}

            # --- 1. GESTIONE FESTIVI E WEEKEND ---
            
            # Se weekend -> Cella vuota e skip (Ma non visibile in output finale)
            if d_obj.weekday() >= 5:
                out[col] = {op: "" for op in ops}
                continue
                
            # Se festivo -> Mostra "Festivo" (colore rosa) e skip assegnazione
            if d_obj in hols:
                out[col] = {op: f"🎉 {hols[d_obj]}" for op in ops}
                continue

            # --- 2. PREPARAZIONE DISPONIBILITÀ GIORNALIERA ---
            day_ass = {op: "" for op in ops}
            available_ops = [] # Operatori presenti (anche parzialmente)
            
            for op in ops:
                if in_ferie.at[op, col]: day_ass[op] = "FERIE"
                elif in_pm.at[op, col]: day_ass[op] = "P.MATT"; available_ops.append(op)
                elif in_pp.at[op, col]: day_ass[op] = "P.POM"; available_ops.append(op)
                else: available_ops.append(op)
            
            if not available_ops:
                out[col] = day_ass
                continue

            # --- 3. LOGICA DI ASSEGNAZIONE "STICKY" ---
            
            # Lista task da assegnare oggi
            tasks_to_assign = copy.deepcopy(all_tasks)
            assigned_this_day = [] # Per tracciare chi ha già lavorato oggi
            
            # FASE A: MANTENIMENTO ASSEGNAZIONI SETTIMANALI (PRIORITÀ ALTA)
            # Se un operatore ha un task settimanale ED è presente, glielo ridiamo.
            for op in available_ops:
                if op in weekly_assignments:
                    # Recupera i task assegnati a questo operatore nel piano settimanale
                    my_weekly_tasks = weekly_assignments[op]
                    
                    # Controlla se questi task sono ancora disponibili nel pool di oggi
                    # (Potrebbero essere stati presi da altri se la logica fosse diversa, ma qui forziamo)
                    tasks_confirmed = []
                    for t in my_weekly_tasks:
                        if t in tasks_to_assign:
                            tasks_confirmed.append(t)
                            tasks_to_assign.remove(t) # Toglie dal pool generale
                    
                    if tasks_confirmed:
                        # Assegna
                        t_str = " + ".join(tasks_confirmed)
                        prefix = f"({day_ass[op]}) " if "P." in day_ass[op] else ""
                        if day_ass[op] and "P." not in day_ass[op]: day_ass[op] += " + " + t_str
                        else: day_ass[op] = prefix + t_str
                        
                        cnt[op][t] = cnt[op].get(t, 0) + 1
                        assigned_this_day.append(op)

            # FASE B: RIEMPIMENTO GAP (ORPHAN TASKS O NUOVE ASSEGNAZIONI)
            # Assegna i task rimanenti (o perché è Lunedì, o perché il titolare è assente)
            
            def load(op):
                if day_ass[op] in ["FERIE", "P.MATT", "P.POM"]: return 99
                if op in assigned_this_day: return day_ass[op].count('+') + 1 # Già ha task settimanali
                if not day_ass[op]: return 0
                return day_ass[op].count('+') + 1

            for t in tasks_to_assign:
                # Trova candidati capaci
                cands = [op for op in available_ops if t in CONFIG["SKILLS"].get(op, [])]
                
                if not cands:
                    if col not in missing: missing[col] = []
                    missing[col].append(t)
                    continue
                
                random.shuffle(cands)
                # Ordina: Prima chi è scarico oggi, poi chi l'ha fatto meno nel mese
                cands.sort(key=lambda x: (load(x), cnt[x].get(t, 0)))
                
                chosen = None
                for op in cands:
                    if load(op) < max_tasks: chosen = op; break
                
                if not chosen: # Force assign a chiunque non sia in ferie
                    for op in cands:
                        if day_ass[op] not in ["FERIE"]: chosen = op; break
                
                if chosen:
                    # Assegna nel giorno
                    prefix = f"({day_ass[chosen]}) " if "P." in day_ass[chosen] else ""
                    if day_ass[chosen] and "P." not in day_ass[chosen]: 
                        day_ass[chosen] += f" + {t}"
                    else: 
                        day_ass[chosen] = prefix + t
                    
                    cnt[chosen][t] = cnt[chosen].get(t, 0) + 1
                    assigned_this_day.append(chosen)
                    
                    # SALVA NEL PIANO SETTIMANALE SE NON ESISTE (Es. è Lunedì o è un nuovo task)
                    # Nota: Se è un sostituto (il titolare originale è in weekly_assignments ma è assente),
                    # NON sovrascriviamo il weekly_assignments del titolare.
                    # Ma se nessuno aveva questo task, il sostituto diventa titolare per la settimana?
                    # Semplificazione richiesta: "Se manca, va ad altro, se torna riprende".
                    # Quindi salviamo in weekly solo se non c'era già un assegnatario per quel task?
                    # O più semplicemente: Salviamo in weekly_assignments solo il Lunedì.
                    
                    if d_obj.weekday() == 0: # Solo Lunedì "congela" il piano
                        if chosen not in weekly_assignments: weekly_assignments[chosen] = []
                        weekly_assignments[chosen].append(t)

            # --- 4. PAUSE & TELEFONI ---
            
            # Gestione Pause Sticky
            slots = copy.deepcopy(CONFIG["PAUSE"]["SLOTS"])
            random.shuffle(slots)
            s_i = 0
            
            for op in available_ops:
                # Solo se lavora giornata intera (no permessi, no ferie)
                if "P." not in day_ass[op] and "FERIE" not in day_ass[op]:
                    
                    p_time = None
                    
                    # 1. Pausa Fissa (Configurazione)
                    if op in CONFIG["PAUSE"]["FISSI"]:
                        p_time = CONFIG["PAUSE"]["FISSI"][op]
                    
                    # 2. Pausa Settimanale (Se già assegnata lunedì)
                    elif op in weekly_lunches:
                        p_time = weekly_lunches[op]
                    
                    # 3. Nuova Pausa (Rotazione)
                    elif slots:
                        p_time = slots[s_i % len(slots)]
                        s_i += 1
                        # Se è Lunedì, salva per la settimana
                        if d_obj.weekday() == 0:
                            weekly_lunches[op] = p_time
                    
                    if p_time:
                        day_ass[op] += f"\n☕ {p_time}"
            
            out[col] = day_ass
            
        res_df = pd.DataFrame(out)

        # -----------------------------------------------------------
        # VISUALIZZAZIONE FINALE: NO SAB/DOM
        # -----------------------------------------------------------
        # Mostra colonne Lun-Ven (Inclusi festivi se cadono in settimana)
        cols_to_show = [c for i, c in enumerate(cols) if days[i].weekday() < 5]
        final_view_df = res_df[cols_to_show]

        # Aggiungi Telefono all'intestazione (Indice)
        new_index = []
        for op in final_view_df.index:
            tel = CONFIG["TELEFONI"].get(op)
            lbl = f"{op} (☎️ {tel})" if tel else op
            new_index.append(lbl)
        final_view_df.index = new_index

        def styler(v):
            s = str(v)
            if "FERIE" in s: return "background-color: #ffc4c4" # Rosa Pastello
            if "P." in s: return "background-color: #ffd966"
            if "🎉" in s: return "background-color: #f4cccc" # Festivo
            for t, c in col_map.items():
                if t in s: return f"background-color: {c}"
            return ""

        st.success("Turni Calcolati con logica Settimanale!")
        
        weeks = []
        curr_week = []
        for col in final_view_df.columns:
            if "Lun" in col and curr_week: weeks.append(curr_week); curr_week = []
            curr_week.append(col)
        if curr_week: weeks.append(curr_week)

        for i, w_cols in enumerate(weeks):
            st.markdown(f"### 📅 Settimana {i+1}")
            st.dataframe(final_view_df[w_cols].style.applymap(styler), use_container_width=True)
            with st.expander(f"Copia Settimana {i+1}"):
                st.code(final_view_df[w_cols].to_csv(sep='\t'), language='text')
            st.markdown("---")

        if missing: st.warning("Task scoperti:"); st.json(missing)
        st.download_button("Scarica Mese (No Weekend)", final_view_df.to_csv(sep=";").encode("utf-8"), f"Turni_{mese_s}.csv")
