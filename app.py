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
        st.error("Errore critico: config.json mancante o struttura errata.")
        st.stop()
    
    leaves_data, leaves_sha = get_file_from_github("leaves.json")
    st.session_state.leaves = leaves_data if leaves_data else {}
    st.session_state.leaves_sha = leaves_sha

    shifts_data, shifts_sha = get_file_from_github("shifts.json")
    st.session_state.shifts = shifts_data if shifts_data else {}
    st.session_state.shifts_sha = shifts_sha
    
    st.toast("Dati sincronizzati col Cloud!", icon="☁️")

CONFIG = st.session_state.config

# ==============================================================================
# 3. UTILS DI VISUALIZZAZIONE
# ==============================================================================

def get_style_map():
    col_map = {}
    for s, d in CONFIG["SERVICES"].items():
        for t in d["tasks"]:
            col_map[f"{s}: {t}"] = d["color"]
    return col_map

def styler(v, col_map):
    s = str(v)
    if "FERIE" in s: return "background-color: #ffc4c4"
    if "P." in s: return "background-color: #ffd966"
    if "🎉" in s: return "background-color: #f4cccc"
    for t, c in col_map.items():
        if t in s: return f"background-color: {c}"
    return ""

def display_weeks(df_month, col_map, month_name, year):
    weeks_list = []
    current_week_cols = []
    for col in df_month.columns:
        if "Lun" in col and current_week_cols: 
            weeks_list.append(df_month[current_week_cols])
            current_week_cols = []
        current_week_cols.append(col)
    if current_week_cols: 
        weeks_list.append(df_month[current_week_cols])

    for i, w_df in enumerate(weeks_list):
        week_num = i + 1
        st.markdown(f"### 📅 Settimana {week_num}")
        st.dataframe(w_df.style.applymap(lambda x: styler(x, col_map)), use_container_width=True)
        
        c1, c2 = st.columns(2)
        csv_data = w_df.to_csv(sep=";").encode("utf-8")
        c1.download_button(
            label=f"📥 Scarica CSV (Settimana {week_num})",
            data=csv_data,
            file_name=f"Turni_{month_name}_{year}_Week{week_num}.csv",
            mime="text/csv",
            key=f"dl_csv_{month_name}_{week_num}_{random.randint(0,9999)}"
        )
        
        def html_formatter(val):
            return str(val).replace("\n", "<br>")
            
        html_table = w_df.style.applymap(lambda x: styler(x, col_map)).format(html_formatter).to_html()
        
        html_full = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                table {{ border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 12px; }}
                th, td {{ border: 1px solid #999; padding: 8px; text-align: center; vertical-align: top; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                td {{ white-space: pre-wrap; }} 
            </style>
        </head>
        <body>
            <h3>Turni {month_name} {year} - Settimana {week_num}</h3>
            {html_table}
        </body>
        </html>
        """
        c2.download_button(
            label=f"📥 Scarica HTML (Settimana {week_num})",
            data=html_full,
            file_name=f"Turni_{month_name}_{year}_Week{week_num}.html",
            mime="text/html",
            key=f"dl_html_{month_name}_{week_num}_{random.randint(0,9999)}"
        )
        st.markdown("---")

# ==============================================================================
# 4. INTERFACCIA PRINCIPALE
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
            if new_color != s_data["color"]: s_data["color"] = new_color
            
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

    # 4. PAUSE E TELEFONI
    with st.expander("☕ 4. Telefoni & Pause", expanded=False):
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("#### 📞 Orari Telefono")
            ph_rows = []
            for op in CONFIG["OPERATORS"]:
                ph_rows.append({"Operatore": op, "Orario Telefono": CONFIG["TELEFONI"].get(op, "")})
            
            df_ph = pd.DataFrame(ph_rows)
            ed_ph = st.data_editor(df_ph, hide_index=True, use_container_width=True, key="ph_editor")
            
        with c2:
            st.markdown("#### 🥪 Gestione Pause (Fisse vs Variabili)")
            st.info("Se lasci l'orario **VUOTO**, la pausa sarà **VARIABILE** (a rotazione sugli slot disponibili sotto). Se scrivi un orario, sarà **FISSA**.")
            
            # Tabella Pause Fisse
            pause_rows = []
            for op in CONFIG["OPERATORS"]:
                # Se c'è una pausa fissa salvata, la mostriamo, altrimenti vuoto
                fixed_p = CONFIG["PAUSE"]["FISSI"].get(op, "")
                pause_rows.append({"Operatore": op, "Orario Pausa (Es. 13:00)": fixed_p})
            
            df_pause = pd.DataFrame(pause_rows)
            ed_pause = st.data_editor(df_pause, hide_index=True, use_container_width=True, key="pause_editor")
            
            st.markdown("##### 🎰 Slot per Pause Variabili (Rotazione)")
            slots_str = "\n".join(CONFIG["PAUSE"]["SLOTS"])
            new_slots = st.text_area("Elenco Slot (uno per riga)", value=slots_str, height=100)

        # Pulsante unico di salvataggio per la sezione
        if st.button("💾 Salva Telefoni e Pause"):
            # 1. Salva Telefoni
            new_telefoni = {}
            for index, row in ed_ph.iterrows():
                if row["Orario Telefono"]:
                    new_telefoni[row["Operatore"]] = row["Orario Telefono"]
            CONFIG["TELEFONI"] = new_telefoni
            
            # 2. Salva Pause Fisse
            new_fissi = {}
            for index, row in ed_pause.iterrows():
                if row["Orario Pausa (Es. 13:00)"]:
                    new_fissi[row["Operatore"]] = row["Orario Pausa (Es. 13:00)"]
            CONFIG["PAUSE"]["FISSI"] = new_fissi
            
            # 3. Salva Slot
            CONFIG["PAUSE"]["SLOTS"] = [x.strip() for x in new_slots.split("\n") if x.strip()]
            
            save_file_to_github("config.json", CONFIG, st.session_state.config_sha)
            st.success("Configurazione salvata!")
            st.rerun()

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
        max_tasks = st.slider("Max Task Simultanei", 1, 6, 1)

    LEAVES_KEY = f"{anno_s}_{mese_n}"
    _, nd = calendar.monthrange(anno_s, mese_n)
    days = [date(anno_s, mese_n, x) for x in range(1, nd+1)]
    hols = holidays.IT(years=anno_s)
    cols = [f"{d.day:02d} {['Lun','Mar','Mer','Gio','Ven','Sab','Dom'][d.weekday()]}" for d in days]
    ops = CONFIG["OPERATORS"]
    
    st.divider()
    
    # 1. GESTIONE ASSENZE
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
                st.success("Assenze salvate!")

    st.divider()

    # 2. LOGICA TURNI
    saved_shifts_for_month = st.session_state.shifts.get(LEAVES_KEY, None)
    smart_update = False
    
    if saved_shifts_for_month:
        st.warning(f"Ci sono turni già salvati per {mese_s} {anno_s}.")
        col_opt1, col_opt2 = st.columns([1, 1])
        with col_opt1:
            smart_update = st.checkbox("🔄 Preserva turni esistenti (Modifica solo assenti)", value=True)
        with col_opt2:
            if st.button("🗑️ ELIMINA TURNI SALVATI (RESET)", type="primary"):
                del st.session_state.shifts[LEAVES_KEY]
                res, new_sha = save_file_to_github("shifts.json", st.session_state.shifts, st.session_state.shifts_sha)
                if res:
                    st.session_state.shifts_sha = new_sha
                    st.rerun()

    if st.button("🚀 CALCOLA TURNI", type="primary"):
        out = {}
        missing = {}
        cnt = {op: {} for op in ops}
        
        all_tasks = []
        for s, d in CONFIG["SERVICES"].items():
            for t in d["tasks"]:
                all_tasks.append(f"{s}: {t}")
        
        def scarcity(t): return sum(1 for op in ops if t in CONFIG["SKILLS"].get(op, []))
        all_tasks.sort(key=scarcity)
        
        weekly_assignments = {} 
        last_week_assignments = {} 
        weekly_lunches = {}
        current_week_idx = 0 
        
        for i, col in enumerate(cols):
            d_obj = days[i]
            if d_obj.weekday() == 0:
                last_week_assignments = copy.deepcopy(weekly_assignments)
                weekly_assignments = {}
                weekly_lunches = {}
                current_week_idx += 1

            if d_obj.weekday() >= 5: 
                out[col] = {op: "" for op in ops}; continue
            if d_obj in hols: 
                out[col] = {op: f"🎉 {hols[d_obj]}" for op in ops}; continue

            day_ass = {op: "" for op in ops}
            available_ops = []
            for op in ops:
                if in_ferie.at[op, col]: day_ass[op] = "FERIE"
                elif in_pm.at[op, col]: day_ass[op] = "P.MATT"; available_ops.append(op)
                elif in_pp.at[op, col]: day_ass[op] = "P.POM"; available_ops.append(op)
                else: available_ops.append(op)
            
            if not available_ops:
                out[col] = day_ass; continue

            tasks_to_assign = copy.deepcopy(all_tasks)
            assigned_this_day = []
            
            # SMART UPDATE LOGIC
            if smart_update and saved_shifts_for_month and col in saved_shifts_for_month:
                saved_day = saved_shifts_for_month[col]
                for op in available_ops:
                    if op in saved_day:
                        prev = saved_day[op]
                        found_tasks = [t for t in tasks_to_assign if t in prev]
                        if found_tasks:
                            day_ass[op] = prev
                            assigned_this_day.append(op)
                            for ft in found_tasks: 
                                if ft in tasks_to_assign: tasks_to_assign.remove(ft)
                            if d_obj.weekday() == 0:
                                if op not in weekly_assignments: weekly_assignments[op] = []
                                weekly_assignments[op].extend(found_tasks)

            # STANDARD ASSIGNMENT
            for op in available_ops:
                if op not in assigned_this_day and op in weekly_assignments:
                    my_weekly = weekly_assignments[op]
                    valid_weekly = [t for t in my_weekly if t in tasks_to_assign]
                    confirmed = valid_weekly[:max_tasks]
                    for t in confirmed: tasks_to_assign.remove(t)
                    
                    if confirmed:
                        t_str = " + ".join(confirmed)
                        prefix = f"({day_ass[op]}) " if "P." in day_ass[op] else ""
                        if day_ass[op] and "P." not in day_ass[op]: day_ass[op] += " + " + t_str
                        else: day_ass[op] = prefix + t_str
                        assigned_this_day.append(op)

            # New Tasks
            def load(op):
                if day_ass[op] in ["FERIE", "P.MATT", "P.POM"]: return 99
                if op in assigned_this_day: return day_ass[op].count('+') + 1
                if not day_ass[op]: return 0
                return day_ass[op].count('+') + 1

            for t in tasks_to_assign:
                cands = [op for op in available_ops if t in CONFIG["SKILLS"].get(op, [])]
                if not cands:
                    if col not in missing: missing[col] = []
                    missing[col].append(t)
                    continue
                
                random.shuffle(cands)
                cands.sort(key=lambda x: (
                    load(x), 
                    1 if t in last_week_assignments.get(x, []) else 0,
                    cnt[x].get(t, 0)
                ))
                
                chosen = None
                for op in cands:
                    if load(op) < max_tasks: chosen = op; break
                if not chosen: 
                    for op in cands:
                        if day_ass[op] not in ["FERIE"]: chosen = op; break
                
                if chosen:
                    prefix = f"({day_ass[chosen]}) " if "P." in day_ass[chosen] else ""
                    if day_ass[chosen] and "P." not in day_ass[chosen]: day_ass[chosen] += f" + {t}"
                    else: day_ass[chosen] = prefix + t
                    cnt[chosen][t] = cnt[chosen].get(t, 0) + 1
                    assigned_this_day.append(chosen)
                    if d_obj.weekday() == 0:
                        if chosen not in weekly_assignments: weekly_assignments[chosen] = []
                        weekly_assignments[chosen].append(t)

            # PAUSE
            base_slots = copy.deepcopy(CONFIG["PAUSE"]["SLOTS"])
            if base_slots:
                rotate_idx = current_week_idx % len(base_slots)
                rotated_slots = base_slots[rotate_idx:] + base_slots[:rotate_idx]
            else:
                rotated_slots = []
            s_i = 0
            for op in available_ops:
                has_pause = "☕" in day_ass[op]
                if not has_pause and "P." not in day_ass[op] and "FERIE" not in day_ass[op]:
                    p_time = None
                    if op in CONFIG["PAUSE"]["FISSI"]: p_time = CONFIG["PAUSE"]["FISSI"][op]
                    elif op in weekly_lunches: p_time = weekly_lunches[op]
                    elif rotated_slots:
                        p_time = rotated_slots[s_i % len(rotated_slots)]; s_i += 1
                        if d_obj.weekday() == 0: weekly_lunches[op] = p_time
                    if p_time: day_ass[op] += f"\n☕ {p_time}"
            
            out[col] = day_ass
            
        # SALVATAGGIO
        st.session_state.shifts[LEAVES_KEY] = out
        res, new_sha = save_file_to_github("shifts.json", st.session_state.shifts, st.session_state.shifts_sha)
        if res:
             st.session_state.shifts_sha = new_sha
             st.toast("Turni salvati!", icon="💾")

        # VISUALIZZAZIONE
        res_df = pd.DataFrame(out)
        cols_to_show = [c for i, c in enumerate(cols) if days[i].weekday() < 5]
        final_view = res_df[cols_to_show]

        new_idx = []
        for op in final_view.index:
            t = CONFIG["TELEFONI"].get(op)
            new_idx.append(f"{op} (☎️ {t})" if t else op)
        final_view.index = new_idx
        
        st.success("Turni Generati!")
        if missing: st.warning("Non assegnati:"); st.json(missing)
        
        display_weeks(final_view, get_style_map(), mese_s, anno_s)

    # 3. VISUALIZZAZIONE TURNI SALVATI
    if saved_shifts_for_month and "final_view" not in locals():
        st.divider()
        st.subheader(f"📂 Turni Salvati: {mese_s} {anno_s}")
        
        saved_df = pd.DataFrame(saved_shifts_for_month)
        cols_viz = [c for c in saved_df.columns if "Sab" not in c and "Dom" not in c] 
        saved_view = saved_df[cols_viz]
        
        new_idx_viz = []
        for op in saved_view.index:
            t = CONFIG["TELEFONI"].get(op)
            new_idx_viz.append(f"{op} (☎️ {t})" if t else op)
        saved_view.index = new_idx_viz

        display_weeks(saved_view, get_style_map(), mese_s, anno_s)

