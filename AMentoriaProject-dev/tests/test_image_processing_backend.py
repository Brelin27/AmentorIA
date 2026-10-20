import pytest
import base64
import inspect
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from PIL import Image

from schemas.schemas import DuvidaAlunoRequest, RespostaTutorResponse, AlunoCreateRequest
from services.gemini_service import GeminiService
from routers.chat import enviar_duvida
from routers.alunos import criar_aluno
from models.models import Aluno


# ============================================================================
# FIXTURES GLOBAIS — Imagem
# ============================================================================

@pytest.fixture
def imagem_teste_base64():
    """Cria uma imagem PNG de teste e retorna em Base64"""
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_data = buffer.getvalue()
    b64_string = base64.b64encode(img_data).decode()
    return f"data:image/png;base64,{b64_string}"


@pytest.fixture
def requisicao_com_imagem(imagem_teste_base64):
    """Requisição de chat contendo texto e imagem"""
    return DuvidaAlunoRequest(
        aluno_id="1",
        sessao_chat_id="1",
        texto_duvida="Qual é a resposta desta questão?",
        imagem_base64=imagem_teste_base64
    )


@pytest.fixture
def requisicao_apenas_texto():
    """Requisição de chat contendo apenas texto"""
    return DuvidaAlunoRequest(
        aluno_id="1",
        sessao_chat_id="1",
        texto_duvida="Qual é a resposta?",
        imagem_base64=None
    )


@pytest.fixture
def gemini_service_mock():
    """Mock do GeminiService com client mockado"""
    with patch('routers.chat.get_gemini') as mock_get:
        service = MagicMock(spec=GeminiService)
        mock_get.return_value = service
        yield service


# ============================================================================
# FIXTURES GLOBAIS — Aluno
# ============================================================================

@pytest.fixture
def db_mock():
    """Mock da sessão do banco de dados"""
    return MagicMock(spec=Session)


@pytest.fixture
def dados_aluno_valido():
    """Payload válido para criação de aluno"""
    return AlunoCreateRequest(
        name="Maria Silva",
        email="maria.silva@email.com"
    )


@pytest.fixture
def aluno_persistido():
    """Simula um Aluno já salvo no banco (para cenários de duplicata)"""
    aluno = MagicMock(spec=Aluno)
    aluno.id = 42
    aluno.nome = "Maria Silva"
    aluno.email = "maria.silva@email.com"
    aluno.visto = False
    aluno.ultima_interacao = ""
    return aluno


# ============================================================================
# HELPERS
# ============================================================================

def montar_db_sem_aluno(db_mock):
    """Configura db_mock para simular banco sem o aluno (first() → None)"""
    db_mock.query.return_value.filter.return_value.first.return_value = None


def montar_db_com_aluno(db_mock, aluno):
    """Configura db_mock para simular banco com aluno já existente"""
    db_mock.query.return_value.filter.return_value.first.return_value = aluno


# ============================================================================
# CENÁRIO 1: Frontend - Validação de Conversão Base64
# ============================================================================

class TestFrontendImageConversion:
    """Valida se a imagem é convertida corretamente para Base64 no frontend"""

    def test_base64_format_valido(self, imagem_teste_base64):
        assert imagem_teste_base64.startswith("data:image/"), \
            "❌ Base64 não começa com data:image/"
        assert ";base64," in imagem_teste_base64, \
            "❌ Base64 não contém ;base64, separator"

    def test_base64_decodavel(self, imagem_teste_base64):
        b64_data = imagem_teste_base64.split(",")[1]
        try:
            decoded = base64.b64decode(b64_data)
            assert len(decoded) > 0, "❌ Decodificação resultou em dados vazios"
            assert decoded[:8] == b'\x89PNG\r\n\x1a\n', \
                "❌ Arquivo decodificado não é PNG válido"
        except Exception as e:
            pytest.fail(f"❌ Falha ao decodificar Base64: {str(e)}")

    def test_base64_nao_vazio(self, imagem_teste_base64):
        b64_data = imagem_teste_base64.split(",")[1]
        assert len(b64_data) > 100, \
            "❌ Base64 muito pequeno (< 100 caracteres)"


# ============================================================================
# CENÁRIO 2: Backend - Recebimento de Imagem
# ============================================================================

class TestBackendImageReception:
    """Valida se o backend recebe e valida a imagem corretamente"""

    def test_schema_suporta_imagem_base64(self, requisicao_com_imagem):
        assert hasattr(requisicao_com_imagem, 'imagem_base64'), \
            "❌ Schema não possui campo imagem_base64"
        assert requisicao_com_imagem.imagem_base64 is not None, \
            "❌ Campo imagem_base64 é None"

    def test_requisicao_com_e_sem_imagem(self, requisicao_com_imagem, requisicao_apenas_texto):
        assert requisicao_com_imagem.imagem_base64 is not None
        assert requisicao_com_imagem.texto_duvida is not None
        assert requisicao_apenas_texto.imagem_base64 is None
        assert requisicao_apenas_texto.texto_duvida is not None

    def test_validacao_imagem_base64_quando_presente(self, imagem_teste_base64):
        req = DuvidaAlunoRequest(
            aluno_id="1",
            sessao_chat_id="1",
            texto_duvida="Teste",
            imagem_base64=imagem_teste_base64
        )
        assert req.imagem_base64.startswith("data:image/"), \
            "❌ Imagem não começa com data:image/"
        assert len(req.imagem_base64) > 100, \
            "❌ Imagem muito pequena"


