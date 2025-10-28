import pytest
import requests
import time
import csv

# ===============================================================
# 🔧 CONFIGURAÇÕES GERAIS
# ===============================================================
BASE_URL = "http://172.16.40.100:8025/analise_medidores_temp_hum/status-medidores"
HEADERS = {"accept": "application/json"}
REPETICOES = 5
ARQUIVO_CSV = "csv/temperatura_e_humidade/status_medidores_resultados.csv"
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
def test_status_medidores(session, params, descricao, status_esperado):
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

            # ✅ Deve ser uma lista
            assert isinstance(data, list), f"Retorno esperado: lista, recebido: {type(data)}"
            assert len(data) > 0, "Lista retornada está vazia"

            campos_esperados = [
                "medidor_id",
                "medidor",
                "ultima_leitura",
                "dias_sem_dados",
                "ultima_temperatura_c",
                "ultima_umidade_percent"
            ]

            # ✅ Valida estrutura dos primeiros 5 itens
            for idx, item in enumerate(data[:5]):
                assert isinstance(item, dict), f"Item {idx} não é um objeto JSON"
                for campo in campos_esperados:
                    assert campo in item, f"Campo ausente no item {idx}: {campo}"

                # ✅ Tipagem esperada
                assert isinstance(item["medidor_id"], int)
                assert isinstance(item["medidor"], str)
                assert isinstance(item["ultima_leitura"], str)
                assert isinstance(item["dias_sem_dados"], int)
                assert isinstance(item["ultima_temperatura_c"], (int, float))
                assert isinstance(item["ultima_umidade_percent"], (int, float))

                # ✅ Validações lógicas básicas
                assert item["dias_sem_dados"] >= 0, f"Dias sem dados inválido no item {idx}"
                assert -100 <= item["ultima_temperatura_c"] <= 100, f"Temperatura fora do intervalo plausível no item {idx}"
                assert 0 <= item["ultima_umidade_percent"] <= 100, f"Umidade fora do intervalo (0 a 100%) no item {idx}"

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