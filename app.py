# app.py - Interface Web da AgroNação
import streamlit as st
from agro_ia import AgroIA
from modulo_campo import ModuloCampo

# Configuração da página Web
st.set_page_config(
    page_title="AgroNação - Sistema Operativo Agropecuário",
    page_icon="🌾",
    layout="wide"
)

# Estilo visual moderno e tecnológico
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    .stButton>button { background-color: #238636; color: white; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# Inicializa a IA e o Módulo de Campo
if 'ia' not in st.session_state:
    st.session_state.ia = AgroIA()
if 'historico' not in st.session_state:
    st.session_state.historico = []

# Cabeçalho Principal
st.title("🌾 AgroNação")
st.caption('"Do solo ao mercado. Com a Agro a gerir tudo."')
st.success("● Sistema Operativo Conectado | IA Agro 100% Ativa (Angola)")

# Layout em Colunas (Painel + Chat)
col_painel, col_chat = st.columns([1, 2])

with col_painel:
    st.subheader("📊 Painel de Monitorização")
    
    # Cartões de Métricas do Campo
    st.metric(label="Humidade Média do Solo", value="68%", delta="Ideal")
    st.metric(label="Sensores Ativos", value="12 / 12", delta="Conectados")
    st.metric(label="Alertas de Pragas", value="1 Ativo", delta="-1 Preventivo", delta_color="inverse")
    
    st.divider()
    
    st.subheader("⚙️ Ações Rápidas")
    parcela_sel = st.selectbox("Selecionar Parcela para Análise:", ["1", "2", "3"])
    if st.button("🔍 Ver Dados do Sensor"):
        campo = ModuloCampo()
        res = campo.ler_sensores(parcela_sel)
        st.info(res)
        
    if st.button("🔬 Diagnóstico de Pragas"):
        campo = ModuloCampo()
        res = campo.verificar_pragas()
        st.warning(res)

with col_chat:
    st.subheader("🤖 Conversar com a Agro")
    
    # Exibe o histórico de conversas
    for mensagem in st.session_state.historico:
        with st.chat_message(mensagem["autor"]):
            st.write(mensagem["texto"])
            
    # Caixa de entrada de texto do utilizador
    prompt = st.chat_input("Pergunte algo à Agro (ex: 'Qual o estado da exploração hoje?')...")
    
    if prompt:
        # Regista mensagem do utilizador
        st.session_state.historico.append({"autor": "user", "texto": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        # Resposta da IA Agro
        resposta = st.session_state.ia.processar_comando(prompt)
        st.session_state.historico.append({"autor": "assistant", "texto": resposta})
        with st.chat_message("assistant"):
            st.write(resposta)