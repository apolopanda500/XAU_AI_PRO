import os
import sys
from pathlib import Path
import MetaTrader5 as mt5

# Adiciona o diretório raiz ao path para encontrar pacotes
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

try:
    from Tools.Logger import get_logger
except ImportError:
    # Se falhar o import absoluto, tenta o relativo ou direto se estiver no folder
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from Logger import get_logger

log = get_logger("integration_check")

def check_mt5():
    log.system("Verificando integração MetaTrader 5...")
    if not mt5.initialize():
        err = mt5.last_error()
        log.error(f"MT5: Falha na inicialização. Erro: {err}")
        return False
    
    info = mt5.terminal_info()
    if info is None:
        log.error("MT5: Não foi possível obter informações do terminal.")
        mt5.shutdown()
        return False
    
    log.info(f"MT5: Conectado com sucesso. Terminal: {info.name} ({info.company})")
    log.info(f"MT5: Caminho de dados: {info.data_path}")
    mt5.shutdown()
    return True

def check_env_vars():
    log.system("Verificando variáveis de ambiente (Alpha/Brave)...")
    
    alpha_key = os.environ.get("ALPHAVANTAGE_API_KEY")
    brave_key = os.environ.get("BRAVE_API_KEY")
    
    status = True
    if not alpha_key or alpha_key == "${input:alphavantage_api_key}":
        log.warn("ALPHA: ALPHAVANTAGE_API_KEY não definida ou pendente de input.")
        status = False
    else:
        log.info("ALPHA: Chave Alpha Vantage encontrada.")

    if not brave_key or brave_key == "${input:brave_api_key}":
        log.warn("BRAVE: BRAVE_API_KEY não definida ou pendente de input.")
        status = False
    else:
        log.info("BRAVE: Chave Brave Search encontrada.")
        
    return status

def main():
    log.system("Iniciando Verificação de Integração Completa")
    mt5_ok = check_mt5()
    env_ok = check_env_vars()
    
    print("\n" + "="*50)
    print(" RESULTADO DA INTEGRAÇÃO")
    print("="*50)
    print(f" MetaTrader 5:    {'[ OK ]' if mt5_ok else '[ FALHA ]'}")
    print(f" Alpha Vantage:   {'[ OK ]' if env_ok else '[ PENDENTE ]'}")
    print(f" Brave Search:    {'[ OK ]' if env_ok else '[ PENDENTE ]'}")
    print("="*50)
    print(f"Consulte os logs em: {os.path.join('Logs', 'python.log')}")
    
    if not mt5_ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
