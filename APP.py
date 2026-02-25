# --- CÓDIGO ORIGINAL COM ERRO (NÃO USAR) ---
# meu_reg = registos_db[(registos_db['Técnico'] == st.session_state.user) & (registos_db['Data'] == hoje)]
# lista_p_exibir = st.session_state.turnos_temp
# if meu_reg.empty else meu_reg.iloc[0]
# ['Turnos'].split(', ')  # ← ERRO AQUI!

# --- CÓDIGO CORRIGIDO ---
hoje = datetime.now().strftime("%d/%m/%Y")
meu_reg = registos_db[(registos_db['Técnico'] == st.session_state.user) & (registos_db['Data'] == hoje)]

# CORREÇÃO IMPORTANTE:
if meu_reg.empty:
    lista_p_exibir = st.session_state.turnos_temp
else:
    # Verificar se a coluna Turnos existe e não é nula
    if 'Turnos' in meu_reg.columns and pd.notna(meu_reg.iloc[0]['Turnos']):
        lista_p_exibir = meu_reg.iloc[0]['Turnos'].split(', ')
    else:
        lista_p_exibir = []
