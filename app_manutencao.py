import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
from datetime import datetime
import sqlite3
import json
import pytz  # Importar pytz para lidar com fusos horários

# Definir variáveis globais para colunas de fotos a excluir
FOTO_COLUMNS = [
    'FOTO 1 - ANTES - Tampa da Maquina Aberta com os Filtros SUJOS Instalados na Maquina.',
    'FOTO 2 - ANTES - Foto com Etiqueta QRCODE (Mar Brasil) da Maquina.',
    'FOTO 3 - ANTES - Foto com Etiqueta técnica da maquina (Etiqueta de Identificação do Fabricante na Evaporadora).',
    'Foto 1 - DEPOIS - Tampa da Maquina Aberta com os Filtros LIMPOS Instalados na Maquina.',
    'Foto 2 - DEPOIS - Limpeza geral da maquina e display de funcionamento (Se houver display)'
]

# Definir tipos de manutenção
TIPO_MANUTENCAO_MENSAL = 'mensal'
TIPO_MANUTENCAO_SEMESTRAL = 'semestral'
TIPO_MANUTENCAO_CORRETIVA = 'corretiva'

# Função para obter colunas excluídas (incluindo colunas de fotos)
def get_excluded_columns():
    return ['Colaborador', 'Cliente', 'Identificador', 'Manutencao_Realizada'] + FOTO_COLUMNS

# Configuração da página
st.set_page_config(
    page_title="Sistema de Verificação de Manutenção de Ar Condicionado",
    page_icon="🔧",
    layout="wide"
)

# Título principal
st.title("Painel dos Oficiais e Credenciados")
st.markdown("---")

# Função para criar ou conectar ao banco de dados SQLite
def get_db_connection():
    conn = sqlite3.connect('manutencao.db')
    
    # Desativar temporariamente a verificação de chaves estrangeiras para permitir
    # a exclusão das tabelas sem problemas
    conn.execute("PRAGMA foreign_keys = OFF")
    
    # Create or recreate tables with the correct structure
    # Vamos apenas criar as tabelas sem tentar excluí-las primeiro
    conn.execute('''
    CREATE TABLE IF NOT EXISTS planilha_mensal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_upload TEXT,
        dados TEXT,
        tipo_manutencao TEXT DEFAULT 'mensal'
    )
    ''')
    conn.execute('''
    CREATE TABLE IF NOT EXISTS planilha_semestral (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_upload TEXT,
        dados TEXT,
        tipo_manutencao TEXT DEFAULT 'semestral'
    )
    ''')
    conn.execute('''
    CREATE TABLE IF NOT EXISTS planilha_corretiva (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_upload TEXT,
        dados TEXT,
        tipo_manutencao TEXT DEFAULT 'corretiva'
    )
    ''')
    conn.execute('''
    CREATE TABLE IF NOT EXISTS equipamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_upload TEXT,
        dados TEXT
    )
    ''')
    conn.execute('''
    CREATE TABLE IF NOT EXISTS manutencoes_realizadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_upload TEXT,
        identificador TEXT,
        colaborador TEXT,
        cliente TEXT,
        data_manutencao TEXT,
        tipo_manutencao TEXT,
        cumprimento TEXT
    )
    ''')
    conn.execute('''
    CREATE TABLE IF NOT EXISTS ultima_atualizacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT
    )
    ''')
    return conn

# Função para obter a data e hora atual no fuso horário de São Paulo
def obter_data_hora_sao_paulo():
    # Definir o fuso horário de São Paulo
    fuso_horario_sp = pytz.timezone('America/Sao_Paulo')
    
    # Obter a data e hora atual no fuso horário UTC
    data_hora_utc = datetime.now(pytz.UTC)
    
    # Converter para o fuso horário de São Paulo
    data_hora_sp = data_hora_utc.astimezone(fuso_horario_sp)
    
    # Formatar a data e hora
    return data_hora_sp.strftime('%d/%m/%Y %H:%M:%S')

# Função para salvar a data e hora da última atualização
def salvar_ultima_atualizacao():
    conn = get_db_connection()
    
    # Obter data e hora no fuso horário de São Paulo
    data_hora_atual = obter_data_hora_sao_paulo()
    
    # Limpar tabela antes de inserir novo registro
    conn.execute("DELETE FROM ultima_atualizacao")
    
    # Inserir nova data/hora
    conn.execute(
        "INSERT INTO ultima_atualizacao (data_hora) VALUES (?)",
        (data_hora_atual,)
    )
    conn.commit()
    conn.close()
    return data_hora_atual

# Função para obter a data e hora da última atualização
def obter_ultima_atualizacao():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT data_hora FROM ultima_atualizacao ORDER BY id DESC LIMIT 1")
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado:
        return resultado[0]
    else:
        return "Nenhuma atualização registrada"

# Função para salvar a planilha no banco de dados de acordo com o tipo
def salvar_planilha(df, tipo_manutencao=TIPO_MANUTENCAO_MENSAL):
    conn = get_db_connection()
    # Converter o DataFrame para JSON
    df_json = df.to_json(orient='records')
    
    # Determinar a tabela correta com base no tipo de manutenção
    tabela = None
    if tipo_manutencao == TIPO_MANUTENCAO_MENSAL:
        tabela = "planilha_mensal"
    elif tipo_manutencao == TIPO_MANUTENCAO_SEMESTRAL:
        tabela = "planilha_semestral"
    elif tipo_manutencao == TIPO_MANUTENCAO_CORRETIVA:
        tabela = "planilha_corretiva"
    else:
        # Se não for um tipo conhecido, usar mensal como padrão
        tabela = "planilha_mensal"
    
    # Salvar no banco de dados
    conn.execute(
        f"INSERT INTO {tabela} (data_upload, dados, tipo_manutencao) VALUES (?, ?, ?)",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), df_json, tipo_manutencao)
    )
    conn.commit()
    conn.close()

# Função para salvar a planilha mensal no banco de dados (mantida para compatibilidade)
def salvar_planilha_mensal(df):
    salvar_planilha(df, TIPO_MANUTENCAO_MENSAL)

# Função para salvar a planilha de equipamentos no banco de dados
def salvar_equipamentos(df):
    conn = get_db_connection()
    # Converter o DataFrame para JSON
    df_json = df.to_json(orient='records')
    # Salvar no banco de dados
    conn.execute(
        "INSERT INTO equipamentos (data_upload, dados) VALUES (?, ?)",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), df_json)
    )
    conn.commit()
    conn.close()

# Função para obter a planilha mensal mais recente
def obter_planilha_mensal():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT dados FROM planilha_mensal ORDER BY id DESC LIMIT 1")
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado:
        # Converter JSON de volta para DataFrame
        return pd.read_json(resultado[0], orient='records')
    return None

