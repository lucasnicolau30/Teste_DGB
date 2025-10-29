import pytest
import requests
import time
import csv
from datetime import date, timedelta

# ===============================================================
# CONFIGURAÇÕES GERAIS
# ===============================================================
BASE_URL = "http://172.16.40.100:8025/analise_energia/consumo-temporal" 
HEADERS = {"accept": "application/json"}
REPETICOES = 5
ARQUIVO_CSV = "csv/energia/consumo_temporal_resultados.csv"
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
hoje = date.today()
tres_dias_atras = (hoje - timedelta(days=3)).isoformat()
dez_dias_atras = (hoje - timedelta(days=10)).isoformat()

cenarios = [
    # Cenário 1 - padrão (sem parâmetros)
    ({}, "Sem parâmetros", 200),

    # Cenário 2 - limit pequeno
    ({"limit": 10}, "Limit 10", 200),

    # Cenário 3 - limit grande
    ({"limit": 100000}, "Limit 100000", 200),

    # Cenário 4 - intervalo de datas curto
    ({"data_inicio": tres_dias_atras, "data_fim": hoje.isoformat(), "limit": 5000}, "Intervalo 3 dias", 200),

    # Cenário 5 - apenas data_inicio
    ({"data_inicio": dez_dias_atras}, "Apenas data_inicio", 200),

    # Cenário 6 - apenas data_fim
    ({"data_fim": hoje.isoformat()}, "Apenas data_fim", 200),

    # Cenário 7 - agregação por hora
    ({"agregacao": "hora"}, "Agregação hora", 200),

    # Cenário 8 - agregação por semana
    ({"agregacao": "semana"}, "Agregação semana", 200),

    # Cenário 9 - agregação por mês
    ({"agregacao": "mes"}, "Agregação mês", 200),

    # Cenário 10 - lista curta de medidores
    ({"medidor_ids": [123, 120, 67, 64]}, "Lista curta de medidores", 200),

    # Cenário 11 - lista longa de medidores
    ({"medidor_ids": list(range(1, 51))}, "Lista longa de medidores", 200),

    # Cenário 12 - medidores inválidos
    ({"medidor_ids": ["a", "b", "c"]}, "Medidores inválidos", 422),

    # Cenário 13 - agregação inválida
    ({"agregacao": "ano"}, "Agregação inválida", 422),

    # Cenário 14 - datas invertidas
    ({"data_inicio": hoje.isoformat(), "data_fim": dez_dias_atras}, "Datas invertidas", 422),
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
def test_consumo_temporal(session, params, descricao, status_esperado):
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

        # Se for 200, valida estrutura do JSON
        if status_real == 200:
            data = resp.json()
            assert isinstance(data, list), "Resposta deve ser uma lista"
            if len(data) > 0:
                for item in data:
                    for campo in [
                        "periodo",
                        "medidor_id",
                        "medidor_descricao",
                        "consumo_total_kwh",
                        "consumo_medio_kwh",
                        "total_leituras",
                    ]:
                        assert campo in item, f"Campo ausente no JSON: {campo}"

                    # Validar tipos básicos
                    assert isinstance(item["periodo"], str)
                    assert isinstance(item["medidor_id"], int)
                    assert item["medidor_descricao"] is None or isinstance(item["medidor_descricao"], str)
                    assert isinstance(item["consumo_total_kwh"], (int, float))
                    assert isinstance(item["consumo_medio_kwh"], (int, float))
                    assert isinstance(item["total_leituras"], int)
                    assert item["total_leituras"] >= 0

    # Estatísticas de tempo
    media = sum(tempos) / len(tempos)
    menor = min(tempos)
    maior = max(tempos)

    print(f"\n Resultados — {descricao}")
    print(f"  Status Esperado: {status_esperado}")
    print(f"  Status Real: {status_real}")
    print(f"  Média: {media:.3f}s | Mínimo: {menor:.3f}s | Máximo: {maior:.3f}s")

    # Salva no CSV
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

    # Verifica tempo médio
    if status_esperado == 200:
        assert media < LIMITE_TEMPO_MEDIO, f"Tempo médio alto ({media:.2f}s) em {descricao}"
