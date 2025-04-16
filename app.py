import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events
import io
import os
import database as db

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Manutenção de Ar Condicionado",
    page_icon="❄️",
    layout="wide"
)

# Título principal
st.title("Dashboard de Manutenção de Ar Condicionado")
st.markdown("---")

# Função para carregar e processar os arquivos Excel
def processar_dados(arquivo_mensal, arquivo_equipamentos):
    try:
        # Carregar dados
        df_mensal = pd.read_excel(arquivo_mensal)
        df_equipamentos = pd.read_excel(arquivo_equipamentos)
        # --- Substituição direta dos nomes por setor ---
        SETOR_MAP_EXATO = {
            "Setor 3 GWSB e Vitor Hugo": ["Victor Hugo Nascimento Soares", "GWSB"],
            "Setor 1 Paco Ruhan e LUKREFRIGERAÇÃO": ["Pako Ruhan", "LUKREFRIGERACAO"],
            "Setor 5 RNCLIMATIZACAO e Robson": ["Robson Roque Bernardo", "RN CLIMATIZACAO"],
            "Setor 4 ADS e Wando": ["Wanderley Souza da Silva", "ADS"],
            "Setor 2 Renan e MVF": ["Renan de Souza Miranda", "MVF Climatizacao"],
        }
        def substituir_por_setor(colaborador):
            for setor, nomes in SETOR_MAP_EXATO.items():
                for nome in nomes:
                    if nome.lower() in str(colaborador).lower():
                        return setor
            return colaborador
        if 'Colaborador' in df_mensal.columns:
            df_mensal['Colaborador'] = df_mensal['Colaborador'].apply(substituir_por_setor)
        # ------------------------------------------------
        
        # Verificar se as colunas necessárias existem
        colunas_necessarias_mensal = ['Colaborador', 'Identificador', 'Cliente']
        colunas_necessarias_equipamentos = ['Identificador']
        
        for coluna in colunas_necessarias_mensal:
            if coluna not in df_mensal.columns:
                st.error(f"Coluna '{coluna}' não encontrada na planilha mensal.")
                return None, None
        for coluna in colunas_necessarias_equipamentos:
            if coluna not in df_equipamentos.columns:
                st.error(f"Coluna '{coluna}' não encontrada na planilha de equipamentos.")
                return None, None
        # --- Substituição direta dos nomes por setor ---
        SETOR_MAP_EXATO = {
            "Setor 3 GWSB e Vitor Hugo": ["Victor Hugo Nascimento Soares", "GWSB"],
            "Setor 1 Paco Ruhan e LUKREFRIGERAÇÃO": ["Pako Ruhan", "LUKREFRIGERACAO"],
            "Setor 5 RNCLIMATIZACAO e Robson": ["Robson Roque Bernardo", "RN CLIMATIZACAO"],
            "Setor 4 ADS e Wando": ["Wanderley Souza da Silva", "ADS"],
            "Setor 2 Renan e MVF": ["Renan de Souza Miranda", "MVF Climatizacao"],
        }
        def substituir_por_setor(colaborador):
            for setor, nomes in SETOR_MAP_EXATO.items():
                for nome in nomes:
                    if nome.lower() in str(colaborador).lower():
                        return setor
            return colaborador
        if 'Colaborador' in df_mensal.columns:
            df_mensal['Colaborador'] = df_mensal['Colaborador'].apply(substituir_por_setor)
        # ------------------------------------------------
        
        # Importar dados para o banco de dados
        sucesso = db.importar_dados_excel(arquivo_mensal, arquivo_equipamentos)
        
        if not sucesso:
            st.error("Erro ao importar dados para o banco de dados.")
            return None, None
            
        # Obter dados do banco de dados
        resumo_colaborador = db.obter_resumo_colaborador()
        total_por_colaborador = db.obter_total_por_colaborador()
        
        return resumo_colaborador, total_por_colaborador
        
    except Exception as e:
        st.error(f"Erro ao processar os arquivos: {str(e)}")
        return None, None