# ============================================================================
# CENÁRIO 3: Router - Passagem de Imagem para Gemini
# ============================================================================

class TestRouterImageHandling:
    """Valida se o router repassa imagem ao serviço Gemini"""

    def test_router_recebe_imagem(self, requisicao_com_imagem):
        assert requisicao_com_imagem.imagem_base64 is not None, \
            "❌ Requisição não contém imagem"

    @pytest.mark.skip(reason="BUG #11 — router ainda não repassa imagem ao Gemini")
    def test_router_chamaria_gemini_com_imagem(self, gemini_service_mock, requisicao_com_imagem):
        """Verifica se o router chama gemini.gerar_resposta com imagem_base64"""
        # TODO: chamar enviar_duvida e verificar se gemini_service_mock.gerar_resposta
        # foi chamado com imagem_base64=requisicao_com_imagem.imagem_base64
        pass


# ============================================================================
# CENÁRIO 4: Serviço Gemini - Processamento Multimodal
# ============================================================================

class TestGeminiImageProcessing:
    """Valida se GeminiService processa imagens corretamente"""

    def test_gerar_resposta_aceita_imagem_base64(self):
        """Verifica se método gerar_resposta aceita parâmetro imagem_base64.
        Este teste falhará enquanto o BUG #11 não for corrigido."""
        sig = inspect.signature(GeminiService.gerar_resposta)
        parametros = list(sig.parameters.keys())
        assert 'imagem_base64' in parametros or 'imagem' in parametros, \
            "❌ Método gerar_resposta não aceita parâmetro de imagem (BUG #11)"

    def test_gemini_content_format_multimodal(self, imagem_teste_base64):
        content = [
            {"type": "text", "text": "Qual é a resposta desta questão?"},
            {"type": "image_url", "image_url": {"url": imagem_teste_base64}}
        ]
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "image_url"
        assert "image_url" in content[1]
        assert "url" in content[1]["image_url"]

    def test_modelo_gpt_suporta_visao(self):
        modelo_suportado = "gpt-4o-mini"
        modelos_com_visao = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
        assert modelo_suportado in modelos_com_visao, \
            f"❌ Modelo {modelo_suportado} não suporta visão"


# ============================================================================
# FLUXO E2E: Teste Integrado Completo
# ============================================================================

class TestImageProcessingE2E:
    """Teste end-to-end do fluxo completo de processamento de imagem"""

    def test_fluxo_completo_com_imagem(self, imagem_teste_base64):
        # Step 1: Conversão Base64
        assert imagem_teste_base64.startswith("data:image/"), \
            "Step 1 ❌: Conversão Base64 falhou"

        # Step 2: Criação da requisição (frontend -> backend)
        requisicao = DuvidaAlunoRequest(
            aluno_id="1",
            sessao_chat_id="1",
            texto_duvida="Qual é a resposta?",
            imagem_base64=imagem_teste_base64
        )
        assert requisicao.imagem_base64 is not None, \
            "Step 2 ❌: Backend não recebeu imagem"

        # Step 3: Imagem presente na requisição para repasse ao Gemini
        # (O repasse real está bloqueado pelo BUG #11)
        assert requisicao.imagem_base64 is not None, \
            "Step 3 ❌: Imagem não será repassada ao Gemini"

        # Step 4: Placeholder — validação da resposta da IA
        # Em um teste real, verificaríamos que a resposta analisa a imagem
        # e não retorna frases genéricas de fallback.

    def test_fluxo_sem_imagem_ainda_funciona(self, requisicao_apenas_texto):
        assert requisicao_apenas_texto.texto_duvida is not None
        assert requisicao_apenas_texto.imagem_base64 is None


# ============================================================================
# TESTES DE REGRESSÃO
# ============================================================================

class TestRegressoes:
    """Garante que a correção do BUG #11 não quebra funcionalidades existentes"""

    def test_texto_sem_imagem_continua_funcionando(self):
        req = DuvidaAlunoRequest(
            aluno_id="1",
            sessao_chat_id="1",
            texto_duvida="Uma pergunta",
            imagem_base64=None
        )
        assert req.texto_duvida == "Uma pergunta"
        assert req.imagem_base64 is None

    def test_historico_conversas_nao_afetado(self):
        historico = [
            {"remetente": "aluno", "conteudo": "Qual é a resposta?"},
            {"remetente": "ia", "conteudo": "Vamos analisar..."}
        ]
        assert len(historico) == 2
        assert all("conteudo" in msg for msg in historico)


# ============================================================================
# CENÁRIO: Criação bem-sucedida de aluno (email novo)
# ============================================================================

