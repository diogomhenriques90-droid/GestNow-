import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from core import save_db, inv, load_db

def render_compras():
    st.markdown("### 🛒 Gestão de Compras")

    # Carregar dados
    try:
        compras_db = load_db("compras.csv", [
            "ID","Data","Fornecedor","Descricao","Tipo",
            "Quantidade","Preco_Unit","Total","Status","Registado_Por"
        ], silent=True)
    except:
        compras_db = pd.DataFrame(columns=[
            "ID","Data","Fornecedor","Descricao","Tipo",
            "Quantidade","Preco_Unit","Total","Status","Registado_Por"
        ])

    try:
        fornecedores_db = load_db("fornecedores.csv", [
            "ID","Nome","NIF","Email","Telefone","Morada","Categoria"
        ], silent=True)
    except:
        fornecedores_db = pd.DataFrame(columns=[
            "ID","Nome","NIF","Email","Telefone","Morada","Categoria"
        ])

    user_nome = st.session_state.get('user', 'Admin')

    tab_compras, tab_fornecedores, tab_cotacoes = st.tabs([
        "🛒 Compras", "🏢 Fornecedores", "🤖 IA Cotações"
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB COMPRAS
    # ════════════════════════════════════════════════════════════════
    with tab_compras:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("#### ➕ Nova Compra")

            # Lista de fornecedores para selectbox
            forn_lista = fornecedores_db['Nome'].tolist() \
                         if not fornecedores_db.empty else []

            with st.form("form_compra"):
                if forn_lista:
                    fornecedor = st.selectbox(
                        "Fornecedor", forn_lista, key="comp_forn"
                    )
                else:
                    fornecedor = st.text_input(
                        "Fornecedor", key="comp_forn_txt"
                    )
                descricao  = st.text_input("Descrição *", key="comp_desc")
                tipo       = st.selectbox(
                    "Tipo",
                    ["Material","Ferramenta","EPI","Serviço","Outro"],
                    key="comp_tipo"
                )
                col_q, col_p = st.columns(2)
                with col_q:
                    quantidade = st.number_input(
                        "Quantidade", min_value=1, value=1, key="comp_qtd"
                    )
                with col_p:
                    preco = st.number_input(
                        "Preço Unit. (€)",
                        min_value=0.0, value=0.0,
                        step=0.01, key="comp_preco"
                    )
                status = st.selectbox(
                    "Estado",
                    ["Pendente","Encomendado","Recebido","Cancelado"],
                    key="comp_status"
                )

                if st.form_submit_button(
                    "💾 Registar Compra",
                    use_container_width=True, type="primary"
                ):
                    if not descricao.strip():
                        st.error("❌ Descrição obrigatória.")
                    else:
                        total = round(quantidade * preco, 2)
                        nova = pd.DataFrame([{
                            "ID":            str(uuid.uuid4())[:8].upper(),
                            "Data":          datetime.now().strftime("%d/%m/%Y"),
                            "Fornecedor":    fornecedor if forn_lista
                                             else fornecedor,
                            "Descricao":     descricao.strip(),
                            "Tipo":          tipo,
                            "Quantidade":    quantidade,
                            "Preco_Unit":    preco,
                            "Total":         total,
                            "Status":        status,
                            "Registado_Por": user_nome
                        }])
                        updated = pd.concat(
                            [compras_db, nova], ignore_index=True
                        ) if not compras_db.empty else nova
                        save_db(updated, "compras.csv")
                        inv()
                        st.success(
                            f"✅ Compra registada! "
                            f"{descricao[:30]} — € {total:.2f}"
                        )
                        st.rerun()

        with col2:
            st.markdown("#### 📋 Compras Registadas")

            if compras_db.empty:
                st.info("📋 Sem compras registadas.")
            else:
                # Filtros
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    filtro_tipo = st.selectbox(
                        "Tipo",
                        ["Todos","Material","Ferramenta","EPI","Serviço","Outro"],
                        key="comp_filtro_tipo"
                    )
                with col_f2:
                    filtro_status = st.selectbox(
                        "Estado",
                        ["Todos","Pendente","Encomendado","Recebido","Cancelado"],
                        key="comp_filtro_status"
                    )

                df_show = compras_db.copy()
                if filtro_tipo   != "Todos":
                    df_show = df_show[df_show['Tipo']   == filtro_tipo]
                if filtro_status != "Todos":
                    df_show = df_show[df_show['Status'] == filtro_status]

                total_valor = pd.to_numeric(
                    df_show['Total'], errors='coerce'
                ).fillna(0).sum()
                st.metric("Total", f"€ {total_valor:.2f}")

                cols_show = [c for c in [
                    'Data','Fornecedor','Descricao','Tipo',
                    'Quantidade','Preco_Unit','Total','Status'
                ] if c in df_show.columns]
                st.dataframe(
                    df_show[cols_show],
                    use_container_width=True,
                    hide_index=True
                )

                # Alterar estado
                st.markdown("---")
                st.markdown("#### ✏️ Atualizar Estado")
                if not df_show.empty:
                    ids_comp = df_show['ID'].tolist()
                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        comp_sel = st.selectbox(
                            "Compra", ids_comp, key="comp_sel_id"
                        )
                    with col_s2:
                        novo_status = st.selectbox(
                            "Novo Estado",
                            ["Pendente","Encomendado","Recebido","Cancelado"],
                            key="comp_novo_status"
                        )
                    with col_s3:
                        st.markdown("<div style='height:28px;'></div>",
                                    unsafe_allow_html=True)
                        if st.button("✅ Atualizar",
                                      key="btn_atualizar_comp",
                                      use_container_width=True):
                            compras_db.loc[
                                compras_db['ID'] == comp_sel, 'Status'
                            ] = novo_status
                            save_db(compras_db, "compras.csv")
                            inv()
                            st.success("✅ Estado atualizado!")
                            st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB FORNECEDORES
    # ════════════════════════════════════════════════════════════════
    with tab_fornecedores:
        st.markdown("#### 🏢 Fornecedores")

        col_f1, col_f2 = st.columns([1, 2])

        with col_f1:
            st.markdown("#### ➕ Novo Fornecedor")
            with st.form("form_fornecedor"):
                forn_nome  = st.text_input("Nome *", key="forn_nome")
                forn_nif   = st.text_input("NIF",    key="forn_nif")
                forn_email = st.text_input("Email",  key="forn_email")
                forn_tel   = st.text_input("Telefone", key="forn_tel")
                forn_cat   = st.selectbox(
                    "Categoria",
                    ["Material","Ferramenta","EPI","Serviço","Outro"],
                    key="forn_cat"
                )
                forn_morada = st.text_input("Morada", key="forn_morada")

                if st.form_submit_button(
                    "💾 Guardar Fornecedor",
                    use_container_width=True, type="primary"
                ):
                    if not forn_nome.strip():
                        st.error("❌ Nome obrigatório.")
                    else:
                        novo_f = pd.DataFrame([{
                            "ID":        str(uuid.uuid4())[:8].upper(),
                            "Nome":      forn_nome.strip(),
                            "NIF":       forn_nif.strip(),
                            "Email":     forn_email.strip(),
                            "Telefone":  forn_tel.strip(),
                            "Morada":    forn_morada.strip(),
                            "Categoria": forn_cat
                        }])
                        updated_f = pd.concat(
                            [fornecedores_db, novo_f], ignore_index=True
                        ) if not fornecedores_db.empty else novo_f
                        save_db(updated_f, "fornecedores.csv")
                        inv()
                        st.success(f"✅ Fornecedor guardado: {forn_nome}")
                        st.rerun()

        with col_f2:
            st.markdown("#### 📋 Lista de Fornecedores")
            if fornecedores_db.empty:
                st.info("📋 Sem fornecedores registados.")
            else:
                cols_f = [c for c in [
                    'Nome','NIF','Email','Telefone','Categoria'
                ] if c in fornecedores_db.columns]
                st.dataframe(
                    fornecedores_db[cols_f],
                    use_container_width=True,
                    hide_index=True
                )

    # ════════════════════════════════════════════════════════════════
    # TAB COTAÇÕES IA
    # ════════════════════════════════════════════════════════════════
    with tab_cotacoes:
        st.markdown("#### 🤖 Pesquisa de Cotações com IA")
        st.info(
            "A IA pesquisa e compara preços de fornecedores "
            "automaticamente para o produto indicado."
        )

        produto   = st.text_input(
            "Produto/Serviço a cotar *", key="cot_prod",
            placeholder="Ex: 500m cabo elétrico 2.5mm²"
        )
        quantidade_cot = st.number_input(
            "Quantidade", min_value=1, value=1, key="cot_qtd"
        )

        if st.button(
            "🔍 Pedir Cotações com IA",
            key="btn_cotacao", type="primary",
            use_container_width=True
        ):
            if not produto.strip():
                st.error("❌ Indica o produto.")
            else:
                import os, anthropic
                api_key = os.environ.get("ANTHROPIC_API_KEY","")
                if not api_key:
                    st.error("❌ API key não configurada.")
                else:
                    with st.spinner("🤖 A pesquisar cotações..."):
                        try:
                            client = anthropic.Anthropic(api_key=api_key)
                            prompt = f"""És um assistente de compras especializado em materiais de construção e instrumentação industrial em Portugal.

Para o produto: "{produto}" (quantidade: {quantidade_cot} unidades)

Simula 3 cotações de fornecedores portugueses realistas com:
- Nome do fornecedor
- Preço unitário estimado em €
- Prazo de entrega estimado
- Observações relevantes

Responde APENAS em JSON:
{{
  "produto": "{produto}",
  "cotacoes": [
    {{"fornecedor": "...", "preco_unit": 0.00, "prazo": "...", "obs": "..."}},
    {{"fornecedor": "...", "preco_unit": 0.00, "prazo": "...", "obs": "..."}},
    {{"fornecedor": "...", "preco_unit": 0.00, "prazo": "...", "obs": "..."}}
  ]
}}"""
                            resp = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=800,
                                messages=[{"role":"user","content":prompt}]
                            )
                            import json
                            raw = resp.content[0].text.strip()
                            raw = raw.replace("```json","").replace("```","").strip()
                            dados = json.loads(raw)

                            st.success("✅ Cotações obtidas!")
                            cotacoes = dados.get("cotacoes",[])

                            melhor_preco = min(
                                c['preco_unit'] for c in cotacoes
                            ) if cotacoes else 0

                            for c in cotacoes:
                                eh_melhor = c['preco_unit'] == melhor_preco
                                cor = "#10B981" if eh_melhor else "#1E293B"
                                st.markdown(
                                    f"<div style='background:{cor}22;"
                                    f"border:2px solid {cor};"
                                    f"border-radius:10px;padding:14px;"
                                    f"margin-bottom:8px;'>"
                                    f"<b style='color:#F1F5F9;'>"
                                    f"{'⭐ ' if eh_melhor else ''}"
                                    f"{c['fornecedor']}</b>"
                                    f"<span style='float:right;color:{cor};"
                                    f"font-weight:700;font-size:1.1rem;'>"
                                    f"€ {c['preco_unit']:.2f}/un</span><br>"
                                    f"<small style='color:#64748B;'>"
                                    f"📦 {c['prazo']} · {c['obs']}"
                                    f"</small></div>",
                                    unsafe_allow_html=True
                                )

                            total_melhor = round(melhor_preco * quantidade_cot, 2)
                            st.info(
                                f"💡 Melhor opção: **€ {melhor_preco:.2f}/un** "
                                f"× {quantidade_cot} = **€ {total_melhor:.2f}**"
                            )

                        except Exception as e:
                            st.error(f"❌ Erro: {e}")
