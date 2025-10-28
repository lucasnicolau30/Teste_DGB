import pytest
import requests
import time
import csv
from datetime import datetime, timedelta

# ===============================================================
# 🔧 CONFIGURAÇÕES GERAIS
# ===============================================================
BASE_URL = "http://172.16.40.100:8025/analise_medidores_temp_hum/resumo-por-medidor"
HEADERS = {"accept": "application/json"}
REPETICOES = 5
ARQUIVO_CSV = "csv/temperatura_e_humidade/resumo_por_medidor_resultados.csv"
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
hoje = datetime.now()
tres_dias_atras = (hoje - timedelta(days=3)).isoformat()
dez_dias_atras = (hoje - timedelta(days=10)).isoformat()

cenarios = [
    # ✅ Cenário 1 - Sem parâmetros
    ({}, "Sem parâmetros", 200),

    # ✅ Cenário 2 - Apenas data_inicio
    ({"data_inicio": dez_dias_atras}, "Apenas data_inicio", 200),

    # ✅ Cenário 3 - Apenas data_fim
    ({"data_fim": hoje.isoformat()}, "Apenas data_fim", 200),

    # ✅ Cenário 4 - Intervalo de datas
    ({"data_inicio": tres_dias_atras, "data_fim": hoje.isoformat()}, "Intervalo de 3 dias", 200),

    # ❌ Cenário 5 - Datas invertidas
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
def test_resumo_por_medidor(session, params, descricao, status_esperado):
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

        # ✅ Se retorno for 200, valida estrutura JSON
        if status_real == 200:
            data = resp.json()
            assert isinstance(data, list), f"Retorno esperado: lista, recebido: {type(data)}"

            if len(data) > 0:
                item = data[0]
                assert isinstance(item, dict), "Cada item deve ser um objeto JSON"

                campos_esperados = [
                    "medidor_id",
                    "medidor_descricao",
                    "total_leituras",
                    "temperatura_media",
                    "temperatura_min",
                    "temperatura_max",
                    "total_anomalias",
                    "percentual_anomalias",
                    "ultima_leitura",
                    "status"
                ]
                for campo in campos_esperados:
                    assert campo in item, f"Campo ausente: {campo}"

                # ✅ Tipos básicos
                assert isinstance(item["medidor_id"], int)
                assert isinstance(item["medidor_descricao"], str)
                assert isinstance(item["total_leituras"], int)
                assert isinstance(item["temperatura_media"], (int, float))
                assert isinstance(item["temperatura_min"], (int, float))
                assert isinstance(item["temperatura_max"], (int, float))
                assert isinstance(item["total_anomalias"], int)
                assert isinstance(item["percentual_anomalias"], (int, float))
                assert isinstance(item["ultima_leitura"], str)
                assert isinstance(item["status"], str)

    # ===============================================================
    # 📊 Estatísticas de tempo
    # ===============================================================
    media = sum(tempos) / len(tempos)
    menor = min(tempos)
    maior = max(tempos)

    print(f"\n Resultados — {descricao}")
    print(f"  Status Esperado: {status_esperado}")
    print(f"  Status Real: {status_real}")
    print(f"  Média: {media:.3f}s | Mínimo: {menor:.3f}s | Máximo: {maior:.3f}s")

    # ===============================================================
    # 💾 Salva no CSV
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
    # ⏱️ Verifica tempo médio
    # ===============================================================
    if status_esperado == 200:
        assert media < LIMITE_TEMPO_MEDIO, f"Tempo médio alto ({media:.2f}s) em {descricao}"
