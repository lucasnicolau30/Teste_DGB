import pytest
import requests
import time
import csv

# ===============================================================
# 🔧 CONFIGURAÇÕES GERAIS
# ===============================================================
BASE_URL = "http://172.16.40.100:8025/analise_medidores_temp_hum/dashboard-operacional"
HEADERS = {"accept": "application/json"}
REPETICOES = 5
ARQUIVO_CSV = "csv/temperatura_e_humidade/dashboard_operacional_temp_hum_resultados.csv"
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
    ({}, "Sem parâmetros", 200),
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
def test_dashboard_operacional_temp_hum(session, params, descricao, status_esperado):
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

        # ✅ Validação do corpo JSON se status = 200
        if status_real == 200:
            data = resp.json()

            campos_esperados = [
                "total_medidores",
                "medidores_ativos",
                "total_leituras_hoje",
                "total_anomalias_hoje",
                "temperatura_media_geral",
                "medidores_com_alerta",
                "timestamp_atualizacao"
            ]

            # ✅ Valida presença dos campos
            for campo in campos_esperados:
                assert campo in data, f"Campo ausente no JSON: {campo}"

            # ✅ Valida tipos dos campos principais
            assert isinstance(data["total_medidores"], int)
            assert isinstance(data["medidores_ativos"], int)
            assert isinstance(data["total_leituras_hoje"], int)
            assert isinstance(data["total_anomalias_hoje"], int)
            assert isinstance(data["temperatura_media_geral"], (int, float))
            assert isinstance(data["medidores_com_alerta"], list)
            assert isinstance(data["timestamp_atualizacao"], str)

    # ============================================================
    # 📈 Estatísticas de tempo
    # ============================================================
    media = sum(tempos) / len(tempos)
    menor = min(tempos)
    maior = max(tempos)

    print(f"\nResultados — {descricao}")
    print(f"  Status Esperado: {status_esperado}")
    print(f"  Status Real: {status_real}")
    print(f"  Média: {media:.3f}s | Mínimo: {menor:.3f}s | Máximo: {maior:.3f}s")

    # ============================================================
    # 🧾 Salva no CSV
    # ============================================================
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

    # ============================================================
    # ⏱️ Valida tempo médio
    # ============================================================
    if status_esperado == 200:
        assert media < LIMITE_TEMPO_MEDIO, f"Tempo médio alto ({media:.2f}s) em {descricao}"
