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


def produtos_df():
    dados = produtos_ws.get_all_records()
    return pd.DataFrame(dados)


def mov_df():
    dados = mov_ws.get_all_records()
    return pd.DataFrame(dados)


def contas_df():
    dados = contas_ws.get_all_records()
    return pd.DataFrame(dados)


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
        "Contas a pagar"
    ]
)


# =========================
# CADASTRO
# =========================

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


# =========================
# ENTRADA
# =========================

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

            valor_divida = int(qtd) * float(produto["custo"])
            contas = contas_df()

            contas_ws.append_row([
                novo_id(contas),
                datetime.now().strftime("%d/%m/%Y %H:%M"),
                f"Compra {int(qtd)}x {nome}",
                valor_divida,
                "nao"
            ])

            st.success(f"Entrada registrada! Dívida adicionada: R$ {valor_divida:.2f}")


# =========================
# VENDA
# =========================

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

        if st.button("Registrar venda"):
            if qtd > estoque_atual:
                st.error("Estoque insuficiente.")
            else:
                mov_ws.append_row([
                    int(produto["id"]),
                    "saida",
                    int(qtd),
                    float(produto["preco"]),
                    datetime.now().strftime("%d/%m/%Y %H:%M")
                ])

                st.success("Venda registrada com sucesso!")


# =========================
# ESTOQUE
# =========================

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


# =========================
# CONTAS A PAGAR
# =========================

elif menu == "Contas a pagar":
    st.subheader("Contas a pagar - Camila")

    df = contas_df()

    if df.empty:
        st.info("Nenhuma dívida registrada.")
    else:
        pendentes = df[df["pago"] == "nao"]

        total_devendo = pendentes["valor"].sum() if not pendentes.empty else 0

        st.metric("Total devendo", f"R$ {total_devendo:.2f}")

        st.markdown("---")
        st.subheader("Dívidas registradas")

        for i, row in df.iterrows():
            col1, col2, col3 = st.columns([4, 2, 1])

            status = "✅ Pago" if row["pago"] == "sim" else "❌ Pendente"

            col1.write(f"**{row['descricao']}**")
            col2.write(f"R$ {float(row['valor']):.2f} — {status}")

            if row["pago"] == "nao":
                if col3.button("PIX pago", key=f"pagar_{row['id']}"):
                    contas_ws.update_cell(i + 2, 5, "sim")
                    st.success("Pagamento confirmado!")
                    st.rerun()

        st.markdown("---")
        st.subheader("Tabela completa")

        st.dataframe(df, use_container_width=True)