# Função para criar gráficos
def criar_graficos(resumo_colaborador, total_por_colaborador, colaborador_selecionado=None):
    if colaborador_selecionado and colaborador_selecionado != "Todos":
        # Filtrar dados para o colaborador selecionado
        dados_filtrados = resumo_colaborador[resumo_colaborador['Colaborador'] == colaborador_selecionado]
        
        # Gráfico de barras interativo para cliente x quantidade de máquinas
        fig_barras = px.bar(
            dados_filtrados,
            x='Cliente',
            y='Quantidade_Maquinas',
            title=f'Máquinas por Cliente - {colaborador_selecionado}',
            labels={'Cliente': 'Cliente', 'Quantidade_Maquinas': 'Quantidade de Máquinas'},
            color='Quantidade_Maquinas',
            color_continuous_scale='Blues',
            text='Quantidade_Maquinas'  # Mostrar valores nas barras
        )
        
        # Configuração para mostrar o valor ao passar o mouse
        fig_barras.update_traces(
            texttemplate='%{text}',
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Quantidade de Máquinas: %{y}<extra></extra>'
        )
        
        # Configurando comportamento de clique
        fig_barras.update_layout(clickmode='event+select')
        
        st.plotly_chart(fig_barras, use_container_width=True)
        
        # Tabela detalhada
        st.subheader(f"Clientes atendidos por {colaborador_selecionado}")
        st.dataframe(dados_filtrados, use_container_width=True)
        
        # Adicionar visualização detalhada de máquinas por cliente
        cliente_selecionado = st.selectbox("Selecione um Cliente para ver detalhes:", 
                                          ["Todos"] + sorted(dados_filtrados['Cliente'].unique().tolist()))
        
        if cliente_selecionado and cliente_selecionado != "Todos":
            # Filtrar para o cliente específico
            dados_cliente = dados_filtrados[dados_filtrados['Cliente'] == cliente_selecionado]
            
            st.subheader(f"Detalhes das Máquinas: {colaborador_selecionado} - {cliente_selecionado}")
            # Métricas destacando a quantidade
            st.metric("Quantidade de Máquinas", dados_cliente['Quantidade_Maquinas'].values[0])
            
            # Espaço para mostrar informações adicionais do equipamento se disponíveis
            st.info("Clique no botão abaixo para visualizar detalhes de cada máquina")
            
            if st.button(f"📊 Ver detalhes das máquinas de {cliente_selecionado}"):
                st.success(f"Quantidade total: {dados_cliente['Quantidade_Maquinas'].values[0]} máquinas")
                st.write("Lista de Identificadores associados:")
                # Buscar identificadores no banco de dados
                identificadores = db.obter_identificadores_cliente(colaborador_selecionado, cliente_selecionado)
                
                if identificadores:
                    for i, ident in enumerate(identificadores, 1):
                        st.code(f"{i}. {ident}", language="")
                else:
                    st.warning("Não foram encontrados identificadores para este cliente.")
                
        
    else:
        # Gráfico de barras interativo para todos os colaboradores
        fig_barras_total = px.bar(
            total_por_colaborador,
            x='Colaborador',
            y='Quantidade_Maquinas',
            title='Total de Máquinas por Colaborador',
            labels={'Colaborador': 'Colaborador', 'Quantidade_Maquinas': 'Total de Máquinas'},
            color='Quantidade_Maquinas',
            color_continuous_scale='Blues',
            text='Quantidade_Maquinas'  # Mostrar valores nas barras
        )
        
        # Configuração para mostrar o valor ao passar o mouse e ao clicar
        fig_barras_total.update_traces(
            texttemplate='%{text}',
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Total de Máquinas: %{y}<extra></extra>'
        )
        
        # Configurando comportamento de clique
        fig_barras_total.update_layout(clickmode='event+select')
        
        st.plotly_chart(fig_barras_total, use_container_width=True)
        
        # Gráfico de pizza interativo para distribuição percentual
        fig_pizza = px.pie(
            total_por_colaborador,
            values='Quantidade_Maquinas',
            names='Colaborador',
            title='Distribuição Percentual de Máquinas por Colaborador',
            hover_data=['Quantidade_Maquinas']
        )
        
        # Configuração para melhorar a visualização ao passar o mouse
        fig_pizza.update_traces(
            textposition='inside', 
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Quantidade: %{value}<br>Percentual: %{percent}<extra></extra>'
        )
        
        st.plotly_chart(fig_pizza, use_container_width=True)
        
        # Gráfico interativo para clique
        st.subheader("Clique em um Colaborador para ver detalhes:")
        fig_click = go.Figure()
        
        for i, row in total_por_colaborador.iterrows():
            fig_click.add_trace(go.Bar(
                x=[row['Colaborador']],
                y=[row['Quantidade_Maquinas']],
                name=row['Colaborador'],
                hoverinfo='text',
                text=f"{row['Colaborador']}: {row['Quantidade_Maquinas']} máquinas",
                marker_color=px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
            ))
        
        fig_click.update_layout(
            title="Selecione um Colaborador",
            xaxis_title="Colaborador",
            yaxis_title="Quantidade de Máquinas",
            showlegend=False,
            clickmode='event+select'
        )
        
        selected_points = plotly_events(fig_click, click_event=True)
        
        if selected_points:
            ponto = selected_points[0]
            indice = ponto['pointIndex']
            colab_clicado = total_por_colaborador.iloc[indice]['Colaborador']
            quant_maquinas = total_por_colaborador.iloc[indice]['Quantidade_Maquinas']
            
            st.success(f"Colaborador: {colab_clicado}")
            st.metric("Total de Máquinas", quant_maquinas)
            
            # Mostrar dados detalhados do colaborador
            dados_colab = resumo_colaborador[resumo_colaborador['Colaborador'] == colab_clicado]
            st.subheader(f"Clientes atendidos por {colab_clicado}")
            st.dataframe(dados_colab)
        
        # Tabela com o total (com clique habilitado)
        st.subheader("Total de Máquinas por Colaborador")
        st.dataframe(total_por_colaborador, use_container_width=True)

