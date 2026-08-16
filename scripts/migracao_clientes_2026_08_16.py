"""
Migração de limpeza de clientes_financeiro.csv — 2026-08-16
feat/limpeza-clientes-financeiro

Consolida 4 grupos de duplicados identificados na auditoria
(feat/auditoria-comercial-orcamentacao-obra):

  1. CPS / CPS-Lda / CPS,Lda           -> mantém "CPS" (10383060)
  2. Luso Finsa S.A / Luso Finsa – ... -> mantém "Luso Finsa – Indústria
                                           e Comércio de Madeiras S.A." (9486CEC0)
  3. TCPI / Tecnoprojecto Internacional -> mantém "Tecnoprojecto
                                           Internacional..." (D81C59E7)
     (TCPI France, 766F9463, fica separada — NIF fiscal próprio)
  4. Elmek - Meivcore Euskadi / MEIVCORE EUSKADI SL -> mantém "MEIVCORE
     EUSKADI SL" (6B0BCDA2), com NIF/Email/Telefone copiados do registo
     Elmek antes de o descartar.

Decisão por grupo aprovada explicitamente pelo utilizador em chat antes
de este script ser escrito. Corre em modo `--dry-run` por omissão —
só escreve em GCS com `--apply`.

Ficheiros afetados: clientes_financeiro.csv, obras_lista.csv,
comercial_oportunidades.csv, com_contactos.csv, usuarios.csv.
orcamentos.csv e comercial_clientes.csv não têm nenhuma referência às
IDs/nomes descartados (confirmado antes de este script ser escrito) —
não são tocados.

Backup pré-existente (feito antes desta limpeza, ficheiros completos):
  gs://gestnow-dados/data/backups/2026-08-16/
"""
import argparse
import io
import sys

import pandas as pd
from google.cloud import storage as gcs

BUCKET = "gestnow-dados"

# ID a manter -> IDs a remover de clientes_financeiro.csv
IDS_REMOVER = {
    "9AAD2D28": "10383060",  # CPS-Lda -> CPS
    "E8148377": "10383060",  # CPS,Lda -> CPS
    "A6A014C9": "9486CEC0",  # Luso Finsa S.A -> Luso Finsa – Indústria...
    "BF2EBBEE": "D81C59E7",  # TCPI -> Tecnoprojecto Internacional...
    "6698DCE7": "6B0BCDA2",  # Elmek - Meivcore Euskadi -> MEIVCORE EUSKADI SL
}

# Nome antigo (tal como aparece hoje nos ficheiros que referenciam Cliente
# por texto) -> nome novo, para reescrever nas colunas Cliente/Cliente_Nome/
# Cliente_Obra dos ficheiros dependentes.
NOME_ANTIGO_PARA_NOVO = {
    "CPS-Lda": "CPS",
    "CPS,Lda": "CPS",
    "Luso Finsa S.A": "Luso Finsa – Indústria e Comércio de Madeiras S.A.",
    "TCPI": "Tecnoprojecto Internacional - Projectos e Realizações Industriais S.A",
    "Elmek - Meivcore Euskadi": "MEIVCORE EUSKADI SL",
}

