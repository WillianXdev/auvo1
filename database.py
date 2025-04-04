import os
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Obter a URL do banco de dados da variável de ambiente
DATABASE_URL = os.environ.get('DATABASE_URL')

# Criar engine do SQLAlchemy
engine = create_engine(DATABASE_URL)

# Criar base declarativa
Base = declarative_base()

# Definir os modelos (tabelas)
class Colaborador(Base):
    __tablename__ = 'colaboradores'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)
    
    # Relacionamento
    manutencoes = relationship("Manutencao", back_populates="colaborador")
    
    def __repr__(self):
        return f"<Colaborador(id={self.id}, nome='{self.nome}')>"


class Cliente(Base):
    __tablename__ = 'clientes'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)
    
    # Relacionamento
    equipamentos = relationship("Equipamento", back_populates="cliente")
    
    def __repr__(self):
        return f"<Cliente(id={self.id}, nome='{self.nome}')>"


class Equipamento(Base):
    __tablename__ = 'equipamentos'
    
    id = Column(Integer, primary_key=True)
    identificador = Column(String(50), nullable=False, unique=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id'))
    descricao = Column(Text, nullable=True)
    
    # Relacionamento
    cliente = relationship("Cliente", back_populates="equipamentos")
    manutencoes = relationship("Manutencao", back_populates="equipamento")
    
    def __repr__(self):
        return f"<Equipamento(id={self.id}, identificador='{self.identificador}')>"


class Manutencao(Base):
    __tablename__ = 'manutencoes'
    
    id = Column(Integer, primary_key=True)
    colaborador_id = Column(Integer, ForeignKey('colaboradores.id'))
    equipamento_id = Column(Integer, ForeignKey('equipamentos.id'))
    data = Column(String(20), nullable=True)  # Formato YYYY-MM-DD
    
    # Relacionamentos
    colaborador = relationship("Colaborador", back_populates="manutencoes")
    equipamento = relationship("Equipamento", back_populates="manutencoes")
    
    def __repr__(self):
        return f"<Manutencao(id={self.id}, data='{self.data}')>"


# Criar todas as tabelas no banco de dados
Base.metadata.create_all(engine)

# Criar uma sessão para interagir com o banco de dados
Session = sessionmaker(bind=engine)


# Funções para interagir com o banco de dados
def importar_dados_excel(arquivo_mensal, arquivo_equipamentos):
    """
    Importa dados das planilhas Excel para o banco de dados
    """
    session = Session()
    try:
        # Limpar dados existentes (opcional, dependendo da necessidade)
        # session.query(Manutencao).delete()
        # session.query(Equipamento).delete()
        # session.query(Cliente).delete()
        # session.query(Colaborador).delete()
        
        # Carregar dados das planilhas
        df_mensal = pd.read_excel(arquivo_mensal)
        df_equipamentos = pd.read_excel(arquivo_equipamentos)
        
        # Processar dados da planilha mensal
        for _, row in df_mensal.iterrows():
            # Adicionar colaborador se não existir
            colaborador = session.query(Colaborador).filter_by(nome=row['Colaborador']).first()
            if not colaborador:
                colaborador = Colaborador(nome=row['Colaborador'])
                session.add(colaborador)
                session.flush()  # Para obter o ID gerado
            
            # Adicionar cliente se não existir
            cliente = session.query(Cliente).filter_by(nome=row['Cliente']).first()
            if not cliente:
                cliente = Cliente(nome=row['Cliente'])
                session.add(cliente)
                session.flush()  # Para obter o ID gerado
            
            # Verificar se o identificador é válido (não é NaN)
            if pd.isna(row['Identificador']):
                continue
                
            # Verificar se o equipamento já existe
            equipamento = session.query(Equipamento).filter_by(identificador=str(row['Identificador'])).first()
            if not equipamento:
                # Buscar informações adicionais do equipamento na outra planilha
                info_equip = df_equipamentos[df_equipamentos['Identificador'] == row['Identificador']]
                
                # Criar o equipamento
                equipamento = Equipamento(
                    identificador=str(row['Identificador']),  # Converter para string para evitar erros
                    cliente_id=cliente.id,
                    descricao=info_equip.iloc[0]['Descricao'] if 'Descricao' in info_equip.columns and not info_equip.empty else None
                )
                session.add(equipamento)
                session.flush()  # Para obter o ID gerado
            
            # Criar a manutenção
            manutencao = Manutencao(
                colaborador_id=colaborador.id,
                equipamento_id=equipamento.id,
                data=row.get('Data', None)  # Se houver coluna de data
            )
            session.add(manutencao)
        
        # Commit para salvar no banco de dados
        session.commit()
        return True
    
    except Exception as e:
        session.rollback()
        print(f"Erro ao importar dados: {str(e)}")
        return False
    
    finally:
        session.close()


def obter_resumo_colaborador():
    """
    Obtém o resumo de quantidade de máquinas por colaborador e cliente
    """
    session = Session()
    try:
        # Consulta SQL usando SQLAlchemy
        resultado = session.query(
            Colaborador.nome.label('Colaborador'),
            Cliente.nome.label('Cliente'),
            func.count().label('Quantidade_Maquinas')
        ).join(Manutencao, Colaborador.id == Manutencao.colaborador_id)\
         .join(Equipamento, Manutencao.equipamento_id == Equipamento.id)\
         .join(Cliente, Equipamento.cliente_id == Cliente.id)\
         .group_by(Colaborador.nome, Cliente.nome)\
         .all()
        
        # Converter para DataFrame
        df_resultado = pd.DataFrame(resultado, columns=['Colaborador', 'Cliente', 'Quantidade_Maquinas'])
        
        return df_resultado
    
    except Exception as e:
        print(f"Erro ao obter resumo: {str(e)}")
        return None
    
    finally:
        session.close()


def obter_total_por_colaborador():
    """
    Obtém o total de máquinas por colaborador
    """
    session = Session()
    try:
        # Consulta SQL usando SQLAlchemy
        resultado = session.query(
            Colaborador.nome.label('Colaborador'),
            func.count().label('Quantidade_Maquinas')
        ).join(Manutencao, Colaborador.id == Manutencao.colaborador_id)\
         .group_by(Colaborador.nome)\
         .all()
        
        # Converter para DataFrame
        df_resultado = pd.DataFrame(resultado, columns=['Colaborador', 'Quantidade_Maquinas'])
        
        return df_resultado
    
    except Exception as e:
        print(f"Erro ao obter total por colaborador: {str(e)}")
        return None
    
    finally:
        session.close()


def obter_identificadores_cliente(colaborador_nome, cliente_nome):
    """
    Obtém os identificadores de equipamentos para um cliente específico
    atendido por um colaborador específico
    """
    session = Session()
    try:
        # Consulta SQL usando SQLAlchemy
        resultado = session.query(
            Equipamento.identificador
        ).join(Manutencao, Equipamento.id == Manutencao.equipamento_id)\
         .join(Colaborador, Manutencao.colaborador_id == Colaborador.id)\
         .join(Cliente, Equipamento.cliente_id == Cliente.id)\
         .filter(Colaborador.nome == colaborador_nome)\
         .filter(Cliente.nome == cliente_nome)\
         .distinct()\
         .all()
        
        # Extrair identificadores da lista de tuplas
        identificadores = [item[0] for item in resultado]
        
        return identificadores
    
    except Exception as e:
        print(f"Erro ao obter identificadores: {str(e)}")
        return []
    
    finally:
        session.close()


def verificar_dados_existentes():
    """
    Verifica se existem dados no banco
    """
    session = Session()
    try:
        count = session.query(Manutencao).count()
        return count > 0
    except Exception as e:
        print(f"Erro ao verificar dados: {str(e)}")
        return False
    finally:
        session.close()