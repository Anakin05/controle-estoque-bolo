import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(
    page_title="Controle de Estoque e Financeiro",
    page_icon="🍰",
    layout="wide"
)

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPE
)

client = gspread.authorize(creds)
planilha = client.open("Estoque Bolos")

produtos_ws = planilha.worksheet("produtos")
mov_ws = planilha.worksheet("movimentacoes")
contas_ws = planilha.worksheet("contas_pagar")
contas_receber_ws = planilha.worksheet("contas_receber")


def produtos_df():
    df = pd.DataFrame(produtos_ws.get_all_records())
    if not df.empty:
        df.columns = df.columns.str.strip().str.lower()
    return df


def mov_df():
    df = pd.DataFrame(mov_ws.get_all_records())
    if not df.empty:
        df.columns = df.columns.str.strip().str.lower()
    return df


def contas_df():
    df = pd.DataFrame(contas_ws.get_all_records())
    if not df.empty:
        df.columns = df.columns.str.strip().str.lower()
    return df


def contas_receber_df():
    df = pd.DataFrame(contas_receber_ws.get_all_records())
    if not df.empty:
        df.columns = df.columns.str.strip().str.lower()
    return df


def novo_id(df):
    if df.empty:
        return 1
    return int(df["id"].max()) + 1


def estoque(produto_id):
    mov = mov_df()

    if mov.empty:
        return 0

    mov_produto = mov[mov["produto_id"] == produto_id]

    entradas = mov_produto[mov_produto["tipo"] == "entrada"]["quantidade"].sum()
    saidas = mov_produto[mov_produto["tipo"] == "saida"]["quantidade"].sum()

    return int(entradas - saidas)


st.title("🍰 Controle de Estoque e Financeiro")

menu = st.sidebar.selectbox(
    "Menu",
    [
        "Cadastro",
        "Entrada",
        "Venda",
        "Estoque",
        "Contas a pagar",
        "Contas a receber"
    ]
)


if menu == "Cadastro":
    st.subheader("Cadastrar sabor")

    nome = st.text_input("Sabor")
    custo = st.number_input("Custo", min_value=0.0, step=0.50)
    preco = st.number_input("Preço", min_value=0.0, step=0.50)

    if st.button("Salvar"):
        if nome.strip() == "":
            st.error("Digite o nome do sabor.")
        elif preco <= 0:
            st.error("Digite um preço válido.")
        else:
            df = produtos_df()

            if not df.empty and nome.strip().lower() in df["nome"].str.lower().values:
                st.error("Esse sabor já existe.")
            else:
                produtos_ws.append_row([
                    novo_id(df),
                    nome.strip(),
                    custo,
                    preco
                ])

                st.success("Produto salvo com sucesso!")


elif menu == "Entrada":
    st.subheader("Entrada de estoque")

    df = produtos_df()

    if df.empty:
        st.warning("Cadastre um produto primeiro.")
    else:
        nome = st.selectbox("Produto", df["nome"])
        qtd = st.number_input("Quantidade", min_value=1)

        if st.button("Registrar entrada"):
            produto = df[df["nome"] == nome].iloc[0]

            mov_ws.append_row([
                int(produto["id"]),
                "entrada",
                int(qtd),
                float(produto["custo"]),
                datetime.now().strftime("%d/%m/%Y %H:%M")
            ])

            contas = contas_df()

            contas_ws.append_row([
                novo_id(contas),
                datetime.now().strftime("%d/%m/%Y %H:%M"),
                nome,
                int(qtd),
                float(produto["custo"]),
                0
            ])

            valor_total = int(qtd) * float(produto["custo"])

            st.success(f"Entrada registrada! Valor adicionado ao contas a pagar: R$ {valor_total:.2f}")


elif menu == "Venda":
    st.subheader("Registrar venda")

    df = produtos_df()

    if df.empty:
        st.warning("Cadastre um produto primeiro.")
    else:
        nome = st.selectbox("Produto", df["nome"])
        produto = df[df["nome"] == nome].iloc[0]

        estoque_atual = estoque(produto["id"])
        st.info(f"Estoque atual: {estoque_atual}")

        qtd = st.number_input("Quantidade vendida", min_value=1)

        tipo_pagamento = st.radio(
            "Status do pagamento",
            ["Pago", "Fiado"]
        )

        cliente = ""

        if tipo_pagamento == "Fiado":
            cliente = st.text_input("Nome do devedor")

        if st.button("Registrar venda"):
            if qtd > estoque_atual:
                st.error("Estoque insuficiente.")
            elif tipo_pagamento == "Fiado" and cliente.strip() == "":
                st.error("Digite o nome do devedor.")
            else:
                mov_ws.append_row([
                    int(produto["id"]),
                    "saida",
                    int(qtd),
                    float(produto["preco"]),
                    datetime.now().strftime("%d/%m/%Y %H:%M")
                ])

                if tipo_pagamento == "Fiado":
                    contas_receber = contas_receber_df()

                    contas_receber_ws.append_row([
                        novo_id(contas_receber),
                        datetime.now().strftime("%d/%m/%Y %H:%M"),
                        cliente.strip(),
                        nome,
                        int(qtd),
                        float(produto["preco"]),
                        "nao"
                    ])

                    st.warning("Venda registrada como FIADO.")
                else:
                    st.success("Venda registrada como PAGA.")


