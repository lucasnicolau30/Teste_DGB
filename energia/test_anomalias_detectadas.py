import pytest
import requests
import time
import csv
from datetime import datetime

# ===============================================================
# 🔧 CONFIGURAÇÕES GERAIS
# ===============================================================
BASE_URL = "http://172.16.40.100:8025/analise_energia/anomalias-detectadas"
HEADERS = {"accept": "application/json"}
REPETICOES = 5
ARQUIVO_CSV = "csv/energia/anomalias_detectadas_resultados.csv"
LIMITE_TEMPO_MEDIO = 30  # segundos

# ===============================================================
# 🧰 FIXTURE HTTP SESSION
# ===============================================================
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update(HEADERS)
    yield s
    s.close()

# ===============================================================
# ⚙️ CENÁRIOS DE TESTE
# ===============================================================
cenarios = [
    # ✅ Cenário 1 - Padrão sem parâmetros
    ({}, "Sem parâmetros", 200),

    # ✅ Cenário 2 - Limit padrão
    ({"limit": 50}, "Limite padrão (50)", 200),

    # ✅ Cenário 3 - Limit máximo permitido
    ({"limit": 500}, "Limite máximo permitido (500)", 200),

    # ❌ Cenário 4 - Limite acima do máximo
    ({"limit": 1000}, "Limite acima do máximo", 422),

    # ❌ Cenário 5 - Parâmetro inválido (string no limit)
    ({"limit": "abc"}, "Limite inválido (string)", 422),

    # ✅ Cenário 6 - Limit + filtro por medidor (array de IDs)
    ({"limit": 50, "medidor_ids": [12345, 67890]}, "Filtro por medidor_ids", 200),
]

# ===============================================================
# 📊 CRIA/INICIALIZA O CSV
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
# 🧪 TESTE PARAMETRIZADO
# ===============================================================
@pytest.mark.parametrize("params, descricao, status_esperado", cenarios, ids=[d for _, d, _ in cenarios])
def test_anomalias_detectadas(session, params, descricao, status_esperado):
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

        # ✅ Validação do conteúdo JSON quando retorno for 200
        if status_real == 200:
            data = resp.json()
            assert isinstance(data, list), "Resposta deve ser uma lista"

            if len(data) > 0:
                for item in data:
                    # Campos esperados no JSON
                    for campo in [
                        "id",
                        "medidor_descricao",
                        "data",
                        "consumo_kwh",
                        "consumo_zscore",
                        "is_anomalia",
                        "gravidade",
                        "motivo"
                    ]:
                        assert campo in item, f"Campo ausente no JSON: {campo}"

                    # Tipagem esperada
                    assert isinstance(item["id"], int), "Campo 'id' deve ser inteiro"
                    assert (item["medidor_descricao"] is None or isinstance(item["medidor_descricao"], str)), \
                        "Campo 'medidor_descricao' deve ser string ou None"
                    assert isinstance(item["data"], str), "Campo 'data' deve ser string (ISO 8601)"
                    assert isinstance(item["consumo_kwh"], (float, int)), "Campo 'consumo_kwh' deve ser numérico"
                    assert isinstance(item["consumo_zscore"], (float, int)), "Campo 'consumo_zscore' deve ser numérico"
                    assert isinstance(item["is_anomalia"], bool), "Campo 'is_anomalia' deve ser booleano"
                    assert isinstance(item["gravidade"], str), "Campo 'gravidade' deve ser string"
                    assert isinstance(item["motivo"], str), "Campo 'motivo' deve ser string"

                    # Validação de formato da data
                    try:
                        datetime.fromisoformat(item["data"])
                    except ValueError:
                        pytest.fail(f"Campo 'data' não está em formato ISO válido: {item['data']}")

    # ===============================================================
    # 📈 Estatísticas de tempo
    # ===============================================================
    media = sum(tempos) / len(tempos)
    menor = min(tempos)
    maior = max(tempos)

    print(f"\n Resultados — {descricao}")
    print(f"  Status Esperado: {status_esperado}")
    print(f"  Status Real: {status_real}")
    print(f"  Média: {media:.3f}s | Mínimo: {menor:.3f}s | Máximo: {maior:.3f}s")

    # ===============================================================
    # 💾 Grava no CSV
    # ===============================================================
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
    # 🚨 Verifica tempo médio máximo
    # ===============================================================
    if status_esperado == 200:
        assert media < LIMITE_TEMPO_MEDIO, f"Tempo médio alto ({media:.2f}s) em {descricao}"