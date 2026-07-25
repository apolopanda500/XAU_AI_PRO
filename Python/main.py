# vazio ou exportações mínimas
class DataEngineXAU:
    def load(self):
        # stub mínimo para evitar erros do linter/execução
        import pandas as pd
        return pd.DataFrame()

class DataPipeline:
    def __init__(self, df):
        self.df = df
    def convert_numeric(self): return self
    def remove_empty(self): return self
    def clean(self): return self
    def sort_time(self): return self
    def remove_duplicates(self): return self
    def reset(self): return self
    def get(self): return self.df

# "python.analysis.extraPaths": ["./Python"]  # ou caminho até a raiz do seu projecto (isto é configuração do editor, não código Python)

import sys, pathlib, importlib

# adicione a raiz do ficheiro ao sys.path (se necessário)
sys.path.append(str(pathlib.Path(__file__).parent))

# tenta importar módulos do package `data` se existirem; senão usa as classes locais acima
data_engine_mod = None
data_pipeline_mod = None
try:
    data_engine_mod = importlib.import_module('data.data_engine_xau')
except ModuleNotFoundError:
    pass

try:
    data_pipeline_mod = importlib.import_module('data.data_pipeline')
except ModuleNotFoundError:
    pass

# reporta onde os módulos foram encontrados (ou informa que não foram)
if data_pipeline_mod is not None:
    print("DataPipeline:", getattr(data_pipeline_mod, '__file__', '<built-in>'))
else:
    print("DataPipeline: módulo 'data.data_pipeline' não encontrado; usando classe local DataPipeline")

if data_engine_mod is not None:
    print("DataEngine  :", getattr(data_engine_mod, '__file__', '<built-in>'))
else:
    print("DataEngine  : módulo 'data.data_engine_xau' não encontrado; usando classe local DataEngineXAU")

# escolhe as classes a usar
EngineClass = getattr(data_engine_mod, 'DataEngineXAU', None) or DataEngineXAU
PipelineClass = getattr(data_pipeline_mod, 'DataPipeline', None) or DataPipeline

engine = EngineClass()

try:
    df = engine.load()
except FileNotFoundError as exc:
    print(f"Arquivo de dados não encontrado: {exc}")
    print("Usando DataEngineXAU local vazio como fallback.")
    engine = DataEngineXAU()
    df = engine.load()

print(df.shape)
print(df.columns)
print(df.head())
pipeline = PipelineClass(df)

dataset = (
    pipeline
        .convert_numeric()
        .remove_empty()
        .clean()
        .sort_time()
        .remove_duplicates()
        .reset()
        .get()
)

print()
print(dataset.head())
print()
print(dataset.info())
print()
print(dataset.describe())

# import data.data_pipeline
# print(data.data_pipeline.__file__)
# (linhas originais comentadas para evitar erros quando o package 'data' não existe)