# Função para obter a planilha de equipamentos mais recente
def obter_equipamentos():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT dados FROM equipamentos ORDER BY id DESC LIMIT 1")
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado:
        # Converter JSON de volta para DataFrame
        return pd.read_json(resultado[0], orient='records')
    return None

# Função para combinar dados da planilha mensal com a de equipamentos
def combinar_dados():
    df_mensal = obter_planilha_mensal()
    df_equipamentos = obter_equipamentos()
    
    if df_mensal is None or df_equipamentos is None:
        return None
    
    # Garantir que ambos os dataframes tenham a coluna 'Identificador'
    if 'Identificador' not in df_mensal.columns or 'Identificador' not in df_equipamentos.columns:
        st.error("As planilhas devem conter a coluna 'Identificador' para a combinação de dados.")
        return None
    
    # Combinar os dados com base no identificador
    df_combinado = pd.merge(
        df_mensal,
        df_equipamentos,
        on='Identificador',
        how='left',
        suffixes=('', '_equip')
    )
    
    return df_combinado

# Função para registrar manutenções realizadas
def registrar_manutencao(df_diaria, tipo_manutencao=TIPO_MANUTENCAO_MENSAL):
    conn = None
    try:
        conn = get_db_connection()
        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Obter registros da planilha inicial para o tipo de manutenção atual
        cursor = conn.cursor()
        
        # Verificar qual tabela consultar para obter os dados iniciais
        tabela_inicial = "planilha_mensal"
        if tipo_manutencao == TIPO_MANUTENCAO_SEMESTRAL:
            tabela_inicial = "planilha_semestral"
        elif tipo_manutencao == TIPO_MANUTENCAO_CORRETIVA:
            tabela_inicial = "planilha_corretiva"
        
        # Consultar dados iniciais mais recentes
        cursor.execute(f"SELECT dados FROM {tabela_inicial} ORDER BY id DESC LIMIT 1")
        resultado_inicial = cursor.fetchone()
        
        if resultado_inicial:
            # Carregar dados iniciais
            import io
            try:
                df_inicial = pd.read_json(io.StringIO(resultado_inicial[0]), orient='records')
            except Exception as json_err:
                st.error(f"Erro ao carregar JSON: {str(json_err)}")
                # Tentar método alternativo
                dados_json = resultado_inicial[0]
                if isinstance(dados_json, str):
                    df_inicial = pd.read_json(dados_json, orient='records')
            
            # Para cada registro na planilha diária (que representa manutenção realizada)
            st.info(f"Processando {len(df_diaria)} registros da planilha diária...")
            registros_processados = 0
            
            for index, row in df_diaria.iterrows():
                # Extrair identificador da planilha diária
                identificador = str(row.get('Identificador', ''))
                data_manutencao = str(row.get('Data', datetime.now().strftime('%Y-%m-%d')))
                
                # Se não tem identificador, pular
                if not identificador or identificador == 'nan' or identificador == 'None':
                    continue
                
                # Verificar se este identificador existe na planilha inicial
                # Usar apenas o identificador como chave para registrar manutenções
                # Isso resolve o problema de duplicidade
                if 'Identificador' in df_inicial.columns:
                    # Verificar se já existe registro para este identificador
                    cursor.execute(
                        "SELECT COUNT(*) FROM manutencoes_realizadas WHERE identificador = ? AND tipo_manutencao = ?",
                        (identificador, tipo_manutencao)
                    )
                    ja_registrado = cursor.fetchone()[0] > 0
                    
                    if ja_registrado:
                        # Já existe registro para este identificador, pular
                        continue
                    
                    # Encontrar todos os registros correspondentes na planilha inicial com este identificador
                    registros_iniciais = df_inicial[df_inicial['Identificador'].astype(str) == identificador]
                    
                    if not registros_iniciais.empty:
                        # Para cada registro inicial correspondente, pegar colaborador e cliente
                        for idx, reg_inicial in registros_iniciais.iterrows():
                            colaborador = str(reg_inicial.get('Colaborador', ''))
                            cliente = str(reg_inicial.get('Cliente', ''))
                            
                            # Marcar como manutenção realizada para este identificador
                            conn.execute(
                                "INSERT INTO manutencoes_realizadas (data_upload, identificador, colaborador, cliente, data_manutencao, tipo_manutencao, cumprimento) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (data_atual, identificador, colaborador, cliente, data_manutencao, tipo_manutencao, 'Sim')
                            )
                            registros_processados += 1
                    else:
                        # Se não encontrou na planilha inicial, pegar cliente e colaborador da planilha diária
                        colaborador = str(row.get('Colaborador', ''))
                        cliente = str(row.get('Cliente', ''))
                        
                        # Usar dados da planilha diária se estiverem disponíveis
                        if colaborador and cliente and colaborador != 'nan' and cliente != 'nan' and colaborador != 'None' and cliente != 'None':
                            conn.execute(
                                "INSERT INTO manutencoes_realizadas (data_upload, identificador, colaborador, cliente, data_manutencao, tipo_manutencao, cumprimento) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (data_atual, identificador, colaborador, cliente, data_manutencao, tipo_manutencao, 'Sim')
                            )
                            registros_processados += 1
            
            st.success(f"Total de {registros_processados} manutenções registradas com sucesso!")
        else:
            # Se não encontrou registros iniciais, continuar com o processo antigo
            st.warning("Não foram encontrados dados iniciais. Processando apenas com dados da planilha diária.")
            for index, row in df_diaria.iterrows():
                identificador = str(row.get('Identificador', ''))
                colaborador = str(row.get('Colaborador', ''))
                cliente = str(row.get('Cliente', ''))
                data_manutencao = str(row.get('Data', datetime.now().strftime('%Y-%m-%d')))
                
                if identificador and colaborador and cliente and identificador != 'nan' and colaborador != 'nan' and cliente != 'nan':
                    # Verificar se já existe registro para este identificador
                    cursor.execute(
                        "SELECT COUNT(*) FROM manutencoes_realizadas WHERE identificador = ? AND tipo_manutencao = ?",
                        (identificador, tipo_manutencao)
                    )
                    ja_registrado = cursor.fetchone()[0] > 0
                    
                    if not ja_registrado:
                        conn.execute(
                            "INSERT INTO manutencoes_realizadas (data_upload, identificador, colaborador, cliente, data_manutencao, tipo_manutencao, cumprimento) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (data_atual, identificador, colaborador, cliente, data_manutencao, tipo_manutencao, 'Sim')
                        )
        
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao registrar manutenções: {str(e)}")
        if conn:
            try:
                conn.close()
            except:
                pass

