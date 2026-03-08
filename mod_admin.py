"""
GESTNOW v3 — mod_admin.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Painel do administrador.

Tabs: Dashboard · Aprovações · Pessoal (avaliações, preço/hora)
      Obras · Folhas de Ponto · Comunicados · Ferramentaria
      Compras · Geolocalização · Faturação · Relatórios · Segurança

Para adicionar uma tab nova → adicionar a string em st.tabs() e criar o bloco.
Para alterar lógica de BD → editar core.py (load_all / save_db).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from core import *


def render_admin(users, obras_db, frentes_db, registos_db, faturas_db,
                 docs_db, incs_db, sw_db, obs_db, equip_db,
                 diags_db, diags_u_db, folhas_db,
                 comuns_db, comuns_u_db, req_fer_db, req_mat_db, req_epi_db, avals_db):
    """Renderiza o painel completo do administrador."""
    # 11. ADMIN
    # ============================================================
    tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8,tab9,tab10,tab11,tab12=st.tabs([
        "📊 Dashboard","✅ Aprovações","👥 Pessoal","🏗️ Obras",
        "📋 Folhas de Ponto","📢 Comunicados","🔧 Ferramentaria","🛒 Compras",
        "📍 Geolocalização","💰 Faturação","📈 Relatórios","🛡️ Segurança"
    ])

    with tab1:
        st.markdown('<div class="section-title">📊 Dashboard</div>',unsafe_allow_html=True)
        c_,_=st.columns([1,3])
        with c_: per=st.selectbox("",["Hoje","7 dias","30 dias","90 dias","12 meses"],label_visibility="collapsed")
        d_ini=datetime.now()-timedelta(days={"Hoje":1,"7 dias":7,"30 dias":30,"90 dias":90,"12 meses":365}[per])
        dados=registos_db[registos_db['Data']>=pd.Timestamp(d_ini)].copy() if not registos_db.empty else pd.DataFrame()
        c1,c2,c3,c4=st.columns(4)
        with c1: render_metric("⏱️",fh(dados['Horas_Total'].sum()) if not dados.empty else "0h","Horas Totais")
        with c2: render_metric("👷",dados['Técnico'].nunique() if not dados.empty else 0,"Técnicos")
        with c3: render_metric("🏗️",dados['Obra'].nunique() if not dados.empty else 0,"Obras")
        with c4: render_metric("⏳",len(registos_db[registos_db['Status']=="0"]) if not registos_db.empty else 0,"Pendentes")
        if not dados.empty:
            st.markdown("<br>",unsafe_allow_html=True)
            g1,g2=st.columns(2)
            with g1:
                hd=dados.groupby('Data')['Horas_Total'].sum().reset_index()
                fig=px.area(hd,x='Data',y='Horas_Total',title='Horas por Dia',color_discrete_sequence=['#3E92CC'],template='plotly_white')
                fig.update_traces(line_color='#0A2463',fillcolor='rgba(62,146,204,0.1)')
                fig.update_layout(showlegend=False,title_font=dict(color='#0A2463',size=14),margin=dict(t=40,b=20,l=10,r=10))
                st.plotly_chart(fig,use_container_width=True)
            with g2:
                ho=dados.groupby('Obra')['Horas_Total'].sum().reset_index().sort_values('Horas_Total',ascending=False).head(8)
                fig2=px.bar(ho,x='Horas_Total',y='Obra',orientation='h',title='Top Obras',color_discrete_sequence=['#0A2463'],template='plotly_white')
                fig2.update_layout(showlegend=False,title_font=dict(color='#0A2463',size=14),yaxis=dict(autorange='reversed'),margin=dict(t=40,b=20,l=10,r=10))
                st.plotly_chart(fig2,use_container_width=True)
            if 'TipoFrente' in dados.columns and dados['TipoFrente'].notna().any() and (dados['TipoFrente']!='').any():
                hf=dados[dados['TipoFrente']!=''].groupby('TipoFrente')['Horas_Total'].sum().reset_index()
                if not hf.empty:
                    fig3=px.pie(hf,values='Horas_Total',names='TipoFrente',title='Horas por Tipo de Frente',template='plotly_white',hole=0.4)
                    st.plotly_chart(fig3,use_container_width=True)
            res=dados.groupby('Técnico').agg(Horas=('Horas_Total','sum'),Registos=('Técnico','count'),Obras=('Obra','nunique')).reset_index().sort_values('Horas',ascending=False)
            res['Horas']=res['Horas'].apply(fh)
            st.markdown("#### 👷 Resumo por Técnico"); st.dataframe(res,use_container_width=True,hide_index=True)
        else: st.info("📭 Sem dados no período.")

    with tab2:
        st.markdown('<div class="section-title">✅ Aprovações</div>',unsafe_allow_html=True)
        pend=registos_db[registos_db['Status']=="0"].copy() if not registos_db.empty else pd.DataFrame()
        if pend.empty: st.success("🎉 Nenhum registo pendente!")
        else:
            st.info(f"📋 {len(pend)} pendente(s).")
            f1,f2=st.columns(2)
            with f1: ft=st.selectbox("Técnico",["Todos"]+pend['Técnico'].unique().tolist())
            with f2: fo=st.selectbox("Obra",["Todas"]+pend['Obra'].unique().tolist())
            if ft!="Todos": pend=pend[pend['Técnico']==ft]
            if fo!="Todas": pend=pend[pend['Obra']==fo]
            ca,cb,_=st.columns([1,1,2])
            with ca:
                if st.button("✅ Aprovar Todos"):
                    for i in pend.index: registos_db.at[i,'Status']="1"
                    save_db(registos_db,"registos.csv"); inv(); st.rerun()
            with cb:
                if st.button("🔵 Fechar Todos"):
                    for i in pend.index: registos_db.at[i,'Status']="2"
                    save_db(registos_db,"registos.csv"); inv(); st.rerun()
            st.divider()
            for idx,row in pend.iterrows():
                ds=row['Data'].strftime('%d/%m/%Y') if pd.notna(row['Data']) and hasattr(row['Data'],'strftime') else "—"
                cod=obras_db[obras_db['Obra']==row['Obra']]['Codigo'].values[0] if not obras_db.empty and row['Obra'] in obras_db['Obra'].values else ""
                c1,c2,c3,c4=st.columns([3,1,1,1])
                with c1: st.markdown(f"**{row['Técnico']}** | {row['Obra']} <span class='obra-codigo'>{cod}</span> | {ds} | `{row['Turnos']}` | **{fh(float(row['Horas_Total']))}**",unsafe_allow_html=True)
                with c2:
                    if st.button("✅",key=f"ap_{idx}"): registos_db.at[idx,'Status']="1"; save_db(registos_db,"registos.csv"); inv(); st.rerun()
                with c3:
                    if st.button("🔵",key=f"fe_{idx}"): registos_db.at[idx,'Status']="2"; save_db(registos_db,"registos.csv"); inv(); st.rerun()
                with c4:
                    if st.button("❌",key=f"rej_{idx}"):
                        registos_db=registos_db.drop(idx).reset_index(drop=True); save_db(registos_db,"registos.csv"); inv(); st.rerun()
                if row.get('Relatorio'):
                    with st.expander("📝 Relatório"): st.write(row['Relatorio'])
                st.divider()

    with tab3:
        st.markdown('<div class="section-title">👥 Pessoal</div>',unsafe_allow_html=True)
        with st.expander("➕ Novo Utilizador"):
            with st.form("nu"):
                c1,c2=st.columns(2)
                with c1:
                    nu=st.text_input("Nome *"); np_=st.text_input("Password *",type="password"); np2=st.text_input("Confirmar *",type="password")
                    nt=st.selectbox("Tipo",["Técnico","Chefe de Equipa","Admin"]); cg=st.selectbox("Cargo",CARGOS)
                with c2:
                    em=st.text_input("Email"); tel=st.text_input("Telefone"); nif=st.text_input("NIF"); niss=st.text_input("NISS")
                    cc=st.text_input("CC / Passaporte"); nasc=st.date_input("Data Nasc.",value=date(1990,1,1))
                    nac=st.text_input("Nacionalidade","Portugal"); mor=st.text_area("Morada",height=68)
                if st.form_submit_button("Registar",use_container_width=True):
                    erros=[]
                    if not nu.strip(): erros.append("Nome obrigatório.")
                    if not np_: erros.append("Password obrigatória.")
                    elif np_!=np2: erros.append("Passwords não coincidem.")
                    else:
                        ok,msg=val_pw(np_)
                        if not ok: erros.append(msg)
                    if nu.strip() in users['Nome'].values: erros.append(f"'{nu}' já existe.")
                    if erros:
                        for e in erros: st.error(e)
                    else:
                        novo=pd.DataFrame([{"Nome":nu.strip(),"Password":hp(np_),"Tipo":nt,"Email":em,"Telefone":tel,"Cargo":cg,"NIF":nif,"NISS":niss,"CC":cc,"DataNasc":str(nasc),"Nacionalidade":nac,"Morada":mor,"Foto":""}])
                        if save_db(pd.concat([users,novo],ignore_index=True),"usuarios.csv"): inv(); st.success(f"✅ {nu} registado!"); st.rerun()
        if not users.empty:
            st.dataframe(users[[c for c in ['Nome','Cargo','Tipo','Email','Telefone'] if c in users.columns]],use_container_width=True,hide_index=True)
            with st.expander("🔑 Alterar Password"):
                with st.form("apw"):
                    us_=st.selectbox("Utilizador",users['Nome'].tolist()); p1=st.text_input("Nova",type="password"); p2=st.text_input("Confirmar",type="password")
                    if st.form_submit_button("Alterar"):
                        if p1!=p2: st.error("Não coincidem.")
                        else:
                            ok,msg=val_pw(p1)
                            if not ok: st.error(msg)
                            else:
                                i=users[users['Nome']==us_].index[0]; users.at[i,'Password']=hp(p1)
                                save_db(users,"usuarios.csv"); inv(); st.success("✅ Alterada!")
        else: st.info("Sem utilizadores.")

        # ── Preço/hora ──────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 💶 Preço/Hora dos Colaboradores")
        st.caption("Define o valor hora de cada colaborador. O colaborador verá a proposta e pode aceitar ou recusar.")
        colab_list=users[users['Tipo']!='Admin'] if not users.empty else pd.DataFrame()
        if not colab_list.empty:
            for _,u_ph in colab_list.iterrows():
                nome_ph=u_ph['Nome']; atual_ph=u_ph.get('PrecoHora',''); status_ph=u_ph.get('PrecoHoraStatus',''); data_ph=u_ph.get('PrecoHoraData','')
                st_ic_ph={"Aceite":"✅","Recusado":"❌","Pendente":"⏳"}.get(status_ph,"⚪")
                ca_ph,cb_ph,cc_ph=st.columns([3,1.5,1])
                with ca_ph:
                    st.markdown(f"<div style='padding:.4rem 0;'><b>{nome_ph}</b> <small style='color:#7A8BA6;'>({u_ph.get('Cargo','—')})</small><br>"
                        f"<span style='font-size:.85rem;'>💶 <b>{atual_ph or '—'} €/h</b>"
                        f"{'&nbsp;&nbsp;'+st_ic_ph+' '+status_ph+' ('+data_ph+')' if status_ph else ''}</span></div>",unsafe_allow_html=True)
                with cb_ph:
                    novo_ph=st.number_input("€/h",min_value=0.0,value=float(atual_ph) if atual_ph else 15.0,step=0.5,format="%.2f",key=f"ph_{nome_ph}",label_visibility="collapsed")
                with cc_ph:
                    st.markdown("<br>",unsafe_allow_html=True)
                    if st.button("📤",key=f"ph_btn_{nome_ph}",use_container_width=True,help="Definir preço/hora"):
                        i_ph=users[users['Nome']==nome_ph].index[0]
                        users.at[i_ph,'PrecoHora']=str(novo_ph); users.at[i_ph,'PrecoHoraStatus']='Pendente'
                        users.at[i_ph,'PrecoHoraData']=datetime.now().strftime('%d/%m/%Y')
                        save_db(users,"usuarios.csv"); inv(); st.success(f"✅ {novo_ph:.2f}€/h enviado para {nome_ph}!"); st.rerun()

        # ── Avaliações / Classificação ──────────────────────
        st.markdown("---")
        st.markdown("#### ⭐ Classificação dos Colaboradores (0-20)")
        st.caption("Classifica os colaboradores. A pontuação combina avaliação manual com métricas automáticas (assiduidade, documentos, incidentes).")

        def _calc_auto(nome_a):
            score=0.0; hoje_a=date.today(); d30=pd.Timestamp(hoje_a-timedelta(days=30))
            if not registos_db.empty:
                meus_r=registos_db[(registos_db['Técnico']==nome_a)&(registos_db['Data']>=d30)]
                score+=min(8.0,(meus_r['Data'].dt.date.nunique()/22.0)*8.0)
            if not docs_db.empty:
                meus_d=docs_db[docs_db['Utilizador']==nome_a]
                if not meus_d.empty:
                    v_=sum(1 for _,dd in meus_d.iterrows() if pd.to_datetime(dd['Validade'],errors='coerce').date()>=hoje_a if dd['Validade'])
                    score+=(v_/max(len(meus_d),1))*6.0
            if not incs_db.empty:
                n_i=len(incs_db[incs_db['Utilizador']==nome_a]); score+=max(0.0,6.0-min(6.0,n_i*1.5))
            else: score+=6.0
            return round(min(20.0,score),1)

        def _estrelas(p):
            f_=int(p/20*5); e_=5-f_
            return "⭐"*f_+"☆"*e_+f" <small>({p:.1f}/20)</small>"

        at1_,at2_,at3_=st.tabs(["🏆 Ranking","✏️ Avaliar","📜 Histórico"])
        with at1_:
            rank_=[]; 
            colab_rank=users[users['Tipo']!='Admin'] if not users.empty else pd.DataFrame()
            for _,u_r in colab_rank.iterrows():
                nome_r=u_r['Nome']
                man_r=0.0
                if not avals_db.empty:
                    ul_r=avals_db[avals_db['Utilizador']==nome_r].sort_values('Data',ascending=False)
                    if not ul_r.empty:
                        try: man_r=float(ul_r.iloc[0]['PontuacaoManual'])
                        except: pass
                auto_r=_calc_auto(nome_r); comb_r=round(man_r*0.5+auto_r*0.5,1)
                rank_.append({'n':nome_r,'c':u_r.get('Cargo','—'),'m':man_r,'a':auto_r,'t':comb_r})
            rank_.sort(key=lambda x:x['t'],reverse=True)
            for pos_,rr_ in enumerate(rank_,1):
                med_=["🥇","🥈","🥉"][pos_-1] if pos_<=3 else f"#{pos_}"
                st.markdown(f"<div class='turno-card'><div class='turno-header'>"
                    f"<span><b>{med_} {rr_['n']}</b> <small style='color:#7A8BA6;'>{rr_['c']}</small></span>"
                    f"<span>{_estrelas(rr_['t'])}</span></div>"
                    f"<div style='display:flex;gap:2rem;margin-top:5px;'>"
                    f"<span style='font-size:.82rem;color:#7A8BA6;'>✏️ Manual: <b>{rr_['m']:.1f}</b></span>"
                    f"<span style='font-size:.82rem;color:#7A8BA6;'>🤖 Auto: <b>{rr_['a']:.1f}</b></span>"
                    f"<span style='font-size:.82rem;font-weight:700;color:#0A2463;'>⭐ Combinada: <b>{rr_['t']:.1f}/20</b></span>"
                    f"</div></div>",unsafe_allow_html=True)
        with at2_:
            with st.form("f_aval"):
                ca_av,cb_av=st.columns(2)
                with ca_av:
                    colab_av=st.selectbox("Colaborador",users[users['Tipo']!='Admin']['Nome'].tolist() if not users.empty else [],key="sel_av")
                    nota_av=st.slider("Pontuação (0-20)",0.0,20.0,10.0,0.5,key="sl_av")
                with cb_av:
                    auto_prev=_calc_auto(colab_av) if colab_av else 0
                    comb_prev=round(nota_av*0.5+auto_prev*0.5,1)
                    st.markdown(f"""<div style='background:#F8FAFF;border:1px solid #E5EDFF;border-radius:12px;padding:1rem;'>
                    <div style='color:#7A8BA6;font-size:.8rem;'>Pré-visualização</div>
                    <div>🤖 Auto: <b>{auto_prev:.1f}/20</b></div>
                    <div>✏️ Manual: <b>{nota_av:.1f}/20</b></div>
                    <div style='margin-top:6px;border-top:1px solid #E5EDFF;padding-top:6px;font-weight:700;'>
                    ⭐ Combinada: <b>{comb_prev:.1f}/20</b> {_estrelas(comb_prev)}</div></div>""",unsafe_allow_html=True)
                    nota_adm_av=st.text_area("Nota",height=80,key="nota_adm_av")
                if st.form_submit_button("💾 Guardar Avaliação",use_container_width=True):
                    nova_av=pd.DataFrame([{"Utilizador":colab_av,"Data":datetime.now().strftime('%d/%m/%Y'),
                        "PontuacaoManual":nota_av,"NotaAdmin":nota_adm_av,"Avaliador":st.session_state.user}])
                    save_db(pd.concat([avals_db,nova_av],ignore_index=True),"avaliacoes.csv"); inv()
                    st.success(f"✅ {colab_av} avaliado com {comb_prev:.1f}/20 ⭐"); st.rerun()
        with at3_:
            if not avals_db.empty:
                colab_h=st.selectbox("Colaborador",["Todos"]+users[users['Tipo']!='Admin']['Nome'].tolist(),key="hist_av")
                df_h_=avals_db.copy() if colab_h=="Todos" else avals_db[avals_db['Utilizador']==colab_h]
                for _,rh_ in df_h_.sort_values('Data',ascending=False).iterrows():
                    try: pm_h=float(rh_['PontuacaoManual'])
                    except: pm_h=0.0
                    st.markdown(f"<div class='turno-card'><div class='turno-header'>"
                        f"<span><b>{rh_.get('Utilizador','—')}</b></span>"
                        f"<span>{_estrelas(pm_h)}</span></div>"
                        f"<div style='color:#7A8BA6;font-size:.82rem;'>📅 {rh_.get('Data','—')} | 👤 {rh_.get('Avaliador','—')}"
                        f"{'| 📝 '+rh_.get('NotaAdmin','') if rh_.get('NotaAdmin') else ''}</div></div>",unsafe_allow_html=True)
            else: st.info("Sem avaliações registadas.")

    with tab4:
        st.markdown('<div class="section-title">🏗️ Obras</div>',unsafe_allow_html=True)
        with st.expander("➕ Nova Obra"):
            with st.form("no_"):
                c_sug=gen_cod(obras_db)
                c1,c2=st.columns(2)
                with c1:
                    no_=st.text_input("Nome *"); cli_=st.text_input("Cliente *"); loc_=st.text_input("Local")
                    cod_=st.text_input("Código",value=c_sug)
                    # Configuração de assinatura nas folhas de ponto
                    assin_obrig_cfg = st.selectbox(
                        "📋 Assinatura cliente nas folhas de ponto",
                        ["Opcional","Obrigatória"],
                        help="Define se a assinatura do representante do cliente é obrigatória para gerar a folha."
                    )
                    logo_up = st.file_uploader("🖼️ Logo do cliente (para o PDF)",
                        type=["png","jpg","jpeg"], key="obra_logo_up",
                        help="Aparece no cabeçalho da folha de ponto desta obra.")
                with c2:
                    ati_=st.selectbox("Estado",["Ativa","Inativa"])
                    di_=st.date_input("Data Início",value=date.today())
                    df_=st.date_input("Data Prevista Fim",value=date.today()+timedelta(days=180))
                    lat_=st.number_input("Latitude",value=38.7223,format="%.6f")
                    lon_=st.number_input("Longitude",value=-9.1393,format="%.6f")
                    raio_=st.number_input("Raio (m)",value=100,min_value=10)
                if st.form_submit_button("Criar Obra",use_container_width=True):
                    if not no_.strip() or not cli_.strip():
                        st.error("Nome e Cliente obrigatórios.")
                    elif no_.strip() in obras_db['Obra'].values:
                        st.error(f"'{no_}' já existe.")
                    else:
                        import base64 as _b64o
                        logo_b64_obra = ""
                        if logo_up:
                            logo_b64_obra = _b64o.b64encode(logo_up.read()).decode()
                        nova=pd.DataFrame([{
                            "Obra":no_.strip(),"Codigo":cod_,"Cliente":cli_.strip(),
                            "Local":loc_,"Ativa":ati_,"Latitude":str(lat_),
                            "Longitude":str(lon_),"Raio_Validacao":str(raio_),
                            "DataInicio":str(di_),"DataFim":str(df_),
                            "AssinaturaObrigatoria":"Sim" if assin_obrig_cfg=="Obrigatória" else "Não",
                            "Logo_b64": logo_b64_obra
                        }])
                        if save_db(pd.concat([obras_db,nova],ignore_index=True),"obras_lista.csv"):
                            inv(); st.success(f"✅ {no_} ({cod_}) criada!"); st.rerun()
        if not obras_db.empty:
            fil=st.radio("",["Todas","Ativas","Inativas"],horizontal=True,label_visibility="collapsed")
            ds_=obras_db.copy()
            if fil=="Ativas": ds_=ds_[ds_['Ativa']=='Ativa']
            elif fil=="Inativas": ds_=ds_[ds_['Ativa']=='Inativa']
            if 'DataFim' in ds_.columns:
                hj=date.today()
                ven=ds_[ds_.apply(lambda r: r['Ativa']=='Ativa' and bool(r['DataFim']) and pd.to_datetime(r['DataFim'],errors='coerce').date()<hj if r['DataFim'] else False,axis=1)]
                if not ven.empty: st.warning(f"⚠️ Obras com prazo ultrapassado: {', '.join(ven['Obra'].tolist())}")
            st.dataframe(ds_[[c for c in ['Codigo','Obra','Cliente','Local','Ativa','DataInicio','DataFim'] if c in ds_.columns]],use_container_width=True,hide_index=True)
            with st.expander("⚙️ Frentes"):
                ob_f=st.selectbox("Obra",obras_db['Obra'].tolist(),key="sf")
                fr_ob=frentes_db[frentes_db['Obra']==ob_f] if not frentes_db.empty else pd.DataFrame()
                if not fr_ob.empty: st.dataframe(fr_ob[['Frente','Tipo','Responsavel']],use_container_width=True,hide_index=True)
                with st.form("nf_"):
                    c1f,c2f=st.columns(2)
                    with c1f: nf_=st.text_input("Frente")
                    with c2f: tf_=st.selectbox("Tipo",TIPOS_FRENTE); rf_=st.text_input("Responsável")
                    if st.form_submit_button("Adicionar"):
                        if nf_.strip():
                            nova_f=pd.DataFrame([{"Obra":ob_f,"Frente":nf_.strip(),"Tipo":tf_,"Responsavel":rf_}])
                            save_db(pd.concat([frentes_db,nova_f],ignore_index=True),"frentes_lista.csv"); inv(); st.success("✅"); st.rerun()
        else: st.info("Sem obras.")

    with tab5:
        st.markdown('<div class="section-title">📋 Folhas de Ponto</div>', unsafe_allow_html=True)
        st.caption("Folhas de ponto geradas pelos chefes de equipa, organizadas por obra. Use para confrontar com os registos antes de faturar.")

        # Filtros
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_obra_adm = st.selectbox("Filtrar Obra", ["Todas"] + obras_db['Obra'].tolist() if not obras_db.empty else ["Todas"], key="f_fp_obra")
        with fc2:
            f_assin_adm = st.selectbox("Assinatura cliente", ["Todas","✅ Assinadas","⏳ Por assinar"], key="f_fp_assin")
        with fc3:
            f_chefe_adm = st.selectbox("Chefe de Equipa", ["Todos"] + (users[users['Tipo']=='Chefe de Equipa']['Nome'].tolist() if not users.empty else []), key="f_fp_chefe")

        folhas_show = folhas_db.copy() if not folhas_db.empty else pd.DataFrame()
        if not folhas_show.empty:
            if f_obra_adm != "Todas":
                folhas_show = folhas_show[folhas_show['Obra'] == f_obra_adm]
            if f_assin_adm == "✅ Assinadas":
                folhas_show = folhas_show[folhas_show['AssinadoCliente'] == "Sim"]
            elif f_assin_adm == "⏳ Por assinar":
                folhas_show = folhas_show[folhas_show['AssinadoCliente'] != "Sim"]
            if f_chefe_adm != "Todos":
                folhas_show = folhas_show[folhas_show['ChefEquipa'] == f_chefe_adm]

            # Métricas rápidas
            m1,m2,m3,m4 = st.columns(4)
            with m1: render_metric("📋", len(folhas_show), "Folhas")
            with m2: render_metric("✅", len(folhas_show[folhas_show['AssinadoCliente']=="Sim"]), "Assinadas")
            with m3: render_metric("⏳", len(folhas_show[folhas_show['AssinadoCliente']!="Sim"]), "Por assinar")
            with m4:
                try: render_metric("⏱️", fh(float(folhas_show['TotalHoras'].astype(float).sum())), "Total Horas")
                except: render_metric("⏱️","—","Total Horas")
            st.markdown("<br>", unsafe_allow_html=True)

            # Agrupar por obra
            obras_nas_folhas = folhas_show['Obra'].unique().tolist()
            for obra_g in obras_nas_folhas:
                folhas_obra = folhas_show[folhas_show['Obra']==obra_g]
                cod_obra_g = ""
                if not obras_db.empty and obra_g in obras_db['Obra'].values:
                    cod_obra_g = obras_db[obras_db['Obra']==obra_g].iloc[0].get('Codigo','')
                with st.expander(f"🏗️ {obra_g}  {f'({cod_obra_g})' if cod_obra_g else ''}  — {len(folhas_obra)} folha(s)", expanded=True):
                    for _,f_ in folhas_obra.sort_values('DataCriacao',ascending=False).iterrows():
                        assin_ic = "✅" if f_.get('AssinadoCliente','')=="Sim" else "⏳"
                        assin_c = "status-aprovado" if f_.get('AssinadoCliente','')=="Sim" else "status-pendente"
                        col_fa, col_fb = st.columns([5,1])
                        with col_fa:
                            tecnicos_lista = f_.get('Tecnicos','').replace('|',', ')
                            st.markdown(
                                f"<div class='turno-card'>"
                                f"<div class='turno-header'>"
                                f"<span>{assin_ic} Período: <strong>{f_.get('Periodo','—')}</strong></span>"
                                f"<span class='turno-status {assin_c}'>{'Assinado pelo cliente' if f_.get('AssinadoCliente')=='Sim' else 'Sem assinatura cliente'}</span>"
                                f"</div>"
                                f"<div style='color:#374151;font-size:.9rem;margin-top:4px;'>"
                                f"👷 Chefe: {f_.get('ChefEquipa','—')} &nbsp;|&nbsp; "
                                f"⏱️ {f_.get('TotalHoras',0)}h &nbsp;|&nbsp; "
                                f"🆔 {f_.get('ID','—')}"
                                f"</div>"
                                f"<div style='color:#7A8BA6;font-size:.8rem;margin-top:3px;'>"
                                f"👥 Técnicos: {tecnicos_lista} &nbsp;|&nbsp; "
                                f"🤝 Cliente: {f_.get('NomeCliente','—')} &nbsp;|&nbsp; "
                                f"📅 {f_.get('DataCriacao','—')}"
                                f"</div>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        with col_fb:
                            if f_.get('PDF_b64',''):
                                try:
                                    import base64 as b64_adm
                                    pdf_adm = b64_adm.b64decode(f_['PDF_b64'])
                                    st.download_button(
                                        "⬇️ PDF",
                                        data=pdf_adm,
                                        file_name=f"folha_{f_.get('ID','x')}_{obra_g.replace(' ','_')}.pdf",
                                        mime="application/pdf",
                                        key=f"adm_dl_{f_.get('ID','x')}",
                                        use_container_width=True
                                    )
                                except: st.caption("PDF indisponível")

                    # Resumo comparativo com registos da app
                    regs_obra_adm = registos_db[registos_db['Obra']==obra_g] if not registos_db.empty else pd.DataFrame()
                    if not regs_obra_adm.empty:
                        h_app = regs_obra_adm['Horas_Total'].sum()
                        h_folhas = float(folhas_obra['TotalHoras'].astype(float).sum())
                        diff = abs(h_app - h_folhas)
                        cor_diff = "#059669" if diff < 0.5 else ("#D97706" if diff < 5 else "#DC2626")
                        st.markdown(
                            f"<div style='background:#F0FDF4;border:1px solid #D1FAE5;border-radius:10px;"
                            f"padding:.75rem 1rem;margin-top:.5rem;'>"
                            f"<span style='font-weight:600;color:#065F46;'>📊 Conformidade:</span> "
                            f"App registou <strong>{fh(h_app)}</strong> &nbsp;|&nbsp; "
                            f"Folhas mostram <strong>{fh(h_folhas)}</strong> &nbsp;|&nbsp; "
                            f"<span style='color:{cor_diff};font-weight:700;'>Diferença: {fh(diff)}</span>"
                            f"{'&nbsp; ✅ Em conformidade' if diff < 0.5 else '&nbsp; ⚠️ Verificar divergência'}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
        else:
            st.info("Ainda não foram geradas folhas de ponto. Os chefes de equipa geram as folhas na sua app.")
            st.caption("💡 Assim que um chefe de equipa gerar uma folha, ela aparecerá aqui organizada por obra.")

    # ══════════════════════════════════════════════════
    # TAB 6 — COMUNICADOS
    # ══════════════════════════════════════════════════
    with tab6:
        # ── Painel comunicados inline (sem módulo externo) ──
        st.markdown('<div class="section-title">📢 Comunicados</div>', unsafe_allow_html=True)
        st.caption("Envie comunicados a todos, a um grupo, a uma obra ou individualmente.")

        c1m,c2m,c3m,c4m=st.columns(4)
        total_com=len(comuns_db) if not comuns_db.empty else 0
        urg_com=len(comuns_db[comuns_db['Urgente']=="Sim"]) if not comuns_db.empty else 0
        lidos_com=comuns_u_db['ComunicadoID'].nunique() if not comuns_u_db.empty else 0
        with c1m: render_metric("📢",total_com,"Enviados")
        with c2m: render_metric("🚨",urg_com,"Urgentes")
        with c3m: render_metric("✅",lidos_com,"C/ leituras")
        with c4m: render_metric("👥",users[users['Tipo']!='Admin']['Nome'].nunique() if not users.empty else 0,"Colaboradores")
        st.markdown("<br>",unsafe_allow_html=True)

        with st.expander("➕ Novo Comunicado"):
            with st.form("f_com_novo"):
                cc1,cc2=st.columns(2)
                with cc1:
                    com_titulo=st.text_input("Título *",placeholder="Ex: Reunião obrigatória amanhã")
                    com_tipo=st.selectbox("Destinatários",["Todos os colaboradores","Apenas Chefes de Equipa","Colaborador individual","Por obra"])
                    com_urgente=st.checkbox("🚨 Urgente")
                    com_validade=st.date_input("Válido até",value=date.today()+timedelta(days=30))
                with cc2:
                    com_conteudo=st.text_area("Conteúdo *",height=160)
                    com_destino=""
                    if com_tipo=="Colaborador individual":
                        nomes_com=users[users['Tipo']!='Admin']['Nome'].tolist() if not users.empty else []
                        com_destino=st.selectbox("Colaborador",nomes_com,key="com_ind_sel")
                    elif com_tipo=="Por obra":
                        obras_com=obras_db['Obra'].tolist() if not obras_db.empty else []
                        com_destino=st.selectbox("Obra",obras_com,key="com_obra_sel")
                    elif com_tipo=="Apenas Chefes de Equipa":
                        com_destino="__CHEFES__"
                    else:
                        com_destino="__TODOS__"
                if st.form_submit_button("📤 Enviar",use_container_width=True):
                    if not com_titulo.strip() or not com_conteudo.strip():
                        st.error("Título e conteúdo obrigatórios.")
                    else:
                        import uuid as _uuid_com
                        cid=_uuid_com.uuid4().hex[:10].upper()
                        novo_com=pd.DataFrame([{"ID":cid,"Titulo":com_titulo.strip(),"Conteudo":com_conteudo.strip(),
                            "Tipo":com_tipo,"Destino":com_destino,"Obra":com_destino if com_tipo=="Por obra" else "",
                            "DataCriacao":datetime.now().strftime('%d/%m/%Y %H:%M'),"Autor":st.session_state.user,
                            "Validade":str(com_validade),"Urgente":"Sim" if com_urgente else "Não"}])
                        save_db(pd.concat([comuns_db,novo_com],ignore_index=True),"comunicados.csv"); inv()
                        st.success(f"✅ Comunicado {cid} enviado!"); st.rerun()

        st.markdown("#### 📋 Comunicados Enviados")
        if not comuns_db.empty:
            for _,row_c in comuns_db.sort_values('DataCriacao',ascending=False).iterrows():
                try: exp_c=(pd.to_datetime(row_c.get('Validade','')).date()<date.today())
                except: exp_c=False
                n_lid=len(comuns_u_db[comuns_u_db['ComunicadoID']==row_c['ID']]) if not comuns_u_db.empty else 0
                urg_ic="🚨 " if row_c.get('Urgente')=="Sim" else ""
                exp_label = '<small style="color:#9CA3AF;">[expirado]</small>' if exp_c else ''
                status_cls = 'status-fechado' if exp_c else 'status-aprovado'
                st.markdown(f"<div class='turno-card'><div class='turno-header'>"
                    f"<span>{urg_ic}<b>{row_c.get('Titulo','—')}</b>"
                    f"{exp_label}</span>"
                    f"<span class='turno-status {status_cls}'>{row_c.get('Tipo','—')}</span>"
                    f"</div><div style='color:#374151;font-size:.85rem;'>{row_c.get('Conteudo','')[:180]}...</div>"
                    f"<div style='color:#7A8BA6;font-size:.78rem;'>📅 {row_c.get('DataCriacao','—')} | "
                    f"👤 {row_c.get('Autor','—')} | ✅ {n_lid} leitura(s)</div></div>",unsafe_allow_html=True)
                if n_lid>0:
                    with st.expander(f"Quem leu ({n_lid})"):
                        lidos_c=comuns_u_db[comuns_u_db['ComunicadoID']==row_c['ID']]
                        for _,lr in lidos_c.iterrows():
                            st.markdown(f"✅ **{lr.get('Utilizador','—')}** — {lr.get('DataLeitura','—')}")
        else:
            st.info("Sem comunicados. Usa o formulário acima para criar o primeiro.")

    # ══════════════════════════════════════════════════
    # TAB 7 — FERRAMENTARIA
    # ══════════════════════════════════════════════════
    with tab7:
        st.markdown('<div class="section-title">🔧 Ferramentaria</div>', unsafe_allow_html=True)
        st.caption("Requisições de ferramentas e EPIs/fardamento. Aprova, rejeita ou marca como entregue.")
        ft_fer, ft_epi = st.tabs(["🔧 Ferramentas","🦺 EPI / Fardamento"])

        def _admin_req_panel(req_db, tipo_key, csv_fn):
            if req_db.empty:
                st.info("Sem requisições."); return
            cc1,cc2,cc3,cc4=st.columns(4)
            with cc1: render_metric("📋",len(req_db),"Total")
            with cc2: render_metric("⏳",len(req_db[req_db['Status']=='Pendente']),"Pendentes")
            with cc3: render_metric("✅",len(req_db[req_db['Status']=='Aprovada']),"Aprovadas")
            with cc4: render_metric("📦",len(req_db[req_db['Status']=='Entregue']),"Entregues")
            st.markdown("<br>",unsafe_allow_html=True)
            filt_s=st.selectbox("Estado",["Pendente","Aprovada","Entregue","Rejeitada","Todos"],key=f"fs_{tipo_key}")
            df_s=req_db[req_db['Status']==filt_s].copy() if filt_s!="Todos" else req_db.copy()
            for _,row_r in df_s.sort_values('Data',ascending=False).iterrows():
                st_ic={"Pendente":"⏳","Aprovada":"✅","Rejeitada":"❌","Entregue":"📦"}.get(row_r.get('Status','Pendente'),"⏳")
                st_cls_r={"Pendente":"status-pendente","Aprovada":"status-aprovado","Rejeitada":"status-fechado","Entregue":"status-aprovado"}.get(row_r.get('Status',''),"")
                qtd_label=f"{row_r.get('Quantidade','—')}"
                if 'Unidade' in row_r and row_r.get('Unidade',''): qtd_label+=f" {row_r['Unidade']}"
                if 'Tamanho' in row_r and row_r.get('Tamanho','') not in ('','N/A'): qtd_label+=f" (tam. {row_r['Tamanho']})"
                st.markdown(f"<div class='turno-card'><div class='turno-header'>"
                    f"<span>{st_ic} <b>{row_r.get('Descricao',row_r.get('Item','—'))}</b> "
                    f"<small style='color:#7A8BA6;'>({row_r.get('Categoria',row_r.get('TipoReq','—'))})</small></span>"
                    f"<span class='turno-status {st_cls_r}'>{row_r.get('Status','—')}</span></div>"
                    f"<div style='color:#374151;font-size:.85rem;'>📋 {row_r.get('Obra','—')} | "
                    f"🔢 {qtd_label} | 📅 Necessário: {row_r.get('DataNecessaria','—')}</div>"
                    f"<div style='color:#7A8BA6;font-size:.78rem;'>👤 {row_r.get('Solicitante','—')} | "
                    f"{row_r.get('Data','—')} | 🆔 {row_r.get('ID','—')}"
                    f"{'| 📝 '+row_r.get('NotaAdmin','') if row_r.get('NotaAdmin') else ''}"
                    f"</div></div>",unsafe_allow_html=True)
                if row_r.get('Status','')=='Pendente':
                    ca_,cb_,cc_=st.columns([3,1,1])
                    nota_r=ca_.text_input("Nota",key=f"nota_{tipo_key}_{row_r['ID']}")
                    with cb_:
                        if st.button("✅ Aprovar",key=f"apr_{tipo_key}_{row_r['ID']}",use_container_width=True):
                            i_=req_db[req_db['ID']==row_r['ID']].index
                            if not i_.empty:
                                req_db.at[i_[0],'Status']='Aprovada'; req_db.at[i_[0],'NotaAdmin']=nota_r
                                req_db.at[i_[0],'DataResposta']=datetime.now().strftime('%d/%m/%Y %H:%M')
                                save_db(req_db,csv_fn); inv(); st.success("✅ Aprovada!"); st.rerun()
                    with cc_:
                        if st.button("❌ Rejeitar",key=f"rej_{tipo_key}_{row_r['ID']}",use_container_width=True):
                            i_=req_db[req_db['ID']==row_r['ID']].index
                            if not i_.empty:
                                req_db.at[i_[0],'Status']='Rejeitada'; req_db.at[i_[0],'NotaAdmin']=nota_r
                                req_db.at[i_[0],'DataResposta']=datetime.now().strftime('%d/%m/%Y %H:%M')
                                save_db(req_db,csv_fn); inv(); st.success("❌ Rejeitada!"); st.rerun()
                elif row_r.get('Status','')=='Aprovada':
                    if st.button("📦 Marcar Entregue",key=f"ent_{tipo_key}_{row_r['ID']}",use_container_width=True):
                        i_=req_db[req_db['ID']==row_r['ID']].index
                        if not i_.empty:
                            req_db.at[i_[0],'Status']='Entregue'
                            req_db.at[i_[0],'DataResposta']=datetime.now().strftime('%d/%m/%Y %H:%M')
                            save_db(req_db,csv_fn); inv(); st.success("📦 Entregue!"); st.rerun()

        with ft_fer: _admin_req_panel(req_fer_db,"fer","req_ferramentas.csv")
        with ft_epi: _admin_req_panel(req_epi_db,"epi","req_epis.csv")

    # ══════════════════════════════════════════════════
    # TAB 8 — COMPRAS
    # ══════════════════════════════════════════════════
    with tab8:
        st.markdown('<div class="section-title">🛒 Compras</div>', unsafe_allow_html=True)
        st.caption("Requisições de materiais e consumíveis por obra.")
        if req_mat_db.empty:
            st.info("Sem requisições de materiais.")
        else:
            cc1,cc2,cc3,cc4=st.columns(4)
            with cc1: render_metric("📋",len(req_mat_db),"Total")
            with cc2: render_metric("⏳",len(req_mat_db[req_mat_db['Status']=='Pendente']),"Pendentes")
            with cc3: render_metric("✅",len(req_mat_db[req_mat_db['Status']=='Aprovada']),"Aprovadas")
            with cc4:
                try:
                    urg_hoje=req_mat_db[(pd.to_datetime(req_mat_db['DataNecessaria'],errors='coerce').dt.date<=date.today())&(req_mat_db['Status']=='Pendente')]
                    render_metric("🚨",len(urg_hoje),"Urgentes hoje")
                except: render_metric("🚨",0,"Urgentes hoje")
            st.markdown("<br>",unsafe_allow_html=True)
            filt_mat=st.selectbox("Estado",["Pendente","Aprovada","Em curso","Entregue","Rejeitada","Todos"],key="filt_mat_adm")
            df_mat_s=req_mat_db[req_mat_db['Status']==filt_mat].copy() if filt_mat!="Todos" else req_mat_db.copy()
            if not df_mat_s.empty:
                for obra_m in df_mat_s['Obra'].unique():
                    req_obra_m=df_mat_s[df_mat_s['Obra']==obra_m]
                    with st.expander(f"🏗️ {obra_m} — {len(req_obra_m)} req."):
                        for _,row_m in req_obra_m.sort_values('DataNecessaria').iterrows():
                            st_ic={"Pendente":"⏳","Aprovada":"✅","Rejeitada":"❌","Entregue":"📦","Em curso":"🔄"}.get(row_m.get('Status',''),"⏳")
                            st.markdown(f"<div class='turno-card'><div class='turno-header'>"
                                f"<span>{st_ic} <b>{row_m.get('Descricao','—')}</b> <small>({row_m.get('Categoria','—')})</small></span>"
                                f"<span class='turno-status status-pendente'>{row_m.get('Status','—')}</span></div>"
                                f"<div style='color:#374151;font-size:.85rem;'>🔢 {row_m.get('Quantidade','—')} {row_m.get('Unidade','')} | "
                                f"📅 Necessário: {row_m.get('DataNecessaria','—')} | 👤 {row_m.get('Solicitante','—')}</div>"
                                f"<div style='color:#7A8BA6;font-size:.78rem;'>🆔 {row_m.get('ID','—')} | {row_m.get('Data','—')}"
                                f"{'| 📝 '+row_m.get('NotaAdmin','') if row_m.get('NotaAdmin') else ''}"
                                f"</div></div>",unsafe_allow_html=True)
                            if row_m.get('Status','')=='Pendente':
                                ca_m,cb_m,cc_m=st.columns([3,1,1])
                                nota_m=ca_m.text_input("Nota",key=f"nota_mat_{row_m['ID']}")
                                with cb_m:
                                    if st.button("✅ Aprovar",key=f"apr_mat_{row_m['ID']}",use_container_width=True):
                                        i_=req_mat_db[req_mat_db['ID']==row_m['ID']].index
                                        if not i_.empty:
                                            req_mat_db.at[i_[0],'Status']='Aprovada'; req_mat_db.at[i_[0],'NotaAdmin']=nota_m
                                            req_mat_db.at[i_[0],'DataResposta']=datetime.now().strftime('%d/%m/%Y %H:%M')
                                            save_db(req_mat_db,"req_materiais.csv"); inv(); st.success("✅"); st.rerun()
                                with cc_m:
                                    if st.button("❌ Rejeitar",key=f"rej_mat_{row_m['ID']}",use_container_width=True):
                                        i_=req_mat_db[req_mat_db['ID']==row_m['ID']].index
                                        if not i_.empty:
                                            req_mat_db.at[i_[0],'Status']='Rejeitada'; req_mat_db.at[i_[0],'NotaAdmin']=nota_m
                                            req_mat_db.at[i_[0],'DataResposta']=datetime.now().strftime('%d/%m/%Y %H:%M')
                                            save_db(req_mat_db,"req_materiais.csv"); inv(); st.success("❌"); st.rerun()
            else:
                st.info(f"Sem requisições com estado '{filt_mat}'.")

    with tab9:
        st.markdown('<div class="section-title">📍 Geolocalização</div>',unsafe_allow_html=True)
        gt1,gt2=st.tabs(["🗺️ Mapa","⚙️ Coordenadas"])
        with gt1:
            if not obras_db.empty:
                og=obras_db[obras_db['Latitude'].notna() & (obras_db['Latitude']!='')]
                if not og.empty:
                    try: lc,lnc=og['Latitude'].astype(float).mean(),og['Longitude'].astype(float).mean()
                    except: lc,lnc=38.7223,-9.1393
                    m=folium.Map(location=[lc,lnc],zoom_start=7,tiles='CartoDB positron')
                    for _,o in og.iterrows():
                        try:
                            la,lo=float(o['Latitude']),float(o['Longitude']); r_=float(o['Raio_Validacao']) if o['Raio_Validacao'] else 100
                            cor='green' if o.get('Ativa')=='Ativa' else 'gray'
                            cod_p=f"<br><small>{o.get('Codigo','')}</small>" if o.get('Codigo') else ""
                            folium.Marker([la,lo],popup=folium.Popup(f"<b>{o['Obra']}</b>{cod_p}<br>{o['Cliente']}<br>{o['Local']}",max_width=220),tooltip=o['Obra'],icon=folium.Icon(color=cor,icon='building',prefix='fa')).add_to(m)
                            folium.Circle([la,lo],radius=r_,color='#0A2463',fill=True,fill_opacity=0.1,weight=2).add_to(m)
                        except: pass
                    folium_static(m,height=430)
                else: st.info("Sem coordenadas.")
            else: st.info("Sem obras.")
        with gt2:
            if not obras_db.empty:
                oc_=st.selectbox("Obra",obras_db['Obra'].tolist(),key="go")
                od_=obras_db[obras_db['Obra']==oc_].iloc[0]
                with st.form("gf"):
                    c1,c2,c3=st.columns(3)
                    with c1: lv=float(od_['Latitude']) if od_['Latitude'] else 38.7223; lat_g=st.number_input("Latitude",value=lv,format="%.6f")
                    with c2: lnv=float(od_['Longitude']) if od_['Longitude'] else -9.1393; lon_g=st.number_input("Longitude",value=lnv,format="%.6f")
                    with c3: rv=int(float(od_['Raio_Validacao'])) if od_['Raio_Validacao'] else 100; raio_g=st.number_input("Raio (m)",value=rv,min_value=10)
                    st.caption("💡 Botão direito no Google Maps para copiar coordenadas.")
                    if st.form_submit_button("💾 Guardar",use_container_width=True):
                        i=obras_db[obras_db['Obra']==oc_].index[0]; obras_db.at[i,'Latitude']=str(lat_g); obras_db.at[i,'Longitude']=str(lon_g); obras_db.at[i,'Raio_Validacao']=str(raio_g)
                        save_db(obras_db,"obras_lista.csv"); inv(); st.success("✅"); st.rerun()
            else: st.info("Sem obras.")

    with tab10:
        st.markdown('<div class="section-title">💰 Faturação</div>',unsafe_allow_html=True)
        ft1,ft2=st.tabs(["➕ Nova Fatura","📋 Histórico"])
        with ft1:
            if not obras_db.empty and not registos_db.empty:
                c1,c2=st.columns(2)
                with c1:
                    cl_f=st.selectbox("Cliente",obras_db['Cliente'].dropna().unique())
                    ob_f=st.selectbox("Obra",obras_db[obras_db['Cliente']==cl_f]['Obra'].tolist())
                with c2:
                    ini_f=st.date_input("Início",date.today()-timedelta(days=30))
                    fim_f=st.date_input("Fim",date.today())
                if ini_f>fim_f: st.error("Início > Fim.")
                else:
                    rf=registos_db[(registos_db['Obra']==ob_f)&(registos_db['Data']>=pd.Timestamp(ini_f))&(registos_db['Data']<=pd.Timestamp(fim_f))&(registos_db['Status']=="1")].copy()
                    if not rf.empty:
                        th=rf['Horas_Total'].sum(); vt=calc_val(rf,users)
                        c1m,c2m=st.columns(2)
                        with c1m: render_metric("⏱️",fh(th),"Total Horas")
                        with c2m: render_metric("💶",f"€{vt:,.2f}","Valor Total")
                        st.dataframe(rf.assign(Data=rf['Data'].dt.strftime('%d/%m/%Y'),Horas=rf['Horas_Total'].apply(fh))[['Data','Técnico','Frente','Turnos','Horas']],use_container_width=True,hide_index=True)
                        if st.button("📄 Gerar Fatura PDF",use_container_width=True):
                            ano=datetime.now().year; ult=len(faturas_db[faturas_db['Data_Emissao'].dt.year==ano]) if not faturas_db.empty else 0
                            num=f"FT-{ano}-{ult+1:04d}"
                            d_fat={"Numero":num,"Cliente":cl_f,"Obra":ob_f,"Data_Emissao":datetime.now(),"Data_Vencimento":datetime.now()+timedelta(days=30),"Valor":vt,"Status":"Pendente","Periodo_Inicio":datetime.combine(ini_f,datetime.min.time()),"Periodo_Fim":datetime.combine(fim_f,datetime.min.time())}
                            nf_df=pd.DataFrame([{**d_fat,"Data_Emissao":d_fat["Data_Emissao"].strftime('%d/%m/%Y'),"Data_Vencimento":d_fat["Data_Vencimento"].strftime('%d/%m/%Y'),"Periodo_Inicio":ini_f.strftime('%d/%m/%Y'),"Periodo_Fim":fim_f.strftime('%d/%m/%Y')}])
                            save_db(pd.concat([faturas_db,nf_df],ignore_index=True),"faturas.csv"); inv()
                            pdf=gerar_pdf(d_fat,rf,users); st.success(f"✅ Fatura {num} gerada!")
                            st.download_button("📥 Download PDF",data=pdf,file_name=f"Fatura_{num}.pdf",mime="application/pdf",use_container_width=True)
                    else: st.warning("Sem registos aprovados.")
            else: st.warning("Sem dados.")
        with ft2:
            if not faturas_db.empty:
                tf_=faturas_db['Valor'].sum(); pf_=faturas_db[faturas_db['Status']=='Pendente']['Valor'].sum(); pg_=faturas_db[faturas_db['Status']=='Paga']['Valor'].sum()
                c1,c2,c3=st.columns(3)
                with c1: render_metric("💶",f"€{tf_:,.0f}","Total")
                with c2: render_metric("⏳",f"€{pf_:,.0f}","Por Receber")
                with c3: render_metric("✅",f"€{pg_:,.0f}","Recebido")
                st.markdown("<br>",unsafe_allow_html=True)
                for _,fat in faturas_db.sort_values('Data_Emissao',ascending=False).iterrows():
                    sc={"Pendente":"status-pendente","Paga":"status-aprovado","Vencida":"status-vencida"}.get(fat['Status'],"status-fechado")
                    em=fat['Data_Emissao'].strftime('%d/%m/%Y') if pd.notna(fat['Data_Emissao']) else "—"
                    ve=fat['Data_Vencimento'].strftime('%d/%m/%Y') if pd.notna(fat['Data_Vencimento']) else "—"
                    st.markdown(f"<div class='turno-card'><div style='display:flex;justify-content:space-between;align-items:center;'><strong style='color:#0A2463;'>📄 {fat['Numero']}</strong><span class='turno-status {sc}'>{fat['Status']}</span></div><div style='color:#374151;margin-top:6px;'>{fat['Cliente']} | <strong>€{fat['Valor']:,.2f}</strong></div><div style='color:#9CA3AF;font-size:.8rem;'>Emissão: {em} • Venc.: {ve}</div></div>",unsafe_allow_html=True)
            else: st.info("Sem faturas.")

    with tab11:
        st.markdown('<div class="section-title">📈 Relatórios</div>',unsafe_allow_html=True)
        if not registos_db.empty:
            c1,c2,c3=st.columns(3)
            with c1: r_i=st.date_input("De",date.today()-timedelta(days=30))
            with c2: r_f=st.date_input("Até",date.today())
            with c3: r_t=st.selectbox("Técnico",["Todos"]+users['Nome'].tolist() if not users.empty else ["Todos"])
            dr=registos_db[(registos_db['Data']>=pd.Timestamp(r_i))&(registos_db['Data']<=pd.Timestamp(r_f))].copy()
            if r_t!="Todos": dr=dr[dr['Técnico']==r_t]
            if not dr.empty:
                res=dr.groupby(['Técnico','Obra']).agg(Horas=('Horas_Total','sum'),Registos=('Técnico','count')).reset_index()
                res['Horas_fmt']=res['Horas'].apply(fh); res['Valor']=res.apply(lambda row: f"€{calc_val(dr[(dr['Técnico']==row['Técnico'])&(dr['Obra']==row['Obra'])],users):,.2f}",axis=1)
                st.dataframe(res[['Técnico','Obra','Horas_fmt','Registos','Valor']].rename(columns={'Horas_fmt':'Horas'}),use_container_width=True,hide_index=True)
                csv_=dr.copy(); csv_['Data']=csv_['Data'].dt.strftime('%d/%m/%Y')
                st.download_button("📥 Exportar CSV",data=csv_.to_csv(index=False,encoding='utf-8-sig'),file_name=f"rel_{r_i}_{r_f}.csv",mime="text/csv",use_container_width=True)
            else: st.info("Sem dados.")
        else: st.info("Sem registos.")

    with tab12:
        st.markdown('<div class="section-title">🛡️ Segurança e Conformidade</div>',unsafe_allow_html=True)
        s1,s2,s3,s4,s5,s6,s7=st.tabs(["📋 Regras de Ouro","⚠️ Incidentes","🚶 Safety Walks","👁️ Observações","🔧 Equipamentos","💬 Diálogos","📄 Documentação"])
        with s1:
            st.markdown("#### 🥇 As 10 Regras de Ouro")
            for icn,titulo,desc in REGRAS_OURO:
                st.markdown(f"<div class='seg-card'><div class='seg-icon' style='background:#FFF3CD;'>{icn}</div><div><div class='seg-title'>{titulo}</div><div class='seg-sub'>{desc}</div></div></div>",unsafe_allow_html=True)
        with s2:
            st.markdown("#### ⚠️ Incidentes")
            with st.expander("➕ Registar"):
                with st.form("inc_adm"):
                    c1,c2=st.columns(2)
                    with c1: io_=st.selectbox("Obra",obras_db['Obra'].tolist() if not obras_db.empty else ["—"]); it_=st.selectbox("Tipo",["Quase-acidente","Acidente com baixa","Acidente sem baixa","Situação insegura","Dano material","Outro"]); ig_=st.selectbox("Gravidade",["Baixa","Média","Alta","Crítica"])
                    with c2: id_=st.text_area("Descrição",height=120)
                    if st.form_submit_button("Registar"):
                        ni=pd.DataFrame([{"Data":datetime.now().strftime('%d/%m/%Y'),"Utilizador":st.session_state.user,"Obra":io_,"Tipo":it_,"Descricao":id_,"Gravidade":ig_,"Status":"Aberto"}])
                        save_db(pd.concat([incs_db,ni],ignore_index=True),"incidentes.csv"); inv(); st.success("✅"); st.rerun()
            if not incs_db.empty:
                gc={"Baixa":"status-aprovado","Média":"status-pendente","Alta":"status-vencida","Crítica":"status-vencida"}
                for _,inc in incs_db.sort_values('Data',ascending=False).iterrows():
                    gv=gc.get(inc.get('Gravidade',''),"status-fechado")
                    st.markdown(f"<div class='turno-card'><div class='turno-header'><span>⚠️ {inc.get('Tipo','—')} — {inc.get('Obra','—')}</span><span class='turno-status {gv}'>{inc.get('Gravidade','—')}</span></div><div style='color:#374151;font-size:.9rem;'>{inc.get('Descricao','')}</div><div style='color:#9CA3AF;font-size:.8rem;margin-top:4px;'>{inc.get('Data','—')} • {inc.get('Utilizador','—')}</div></div>",unsafe_allow_html=True)
            else: st.info("Sem incidentes.")
        with s4:
            st.markdown("#### 🚶 Safety Walks — Inspeções de Segurança")
            with st.expander("➕ Registar Safety Walk"):
                with st.form("sw_adm"):
                    c1,c2=st.columns(2)
                    with c1:
                        sw_ob=st.selectbox("Obra",obras_db['Obra'].tolist() if not obras_db.empty else ["—"],key="sw_ob")
                        sw_cat=st.selectbox("Categoria",CATEGORIAS_SAFETY_WALK,key="sw_cat")
                        sw_urg=st.selectbox("Urgência",["Baixa","Média","Alta","Crítica"],key="sw_urg")
                    with c2:
                        sw_desc=st.text_area("Descrição da Observação",height=80,key="sw_desc")
                        sw_ac=st.text_area("Ação Corretiva",height=80,key="sw_ac")
                    if st.form_submit_button("Registar Safety Walk",use_container_width=True):
                        nsw=pd.DataFrame([{"Data":datetime.now().strftime('%d/%m/%Y'),"Utilizador":st.session_state.user,"Obra":sw_ob,"Categoria":sw_cat,"Descricao":sw_desc,"AcaoCorretiva":sw_ac,"Status":"Aberta","Urgencia":sw_urg}])
                        save_db(pd.concat([sw_db,nsw],ignore_index=True),"safety_walks.csv"); inv(); st.success("✅ Safety Walk registada!"); st.rerun()
            # Filtros
            col_sf1,col_sf2=st.columns(2)
            with col_sf1: sf_ob=st.selectbox("Filtrar Obra",["Todas"]+obras_db['Obra'].tolist() if not obras_db.empty else ["Todas"],key="sf_ob")
            with col_sf2: sf_cat=st.selectbox("Filtrar Categoria",["Todas"]+CATEGORIAS_SAFETY_WALK,key="sf_cat")
            sw_show=sw_db.copy() if not sw_db.empty else pd.DataFrame()
            if not sw_show.empty:
                if sf_ob!="Todas": sw_show=sw_show[sw_show['Obra']==sf_ob]
                if sf_cat!="Todas": sw_show=sw_show[sw_show['Categoria']==sf_cat]
                ug_cor={"Baixa":"status-aprovado","Média":"status-pendente","Alta":"status-vencida","Crítica":"status-vencida"}
                for _,sw_r in sw_show.sort_values('Data',ascending=False).iterrows():
                    uc=ug_cor.get(sw_r.get('Urgencia',''),"status-fechado")
                    st.markdown(f"<div class='turno-card'><div class='turno-header'><span>🚶 {sw_r.get('Categoria','—')} — {sw_r.get('Obra','—')}</span><span class='turno-status {uc}'>{sw_r.get('Urgencia','—')}</span></div><div style='color:#374151;font-size:.9rem;'>{sw_r.get('Descricao','')}</div><div style='color:#3E92CC;font-size:.85rem;margin-top:4px;'>🔧 {sw_r.get('AcaoCorretiva','')}</div><div style='color:#9CA3AF;font-size:.8rem;margin-top:4px;'>{sw_r.get('Data','—')} • {sw_r.get('Utilizador','—')}</div></div>",unsafe_allow_html=True)
            else: st.info("Sem Safety Walks registadas.")

        with s5:
            st.markdown("#### 👁️ Observações de Segurança")
            with st.expander("➕ Registar Observação"):
                with st.form("obs_adm"):
                    c1,c2=st.columns(2)
                    with c1:
                        ob_obs=st.selectbox("Obra",obras_db['Obra'].tolist() if not obras_db.empty else ["—"],key="ob_obs")
                        tp_obs=st.selectbox("Tipo",["Situação Insegura","Comportamento Inseguro","Boas Práticas","Condição Perigosa","Sugestão de Melhoria","Outro"],key="tp_obs")
                    with c2:
                        desc_obs=st.text_area("Descrição",height=120,key="desc_obs")
                    if st.form_submit_button("Registar",use_container_width=True):
                        no=pd.DataFrame([{"Data":datetime.now().strftime('%d/%m/%Y'),"Utilizador":st.session_state.user,"Obra":ob_obs,"Tipo":tp_obs,"Descricao":desc_obs,"Status":"Aberta"}])
                        save_db(pd.concat([obs_db,no],ignore_index=True),"obs_seguranca.csv"); inv(); st.success("✅"); st.rerun()
            sf_obs=st.selectbox("Estado",["Todos","Aberta","Fechada","Em Análise"],key="sf_obs")
            obs_show=obs_db.copy() if not obs_db.empty else pd.DataFrame()
            if not obs_show.empty:
                if sf_obs!="Todos": obs_show=obs_show[obs_show['Status']==sf_obs]
                for _,o_ in obs_show.sort_values('Data',ascending=False).iterrows():
                    cor_t={"Situação Insegura":"status-vencida","Comportamento Inseguro":"status-pendente","Boas Práticas":"status-aprovado"}.get(o_.get('Tipo',''),"status-fechado")
                    st.markdown(f"<div class='turno-card'><div class='turno-header'><span>👁️ {o_.get('Tipo','—')} — {o_.get('Obra','—')}</span><span class='turno-status {cor_t}'>{o_.get('Status','—')}</span></div><div style='color:#374151;font-size:.9rem;'>{o_.get('Descricao','')}</div><div style='color:#9CA3AF;font-size:.8rem;margin-top:4px;'>{o_.get('Data','—')} • {o_.get('Utilizador','—')}</div></div>",unsafe_allow_html=True)
            else: st.info("Sem observações.")

        with s6:
            st.markdown("#### 🔧 Meios e Equipamentos")
            with st.expander("➕ Atribuir Equipamento"):
                with st.form("eq_adm"):
                    c1,c2=st.columns(2)
                    with c1:
                        eq_ob=st.selectbox("Obra",obras_db['Obra'].tolist() if not obras_db.empty else ["—"],key="eq_ob")
                        eq_tp=st.selectbox("Tipo",TIPOS_EQUIPAMENTO,key="eq_tp")
                        eq_desc=st.text_input("Descrição / Modelo",key="eq_desc")
                        eq_ns=st.text_input("Nº Série / Matrícula",key="eq_ns")
                    with c2:
                        eq_ut=st.selectbox("Atribuído a",["(Obra)"]+users['Nome'].tolist() if not users.empty else ["(Obra)"],key="eq_ut")
                        eq_dat=st.date_input("Data Atribuição",value=date.today(),key="eq_dat")
                        eq_val=st.date_input("Validade / Próxima Inspeção",value=date.today()+timedelta(days=365),key="eq_val")
                        eq_est=st.selectbox("Estado",["Operacional","Em Manutenção","Avariado","Retirado"],key="eq_est")
                    if st.form_submit_button("Atribuir",use_container_width=True):
                        ne=pd.DataFrame([{"Obra":eq_ob,"Tipo":eq_tp,"Descricao":eq_desc,"NumSerie":eq_ns,"Utilizador":eq_ut,"DataAtrib":str(eq_dat),"Validade":str(eq_val),"Estado":eq_est}])
                        save_db(pd.concat([equip_db,ne],ignore_index=True),"equipamentos.csv"); inv(); st.success("✅ Equipamento atribuído!"); st.rerun()
            # Filtro por obra
            eq_f_ob=st.selectbox("Filtrar por Obra",["Todas"]+obras_db['Obra'].tolist() if not obras_db.empty else ["Todas"],key="eq_f_ob")
            eq_show=equip_db.copy() if not equip_db.empty else pd.DataFrame()
            if not eq_show.empty:
                if eq_f_ob!="Todas": eq_show=eq_show[eq_show['Obra']==eq_f_ob]
                hj_eq=date.today()
                for _,eq in eq_show.iterrows():
                    try: vd_eq=pd.to_datetime(eq['Validade']).date(); exp_eq=vd_eq<hj_eq; prx_eq=0<=(vd_eq-hj_eq).days<=30
                    except: exp_eq=False; prx_eq=False
                    ic_eq="🔴" if exp_eq else ("🟡" if prx_eq else "🟢")
                    est_cor={"Operacional":"status-aprovado","Em Manutenção":"status-pendente","Avariado":"status-vencida","Retirado":"status-fechado"}.get(eq.get('Estado',''),"status-fechado")
                    st.markdown(f"<div class='turno-card'><div class='turno-header'><span>{ic_eq} {eq.get('Tipo','—')} — {eq.get('Descricao','—')}</span><span class='turno-status {est_cor}'>{eq.get('Estado','—')}</span></div><div style='color:#374151;font-size:.9rem;'>📍 {eq.get('Obra','—')} &nbsp;|&nbsp; 👤 {eq.get('Utilizador','—')} &nbsp;|&nbsp; 🔢 {eq.get('NumSerie','—')}</div><div style='color:#7A8BA6;font-size:.8rem;margin-top:4px;'>Validade/Inspeção: {eq.get('Validade','—')}</div></div>",unsafe_allow_html=True)
            else: st.info("Sem equipamentos registados.")

        with s6:
            st.markdown("#### 💬 Diálogos de Segurança")
            st.caption("Crie diálogos de segurança e atribua a colaboradores. Eles confirmam a leitura na app.")
            with st.expander("➕ Criar Diálogo"):
                with st.form("dlg_cria"):
                    c1,c2=st.columns(2)
                    with c1:
                        dlg_titulo=st.text_input("Título do diálogo",key="dlg_t")
                        dlg_tipo=st.selectbox("Tipo",["Procedimento","Regra","Alerta","Formação","Outro"],key="dlg_tp")
                        dlg_estado=st.selectbox("Estado",["Ativo","Inativo"],key="dlg_est")
                    with c2:
                        dlg_desc=st.text_area("Conteúdo / Descrição",height=120,key="dlg_d")
                        dlg_atrib=st.multiselect("Atribuir a",users['Nome'].tolist() if not users.empty else [],key="dlg_atr")
                    if st.form_submit_button("Criar e Atribuir",use_container_width=True):
                        if dlg_titulo.strip():
                            nd=pd.DataFrame([{"Titulo":dlg_titulo,"Descricao":dlg_desc,"Tipo":dlg_tipo,"DataCriacao":datetime.now().strftime('%d/%m/%Y'),"Atribuidos":"|".join(dlg_atrib),"Estado":dlg_estado}])
                            save_db(pd.concat([diags_db,nd],ignore_index=True),"dialogos.csv")
                            # Criar registos por utilizador
                            if dlg_atrib:
                                novos_u=[{"Dialogo":dlg_titulo,"Utilizador":u_,"DataLeitura":"","Confirmado":"0"} for u_ in dlg_atrib]
                                save_db(pd.concat([diags_u_db,pd.DataFrame(novos_u)],ignore_index=True),"dialogos_users.csv")
                            inv(); st.success("✅ Diálogo criado!"); st.rerun()
            # Lista de diálogos
            f_dlg_est=st.selectbox("Filtrar Estado",["Todos","Ativo","Inativo"],key="f_dlg_e")
            dlg_show=diags_db.copy() if not diags_db.empty else pd.DataFrame()
            if not dlg_show.empty:
                if f_dlg_est!="Todos": dlg_show=dlg_show[dlg_show['Estado']==f_dlg_est]
                for _,dlg in dlg_show.iterrows():
                    # Contar confirmações
                    atrib=dlg.get('Atribuidos','').split('|') if dlg.get('Atribuidos') else []
                    n_atr=len([a for a in atrib if a])
                    conf_df=diags_u_db[diags_u_db['Dialogo']==dlg['Titulo']] if not diags_u_db.empty else pd.DataFrame()
                    n_conf=len(conf_df[conf_df['Confirmado']=="1"]) if not conf_df.empty else 0
                    est_c="status-aprovado" if dlg.get('Estado')=="Ativo" else "status-fechado"
                    st.markdown(f"<div class='turno-card'><div class='turno-header'><span>💬 {dlg.get('Titulo','—')}</span><span class='turno-status {est_c}'>{dlg.get('Estado','—')}</span></div><div style='color:#374151;font-size:.9rem;'>{dlg.get('Tipo','—')} • {dlg.get('DataCriacao','—')}</div><div style='color:#7A8BA6;font-size:.85rem;margin-top:4px;'>👥 {n_atr} atribuídos &nbsp;|&nbsp; ✅ {n_conf} confirmados</div></div>",unsafe_allow_html=True)
            else: st.info("Sem diálogos criados.")

        with s3:
            st.markdown("#### 📄 Documentação")
            if not users.empty:
                ud_=st.selectbox("Colaborador",users['Nome'].tolist())
                du_=docs_db[docs_db['Utilizador']==ud_] if not docs_db.empty else pd.DataFrame()
                with st.expander("➕ Adicionar"):
                    with st.form("df_"):
                        c1,c2=st.columns(2)
                        with c1: dt_=st.selectbox("Tipo",["Cartão Cidadão","NIF","Carta de Condução","Certif. CAT","Certif. SST","Formação","Outro"]); dn_=st.text_input("Descrição")
                        with c2: dv_=st.date_input("Validade",value=date.today()+timedelta(days=365))
                        if st.form_submit_button("Guardar"):
                            nd=pd.DataFrame([{"Utilizador":ud_,"Tipo":dt_,"Nome":dn_,"Validade":str(dv_),"Ficheiro":""}])
                            save_db(pd.concat([docs_db,nd],ignore_index=True),"documentos.csv"); inv(); st.success("✅"); st.rerun()
                if not du_.empty:
                    hj_=date.today()
                    for _,doc in du_.iterrows():
                        try: vd=pd.to_datetime(doc['Validade']).date(); exp=vd<hj_; prx=0<=(vd-hj_).days<=30
                        except: exp=False; prx=False
                        ic="🔴" if exp else ("🟡" if prx else "🟢")
                        st.markdown(f"<div class='turno-card'><div class='turno-header'><span>{ic} {doc['Tipo']}</span></div><div style='color:#374151;'>{doc['Nome']} • Validade: {doc['Validade']}</div></div>",unsafe_allow_html=True)
                else: st.info("Sem documentos.")

    # ============================================================
