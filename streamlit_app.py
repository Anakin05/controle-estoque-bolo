import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="Estoque Bolos", page_icon="🍰")

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

st.title("🍰 Estoque de Bolos no Pote")

menu = st.sidebar.selectbox(
    "Menu",
    ["Cadastrar produto", "Entrada", "Venda", "Estoque"]
)

def produtos_df():
    dados = produtos_ws.get_all_records()
    return pd.DataFrame(dados)

def mov_df():
    dados = mov_ws.get_all_records()
    return pd.DataFrame(dados)

def novo_id():
    df = produtos_df()
    if df.empty:
        return 1
    return int(df["id"].max()) + 1

def calcular_estoque(produto_id):
    mov = mov_df()
    if mov.empty:
        return 0

    mov_prod = mov[mov["produto_id"] == produto_id]

    entradas = mov_prod[mov_prod["tipo"] == "entrada"]["quantidade"].sum()
    saidas = mov_prod[mov_prod["tipo"] == "saida"]["quantidade"].sum()

    return int(entradas - saidas)

if menu == "Cadastrar produto":
    st.subheader("Cadastrar sabor")

    nome = st.text_input("Sabor")
    custo = st.number_input("Custo unitário", min_value=0.0, step=0.5)
    preco = st.number_input("Preço de venda", min_value=0.0, step=0.5)

    if st.button("Salvar"):
        produtos_ws.append_row([novo_id(), nome, custo, preco])
        st.success("Produto salvo!")

elif menu == "Entrada":
    st.subheader("Entrada de estoque")

    produtos = produtos_df()

    if produtos.empty:
        st.warning("Cadastre um produto primeiro.")
    else:
        nome = st.selectbox("Produto", produtos["nome"])
        qtd = st.number_input("Quantidade", min_value=1)

        if st.button("Registrar entrada"):
            produto = produtos[produtos["nome"] == nome].iloc[0]

            mov_ws.append_row([
                int(produto["id"]),
                "entrada",
                int(qtd),
                float(produto["custo"]),
                datetime.now().strftime("%d/%m/%Y %H:%M")
            ])

            st.success("Entrada registrada!")

elif menu == "Venda":
    st.subheader("Registrar venda")

    produtos = produtos_df()

    if produtos.empty:
        st.warning("Cadastre um produto primeiro.")
    else:
        nome = st.selectbox("Produto", produtos["nome"])
        produto = produtos[produtos["nome"] == nome].iloc[0]

        estoque = calcular_estoque(produto["id"])
        st.info(f"Estoque atual: {estoque}")

        qtd = st.number_input("Quantidade vendida", min_value=1)

        if st.button("Registrar venda"):
            if qtd > estoque:
                st.error("Estoque insuficiente.")
            else:
                mov_ws.append_row([
                    int(produto["id"]),
                    "saida",
                    int(qtd),
                    float(produto["preco"]),
                    datetime.now().strftime("%d/%m/%Y %H:%M")
                ])

                st.success("Venda registrada!")

elif menu == "Estoque":
    st.subheader("Estoque atual")

    produtos = produtos_df()

    if produtos.empty:
        st.info("Nenhum produto cadastrado.")
    else:
        lista = []

        for _, produto in produtos.iterrows():
            estoque = calcular_estoque(produto["id"])

            lista.append({
                "Sabor": produto["nome"],
                "Estoque": estoque,
                "Custo": produto["custo"],
                "Preço": produto["preco"]
            })

        st.dataframe(pd.DataFrame(lista), use_container_width=True)