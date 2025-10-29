import pytest
import requests
import time
import csv

# ===============================================================
# CONFIGURAÇÕES GERAIS
# ===============================================================
BASE_URL = "http://172.16.40.100:8025/"
HEADERS = {"accept": "application/json"}
REPETICOES = 5
ARQUIVO_CSV = "csv/default/endpoint_raiz_resultados.csv"
LIMITE_TEMPO_MEDIO = 30  # segundos

# ===============================================================
# FIXTURE HTTP SESSION
# ===============================================================
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update(HEADERS)
    yield s
    s.close()

# ===============================================================
# CENÁRIOS DE TESTE
# ===============================================================
cenarios = [
    ({}, "Acesso ao endpoint raiz", 200),
]

# ===============================================================
# CRIA/INICIALIZA O CSV
# ===============================================================
with open(ARQUIVO_CSV, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([
        "Cenário",
        "Parâmetros",
        "Status Esperado",
        "Status Real",
        "Tempo Médio (s)",
        "Tempo Mínimo (s)",
        "Tempo Máximo (s)",
        "Sucesso"
    ])

# ===============================================================
# TESTE PARAMETRIZADO
# ===============================================================
@pytest.mark.parametrize("params, descricao, status_esperado", cenarios, ids=[d for _, d, _ in cenarios])
def test_endpoint_raiz(session, params, descricao, status_esperado):
    tempos = []
    sucesso = True
    status_real = None

    print(f"\n=== Cenário: {descricao} ===")
    print(f"Parâmetros: {params}")

    for i in range(REPETICOES):
        inicio = time.perf_counter()
        resp = session.get(BASE_URL, params=params)
        fim = time.perf_counter()

        duracao = fim - inicio
        tempos.append(duracao)
        status_real = resp.status_code

        print(f"➡️ Tentativa {i+1}: {status_real} em {duracao:.3f}s")

        if status_real != status_esperado:
            sucesso = False
            print(f"❌ Status inesperado: {status_real}, esperado: {status_esperado}")
            break

        # Validação do JSON esperado
        if status_real == 200:
            data = resp.json()
            assert isinstance(data, dict), "Resposta deve ser um objeto JSON"

            # Campos obrigatórios
            for campo in ["service", "version", "status", "docs"]:
                assert campo in data, f"Campo ausente: {campo}"

            # Tipos e valores esperados
            assert isinstance(data["service"], str), "'service' deve ser string"
            assert isinstance(data["version"], str), "'version' deve ser string"
            assert isinstance(data["status"], str), "'status' deve ser string"
            assert isinstance(data["docs"], str), "'docs' deve ser string"

            # Conteúdo esperado
            assert data["service"].startswith("Time Series"), "Campo 'service' inesperado"
            assert data["version"] == "0.0.1", "Versão incorreta"
            assert data["status"] in ["Desenvolvimento", "Produção", "Homologação"], "Status fora do padrão"
            assert data["docs"] == "/docs", "Campo 'docs' deve ser '/docs'"

    # ===========================================================
    # Estatísticas de tempo e registro no CSV
    # ===========================================================
    media = sum(tempos) / len(tempos)
    menor = min(tempos)
    maior = max(tempos)

    print(f"\n📈 Resultados — {descricao}")
    print(f"  Status Esperado: {status_esperado}")
    print(f"  Status Real: {status_real}")
    print(f"  Média: {media:.3f}s | Mínimo: {menor:.3f}s | Máximo: {maior:.3f}s")

    # Registra no CSV
    with open(ARQUIVO_CSV, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            descricao,
            str(params),
            status_esperado,
            status_real,
            round(media, 3),
            round(menor, 3),
            round(maior, 3),
            "OK" if sucesso else "FALHA"
        ])

    # ===============================================================
    # Verifica tempo médio máximo
    # ===============================================================

    if status_esperado == 200:
        assert media < LIMITE_TEMPO_MEDIO, f"Tempo médio alto ({media:.2f}s) em {descricao}"
