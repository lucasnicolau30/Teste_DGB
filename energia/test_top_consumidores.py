import pytest
import requests
import time
import csv
from datetime import date, timedelta

# ===============================================================
# 🔧 CONFIGURAÇÕES GERAIS
# ===============================================================
BASE_URL = "http://172.16.40.100:8025/analise_energia/top-consumidores"
HEADERS = {"accept": "application/json"}
REPETICOES = 5
ARQUIVO_CSV = "csv/energia/ranking_maiores_consumidores_resultados.csv"
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
hoje = date.today()
tres_dias_atras = (hoje - timedelta(days=3)).isoformat()
quinze_dias_atras = (hoje - timedelta(days=15)).isoformat()

cenarios = [
    # ✅ Cenário 1 - padrão (top 10)
    ({"top_n": 10}, "Top 10 padrão", 200),

    # ✅ Cenário 2 - top 5 (mínimo permitido)
    ({"top_n": 5}, "Top 5 mínimo", 200),

    # ✅ Cenário 3 - top 50 (máximo permitido)
    ({"top_n": 50}, "Top 50 máximo", 200),

    # ✅ Cenário 4 - com intervalo de datas curto
    ({"data_inicio": tres_dias_atras, "data_fim": hoje.isoformat(), "top_n": 10}, "Intervalo 3 dias", 200),

    # ✅ Cenário 5 - intervalo maior (15 dias)
    ({"data_inicio": quinze_dias_atras, "data_fim": hoje.isoformat(), "top_n": 10}, "Intervalo 15 dias", 200),

    # ❌ Cenário 6 - top_n abaixo do mínimo
    ({"top_n": 1}, "Top_n abaixo do mínimo (1)", 422),

    # ❌ Cenário 7 - top_n acima do máximo
    ({"top_n": 100}, "Top_n acima do máximo (100)", 422),

    # ❌ Cenário 8 - datas invertidas
    ({"data_inicio": hoje.isoformat(), "data_fim": quinze_dias_atras, "top_n": 10}, "Datas invertidas", 422),

    # ❌ Cenário 9 - parâmetros inválidos
    ({"top_n": "dez"}, "Top_n inválido (string)", 422),
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
def test_ranking_maiores_consumidores(session, params, descricao, status_esperado):
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

        # Validação da resposta JSON se for 200
        if status_real == 200:
            data = resp.json()
            assert isinstance(data, list), "Resposta deve ser uma lista"

            if len(data) > 0:
                for item in data:
                    for campo in [
                        "posicao",
                        "medidor",
                        "consumo_total_kwh",
                        "custo_total"
                    ]:
                        assert campo in item, f"Campo ausente: {campo}"

                    assert isinstance(item["posicao"], int), "'posicao' deve ser int"
                    assert isinstance(item["medidor"], str), "'medidor' deve ser string"
                    assert isinstance(item["consumo_total_kwh"], (int, float)), "'consumo_total_kwh' deve ser numérico"
                    assert isinstance(item["custo_total"], (int, float)), "'custo_total' deve ser numérico"

                    assert item["consumo_total_kwh"] >= 0, "'consumo_total_kwh' deve ser >= 0"
                    assert item["custo_total"] >= 0, "'custo_total' deve ser >= 0"

                # Verifica se o ranking está em ordem crescente
                posicoes = [i["posicao"] for i in data]
                assert posicoes == sorted(posicoes), "Lista de posições fora de ordem"

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

    # Verifica tempo médio (só se esperado 200)
    if status_esperado == 200:
        assert media < LIMITE_TEMPO_MEDIO, f"⏱ Tempo médio alto ({media:.2f}s) em {descricao}"