# Função para verificar se um equipamento já recebeu manutenção
def verificar_manutencao_realizada(identificador, colaborador=None, cliente=None, tipo_manutencao=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construir a consulta base (usar apenas identificador, sem depender de cliente e colaborador)
        consulta = "SELECT COUNT(*) FROM manutencoes_realizadas WHERE identificador = ?"
        parametros = [identificador]
        
        # Adicionar filtro por tipo de manutenção, se fornecido
        if tipo_manutencao and tipo_manutencao in [TIPO_MANUTENCAO_MENSAL, TIPO_MANUTENCAO_SEMESTRAL, TIPO_MANUTENCAO_CORRETIVA]:
            consulta += " AND tipo_manutencao = ?"
            parametros.append(tipo_manutencao)
        
        # Executar a consulta
        cursor.execute(consulta, parametros)
        resultado = cursor.fetchone()
        conn.close()
        return bool(resultado and resultado[0] > 0)
    except Exception as e:
        st.error(f"Erro ao verificar manutenção: {str(e)}")
        return False

# Função para processar os dados das planilhas
def processar_dados_manutencao(arquivo_mensal=None, arquivo_equipamentos=None, arquivo_diario=None, usar_armazenado=False):
    try:
        # Se usar_armazenado for True, carregar dados do banco de dados
        if usar_armazenado:
            # Obter planilha mensal mais recente
            df_mensal = obter_planilha_mensal()
            # Obter planilha de equipamentos mais recente
            df_equipamentos = obter_equipamentos()
            
            if df_mensal is not None and df_equipamentos is not None:
                # Combinar dados
                df_combinado = combinar_dados()
                
                if df_combinado is not None:
                    # Atualizar a data e hora da última atualização
                    salvar_ultima_atualizacao()
                    
                    # Armazenar na sessão
                    st.session_state['dados_carregados'] = df_combinado
                    return df_combinado
                else:
                    st.error("Erro ao combinar os dados.")
                    return None
            else:
                st.error("Não foi possível carregar os dados armazenados.")
                return None
    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")
        return None
        
    # Processar planilha mensal e de equipamentos
    if usar_armazenado:
        df_combinado = combinar_dados()
        if df_combinado is None and (arquivo_mensal is None or arquivo_equipamentos is None):
            st.error("Não há dados armazenados. Faça o upload das planilhas mensal e de equipamentos.")
            return None
    else:
        # Se foram fornecidos arquivos para a planilha mensal e de equipamentos
        if arquivo_mensal is not None and arquivo_equipamentos is not None:
            try:
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
                
                # Verificar colunas necessárias
                if 'Identificador' not in df_mensal.columns:
                    st.error("A planilha mensal deve conter a coluna 'Identificador'.")
                    return None
                
                if 'Identificador' not in df_equipamentos.columns:
                    st.error("A planilha de equipamentos deve conter a coluna 'Identificador'.")
                    return None
                
                # Limpar a tabela de manutenções realizadas para que todas comecem como "não realizadas"
                try:
                    conn = get_db_connection()
                    # Verificar se a tabela existe antes de tentar excluir os dados
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='manutencoes_realizadas'")
                    if cursor.fetchone():
                        conn.execute("DELETE FROM manutencoes_realizadas")
                    conn.commit()
                    conn.close()
                except Exception as e:
                    st.error(f"Erro ao limpar tabela de manutenções: {str(e)}")
                
                # Salvar ambas as planilhas no banco de dados
                salvar_planilha_mensal(df_mensal)
                salvar_equipamentos(df_equipamentos)
                
                # Combinar os dados
                df_combinado = pd.merge(
                    df_mensal,
                    df_equipamentos,
                    on='Identificador',
                    how='left',
                    suffixes=('', '_equip')
                )
            except Exception as e:
                st.error(f"Erro ao processar as planilhas: {str(e)}")
                return None
        else:
            # Se não foram fornecidos os arquivos necessários e não estamos usando dados armazenados
            return None
    
    # Se o arquivo diário foi fornecido, processá-lo
    if arquivo_diario is not None:
        try:
            df_diario = pd.read_excel(arquivo_diario)
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
            if 'Colaborador' in df_diario.columns:
                df_diario['Colaborador'] = df_diario['Colaborador'].apply(substituir_por_setor)
            # ------------------------------------------------
            # Registrar as manutenções realizadas no banco de dados
            registrar_manutencao(df_diario)
        except Exception as e:
            st.error(f"Erro ao processar a planilha diária: {str(e)}")
            return None
    
    # Se chegou até aqui, pelo menos temos os dados combinados
    if 'df_combinado' in locals() and df_combinado is not None:
        # Atualizar a data e hora da última atualização
        salvar_ultima_atualizacao()
        
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
        if 'Colaborador' in df_combinado.columns:
            df_combinado['Colaborador'] = df_combinado['Colaborador'].apply(substituir_por_setor)
        # ------------------------------------------------
        # Adicionar status de manutenção para cada identificador
        for index, row in df_combinado.iterrows():
            identificador = str(row.get('Identificador', ''))
            colaborador = str(row.get('Colaborador', ''))
            cliente = str(row.get('Cliente', ''))
            df_combinado.at[index, 'Manutencao_Realizada'] = verificar_manutencao_realizada(identificador, colaborador, cliente)
        return df_combinado
    else:
        # Se não temos os dados combinados, tentar usar os dados armazenados
        if usar_armazenado:
            df_combinado = combinar_dados()
            if df_combinado is not None:
                # Atualizar a data e hora da última atualização
                salvar_ultima_atualizacao()
                
                # Adicionar status de manutenção para cada identificador
                for index, row in df_combinado.iterrows():
                    identificador = str(row.get('Identificador', ''))
                    colaborador = str(row.get('Colaborador', ''))
                    cliente = str(row.get('Cliente', ''))
                    df_combinado.at[index, 'Manutencao_Realizada'] = verificar_manutencao_realizada(
                        identificador, colaborador, cliente
                    )
                
                return df_combinado
    
    return None

# Interface principal
with st.sidebar:
    st.header("Configurações")
    
    # Tabs para upload das planilhas
    tab1, tab2 = st.tabs(["Configuração Inicial", "Atualização Diária"])
    
    with tab1:
        st.subheader("Configuração Inicial do Mês")
        st.write("Este passo é realizado apenas uma vez no início do mês")
        
        # Verificar se já existem dados no banco de dados
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar planilha mensal
        cursor.execute("SELECT COUNT(*) FROM planilha_mensal")
        tem_mensal = cursor.fetchone()[0] > 0
        
        # Verificar planilha semestral
        cursor.execute("SELECT COUNT(*) FROM planilha_semestral")
        tem_semestral = cursor.fetchone()[0] > 0
        
        # Verificar planilha corretiva
        cursor.execute("SELECT COUNT(*) FROM planilha_corretiva")
        tem_corretiva = cursor.fetchone()[0] > 0
        
        # Verificar equipamentos
        cursor.execute("SELECT COUNT(*) FROM equipamentos")
        tem_equipamentos = cursor.fetchone()[0] > 0
        
        conn.close()
        
        # Mostrar status das planilhas carregadas
        st.markdown("### Status das Planilhas")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"- Mensal: {'✅ Carregada' if tem_mensal else '❌ Não carregada'}")
            st.markdown(f"- Semestral: {'✅ Carregada' if tem_semestral else '❌ Não carregada'}")
        with col2:
            st.markdown(f"- Corretiva: {'✅ Carregada' if tem_corretiva else '❌ Não carregada'}")
            st.markdown(f"- Equipamentos: {'✅ Carregada' if tem_equipamentos else '❌ Não carregada'}")
        
        st.markdown("---")
        st.write("Carregue novas planilhas apenas se precisar substituir as existentes:")
        
        # Definir inputs para todas as planilhas
        st.markdown("### Selecione todas as planilhas necessárias")
        
        uploaded_mensal = st.file_uploader("Selecione a planilha MENSAL", type=["xls", "xlsx"], key="planilha_mensal")
        uploaded_semestral = st.file_uploader("Selecione a planilha SEMESTRAL", type=["xls", "xlsx"], key="planilha_semestral")
        uploaded_corretiva = st.file_uploader("Selecione a planilha CORRETIVA", type=["xls", "xlsx"], key="planilha_corretiva")
        uploaded_equipamentos = st.file_uploader("Selecione a planilha de EQUIPAMENTOS", type=["xls", "xlsx"], key="equipamentos")
        
        if st.button("Carregar e Salvar Todas as Planilhas"):
            with st.spinner("Processando todas as planilhas..."):
                # Limpar todas as tabelas de manutenções realizadas
                try:
                    conn = get_db_connection()
                    # Verificar se a tabela existe antes de tentar excluir os dados
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='manutencoes_realizadas'")
                    if cursor.fetchone():
                        conn.execute("DELETE FROM manutencoes_realizadas")
                    conn.commit()
                    conn.close()
                except Exception as e:
                    st.error(f"Erro ao limpar tabela de manutenções: {str(e)}")
                
                # Flag para rastrear se pelo menos uma planilha foi processada com sucesso
                alguma_planilha_processada = False
                
                # Processar planilha de equipamentos primeiro (necessária para todos os tipos)
                if uploaded_equipamentos is not None:
                    try:
                        df_equipamentos = pd.read_excel(uploaded_equipamentos)
                        
                        # Verificar coluna identificador
                        if 'Identificador' not in df_equipamentos.columns:
                            st.error("A planilha de equipamentos deve conter a coluna 'Identificador'.")
                        else:
                            # Salvar equipamentos
                            salvar_equipamentos(df_equipamentos)
                            st.success("Planilha de equipamentos carregada com sucesso!")
                            
                            # Processar cada tipo de planilha
                            if uploaded_mensal is not None:
                                try:
                                    df_mensal = pd.read_excel(uploaded_mensal)
                                    if 'Identificador' not in df_mensal.columns:
                                        st.warning("A planilha mensal deve conter a coluna 'Identificador'. Esta planilha foi ignorada.")
                                    else:
                                        # Salvar planilha mensal
                                        salvar_planilha(df_mensal, TIPO_MANUTENCAO_MENSAL)
                                        
                                        # Combinar dados para mensal
                                        df_combinado_mensal = pd.merge(
                                            df_mensal, df_equipamentos,
                                            on='Identificador', how='left', suffixes=('', '_equip')
                                        )
                                        
                                        st.success("Planilha mensal processada com sucesso!")
                                        alguma_planilha_processada = True
                                        
                                        # Armazenar na sessão (último tipo processado)
                                        st.session_state['dados_carregados'] = df_combinado_mensal
                                        st.session_state['tipo_manutencao_atual'] = TIPO_MANUTENCAO_MENSAL
                                except Exception as e:
                                    st.error(f"Erro ao processar a planilha mensal: {str(e)}")
                            
                            if uploaded_semestral is not None:
                                try:
                                    df_semestral = pd.read_excel(uploaded_semestral)
                                    if 'Identificador' not in df_semestral.columns:
                                        st.warning("A planilha semestral deve conter a coluna 'Identificador'. Esta planilha foi ignorada.")
                                    else:
                                        # Salvar planilha semestral
                                        salvar_planilha(df_semestral, TIPO_MANUTENCAO_SEMESTRAL)
                                        
                                        # Combinar dados para semestral
                                        df_combinado_semestral = pd.merge(
                                            df_semestral, df_equipamentos,
                                            on='Identificador', how='left', suffixes=('', '_equip')
                                        )
                                        
                                        st.success("Planilha semestral processada com sucesso!")
                                        alguma_planilha_processada = True
                                        
                                        # Armazenar na sessão (último tipo processado)
                                        st.session_state['dados_carregados'] = df_combinado_semestral
                                        st.session_state['tipo_manutencao_atual'] = TIPO_MANUTENCAO_SEMESTRAL
                                except Exception as e:
                                    st.error(f"Erro ao processar a planilha semestral: {str(e)}")
                            
                            if uploaded_corretiva is not None:
                                try:
                                    df_corretiva = pd.read_excel(uploaded_corretiva)
                                    if 'Identificador' not in df_corretiva.columns:
                                        st.warning("A planilha corretiva deve conter a coluna 'Identificador'. Esta planilha foi ignorada.")
                                    else:
                                        # Salvar planilha corretiva
                                        salvar_planilha(df_corretiva, TIPO_MANUTENCAO_CORRETIVA)
                                        
                                        # Combinar dados para corretiva
                                        df_combinado_corretiva = pd.merge(
                                            df_corretiva, df_equipamentos,
                                            on='Identificador', how='left', suffixes=('', '_equip')
                                        )
                                        
                                        st.success("Planilha corretiva processada com sucesso!")
                                        alguma_planilha_processada = True
                                        
                                        # Armazenar na sessão (último tipo processado)
                                        st.session_state['dados_carregados'] = df_combinado_corretiva
                                        st.session_state['tipo_manutencao_atual'] = TIPO_MANUTENCAO_CORRETIVA
                                except Exception as e:
                                    st.error(f"Erro ao processar a planilha corretiva: {str(e)}")
                            
                            if not alguma_planilha_processada:
                                st.warning("Nenhuma planilha de manutenção foi processada. Carregue pelo menos uma planilha (Mensal, Semestral ou Corretiva).")
                    except Exception as e:
                        st.error(f"Erro ao processar a planilha de equipamentos: {str(e)}")
                else:
                    st.error("A planilha de equipamentos é obrigatória para a configuração inicial.")
    
    with tab2:
        st.subheader("Atualização Diária")
        st.write("Utilize este passo para atualizar as manutenções realizadas diariamente")
        
        # Definir inputs para todas as planilhas diárias
        st.markdown("### Selecione as planilhas diárias")
        
        uploaded_mensal_diario = st.file_uploader("Selecione a planilha diária MENSAL", type=["xls", "xlsx"], key="diario_mensal")
        uploaded_semestral_diario = st.file_uploader("Selecione a planilha diária SEMESTRAL", type=["xls", "xlsx"], key="diario_semestral")
        uploaded_corretiva_diario = st.file_uploader("Selecione a planilha diária CORRETIVA", type=["xls", "xlsx"], key="diario_corretiva")
        
        if st.button("Processar Todas as Planilhas Diárias"):
            with st.spinner("Processando todas as planilhas diárias..."):
                # Flag para rastrear se pelo menos uma planilha foi processada
                alguma_diaria_processada = False
                ultimo_tipo_processado = None
                
                # Processar cada tipo de planilha diária
                if uploaded_mensal_diario is not None:
                    try:
                        df_diario_mensal = pd.read_excel(uploaded_mensal_diario)
                        
                        # Registrar as manutenções (com o tipo específico)
                        registrar_manutencao(df_diario_mensal, TIPO_MANUTENCAO_MENSAL)
                        
                        st.success("Planilha diária mensal processada com sucesso!")
                        alguma_diaria_processada = True
                        ultimo_tipo_processado = TIPO_MANUTENCAO_MENSAL
                    except Exception as e:
                        st.error(f"Erro ao processar a planilha diária mensal: {str(e)}")
                
                if uploaded_semestral_diario is not None:
                    try:
                        df_diario_semestral = pd.read_excel(uploaded_semestral_diario)
                        
                        # Registrar as manutenções (com o tipo específico)
                        registrar_manutencao(df_diario_semestral, TIPO_MANUTENCAO_SEMESTRAL)
                        
                        st.success("Planilha diária semestral processada com sucesso!")
                        alguma_diaria_processada = True
                        ultimo_tipo_processado = TIPO_MANUTENCAO_SEMESTRAL
                    except Exception as e:
                        st.error(f"Erro ao processar a planilha diária semestral: {str(e)}")
                
                if uploaded_corretiva_diario is not None:
                    try:
                        df_diario_corretiva = pd.read_excel(uploaded_corretiva_diario)
                        
                        # Registrar as manutenções (com o tipo específico)
                        registrar_manutencao(df_diario_corretiva, TIPO_MANUTENCAO_CORRETIVA)
                        
                        st.success("Planilha diária corretiva processada com sucesso!")
                        alguma_diaria_processada = True
                        ultimo_tipo_processado = TIPO_MANUTENCAO_CORRETIVA
                    except Exception as e:
                        st.error(f"Erro ao processar a planilha diária corretiva: {str(e)}")
                
                # Se alguma planilha foi processada, atualizar a visualização
                if alguma_diaria_processada and ultimo_tipo_processado is not None:
                    # Obter os dados para exibição
                    df_combinado = combinar_dados()
                    
                    if df_combinado is not None:
                        # Atualizar a data e hora da última atualização
                        salvar_ultima_atualizacao()
                        
                        # Adicionar status de manutenção para cada identificador, filtrando pelo tipo
                        for index, row in df_combinado.iterrows():
                            identificador = str(row.get('Identificador', ''))
                            colaborador = str(row.get('Colaborador', ''))
                            cliente = str(row.get('Cliente', ''))
                            # Usar o último tipo processado para visualização
                            df_combinado.at[index, 'Manutencao_Realizada'] = verificar_manutencao_realizada(
                                identificador, colaborador, cliente, ultimo_tipo_processado
                            )
                        
                        st.session_state['dados_carregados'] = df_combinado
                        st.session_state['tipo_manutencao_atual'] = ultimo_tipo_processado
                    else:
                        st.error("Não foi possível carregar os dados armazenados. Faça o upload das planilhas iniciais primeiro.")
                elif not alguma_diaria_processada:
                    st.warning("Nenhuma planilha diária foi processada. Carregue pelo menos uma planilha (Mensal, Semestral ou Corretiva).")
    
    # Adicionar o botão de atualizar data e hora abaixo das tabs
    st.markdown("---")
    st.subheader("Atualizar Data e Hora")
    if st.button("Atualizar Data/Hora", key="atualizar_data_hora_sidebar"):
        data_hora_atual = salvar_ultima_atualizacao()
        st.success(f"Data e hora atualizadas: {data_hora_atual}")
        st.rerun()  # Recarregar a página para mostrar a nova data/hora
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Instruções")
    st.sidebar.markdown("""
    1. Na aba "Configuração Inicial", carregue todas as planilhas necessárias de uma vez só (Mensal, Semestral, Corretiva e Equipamentos)
    2. Na aba "Atualização Diária", carregue todas as planilhas diárias que deseja processar
    3. O sistema processará todas as planilhas simultaneamente
    4. Use os botões da área principal para selecionar o tipo de manutenção que deseja visualizar
    5. Verde = Manutenção Realizada
    6. Vermelho = Manutenção Pendente
    """)

