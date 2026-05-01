import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="Estoque + Financeiro", page_icon="🍰")

# =========================
# CONEXÃO
# =========================

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

# =========================
# FUNÇÕES
# =========================

def produtos_df():
    return pd.DataFrame(produtos_ws.get_all_records())

def mov_df():
    return pd.DataFrame(mov_ws.get_all_records())

def contas_df():
    return pd.DataFrame(contas_ws.get_all_records())

def novo_id(df):
    if df.empty:
        return 1
    return int(df["id"].max()) + 1

def estoque(produto_id):
    mov = mov_df()
    if mov.empty:
        return 0

    m = mov[mov["produto_id"] == produto_id]
    ent = m[m["tipo"] == "entrada"]["quantidade"].sum()
    sai = m[m["tipo"] == "saida"]["quantidade"].sum()

    return int(ent - sai)

# =========================
# MENU
# =========================

st.title("🍰 Sistema Completo")

menu = st.sidebar.selectbox("Menu", [
    "Produtos",
    "Entrada",
    "Venda",
    "Estoque",
    "Contas a pagar"
])

# =========================
# PRODUTOS
# =========================

if menu == "Produtos":
    nome = st.text_input("Sabor")
    custo = st.number_input("Custo", 0.0)
    preco = st.number_input("Preço", 0.0)

    if st.button("Salvar"):
        df = produtos_df()
        produtos_ws.append_row([novo_id(df), nome, custo, preco])
        st.success("Produto salvo")

# =========================
# ENTRADA + DÍVIDA
# =========================

elif menu == "Entrada":
    df = produtos_df()

    if df.empty:
        st.warning("Cadastre produto")
    else:
        nome = st.selectbox("Produto", df["nome"])
        qtd = st.number_input("Quantidade", 1)

        if st.button("Registrar entrada"):
            produto = df[df["nome"] == nome].iloc[0]

            # estoque
            mov_ws.append_row([
                int(produto["id"]),
                "entrada",
                int(qtd),
                float(produto["custo"]),
                datetime.now().strftime("%d/%m/%Y %H:%M")
            ])

            # dívida
            valor = qtd * float(produto["custo"])
            contas = contas_df()

            contas_ws.append_row([
                novo_id(contas),
                datetime.now().strftime("%d/%m/%Y %H:%M"),
                f"Compra {qtd}x {nome}",
                valor,
                "nao"
            ])

            st.success(f"Entrada + dívida R$ {valor:.2f}")

# =========================
# VENDA
# =========================

elif menu == "Venda":
    df = produtos_df()

    if df.empty:
        st.warning("Cadastre produto")
    else:
        nome = st.selectbox("Produto", df["nome"])
        produto = df[df["nome"] == nome].iloc[0]

        est = estoque(produto["id"])
        st.info(f"Estoque: {est}")

        qtd = st.number_input("Qtd venda", 1)

        if st.button("Vender"):
            if qtd > est:
                st.error("Sem estoque")
            else:
                mov_ws.append_row([
                    int(produto["id"]),
                    "saida",
                    int(qtd),
                    float(produto["preco"]),
                    datetime.now().strftime("%d/%m/%Y %H:%M")
                ])
                st.success("Venda registrada")

# =========================
# ESTOQUE
# =========================

elif menu == "Estoque":
    df = produtos_df()

    if not df.empty:
        lista = []
        for _, p in df.iterrows():
            lista.append({
                "Sabor": p["nome"],
                "Estoque": estoque(p["id"])
            })
        st.dataframe(pd.DataFrame(lista))

# =========================
# CONTAS A PAGAR
# =========================

elif menu == "Contas a pagar":

    df = contas_df()

    if df.empty:
        st.info("Sem dívidas")
    else:
        pend = df[df["pago"] == "nao"]
        total = pend["valor"].sum()

        st.metric("Total devendo", f"R$ {total:.2f}")

        st.markdown("### Dívidas")

        for i, row in df.iterrows():
            col1, col2 = st.columns([4,1])

            col1.write(f"{row['descricao']} - R$ {row['valor']}")

            if row["pago"] == "nao":
                if col2.button(f"Pagar {row['id']}"):
                    # atualizar planilha
                    contas_ws.update_cell(i+2, 5, "sim")
                    st.success("Pago!")
                    st.rerun()