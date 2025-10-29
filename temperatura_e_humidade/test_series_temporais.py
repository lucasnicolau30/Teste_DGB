import pytest
import requests
import time
import csv
from datetime import datetime

# ===============================================================
# CONFIGURAÇÕES GERAIS
# ===============================================================
BASE_URL = "http://172.16.40.100:8025/analise_medidores_temp_hum/series-temporais-hora"
HEADERS = {"accept": "application/json"}
REPETICOES = 5
ARQUIVO_CSV = "csv/temperatura_e_humidade/series_temporais_hora_resultados.csv"
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
    # Cenário 1 - Sem medidor_ids, limite 100
    ({"limit": 100}, "Sem medidor_ids, limit 100", 200),

    # Cenário 2 - Medidor específico
    ({"medidor_ids": [2], "limit": 50}, "Medidor 2, limit 50", 200),

    # Cenário 3 - Vários medidores
    ({"medidor_ids": [123, 120, 67, 64], "limit": 50}, "Medidores 2 e 3, limit 50", 200),

    # Cenário 4 - Data de início e fim
    ({"data_inicio": "2025-07-24T00:00:00", "data_fim": "2025-07-24T23:59:59", "limit": 50},
    "Intervalo de data, limit 50", 200),

    # Cenário 5 - Limit inválido
    ({"limit": -1}, "Limit inválido", 422),
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
def test_series_temporais_hora(session, params, descricao, status_esperado):
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
                    "data_hora",
                    "temp_media",
                    "temp_min",
                    "temp_max",
                    "temp_desvio_padrao",
                    "total_leituras",
                    "total_anomalias"
                ]
                for campo in campos_esperados:
                    assert campo in item, f"Campo ausente: {campo}"

                # Tipos básicos
                assert isinstance(item["medidor_id"], int)
                assert isinstance(item["medidor_descricao"], str)
                assert isinstance(item["data_hora"], str)
                assert isinstance(item["temp_media"], (int, float))
                assert isinstance(item["temp_min"], (int, float))
                assert isinstance(item["temp_max"], (int, float))
                # Pode ser None
                assert item["temp_desvio_padrao"] is None or isinstance(item["temp_desvio_padrao"], (int, float))
                assert isinstance(item["total_leituras"], int)
                assert isinstance(item["total_anomalias"], int)

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