"""
Migração de Local_Obra/Cliente_Obra em usuarios.csv — 2026-08-16
feat/painel-obra-campos-operacionais (Fase 1)

Corrige os dois campos para colaboradores cujo Local_Obra (texto livre)
não correspondia a nenhuma obra real em obras_lista.csv — incluindo o
caso original desta sessão ("Luminus EDF Liege" / "BASF S.A", sem
relação um com o outro).

Regra aplicada, por pessoa (decidida e aprovada em chat, grupo a
grupo, antes de este script ser escrito). O mapeamento NÃO é
hard-coded por nome — é calculado em tempo de execução a partir de
inst_acessos.csv, para evitar erros de transcrição manual:

  1. Pessoa com exatamente 1 alocação ativa (Ativo=Sim) em
     inst_acessos.csv: Local_Obra passa a ser essa obra.
  2. Kelvi Lewe e Argel do Carmo Vieira (Local_Obra="Finsa", ambíguo
     entre CriticalFlow e Lusofinsa em inst_acessos.csv): Local_Obra
     passa a "Lusofinsa - Cedência de mão de obra" (exceção nomeada).
  3. Colaboradores em CPS_ADMINS (Local_Obra="CPS", pessoal interno):
     Local_Obra passa a "Escritório" (exceção nomeada).
  4. Restantes (sem alocação ativa fiável, ou mais de uma): Local_Obra
     fica vazio — para alguém do RH escolher manualmente, em vez de
     adivinhar.

Cliente_Obra é recalculado para TODAS as linhas de usuarios.csv (não só
as corrigidas) a partir do Local_Obra final, usando obras_lista.csv
como única fonte — garante que não fica nenhuma divergência por trás,
mesmo em casos não cobertos pela lista acima.

Corre em modo --dry-run por omissão — só escreve em GCS com --apply.

Backup (ficheiro completo, antes de qualquer escrita):
  gs://gestnow-dados/data/backups/2026-08-16/usuarios_antes_fase1_local_obra.csv
"""
import argparse
import io
import sys

import pandas as pd
from google.cloud import storage as gcs

BUCKET = "gestnow-dados"

# 2 casos ambíguos (Local_Obra="Finsa", 2 alocações ativas simultâneas em
# inst_acessos.csv) — decisão explícita do utilizador.
EXCECOES_LUSOFINSA = {
    "Kelvi Lewe": "Lusofinsa - Cedência de mão de obra",
    "Argel do Carmo Vieira": "Lusofinsa - Cedência de mão de obra",
}

# Admins internos com Local_Obra="CPS" (sem alocação em obra de cliente)
# — decisão explícita do utilizador. Só os de Tipo=Admin; os restantes
# com Local_Obra="CPS" são técnicos de campo sem evidência fiável e
# ficam vazios, como o resto do grupo "sem alocação".
CPS_ADMINS = {
    "Hélder Plácido", "Diana Plácido", "Marco Santos", "Helena Leitão",
    "Ana Carvalho", "Mauricio Figueiredo", "Vera Antunes", "Diogo Henriques",
}


def _client():
    return gcs.Client()


