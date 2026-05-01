import streamlit as st
import sqlite3

conn = sqlite3.connect('estoque.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    estoque INTEGER,
    custo REAL,
    preco REAL
)
''')
conn.commit()

st.title("🍰 Controle de Estoque")

menu = st.sidebar.selectbox("Menu", ["Cadastrar", "Estoque", "Venda"])

if menu == "Cadastrar":
    nome = st.text_input("Sabor")
    estoque = st.number_input("Quantidade", min_value=0)
    custo = st.number_input("Custo", min_value=0.0)
    preco = st.number_input("Preço", min_value=0.0)

    if st.button("Salvar"):
        c.execute("INSERT INTO produtos VALUES (NULL, ?, ?, ?, ?)",
                  (nome, estoque, custo, preco))
        conn.commit()
        st.success("Salvo!")

elif menu == "Estoque":
    produtos = c.execute("SELECT * FROM produtos").fetchall()

    for p in produtos:
        st.write(f"{p[1]} | Estoque: {p[2]} | R${p[4]}")

elif menu == "Venda":
    produtos = c.execute("SELECT * FROM produtos").fetchall()
    nomes = [p[1] for p in produtos]

    escolha = st.selectbox("Produto", nomes)
    qtd = st.number_input("Quantidade", min_value=1)

    if st.button("Vender"):
        for p in produtos:
            if p[1] == escolha:
                novo = p[2] - qtd
                c.execute("UPDATE produtos SET estoque=? WHERE id=?",
                          (novo, p[0]))
                conn.commit()
                st.success("Venda feita!")