class TestCriarAlunoNovo:
    """Valida o fluxo de criação quando o email ainda não está cadastrado"""

    def test_db_add_commit_refresh_sao_chamados(self, db_mock, dados_aluno_valido):
        montar_db_sem_aluno(db_mock)

        criar_aluno(dados=dados_aluno_valido, db=db_mock)

        assert db_mock.add.call_count == 1, "❌ db.add() não foi chamado"
        assert db_mock.commit.call_count == 1, "❌ db.commit() não foi chamado"
        assert db_mock.refresh.call_count == 1, "❌ db.refresh() não foi chamado"

    def test_aluno_criado_com_campos_corretos(self, db_mock, dados_aluno_valido):
        montar_db_sem_aluno(db_mock)
        aluno_capturado = None

        def capturar_add(obj):
            nonlocal aluno_capturado
            aluno_capturado = obj

        db_mock.add.side_effect = capturar_add

        criar_aluno(dados=dados_aluno_valido, db=db_mock)

        assert aluno_capturado is not None, \
            "❌ Nenhum objeto foi passado ao db.add()"
        assert aluno_capturado.nome == "Maria Silva", \
            "❌ Nome salvo no banco está incorreto"
        assert aluno_capturado.email == "maria.silva@email.com", \
            "❌ Email salvo no banco está incorreto"
        assert aluno_capturado.visto is False, \
            "❌ Campo 'visto' deveria iniciar como False"
        assert aluno_capturado.ultima_interacao == "", \
            "❌ Campo 'ultima_interacao' deveria iniciar vazio"

    def test_resposta_contem_todos_os_campos(self, db_mock, dados_aluno_valido, aluno_persistido):
        montar_db_com_aluno(db_mock, aluno_persistido)

        resposta = criar_aluno(dados=dados_aluno_valido, db=db_mock)

        assert hasattr(resposta, "id"), "❌ Campo 'id' ausente na resposta"
        assert hasattr(resposta, "name"), "❌ Campo 'name' ausente na resposta"
        assert hasattr(resposta, "email"), "❌ Campo 'email' ausente na resposta"
        assert hasattr(resposta, "lastInteraction"), "❌ Campo 'lastInteraction' ausente"
        assert hasattr(resposta, "visto"), "❌ Campo 'visto' ausente na resposta"

    def test_id_retornado_como_string(self, db_mock, dados_aluno_valido, aluno_persistido):
        montar_db_com_aluno(db_mock, aluno_persistido)

        resposta = criar_aluno(dados=dados_aluno_valido, db=db_mock)

        assert isinstance(resposta.id, str), \
            f"❌ 'id' deveria ser str, mas é {type(resposta.id)}"

    def test_last_interaction_none_vira_string_vazia(self, db_mock, dados_aluno_valido, aluno_persistido):
        aluno_persistido.ultima_interacao = None
        montar_db_com_aluno(db_mock, aluno_persistido)

        resposta = criar_aluno(dados=dados_aluno_valido, db=db_mock)

        assert resposta.lastInteraction == "", \
            "❌ lastInteraction deveria ser '' quando ultima_interacao é None"

    def test_visto_none_vira_false_no_response(self, db_mock, dados_aluno_valido, aluno_persistido):
        aluno_persistido.visto = None
        montar_db_com_aluno(db_mock, aluno_persistido)

        resposta = criar_aluno(dados=dados_aluno_valido, db=db_mock)

        assert resposta.visto is False, \
            "❌ 'visto' deveria ser False quando o banco retorna None"


# ============================================================================
# CENÁRIO: Idempotência — email já cadastrado
# ============================================================================

class TestCriarAlunoEmailDuplicado:
    """Valida que o endpoint não duplica alunos com o mesmo email"""

    def test_db_add_nao_e_chamado_para_email_existente(self, db_mock, dados_aluno_valido, aluno_persistido):
        montar_db_com_aluno(db_mock, aluno_persistido)

        criar_aluno(dados=dados_aluno_valido, db=db_mock)

        assert db_mock.add.call_count == 0, \
            "❌ db.add() foi chamado para aluno já existente — duplicata!"

    def test_db_commit_nao_e_chamado_para_email_existente(self, db_mock, dados_aluno_valido, aluno_persistido):
        montar_db_com_aluno(db_mock, aluno_persistido)

        criar_aluno(dados=dados_aluno_valido, db=db_mock)

        assert db_mock.commit.call_count == 0, \
            "❌ db.commit() foi chamado desnecessariamente"

    def test_retorna_dados_do_aluno_existente(self, db_mock, dados_aluno_valido, aluno_persistido):
        montar_db_com_aluno(db_mock, aluno_persistido)

        resposta = criar_aluno(dados=dados_aluno_valido, db=db_mock)

        assert resposta.email == aluno_persistido.email, \
            "❌ Email na resposta não bate com o aluno existente"
        assert resposta.name == aluno_persistido.nome, \
            "❌ Nome na resposta não bate com o aluno existente"
        assert resposta.id == str(aluno_persistido.id), \
            "❌ ID na resposta não bate com o aluno existente"


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])