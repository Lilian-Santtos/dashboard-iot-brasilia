"""Painel de análise do Projeto Integrador HMDC680.
Hospedagem: Streamlit Community Cloud. Entrada: leituras_710.csv.
"""
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Monitoramento Ambiental | HMDC680", page_icon="🌡️", layout="wide")

@st.cache_data
def carregar():
    caminho = Path(__file__).parent / "leituras_710.csv"
    if not caminho.exists():
        st.error("Não foi encontrado 'leituras_710.csv' na pasta do aplicativo.")
        st.stop()
    df = pd.read_csv(caminho)
    esperadas = {"data_hora", "temperatura_c", "umidade_pct"}
    if not esperadas.issubset(df.columns):
        st.error("O CSV deve ter data_hora, temperatura_c e umidade_pct.")
        st.stop()
    df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")
    df["temperatura_c"] = pd.to_numeric(df["temperatura_c"], errors="coerce")
    df["umidade_pct"] = pd.to_numeric(df["umidade_pct"], errors="coerce")
    if df[list(esperadas)].isna().any().any():
        st.error("Há registros com datas ou medidas inválidas.")
        st.stop()
    df = df.sort_values("data_hora").reset_index(drop=True)
    if df["data_hora"].duplicated().any():
        st.warning("A base contém horários duplicados.")
    quente = df["temperatura_c"] >= 30
    umidade_alerta = (df["umidade_pct"] < 40) | (df["umidade_pct"] > 75)
    df["status"] = "NORMAL"
    df.loc[quente & ~umidade_alerta, "status"] = "ALERTA_TEMPERATURA"
    df.loc[~quente & umidade_alerta, "status"] = "ALERTA_UMIDADE"
    df.loc[quente & umidade_alerta, "status"] = "ALERTA_MULTIPLO"
    df["dia"] = df["data_hora"].dt.date
    return df

base = carregar()
st.title("🌡️ Monitoramento Ambiental Inteligente")
st.caption("Projeto Integrador HMDC680 • Brasília/DF • Temperatura e umidade relativa do ar")

menor, maior = base["dia"].min(), base["dia"].max()
st.sidebar.header("Filtros")
periodo = st.sidebar.date_input("Período", value=(menor, maior), min_value=menor, max_value=maior)
possiveis = ["NORMAL", "ALERTA_UMIDADE", "ALERTA_TEMPERATURA", "ALERTA_MULTIPLO"]
estados = st.sidebar.multiselect("Tipos de registro", possiveis, default=possiveis)
st.sidebar.caption("Regras didáticas: temperatura ≥ 30 °C; umidade < 40% ou > 75%.")

if not isinstance(periodo, (tuple, list)) or len(periodo) != 2:
    st.info("Selecione as datas inicial e final na barra lateral.")
    st.stop()

filtro = base.loc[
    (base["dia"] >= periodo[0])
    & (base["dia"] <= periodo[1])
    & base["status"].isin(estados)
].copy()
if filtro.empty:
    st.warning("Nenhum registro encontrado. Altere os filtros.")
    st.stop()

n_alertas = int((filtro["status"] != "NORMAL").sum())
a, b, c, d = st.columns(4)
a.metric("Registros", f"{len(filtro)}")
b.metric("Temperatura média", f"{filtro['temperatura_c'].mean():.2f} °C".replace(".", ","))
c.metric("Umidade média", f"{filtro['umidade_pct'].mean():.2f}%".replace(".", ","))
d.metric("Em alerta", f"{n_alertas} ({n_alertas / len(filtro):.1%})".replace(".", ","))

aba1, aba2, aba3 = st.tabs(["Séries temporais", "Alertas e estatísticas", "Registros"])
with aba1:
    st.subheader("Variação de temperatura")
    st.line_chart(filtro.set_index("data_hora")["temperatura_c"], y_label="Temperatura (°C)")
    st.subheader("Variação de umidade")
    st.line_chart(filtro.set_index("data_hora")["umidade_pct"], y_label="Umidade relativa (%)")
with aba2:
    st.subheader("Quantidade de registros por situação")
    contagens = filtro["status"].value_counts().reindex(possiveis, fill_value=0)
    st.bar_chart(contagens, y_label="Quantidade")
    if len(filtro) >= 2:
        st.write(f"**Correlação de Pearson:** {filtro['temperatura_c'].corr(filtro['umidade_pct']):.3f}".replace(".", ","))
    st.subheader("Resumo diário")
    resumo = filtro.groupby("dia").agg(
        leituras=("temperatura_c", "size"),
        temperatura_media=("temperatura_c", "mean"),
        temperatura_min=("temperatura_c", "min"),
        temperatura_max=("temperatura_c", "max"),
        umidade_media=("umidade_pct", "mean"),
    ).round(2)
    st.dataframe(resumo, use_container_width=True)
with aba3:
    st.subheader("Base com classificação calculada")
    dados = filtro[["data_hora", "temperatura_c", "umidade_pct", "status"]]
    st.dataframe(dados, use_container_width=True, hide_index=True)
    st.download_button(
        "Baixar registros filtrados (CSV)",
        data=dados.to_csv(index=False).encode("utf-8-sig"),
        file_name="leituras_filtradas.csv",
        mime="text/csv",
    )

st.caption("Indicadores calculados com a base CSV disponibilizada para análise. Os alertas usam limites definidos no projeto.")
