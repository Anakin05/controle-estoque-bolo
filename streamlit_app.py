import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(
    page_title="Controle de Estoque - Bolos",
    page_icon="🍰",
    layout="wide"
)

# =========================
# CONEXÃO GOOGLE SHEETS
# =========================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credenciais.json",
    scope
)

client = gspread.authorize(creds)

planilha = client.open("Estoque Bolos")

aba_produtos = planilha.worksheet("produtos")
aba_mov = planilha.worksheet("movimentacoes")


# =========================
# FUNÇÕES
# =========================

def carregar_produtos():
    dados = aba_produtos.get_all_records()
    if not dados:
        return pd.DataFrame(columns=["id", "nome", "custo", "preco"])
    return pd.DataFrame(dados)


def carregar_movimentacoes():
    dados = aba_mov.get_all_records()
    if not dados:
        return pd.DataFrame(columns=["produto_id", "tipo", "quantidade", "valor_unitario", "data"])
    return pd.DataFrame(dados)


def proximo_id_produto():
    df = carregar_produtos()
    if df.empty:
        return 1
    return int(df["id"].max()) + 1


def estoque_atual(produto_id):
    mov = carregar_movimentacoes()

    if mov.empty:
        return 0

    mov_produto = mov[mov["produto_id"] == produto_id]

    entradas = mov_produto[mov_produto["tipo"] == "entrada"]["quantidade"].sum()
    saidas = mov_produto[mov_produto["tipo"] == "saida"]["quantidade"].sum()

    return int(entradas - saidas)


# =========================
# INTERFACE
# =========================

st.title("🍰 Controle de Estoque - Bolos no Pote")

menu = st.sidebar.selectbox(
    "Menu",
    ["Dashboard", "Produtos", "Entrada", "Venda", "Estoque", "Histórico"]
)


# =========================
# DASHBOARD
# =========================

if menu == "Dashboard":
    st.subheader("📊 Resumo geral")

    produtos = carregar_produtos()
    mov = carregar_movimentacoes()

    total_estoque = 0
    total_receita = 0
    total_custo = 0

    if not produtos.empty:
        for _, produto in produtos.iterrows():
            produto_id = produto["id"]
            custo = float(produto["custo"])
            preco = float(produto["preco"])

            estoque = estoque_atual(produto_id)
            total_estoque += estoque

            if not mov.empty:
                vendas = mov[
                    (mov["produto_id"] == produto_id) &
                    (mov["tipo"] == "saida")
                ]["quantidade"].sum()
            else:
                vendas = 0

            total_receita += vendas * preco
            total_custo += vendas * custo

    lucro = total_receita - total_custo

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Produtos cadastrados", len(produtos))
    col2.metric("Unidades em estoque", total_estoque)
    col3.metric("Receita total", f"R$ {total_receita:.2f}")
    col4.metric("Lucro total", f"R$ {lucro:.2f}")

    st.markdown("---")

    if produtos.empty:
        st.info("Nenhum produto cadastrado ainda.")
    else:
        dados = []

        for _, produto in produtos.iterrows():
            produto_id = produto["id"]
            nome = produto["nome"]
            custo = float(produto["custo"])
            preco = float(produto["preco"])
            estoque = estoque_atual(produto_id)

            if not mov.empty:
                vendidos = mov[
                    (mov["produto_id"] == produto_id) &
                    (mov["tipo"] == "saida")
                ]["quantidade"].sum()
            else:
                vendidos = 0

            dados.append({
                "Sabor": nome,
                "Estoque": estoque,
                "Vendidos": int(vendidos),
                "Custo": custo,
                "Preço": preco,
                "Lucro": vendidos * (preco - custo)
            })

        df_dashboard = pd.DataFrame(dados)
        st.dataframe(df_dashboard, use_container_width=True)


# =========================
# PRODUTOS
# =========================