# Carregar dados automaticamente ao iniciar o aplicativo
if 'dados_carregados' not in st.session_state:
    # Verificar se existem dados no banco de dados
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se há dados nas tabelas
    cursor.execute("SELECT COUNT(*) FROM planilha_mensal")
    tem_mensal = cursor.fetchone()[0] > 0
    
    cursor.execute("SELECT COUNT(*) FROM equipamentos")
    tem_equipamentos = cursor.fetchone()[0] > 0
    
    conn.close()
    
    # Se existirem dados, carregá-los automaticamente
    if tem_mensal and tem_equipamentos:
        with st.spinner("Carregando dados armazenados..."):
            dados_processados = processar_dados_manutencao(usar_armazenado=True)
            if dados_processados is not None:
                st.session_state['dados_carregados'] = dados_processados
                st.session_state['tipo_manutencao_atual'] = TIPO_MANUTENCAO_MENSAL

# Criar um container para a data e hora com estilo destacado
data_hora_container = st.container()
with data_hora_container:
    # Usar colunas para organizar o layout
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("### Última atualização:")
    with col2:
        # Obter a data e hora da última atualização
        ultima_atualizacao = obter_ultima_atualizacao()
        # Usar markdown para destacar a informação
        st.markdown(f"### *{ultima_atualizacao}*")

