import pytest
import requests
import time
import csv
from datetime import datetime, timedelta

# ===============================================================
# 🔧 CONFIGURAÇÕES GERAIS
# ===============================================================
BASE_URL = "http://172.16.40.100:8025/analise_medidores_temp_hum/medicoes-enriquecidas"
HEADERS = {"accept": "application/json"}
REPETICOES = 5
ARQUIVO_CSV = "csv/temperatura_e_humidade/medicoes_enriquecidas_resultados.csv"
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
tres_dias_atras = hoje - timedelta(days=3)
dez_dias_atras = hoje - timedelta(days=10)

cenarios = [
    # ✅ Cenário 1 - Sem parâmetros
    ({}, "Sem parâmetros", 200),

    # ✅ Cenário 2 - tipo_sensor AMBIENTE
    ({"tipo_sensor": "AMBIENTE"}, "Tipo sensor AMBIENTE", 200),

    # ✅ Cenário 3 - tipo_sensor FREEZER
    ({"tipo_sensor": "FREEZER"}, "Tipo sensor FREEZER", 200),

    # ✅ Cenário 4 - Apenas data_inicio
    ({"data_inicio": dez_dias_atras.isoformat()}, "Apenas data_inicio", 200),

    # ✅ Cenário 5 - Apenas data_fim
    ({"data_fim": hoje.isoformat()}, "Apenas data_fim", 200),

    # ✅ Cenário 6 - Intervalo curto (3 dias)
    ({"data_inicio": tres_dias_atras.isoformat(), "data_fim": hoje.isoformat()}, "Intervalo de 3 dias", 200),

    # ✅ Cenário 7 - Limit pequeno
    ({"limit": 10}, "Limit 10", 200),

    # ✅ Cenário 8 - Limit máximo permitido
    ({"limit": 1000}, "Limit 1000", 200),

    # ✅ Cenário 9 - Apenas anomalias = true
    ({"apenas_anomalias": True}, "Apenas anomalias", 200),

    # ✅ Cenário 10 - Filtro por medidor_ids simples
    ({"medidor_ids": [123, 120, 67, 64]}, "Lista curta de medidores", 200),

    # ✅ Cenário 11 - Filtro com offset
    ({"limit": 20, "offset": 5}, "Limit 20 + Offset 5", 200),

    # ✅ Cenário 12 - Combinação completa
    ({
        "tipo_sensor": "AMBIENTE",
        "data_inicio": tres_dias_atras.isoformat(),
        "data_fim": hoje.isoformat(),
        "apenas_anomalias": False,
        "limit": 50,
        "offset": 0,
        "medidor_ids": [123, 120, 67, 64]
    }, "Cenário completo", 200),

    # ❌ Cenário 13 - tipo_sensor inválido
    ({"tipo_sensor": "INVALIDO"}, "Tipo sensor inválido", 422),

    # ❌ Cenário 14 - Datas invertidas
    ({"data_inicio": hoje.isoformat(), "data_fim": dez_dias_atras.isoformat()}, "Datas invertidas", 422),

    # ❌ Cenário 15 - medidor_ids inválido
    ({"medidor_ids": ["a", "b", "c"]}, "Medidores inválidos", 422),
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
def test_medicoes_enriquecidas(session, params, descricao, status_esperado):
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
                    "data_leitura",
                    "medidor_id",
                    "temperatura",
                    "umidade",
                    "tipo_medidor",
                    "anomalia_estatistica",
                    "fora_limites_definidos",
                    "anomalia_alvo"
                ]
                for campo in campos_esperados:
                    assert campo in item, f"Campo ausente: {campo}"

                # ✅ Tipos básicos
                assert isinstance(item["data_leitura"], str)
                assert isinstance(item["medidor_id"], int)
                assert isinstance(item["temperatura"], (int, float))
                assert isinstance(item["umidade"], (int, float))
                assert isinstance(item["tipo_medidor"], str)
                assert isinstance(item["anomalia_estatistica"], (int, float, bool))
                assert isinstance(item["fora_limites_definidos"], (int, float, bool))
                assert isinstance(item["anomalia_alvo"], (int, float, bool))

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