elif menu == "Produtos":
    st.subheader("🍰 Cadastro de sabores")

    with st.form("form_produto"):
        nome = st.text_input("Nome do sabor")
        custo = st.number_input("Custo unitário", min_value=0.0, step=0.50)
        preco = st.number_input("Preço de venda", min_value=0.0, step=0.50)

        salvar = st.form_submit_button("Salvar produto")

    if salvar:
        if nome.strip() == "":
            st.error("Digite o nome do sabor.")
        elif preco <= 0:
            st.error("Digite um preço válido.")
        else:
            produtos = carregar_produtos()

            if not produtos.empty and nome.strip().lower() in produtos["nome"].str.lower().values:
                st.error("Esse sabor já existe.")
            else:
                novo_id = proximo_id_produto()

                aba_produtos.append_row([
                    novo_id,
                    nome.strip(),
                    custo,
                    preco
                ])

                st.success("Produto cadastrado com sucesso!")

    st.markdown("---")
    st.subheader("Produtos cadastrados")

    produtos = carregar_produtos()

    if produtos.empty:
        st.info("Nenhum produto cadastrado.")
    else:
        st.dataframe(produtos, use_container_width=True)


# =========================
# ENTRADA
# =========================

elif menu == "Entrada":
    st.subheader("📦 Entrada de estoque")

    produtos = carregar_produtos()

    if produtos.empty:
        st.warning("Cadastre um produto primeiro.")
    else:
        nomes = produtos["nome"].tolist()

        escolha = st.selectbox("Produto", nomes)
        quantidade = st.number_input("Quantidade adicionada", min_value=1)

        if st.button("Registrar entrada"):
            produto = produtos[produtos["nome"] == escolha].iloc[0]

            aba_mov.append_row([
                int(produto["id"]),
                "entrada",
                int(quantidade),
                float(produto["custo"]),
                datetime.now().strftime("%d/%m/%Y %H:%M")
            ])

            st.success("Entrada registrada!")


# =========================
# VENDA
# =========================

elif menu == "Venda":
    st.subheader("💰 Registrar venda")

    produtos = carregar_produtos()

    if produtos.empty:
        st.warning("Cadastre um produto primeiro.")
    else:
        nomes = produtos["nome"].tolist()

        escolha = st.selectbox("Produto", nomes)
        produto = produtos[produtos["nome"] == escolha].iloc[0]

        estoque = estoque_atual(produto["id"])

        st.info(f"Estoque atual: {estoque}")

        quantidade = st.number_input("Quantidade vendida", min_value=1)

        if st.button("Registrar venda"):
            if quantidade > estoque:
                st.error("Estoque insuficiente!")
            else:
                aba_mov.append_row([
                    int(produto["id"]),
                    "saida",
                    int(quantidade),
                    float(produto["preco"]),
                    datetime.now().strftime("%d/%m/%Y %H:%M")
                ])

                st.success("Venda registrada!")


# =========================
# ESTOQUE
# =========================

elif menu == "Estoque":
    st.subheader("📦 Estoque atual")

    produtos = carregar_produtos()

    if produtos.empty:
        st.info("Nenhum produto cadastrado.")
    else:
        dados = []

        for _, produto in produtos.iterrows():
            estoque = estoque_atual(produto["id"])

            dados.append({
                "Sabor": produto["nome"],
                "Estoque": estoque,
                "Custo": float(produto["custo"]),
                "Preço": float(produto["preco"]),
                "Status": "⚠️ Baixo" if estoque <= 3 else "OK"
            })

        st.dataframe(pd.DataFrame(dados), use_container_width=True)


# =========================
# HISTÓRICO
# =========================

elif menu == "Histórico":
    st.subheader("🧾 Histórico")

    produtos = carregar_produtos()
    mov = carregar_movimentacoes()

    if mov.empty:
        st.info("Sem movimentações ainda.")
    else:
        hist = mov.merge(
            produtos,
            left_on="produto_id",
            right_on="id",
            how="left"
        )

        hist = hist[["data", "nome", "tipo", "quantidade", "valor_unitario"]]
        hist.columns = ["Data", "Sabor", "Tipo", "Qtd", "Valor"]

        st.dataframe(hist, use_container_width=True)

        csv = hist.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Baixar CSV",
            csv,
            "historico.csv",
            "text/csv"
        )