import pytest
import requests
import time
import csv
import re

# ===============================================================
# CONFIGURAÇÕES GERAIS
# ===============================================================
BASE_URL = "http://172.16.40.100:8025/metricas"
HEADERS = {"accept": "application/json"}
REPETICOES = 5
ARQUIVO_CSV = "csv/default/metricas_prometheus_resultados.csv"
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
    ({}, "Métricas Prometheus expostas corretamente", 200),
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
def test_metricas_prometheus(session, params, descricao, status_esperado):
    tempos = []
    sucesso = True
    status_real = None

    print(f"\n=== Cenário: {descricao} ===")
    print(f"Parâmetros: {params}")

    for i in range(REPETICOES):
        inicio = time.perf_counter()
        resp = session.get(BASE_URL, params=params, timeout=10)
        fim = time.perf_counter()

        duracao = fim - inicio
        tempos.append(duracao)
        status_real = resp.status_code

        print(f"➡️ Tentativa {i+1}: {status_real} em {duracao:.3f}s")

        if status_real != status_esperado:
            sucesso = False
            print(f"❌ Status inesperado: {status_real}, esperado: {status_esperado}")
            break

        # Validação do formato Prometheus
        if status_real == 200:
            texto = resp.text.strip()

            # Corrige escape de JSON — converte texto "\n" em quebras reais
            if texto.startswith('"') and texto.endswith('"'):
                texto = texto[1:-1]  # remove aspas externas
            texto = texto.encode('utf-8').decode('unicode_escape')

            # Deve conter cabeçalhos típicos de métricas
            assert "# HELP" in texto, "Saída Prometheus deve conter '# HELP'"
            assert "# TYPE" in texto, "Saída Prometheus deve conter '# TYPE'"

            # Deve conter pelo menos uma métrica válida
            padrao = r'^[a-zA-Z_:][a-zA-Z0-9_:]*\{?.*?\}?\s+[0-9eE+.\-]+$'
            assert re.search(padrao, texto, re.MULTILINE), "Nenhuma métrica Prometheus válida encontrada"

            # Deve conter métricas conhecidas
            assert "api_requests_total" in texto, "Métrica 'api_requests_total' ausente"
            assert "api_request_duration_seconds" in texto, "Métrica 'api_request_duration_seconds' ausente"

    # ============================================================
    # Estatísticas e escrita do CSV
    # ============================================================
    tempo_medio = sum(tempos) / len(tempos)
    tempo_min = min(tempos)
    tempo_max = max(tempos)

    print(f"\n Tempo médio: {tempo_medio:.3f}s (mín: {tempo_min:.3f}s, máx: {tempo_max:.3f}s)")
    print(f"✅ Sucesso: {sucesso}")

    # Escreve no CSV
    with open(ARQUIVO_CSV, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            descricao,
            params,
            status_esperado,
            status_real,
            f"{tempo_medio:.3f}",
            f"{tempo_min:.3f}",
            f"{tempo_max:.3f}",
            "Sim" if sucesso else "Não"
        ])

    # Valida tempo médio
    assert tempo_medio < LIMITE_TEMPO_MEDIO, f"Tempo médio acima do limite ({LIMITE_TEMPO_MEDIO}s)"
    assert sucesso, f"Falha no cenário: {descricao}"