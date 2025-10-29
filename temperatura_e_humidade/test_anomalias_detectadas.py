import pytest
import requests
import time
import csv
from datetime import datetime

# ===============================================================
# CONFIGURAÇÕES GERAIS
# ===============================================================
BASE_URL = "http://172.16.40.100:8025/analise_medidores_temp_hum/anomalias-detectadas"
HEADERS = {"accept": "application/json"}
REPETICOES = 5
ARQUIVO_CSV = "csv/temperatura_e_humidade/anomalias_detectadas_resultados.csv"
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
    # Cenário 1 - Sem medidores, gravidade mínima baixa
    ({"gravidade_min": "baixa", "limit": 50}, "Sem medidor_ids, gravidade_min baixa", 200),

    # Cenário 2 - Gravidade mínima média
    ({"gravidade_min": "media", "limit": 50}, "Sem medidor_ids, gravidade_min média", 200),

    # Cenário 3 - Gravidade mínima alta
    ({"gravidade_min": "alta", "limit": 50}, "Sem medidor_ids, gravidade_min alta", 200),

    # Cenário 4 - Medidor específico
    ({"medidor_ids": [120], "gravidade_min": "baixa", "limit": 50}, "Medidor 11, gravidade_min baixa", 200),

    # Cenário 5 - Gravidade inválida
    ({"gravidade_min": "muito_alta", "limit": 50}, "Gravidade inválida", 422),
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

        # Se retorno for 200, valida estrutura JSON
        if status_real == 200:
            data = resp.json()
            assert isinstance(data, list), f"Retorno esperado: lista, recebido: {type(data)}"

            if len(data) > 0:
                item = data[0]
                assert isinstance(item, dict), "Cada item deve ser um objeto JSON"

                campos_esperados = [
                    "medidor_id",
                    "medidor_descricao",
                    "data_leitura",
                    "temperatura",
                    "temp_zscore",
                    "anomalia_tipo",
                    "gravidade"
                ]
                for campo in campos_esperados:
                    assert campo in item, f"Campo ausente: {campo}"

                # Tipos básicos
                assert isinstance(item["medidor_id"], int)
                assert isinstance(item["medidor_descricao"], str)
                assert isinstance(item["data_leitura"], str)
                assert isinstance(item["temperatura"], (int, float))
                assert isinstance(item["temp_zscore"], (int, float))
                assert isinstance(item["anomalia_tipo"], str)
                assert isinstance(item["gravidade"], str)

    # ===============================================================
    # Estatísticas de tempo
    # ===============================================================
    media = sum(tempos) / len(tempos)
    menor = min(tempos)
    maior = max(tempos)

    print(f"\n Resultados — {descricao}")
    print(f"  Status Esperado: {status_esperado}")
    print(f"  Status Real: {status_real}")
    print(f"  Média: {media:.3f}s | Mínimo: {menor:.3f}s | Máximo: {maior:.3f}s")

    # ===============================================================
    # Salva no CSV
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
    # Verifica tempo médio
    # ===============================================================
    if status_esperado == 200:
        assert media < LIMITE_TEMPO_MEDIO, f"Tempo médio alto ({media:.2f}s) em {descricao}"