# Opções de visualização
st.markdown("---")
st.subheader("Opções de Visualização")
show_by = st.radio(
    "Ver manutenções por:",
    ["Colaborador", "Cliente", "Identificador"]
)

# Adicionar seleção de tipo de manutenção para visualização
tipo_visualizacao = st.radio(
    "Selecione o tipo de manutenção para visualizar:",
    ["Mensal", "Semestral", "Corretiva"],
    horizontal=True,
    key="tipo_visualizacao"
)

# Converter escolha do usuário para o tipo no sistema
tipo_sistema_visualizacao = TIPO_MANUTENCAO_MENSAL
if tipo_visualizacao == "Semestral":
    tipo_sistema_visualizacao = TIPO_MANUTENCAO_SEMESTRAL
elif tipo_visualizacao == "Corretiva":
    tipo_sistema_visualizacao = TIPO_MANUTENCAO_CORRETIVA

# Botão para carregar os dados atuais
if st.button(f"Carregar Dados Atuais ({tipo_visualizacao})"):
    with st.spinner(f"Carregando dados de {tipo_visualizacao.lower()}..."):
        # Combinar os dados disponíveis
        df_combinado = combinar_dados()
        
        if df_combinado is not None:
            # Atualizar a data e hora da última atualização
            salvar_ultima_atualizacao()
            
            # Adicionar status de manutenção para cada identificador, filtrando pelo tipo
            for index, row in df_combinado.iterrows():
                identificador = str(row.get('Identificador', ''))
                colaborador = str(row.get('Colaborador', ''))
                cliente = str(row.get('Cliente', ''))
                df_combinado.at[index, 'Manutencao_Realizada'] = verificar_manutencao_realizada(
                    identificador, colaborador, cliente, tipo_sistema_visualizacao
                )
            
            st.session_state['dados_carregados'] = df_combinado
            st.session_state['tipo_manutencao_atual'] = tipo_sistema_visualizacao
            st.success(f"Dados de {tipo_visualizacao.lower()} carregados com sucesso!")
        else:
            st.warning("Nenhum dado disponível. Faça o upload das planilhas iniciais primeiro.")

