# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, '.')
os.environ['ENVIRONMENT'] = 'production'

print('='*70)
print('TESTE FINAL - XAU AI PRO + SENTRY')
print('='*70)

from sentry_config import init_sentry, capture_training_error, capture_prediction_error, capture_model_performance

print('\n1. Inicializando Sentry...')
init_sentry()

print('\n2. Testando treinamento...')
capture_training_error(50, 0.23, 'Gradient explosion in LSTM')

print('\n3. Testando predicao...')
capture_prediction_error('XAUUSD', 'M5', 'Low confidence 45%')

print('\n4. Enviando metricas...')
capture_model_performance({
    'accuracy': 0.87,
    'f1_score': 0.85,
    'win_rate': '75%'
})

print('\n5. Flush...')
import sentry_sdk
sentry_sdk.flush(timeout=10)

print('\n' + '='*70)
print('SUCESSO!')
print('='*70)
print('Verifique: https://henrique-7n.sentry.io/issues/views/28799/')
