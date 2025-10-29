import pytest
import requests
import time
import csv
from datetime import date, timedelta

# ===============================================================
# CONFIGURAÇÕES GERAIS
# ===============================================================
BASE_URL = "http://172.16.40.100:8025/analise_energia/comparacao-medidores"
HEADERS = {"accept": "application/json"}
REPETICOES = 5
ARQUIVO_CSV = "csv/energia/comparacao_performance_medidores_resultados.csv"
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
# ⚙️ CENÁRIOS DE TESTE
# ===============================================================
hoje = date.today()
tres_dias_atras = (hoje - timedelta(days=3)).isoformat()
dez_dias_atras = (hoje - timedelta(days=10)).isoformat()

cenarios = [
    # ✅ Cenário 1 - padrão (sem parâmetros)
    ({}, "Sem parâmetros", 200),

    # ✅ Cenário 2 - limit pequeno (mesmo que não exista, força teste de estabilidade)
    ({"limit": 10}, "Limit 10", 200),

    # ✅ Cenário 3 - limit grande
    ({"limit": 100000}, "Limit 100000", 200),

    # ✅ Cenário 4 - intervalo de datas curto
    ({"data_inicio": tres_dias_atras, "data_fim": hoje.isoformat()}, "Intervalo 3 dias", 200),

    # ✅ Cenário 5 - apenas data_inicio
    ({"data_inicio": dez_dias_atras}, "Apenas data_inicio", 200),

    # ✅ Cenário 6 - apenas data_fim
    ({"data_fim": hoje.isoformat()}, "Apenas data_fim", 200),

    # ❌ Cenário 7 - datas invertidas
    ({"data_inicio": hoje.isoformat(), "data_fim": dez_dias_atras}, "Datas invertidas", 422),
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
def test_comparacao_performance_medidores(session, params, descricao, status_esperado):
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

        # Se for 200, valida estrutura do JSON retornado
        if status_real == 200:
            data = resp.json()
            assert isinstance(data, list), "Resposta deve ser uma lista"
            for medidor in data:
                for campo in [
                    "medidor_descricao",
                    "periodo",
                    "consumo_total_kwh",
                    "custo_total",
                    "consumo_medio_kwh",
                    "pico_consumo_kwh",
                    "fator_potencia_medio",
                    "total_leituras",
                ]:
                    assert campo in medidor, f"Campo ausente no JSON: {campo}"

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