# Campos a copiar do registo perdedor para o vencedor antes de o descartar
# (só aplicável ao grupo 4 — os outros vencedores já têm os dados que precisam).
COPIAR_CAMPOS = {
    "6698DCE7": {  # de: Elmek - Meivcore Euskadi
        "para_id": "6B0BCDA2",  # para: MEIVCORE EUSKADI SL
        "campos": ["NIF", "Email", "Telefone"],
    }
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                     help="Escreve mesmo em GCS. Sem esta flag, só mostra o que faria.")
    args = ap.parse_args()
    apply_ = args.apply

    client = _client()
    bucket = client.bucket(BUCKET)

    print(f"{'A APLICAR' if apply_ else 'DRY-RUN (nada é escrito)'} — migração clientes_financeiro.csv\n")

    cf = _ler_csv(bucket, "clientes_financeiro.csv")
    obr = _ler_csv(bucket, "obras_lista.csv")
    op = _ler_csv(bucket, "comercial_oportunidades.csv")
    ct = _ler_csv(bucket, "com_contactos.csv")
    usr = _ler_csv(bucket, "usuarios.csv")

    # ── 1. Copiar campos do perdedor para o vencedor (grupo 4) ────────
    for id_perder, cfg in COPIAR_CAMPOS.items():
        row_perder = cf[cf["ID"] == id_perder]
        if row_perder.empty:
            print(f"  [aviso] ID a copiar '{id_perder}' não encontrado — a saltar.")
            continue
        row_perder = row_perder.iloc[0]
        mask_ganhar = cf["ID"] == cfg["para_id"]
        if not mask_ganhar.any():
            print(f"  [aviso] ID destino '{cfg['para_id']}' não encontrado — a saltar cópia.")
            continue
        for campo in cfg["campos"]:
            valor = row_perder.get(campo, "")
            atual = cf.loc[mask_ganhar, campo].iloc[0] if campo in cf.columns else ""
            if valor and not str(atual).strip():
                print(f"  clientes_financeiro.csv: {cfg['para_id']}.{campo} "
                      f"'{atual}' -> '{valor}' (copiado de {id_perder})")
                cf.loc[mask_ganhar, campo] = valor

    # ── 2. Remover linhas duplicadas de clientes_financeiro.csv ───────
    n_antes = len(cf)
    ids_remover = list(IDS_REMOVER.keys())
    removidas = cf[cf["ID"].isin(ids_remover)]
    for _, r in removidas.iterrows():
        print(f"  clientes_financeiro.csv: remover ID={r['ID']} Nome='{r['Nome']}'")
    cf = cf[~cf["ID"].isin(ids_remover)].reset_index(drop=True)
    print(f"  clientes_financeiro.csv: {n_antes} -> {len(cf)} linhas "
          f"({n_antes - len(cf)} removidas)\n")

    # ── 3. Reescrever nomes nos ficheiros dependentes ──────────────────
    def _renomear(df, col, nome_ficheiro):
        alteradas = 0
        for antigo, novo in NOME_ANTIGO_PARA_NOVO.items():
            if col not in df.columns:
                continue
            mask = df[col].astype(str).str.strip() == antigo
            n = int(mask.sum())
            if n:
                print(f"  {nome_ficheiro}: {n}x '{antigo}' -> '{novo}' (coluna {col})")
                df.loc[mask, col] = novo
                alteradas += n
        return df, alteradas

    obr, n_obr = _renomear(obr, "Cliente", "obras_lista.csv")
    op, n_op = _renomear(op, "Cliente", "comercial_oportunidades.csv")
    ct, n_ct = _renomear(ct, "Cliente_Nome", "com_contactos.csv")
    usr, n_usr = _renomear(usr, "Cliente_Obra", "usuarios.csv")

    total = n_obr + n_op + n_ct + n_usr
    print(f"\n  Total de referências reescritas nos 4 ficheiros: {total}\n")

    # ── 4. Verificação final — nenhum nome órfão ───────────────────────
    nomes_validos = set(cf["Nome"].astype(str).str.strip()) - {""}
    problemas = []
    for df, col, nome_ficheiro in [
        (obr, "Cliente", "obras_lista.csv"),
        (op, "Cliente", "comercial_oportunidades.csv"),
        (ct, "Cliente_Nome", "com_contactos.csv"),
        (usr, "Cliente_Obra", "usuarios.csv"),
    ]:
        if col not in df.columns:
            continue
        usados = set(df[col].astype(str).str.strip()) - {""}
        orfaos = usados - nomes_validos
        if orfaos:
            problemas.append((nome_ficheiro, orfaos))

    print("── Verificação final: nomes órfãos ──")
    if problemas:
        for fn, orfaos in problemas:
            print(f"  ❌ {fn}: nomes sem correspondência em clientes_financeiro.csv: {sorted(orfaos)}")
        print("\n  MIGRAÇÃO ABORTADA — corrigir antes de aplicar." if apply_ else
              "\n  (dry-run: corrigir antes de correr com --apply)")
        if apply_:
            sys.exit(1)
    else:
        print("  ✅ Nenhum nome órfão em obras_lista.csv, comercial_oportunidades.csv, "
              "com_contactos.csv, usuarios.csv.")

    # ── 5. Escrever (só com --apply) ────────────────────────────────
    if apply_:
        _escrever_csv(bucket, "clientes_financeiro.csv", cf, apply_)
        _escrever_csv(bucket, "obras_lista.csv", obr, apply_)
        _escrever_csv(bucket, "comercial_oportunidades.csv", op, apply_)
        _escrever_csv(bucket, "com_contactos.csv", ct, apply_)
        _escrever_csv(bucket, "usuarios.csv", usr, apply_)
        print("\n✅ Alterações escritas em GCS.")
    else:
        print("\n(dry-run — nada foi escrito; corre com --apply para aplicar)")


if __name__ == "__main__":
    main()