# Se os dados estiverem disponíveis na sessão, exibi-los
if 'dados_carregados' in st.session_state:
    dados_manutencao = st.session_state['dados_carregados']
    
    # Verificar se a coluna Manutencao_Realizada existe, se não, adicioná-la como False (não realizada)
    if 'Manutencao_Realizada' not in dados_manutencao.columns:
        # Adicionar a coluna faltante
        dados_manutencao['Manutencao_Realizada'] = False
        
        # Atualizar o status das manutenções realizadas com base no tipo atual
        tipo_atual = st.session_state.get('tipo_manutencao_atual', TIPO_MANUTENCAO_MENSAL)
        for index, row in dados_manutencao.iterrows():
            identificador = str(row.get('Identificador', ''))
            colaborador = str(row.get('Colaborador', ''))
            cliente = str(row.get('Cliente', ''))
            dados_manutencao.at[index, 'Manutencao_Realizada'] = verificar_manutencao_realizada(
                identificador, colaborador, cliente, tipo_atual
            )
        
        # Atualizar dados na sessão
        st.session_state['dados_carregados'] = dados_manutencao
    
    # Exibir estatísticas resumidas
    col1, col2, col3, col4 = st.columns(4)
    
    # Contar status de manutenção
    total_equipamentos = len(dados_manutencao)
    realizadas = dados_manutencao['Manutencao_Realizada'].sum()
    pendentes = total_equipamentos - realizadas
    
    with col1:
        st.metric("Total de Equipamentos", total_equipamentos)
    with col2:
        st.metric("Manutenções Realizadas", int(realizadas), delta=f"{int(realizadas/total_equipamentos*100)}%" if total_equipamentos > 0 else "0%")
    with col3:
        st.metric("Manutenções Pendentes", int(pendentes), delta=f"-{int(pendentes/total_equipamentos*100)}%" if total_equipamentos > 0 else "0%")
    with col4:
        # Criar gráfico de progresso
        fig = px.pie(
            values=[realizadas, pendentes],
            names=['Realizadas', 'Pendentes'],
            color=['green', 'red'],
            color_discrete_map={'Realizadas': 'green', 'Pendentes': 'red'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Visualização de acordo com a seleção
    if show_by == "Colaborador":
        st.subheader("Status por Colaborador")
        
        # Preparar dados por colaborador
        resumo_colaborador = dados_manutencao.groupby('Colaborador').agg({
            'Identificador': 'count',
            'Manutencao_Realizada': 'sum'
        }).reset_index()
        
        resumo_colaborador.rename(columns={
            'Identificador': 'Total_Equipamentos',
            'Manutencao_Realizada': 'Manutencoes_Realizadas'
        }, inplace=True)
        
        resumo_colaborador['Manutencoes_Pendentes'] = resumo_colaborador['Total_Equipamentos'] - resumo_colaborador['Manutencoes_Realizadas']
        # Evitar divisão por zero
        resumo_colaborador['Percentual_Concluido'] = resumo_colaborador.apply(
            lambda row: round(row['Manutencoes_Realizadas'] / row['Total_Equipamentos'] * 100, 2) 
            if row['Total_Equipamentos'] > 0 else 0.0, 
            axis=1
        )
        
        # Criar gráfico de barras
        fig = px.bar(
            resumo_colaborador,
            x='Colaborador',
            y=['Manutencoes_Realizadas', 'Manutencoes_Pendentes'],
            title='Manutenções por Colaborador',
            barmode='stack',
            color_discrete_map={'Manutencoes_Realizadas': 'green', 'Manutencoes_Pendentes': 'red'},
            text='Percentual_Concluido'
        )
        
        fig.update_layout(legend_title_text='Status')
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Adicionar filtro por colaborador
        colaborador_selecionado = st.selectbox(
            "Selecione um colaborador para ver os detalhes:",
            ["Todos"] + sorted([str(c) for c in dados_manutencao['Colaborador'].unique() if c is not None and pd.notna(c)])
        )
        
        if colaborador_selecionado != "Todos":
            # Filtrar dados por colaborador
            dados_filtrados = dados_manutencao[dados_manutencao['Colaborador'] == colaborador_selecionado]
            
            # Mostrar clientes atendidos
            st.subheader(f"Clientes atendidos por {colaborador_selecionado}")
            
            # Agrupar por cliente
            clientes = dados_filtrados.groupby('Cliente').agg({
                'Identificador': 'count',
                'Manutencao_Realizada': 'sum'
            }).reset_index()
            
            clientes.rename(columns={
                'Identificador': 'Total_Equipamentos',
                'Manutencao_Realizada': 'Manutencoes_Realizadas'
            }, inplace=True)
            
            clientes['Manutencoes_Pendentes'] = clientes['Total_Equipamentos'] - clientes['Manutencoes_Realizadas']
            
            # Exibir em formato de tabela com ícones
            for _, row in clientes.iterrows():
                with st.container():
                    cols = st.columns([3, 1, 1, 1])
                    with cols[0]:
                        st.markdown(f"**{row['Cliente']}**")
                    with cols[1]:
                        st.markdown(f"Total: {row['Total_Equipamentos']}")
                    with cols[2]:
                        st.markdown(f"✅ {int(row['Manutencoes_Realizadas'])}")
                    with cols[3]:
                        st.markdown(f"❌ {int(row['Manutencoes_Pendentes'])}")
                    
                    # Expandir para mostrar equipamentos
                    with st.expander(f"Ver equipamentos de {row['Cliente']}"):
                        equips = dados_filtrados[dados_filtrados['Cliente'] == row['Cliente']]
                        for _, equip in equips.iterrows():
                            status_icon = "✅" if equip['Manutencao_Realizada'] else "❌"
                            st.markdown(f"{status_icon} **{equip['Identificador']}**")
                            st.write(f"Colaborador responsável: {equip['Colaborador']}")
                            
                            # Adicionar mais informações dos equipamentos se disponíveis
                            # Verificar colunas que possam conter informações adicionais, excluindo colunas de fotos
                            foto_columns = [
                                'FOTO 1 - ANTES - Tampa da Maquina Aberta com os Filtros SUJOS Instalados na Maquina.',
                                'FOTO 2 - ANTES - Foto com Etiqueta QRCODE (Mar Brasil) da Maquina.',
                                'FOTO 3 - ANTES - Foto com Etiqueta técnica da maquina (Etiqueta de Identificação do Fabricante na Evaporadora).',
                                'Foto 1 - DEPOIS - Tampa da Maquina Aberta com os Filtros LIMPOS Instalados na Maquina.',
                                'Foto 2 - DEPOIS - Limpeza geral da maquina e display de funcionamento (Se houver display)'
                            ]
                            excluded_columns = ['Colaborador', 'Cliente', 'Identificador', 'Manutencao_Realizada'] + foto_columns
                            info_columns = [col for col in equip.index if col not in excluded_columns]
                            
                            for col in info_columns:
                                if pd.notna(equip[col]) and str(equip[col]).strip() != '':
                                    st.write(f"**{col}:** {equip[col]}")
                            
                            st.markdown("---")
        else:
            # Mostrar todos os colaboradores
            st.subheader("Todos os Colaboradores")
            
            # Criar tabela com status de cada colaborador
            # --- Substituição direta dos nomes por setor antes da exibição ---
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
            if 'Colaborador' in dados_manutencao.columns:
                dados_manutencao['Colaborador'] = dados_manutencao['Colaborador'].apply(substituir_por_setor)
            # --------------------------------------------------------------
            for colaborador in dados_manutencao['Colaborador'].unique():
                dados_colab = dados_manutencao[dados_manutencao['Colaborador'] == colaborador]
                total = len(dados_colab)
                realizados = dados_colab['Manutencao_Realizada'].sum()
                pendentes = total - realizados
                
                with st.container():
                    cols = st.columns([3, 1, 1, 1])
                    with cols[0]:
                        st.markdown(f"**{colaborador}**")
                    with cols[1]:
                        st.markdown(f"Total: {total}")
                    with cols[2]:
                        st.markdown(f"✅ {int(realizados)}")
                    with cols[3]:
                        st.markdown(f"❌ {int(pendentes)}")
                
                # Adicionar barra de progresso
                progresso = int(realizados / total * 100) if total > 0 else 0
                progresso = int(realizadas / total * 100) if total > 0 else 0
                st.progress(min(progresso/100, 1.0))
                st.markdown("---")
                
    elif show_by == "Cliente":
        st.subheader("Status por Cliente")
        
        # Preparar dados por cliente
        resumo_cliente = dados_manutencao.groupby('Cliente').agg({
            'Identificador': 'count',
            'Manutencao_Realizada': 'sum'
        }).reset_index()
        
        resumo_cliente.rename(columns={
            'Identificador': 'Total_Equipamentos',
            'Manutencao_Realizada': 'Manutencoes_Realizadas'
        }, inplace=True)
        
        resumo_cliente['Manutencoes_Pendentes'] = resumo_cliente['Total_Equipamentos'] - resumo_cliente['Manutencoes_Realizadas']
        # Evitar divisão por zero
        resumo_cliente['Percentual_Concluido'] = resumo_cliente.apply(
            lambda row: round(row['Manutencoes_Realizadas'] / row['Total_Equipamentos'] * 100, 2) 
            if row['Total_Equipamentos'] > 0 else 0.0, 
            axis=1
        )
        
        # Criar gráfico de barras
        fig = px.bar(
            resumo_cliente,
            x='Cliente',
            y=['Manutencoes_Realizadas', 'Manutencoes_Pendentes'],
            title='Manutenções por Cliente',
            barmode='stack',
            color_discrete_map={'Manutencoes_Realizadas': 'green', 'Manutencoes_Pendentes': 'red'},
            text='Percentual_Concluido'
        )
        
        fig.update_layout(legend_title_text='Status')
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Adicionar filtro por cliente
        cliente_selecionado = st.selectbox(
            "Selecione um cliente para ver os detalhes:",
            ["Todos"] + sorted([str(c) for c in dados_manutencao['Cliente'].unique() if c is not None and pd.notna(c)])
        )
        
        if cliente_selecionado != "Todos":
            # Filtrar dados por cliente
            dados_filtrados = dados_manutencao[dados_manutencao['Cliente'] == cliente_selecionado]
            
            # Mostrar colaboradores que atendem o cliente
            st.subheader(f"Colaboradores que atendem {cliente_selecionado}")
            
            # Agrupar por colaborador
            colaboradores = dados_filtrados.groupby('Colaborador').agg({
                'Identificador': 'count',
                'Manutencao_Realizada': 'sum'
            }).reset_index()
            
            colaboradores.rename(columns={
                'Identificador': 'Total_Equipamentos',
                'Manutencao_Realizada': 'Manutencoes_Realizadas'
            }, inplace=True)
            
            colaboradores['Manutencoes_Pendentes'] = colaboradores['Total_Equipamentos'] - colaboradores['Manutencoes_Realizadas']
            
            # Exibir em formato de tabela com ícones
            for _, row in colaboradores.iterrows():
                with st.container():
                    cols = st.columns([3, 1, 1, 1])
                    with cols[0]:
                        st.markdown(f"**{row['Colaborador']}**")
                    with cols[1]:
                        st.markdown(f"Total: {row['Total_Equipamentos']}")
                    with cols[2]:
                        st.markdown(f"✅ {int(row['Manutencoes_Realizadas'])}")
                    with cols[3]:
                        st.markdown(f"❌ {int(row['Manutencoes_Pendentes'])}")
            
            # Mostrar equipamentos
            st.subheader(f"Equipamentos de {cliente_selecionado}")
            
            # Criar duas colunas: Pendentes e Realizados
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### ❌ Manutenções Pendentes")
                pendentes = dados_filtrados[dados_filtrados['Manutencao_Realizada'] == False]
                
                if len(pendentes) > 0:
                    for _, equip in pendentes.iterrows():
                        st.markdown(f"**{equip['Identificador']}**")
                        st.write(f"Colaborador responsável: {equip['Colaborador']}")
                        
                        # Adicionar mais informações dos equipamentos se disponíveis
                        info_columns = [col for col in equip.index if col not in ['Colaborador', 'Cliente', 'Identificador', 'Manutencao_Realizada']]
                        
                        for col in info_columns:
                            if pd.notna(equip[col]) and str(equip[col]).strip() != '':
                                st.write(f"**{col}:** {equip[col]}")
                                
                        st.markdown("---")
                else:
                    st.success("Não há manutenções pendentes!")
            
            with col2:
                st.markdown("### ✅ Manutenções Realizadas")
                realizadas = dados_filtrados[dados_filtrados['Manutencao_Realizada'] == True]
                
                if len(realizadas) > 0:
                    for _, equip in realizadas.iterrows():
                        st.markdown(f"**{equip['Identificador']}**")
                        st.write(f"Colaborador responsável: {equip['Colaborador']}")
                        
                        # Adicionar mais informações dos equipamentos se disponíveis
                        info_columns = [col for col in equip.index if col not in ['Colaborador', 'Cliente', 'Identificador', 'Manutencao_Realizada']]
                        
                        for col in info_columns:
                            if pd.notna(equip[col]) and str(equip[col]).strip() != '':
                                st.write(f"**{col}:** {equip[col]}")
                                
                        st.markdown("---")
                else:
                    st.error("Nenhuma manutenção foi realizada ainda!")
        else:
            # Mostrar todos os clientes
            st.subheader("Todos os Clientes")
            
            # Criar tabela com status de cada cliente
            for cliente in sorted([str(c) for c in dados_manutencao['Cliente'].unique() if c is not None and pd.notna(c)]):
                df_cliente = dados_manutencao[dados_manutencao['Cliente'] == cliente]
                total = len(df_cliente)
                realizadas = df_cliente['Manutencao_Realizada'].sum()
                pendentes = total - realizadas
                
                with st.container():
                    cols = st.columns([3, 1, 1, 1])
                    with cols[0]:
                        st.markdown(f"**{cliente}**")
                    with cols[1]:
                        st.markdown(f"Total: {total}")
                    with cols[2]:
                        st.markdown(f"✅ {int(realizadas)}")
                    with cols[3]:
                        st.markdown(f"❌ {int(pendentes)}")
                
                # Adicionar barra de progresso
                progresso = int(realizadas / total * 100) if total > 0 else 0
                st.progress(progresso/100)
                st.markdown("---")
                
    else:  # Por Identificador
        st.subheader("Status por Identificador")
        
        # Campo de busca
        id_filtro = st.text_input("Buscar por identificador:")
        
        if id_filtro:
            dados_filtrados = dados_manutencao[dados_manutencao['Identificador'].astype(str).str.contains(id_filtro)]
            
            if not dados_filtrados.empty:
                st.success(f"Encontrado(s) {len(dados_filtrados)} equipamento(s).")
                
                for _, row in dados_filtrados.iterrows():
                    status_icon = "✅" if row['Manutencao_Realizada'] else "❌"
                    st.markdown(f"### {status_icon} Equipamento: {row['Identificador']}")
                    st.write(f"**Cliente:** {row['Cliente']}")
                    st.write(f"**Colaborador:** {row['Colaborador']}")
                    
                    # Adicionar mais informações dos equipamentos se disponíveis
                    info_columns = [col for col in row.index if col not in ['Colaborador', 'Cliente', 'Identificador', 'Manutencao_Realizada']]
                    
                    for col in info_columns:
                        if pd.notna(row[col]) and str(row[col]).strip() != '':
                            st.write(f"**{col}:** {row[col]}")
                    
                    st.markdown("---")
            else:
                st.warning(f"Nenhum equipamento encontrado com o identificador '{id_filtro}'.")
        else:
            # Mostrar tabela com todos os equipamentos
            dados_ordenados = dados_manutencao.sort_values(['Cliente', 'Colaborador', 'Identificador'])
            
            for _, row in dados_ordenados.iterrows():
                cols = st.columns([1, 2, 2, 3])
                
                status_icon = "✅" if row['Manutencao_Realizada'] else "❌"
                
                with cols[0]:
                    st.markdown(f"### {status_icon}")
                with cols[1]:
                    st.markdown(f"**{row['Identificador']}**")
                with cols[2]:
                    st.write(f"Cliente: {row['Cliente']}")
                with cols[3]:
                    st.write(f"Colaborador: {row['Colaborador']}")
                
                st.markdown("---")
    
    # Botão para exportar dados filtrados
    st.markdown("---")
    st.subheader("Exportar Dados")
    
    if st.button("Gerar Relatório de Status"):
        # Configurar buffer para download
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Adicionar coluna com status em texto
            df_export = dados_manutencao.copy()
            df_export['Status'] = df_export['Manutencao_Realizada'].apply(lambda x: 'Realizada' if x else 'Pendente')
            
            df_export.to_excel(writer, sheet_name='Status_Manutencoes', index=False)
            
        buffer.seek(0)
        
        # Oferecer para download
        st.download_button(
            label="📥 Baixar Relatório Excel",
            data=buffer,
            file_name=f"relatorio_status_manutencoes_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    # Exibir mensagem inicial
    st.info("Para começar, carregue a configuração inicial na barra lateral:")
    
    st.markdown("""
    ### Passo 1: Configuração Inicial do Mês
    1. Clicar no botão Carregar Dados Atuais (Mensal)
    
    ### Passo 2: Atualizações Diárias
    1. Após a configuração inicial, use a aba "Atualização Diária" para carregar as planilhas diárias
    2. O sistema verifica a coluna "CUMPRIMENTO DOS ITENS MENCIONADOS" com valor "Sim" para marcar manutenções realizadas
    
    ### Visualização
    - O sistema mostrará Verde para equipamentos com manutenção realizada
    - O sistema mostrará Vermelho para equipamentos com manutenção pendente
    """)
    
    # Mostrar exemplo de como os dados devem estar organizados
    with st.expander("Como os dados devem estar organizados nas planilhas?"):
        st.markdown("""
        ### Planilha Mensal (mensal.xls)
        Deve conter as seguintes colunas:
        - **Colaborador**: Nome do colaborador que realizará o serviço
        - **Identificador**: Código que identifica o equipamento
        - **Cliente**: Nome do cliente a ser atendido
        
        ### Planilha de Equipamentos (equipamentos.xlsx)
        Deve conter as colunas:
        - **Identificador**: Código que identifica o equipamento
        - Outras informações do equipamento (Modelo, Descrição, etc.)
        
        ### Planilha Diária (atualizações)
        Deve conter as colunas:
        - **Identificador**: Código que identifica o equipamento
        - **CUMPRIMENTO DOS ITENS MENCIONADOS**: "Sim" quando a manutenção foi realizada
        - **Colaborador**: Nome do colaborador que realizou o serviço
        - **Cliente**: Nome do cliente atendido
        
        O sistema combina a planilha mensal com a de equipamentos, e depois verifica as atualizações diárias para determinar quais equipamentos já receberam manutenção.
        """)