def _ler_csv(bucket, nome):
    blob = bucket.blob(f"data/{nome}")
    buf = io.BytesIO(blob.download_as_bytes())
    df = pd.read_csv(buf, dtype=str, on_bad_lines="skip", encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    return df.fillna("")


def _escrever_csv(bucket, nome, df, apply_):
    if not apply_:
        return
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    blob = bucket.blob(f"data/{nome}")
    blob.upload_from_string(buf.getvalue().encode("utf-8-sig"), content_type="text/csv")


def _calcular_novo_local(nome, local_atual, obras_reais, ia_ativos):
    """Devolve o novo Local_Obra para `nome`, ou None se não for para mexer
    (já vazio ou já é uma obra real)."""
    if local_atual == "" or local_atual in obras_reais:
        return None
    if nome in EXCECOES_LUSOFINSA:
        return EXCECOES_LUSOFINSA[nome]
    if nome in CPS_ADMINS:
        return "Escritório"
    obras_pessoa = sorted(set(
        ia_ativos.loc[ia_ativos["Utilizador"].astype(str).str.strip() == nome, "Obra"]
        .astype(str).str.strip()
    ))
    if len(obras_pessoa) == 1:
        return obras_pessoa[0]
    return ""  # sem alocação fiável (0 ou >1) — limpa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                     help="Escreve mesmo em GCS. Sem esta flag, só mostra o que faria.")
    args = ap.parse_args()
    apply_ = args.apply

    client = _client()
    bucket = client.bucket(BUCKET)

    print(f"{'A APLICAR' if apply_ else 'DRY-RUN (nada é escrito)'} — "
          f"migração Local_Obra/Cliente_Obra (usuarios.csv)\n")

    usr = _ler_csv(bucket, "usuarios.csv")
    obr = _ler_csv(bucket, "obras_lista.csv")
    ia = _ler_csv(bucket, "inst_acessos.csv")
    ia_ativos = ia[ia["Ativo"].astype(str).str.strip() == "Sim"]
    obras_reais = set(obr["Obra"].astype(str).str.strip()) - {""}

    # ── 1. Aplicar o novo Local_Obra ────────────────────────────────────
    n_corrigidos, n_limpos = 0, 0
    for idx, row in usr.iterrows():
        nome = row["Nome"]
        local_atual = str(row.get("Local_Obra", "")).strip()
        novo_local = _calcular_novo_local(nome, local_atual, obras_reais, ia_ativos)
        if novo_local is None:
            continue
        if novo_local:
            print(f"  {nome}: Local_Obra '{local_atual}' -> '{novo_local}'")
            n_corrigidos += 1
        else:
            print(f"  {nome}: Local_Obra '{local_atual}' -> '' "
                  f"(sem evidência fiável — a limpar)")
            n_limpos += 1
        usr.at[idx, "Local_Obra"] = novo_local

    print(f"\n  {n_corrigidos} colaborador(es) com Local_Obra corrigido.")
    print(f"  {n_limpos} colaborador(es) com Local_Obra limpo (sem evidência).\n")

    # ── 2. Recalcular Cliente_Obra para TODAS as linhas ────────────────
    mapa_cliente = dict(zip(obr["Obra"].astype(str).str.strip(),
                             obr["Cliente"].astype(str).str.strip()))
    n_cliente_alterado = 0
    for idx, row in usr.iterrows():
        local = str(row.get("Local_Obra", "")).strip()
        cliente_novo = mapa_cliente.get(local, "")
        cliente_atual = str(row.get("Cliente_Obra", "")).strip()
        if cliente_atual != cliente_novo:
            n_cliente_alterado += 1
            usr.at[idx, "Cliente_Obra"] = cliente_novo

    print(f"  {n_cliente_alterado} colaborador(es) com Cliente_Obra recalculado "
          f"a partir de Local_Obra.\n")

    # ── 3. Verificação final ────────────────────────────────────────────
    print("── Verificação final ──")
    problemas = []
    for _, row in usr.iterrows():
        local = str(row.get("Local_Obra", "")).strip()
        cliente = str(row.get("Cliente_Obra", "")).strip()
        if local and local not in obras_reais:
            problemas.append(f"{row['Nome']}: Local_Obra '{local}' não existe em obras_lista.csv")
            continue
        cliente_esperado = mapa_cliente.get(local, "")
        if cliente != cliente_esperado:
            problemas.append(
                f"{row['Nome']}: Cliente_Obra '{cliente}' != esperado "
                f"'{cliente_esperado}' para Local_Obra '{local}'")

    if problemas:
        for p in problemas:
            print(f"  ❌ {p}")
        print("\n  MIGRAÇÃO ABORTADA — corrigir antes de aplicar." if apply_ else
              "\n  (dry-run: corrigir antes de correr com --apply)")
        if apply_:
            sys.exit(1)
    else:
        print("  ✅ Todo o Local_Obra preenchido corresponde a uma obra real; "
              "todo o Cliente_Obra bate com obras_lista.csv.")

    # ── 4. Escrever (só com --apply) ────────────────────────────────
    if apply_:
        _escrever_csv(bucket, "usuarios.csv", usr, apply_)
        print("\n✅ Alterações escritas em GCS.")
    else:
        print("\n(dry-run — nada foi escrito; corre com --apply para aplicar)")


if __name__ == "__main__":
    main()