elif menu == "Estoque":
    st.subheader("Estoque atual")

    df = produtos_df()

    if df.empty:
        st.info("Nenhum produto cadastrado.")
    else:
        lista = []

        for _, produto in df.iterrows():
            est = estoque(produto["id"])

            lista.append({
                "Sabor": produto["nome"],
                "Estoque": est,
                "Custo": float(produto["custo"]),
                "Preço": float(produto["preco"]),
                "Status": "⚠️ Baixo" if est <= 3 else "✅ OK"
            })

        st.dataframe(pd.DataFrame(lista), use_container_width=True)


elif menu == "Contas a pagar":
    st.subheader("Contas a pagar - Camila")

    df = contas_df()

    if df.empty:
        st.info("Nenhuma dívida registrada.")
    else:
        df["quantidade"] = pd.to_numeric(df["quantidade"])
        df["valor_unitario"] = pd.to_numeric(df["valor_unitario"])
        df["qtd_paga"] = pd.to_numeric(df["qtd_paga"])

        df["qtd_pendente"] = df["quantidade"] - df["qtd_paga"]
        df["valor_pendente"] = df["qtd_pendente"] * df["valor_unitario"]

        total_devendo = df["valor_pendente"].sum()

        st.metric("Total devendo para Camila", f"R$ {total_devendo:.2f}")

        st.markdown("---")

        for i, row in df.iterrows():
            if row["qtd_pendente"] > 0:
                st.write(f"**{row['produto']}**")
                st.write(
                    f"Entrada: {int(row['quantidade'])} un | "
                    f"Pago: {int(row['qtd_paga'])} un | "
                    f"Pendente: {int(row['qtd_pendente'])} un"
                )
                st.write(f"Valor pendente: R$ {row['valor_pendente']:.2f}")

                qtd_pagar = st.number_input(
                    "Quantas unidades pagar?",
                    min_value=1,
                    max_value=int(row["qtd_pendente"]),
                    key=f"qtd_pagar_{row['id']}"
                )

                if st.button("Confirmar PIX", key=f"pagar_{row['id']}"):
                    nova_qtd_paga = int(row["qtd_paga"]) + int(qtd_pagar)

                    contas_ws.update_cell(i + 2, 6, nova_qtd_paga)

                    valor_pago = int(qtd_pagar) * float(row["valor_unitario"])

                    st.success(f"PIX confirmado: R$ {valor_pago:.2f}")
                    st.rerun()

                st.markdown("---")

        st.subheader("Tabela completa")
        st.dataframe(df, use_container_width=True)


elif menu == "Contas a receber":
    st.subheader("Contas a receber")

    df = contas_receber_df()

    if df.empty:
        st.info("Nenhuma venda fiada registrada.")
    else:
        df["quantidade"] = pd.to_numeric(df["quantidade"])
        df["valor_unitario"] = pd.to_numeric(df["valor_unitario"])

        df["total"] = df["quantidade"] * df["valor_unitario"]

        pendentes = df[df["pago"] == "nao"]
        total_receber = pendentes["total"].sum() if not pendentes.empty else 0

        st.metric("Total a receber", f"R$ {total_receber:.2f}")

        st.markdown("---")

        for i, row in df.iterrows():
            status = "✅ Pago" if row["pago"] == "sim" else "❌ Pendente"

            col1, col2, col3 = st.columns([4, 2, 1])

            col1.write(f"**{row['cliente']}** - {row['produto']}")
            col1.write(f"{int(row['quantidade'])} un")
            col2.write(f"R$ {float(row['total']):.2f}")
            col2.write(status)

            if row["pago"] == "nao":
                if col3.button("Receber", key=f"receber_{row['id']}"):
                    contas_receber_ws.update_cell(i + 2, 7, "sim")
                    st.success("Pagamento recebido!")
                    st.rerun()

        st.markdown("---")
        st.subheader("Tabela completa")
        st.dataframe(df, use_container_width=True)