# Interface principal
with st.sidebar:
    st.header("Configurações")
    
    # Upload dos arquivos
    uploaded_mensal = st.file_uploader("Selecione a planilha mensal", type=["xls", "xlsx"])
    uploaded_equipamentos = st.file_uploader("Selecione a planilha de equipamentos", type=["xls", "xlsx"])
    
    # Botão para limpar banco de dados
    if st.button("🗑️ Limpar Dados Salvos"):
        # Criar tabelas novamente (limpa os dados)
        try:
            db.Base.metadata.drop_all(db.engine)
            db.Base.metadata.create_all(db.engine)
            st.sidebar.success("Dados anteriores foram removidos com sucesso.")
        except Exception as e:
            st.sidebar.error(f"Erro ao limpar dados: {str(e)}")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Instruções")
    st.sidebar.markdown("""
    1. Faça o upload das planilhas mensal e de equipamentos
    2. Os dados serão processados automaticamente e salvos no banco de dados
    3. Utilize o filtro para selecionar um colaborador específico
    4. Os gráficos e tabelas serão atualizados com base na seleção
    5. Dados ficam salvos mesmo ao fechar o navegador
    """)

# Verificar se há dados no banco ou se os arquivos foram carregados
dados_existentes = db.verificar_dados_existentes()

if uploaded_mensal is not None and uploaded_equipamentos is not None:
    # Processar os dados dos arquivos
    resumo_colaborador, total_por_colaborador = processar_dados(uploaded_mensal, uploaded_equipamentos)
    dados_processados = True
elif dados_existentes:
    # Carregar dados do banco de dados
    resumo_colaborador = db.obter_resumo_colaborador()
    total_por_colaborador = db.obter_total_por_colaborador()
    dados_processados = True
    st.info("Carregando dados salvos anteriormente no banco de dados. Para atualizar, faça upload das planilhas novamente.")
else:
    dados_processados = False

# Se tiver dados para mostrar (do upload ou do banco)
if dados_processados and resumo_colaborador is not None and total_por_colaborador is not None:
    # Exibir estatísticas resumidas
    st.success("Dados carregados com sucesso!")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Colaboradores", len(total_por_colaborador))
    with col2:
        st.metric("Total de Clientes", resumo_colaborador['Cliente'].nunique())
    with col3:
        st.metric("Total de Máquinas", total_por_colaborador['Quantidade_Maquinas'].sum())
    
    st.markdown("---")
    
    # Adicionar filtro para selecionar colaborador
    lista_colaboradores = ["Todos"] + sorted(resumo_colaborador['Colaborador'].unique().tolist())
    colaborador_selecionado = st.selectbox("Selecione um Colaborador:", lista_colaboradores)
    
    st.markdown("---")
    
    # Criar gráficos baseados na seleção
    criar_graficos(resumo_colaborador, total_por_colaborador, colaborador_selecionado)
    
    # Exibir dados detalhados
    with st.expander("Ver Dados Detalhados"):
        st.dataframe(resumo_colaborador)

else:
    # Exibir mensagem solicitando o upload dos arquivos
    st.info("Por favor, faça o upload das planilhas mensal e de equipamentos para visualizar o dashboard.")
    
    # Mostrar exemplo de como os dados devem estar organizados
    with st.expander("Como os dados devem estar organizados nas planilhas?"):
        st.markdown("""
        ### Planilha Mensal (mensal.xls)
        Deve conter as seguintes colunas:
        - **Colaborador**: Nome do colaborador que realizou o serviço
        - **Identificador**: Código que identifica o equipamento (mesmo da planilha de equipamentos)
        - **Cliente**: Nome do cliente atendido
        
        ### Planilha de Equipamentos (equipamentos.xls)
        Deve conter a coluna:
        - **Identificador**: Código que identifica o equipamento
        - Outras informações sobre o equipamento (opcional)
        
        O sistema irá fazer o relacionamento entre as duas planilhas utilizando a coluna "Identificador" e salvar no banco de dados.
        """)
