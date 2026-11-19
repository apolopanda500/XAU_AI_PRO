package com.xau_ai_pro.desktop

import android.os.Bundle
import androidx.activity.enableEdgeToEdge
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat

class MainActivity : TauriActivity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    enableEdgeToEdge()
    super.onCreate(savedInstanceState)
    aplicarTelaCheia()
  }

  // Tela cheia "sticky": as barras do sistema (relógio, notificações,
  // bateria e navegação) somem ao abrir o app. Arrastar a borda mostra
  // a barra do sistema de novo - ela reaparece transiente e se oculta
  // sozinha, sem o usuário precisar tocar em nada.
  private fun aplicarTelaCheia() {
    val controller = WindowCompat.getInsetsController(window, window.decorView) ?: return
    controller.hide(WindowInsetsCompat.Type.systemBars())
    controller.systemBarsBehavior =
      WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
  }
}
