/**
 * XAU AI PRO — Componente QuantumBackground
 *
 * Canvas animado com partículas quânticas flutuantes e linhas de energia.
 * Cores baseadas no tema ativo (hook useTheme).
 *
 * Performance:
 * - requestAnimationFrame para animação suave
 * - Cleanup completo em useEffect
 * - Respeita prefers-reduced-motion
 *
 * Props:
 * - density: número de partículas (padrão: 50)
 * - speed: velocidade da animação (padrão: 1)
 * - className: classes CSS adicionais
 */

import { useEffect, useRef, useCallback } from 'react';
import { cssVar } from '../hooks/useTheme';

/* ---------- Tipos ---------- */

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  opacity: number;
  color: string;
}

interface QuantumBackgroundProps {
  /** Número de partículas no canvas (padrão: 50) */
  density?: number;
  /** Multiplicador de velocidade (padrão: 1) */
  speed?: number;
  /** Classes CSS adicionais */
  className?: string;
}

/* ---------- Constantes ---------- */

const DEFAULT_DENSITY = 50;
const DEFAULT_SPEED = 1;
const CONNECTION_DISTANCE = 120;
const PARTICLE_MIN_RADIUS = 1;
const PARTICLE_MAX_RADIUS = 3;
const LINE_WIDTH = 0.5;

/* ---------- Componente Principal ---------- */

export default function QuantumBackground({
  density = DEFAULT_DENSITY,
  speed = DEFAULT_SPEED,
  className = '',
}: QuantumBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const particlesRef = useRef<Particle[]>([]);
  const mouseRef = useRef({ x: 0, y: 0 });
  const activeRef = useRef(true);

  // Obtém as cores do tema atual a partir das variáveis CSS
  const getThemeColors = useCallback(() => {
    return {
      primary: cssVar('quantum-primary', '#4f7cff'),
      secondary: cssVar('quantum-secondary', '#00d4ff'),
      accent: cssVar('quantum-accent', '#a855f7'),
    };
  }, []);

  // Cria uma partícula com posição e velocidade aleatórias
  const createParticle = useCallback(
    (width: number, height: number, colors: ReturnType<typeof getThemeColors>): Particle => {
      const colorChoice = Math.random();
      let color: string;
      if (colorChoice < 0.5) {
        color = colors.primary;
      } else if (colorChoice < 0.8) {
        color = colors.secondary;
      } else {
        color = colors.accent;
      }
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.5 * speed,
        vy: (Math.random() - 0.5) * 0.5 * speed,
        radius: PARTICLE_MIN_RADIUS + Math.random() * (PARTICLE_MAX_RADIUS - PARTICLE_MIN_RADIUS),
        opacity: 0.3 + Math.random() * 0.7,
        color,
      };
    },
    [speed]
  );

  // Inicializa as partículas com base na densidade configurada
  const initParticles = useCallback(
    (width: number, height: number) => {
      const colors = getThemeColors();
      const particles: Particle[] = [];
      for (let i = 0; i < density; i++) {
        particles.push(createParticle(width, height, colors));
      }
      particlesRef.current = particles;
    },
    [density, createParticle, getThemeColors]
  );

  // Atualiza a posição de todas as partículas
  const updateParticles = useCallback((width: number, height: number) => {
    particlesRef.current.forEach((p) => {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > width) {
        p.vx *= -1;
        p.x = Math.max(0, Math.min(width, p.x));
      }
      if (p.y < 0 || p.y > height) {
        p.vy *= -1;
        p.y = Math.max(0, Math.min(height, p.y));
      }
      p.opacity = 0.3 + Math.abs(Math.sin(Date.now() * 0.001 + p.x * 0.01)) * 0.7;
    });
  }, []);

  // Desenha todas as partículas no canvas
  const drawParticles = useCallback((ctx: CanvasRenderingContext2D) => {
    particlesRef.current.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = p.opacity;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius * 2, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = p.opacity * 0.2;
      ctx.fill();
    });
    ctx.globalAlpha = 1;
  }, []);

  // Desenha linhas de energia conectando partículas próximas
  const drawConnections = useCallback((ctx: CanvasRenderingContext2D) => {
    const particles = particlesRef.current;
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < CONNECTION_DISTANCE) {
          const opacity = (1 - distance / CONNECTION_DISTANCE) * 0.3;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = particles[i].color;
          ctx.globalAlpha = opacity;
          ctx.lineWidth = LINE_WIDTH;
          ctx.stroke();
        }
      }
    }
    ctx.globalAlpha = 1;
  }, []);

  // Loop principal de animação
  const animate = useCallback(
    (ctx: CanvasRenderingContext2D, width: number, height: number) => {
      ctx.clearRect(0, 0, width, height);
      updateParticles(width, height);
      drawConnections(ctx);
      drawParticles(ctx);
      if (activeRef.current) {
        animationRef.current = requestAnimationFrame(() => animate(ctx, width, height));
      }
    },
    [updateParticles, drawParticles, drawConnections]
  );

  // Redimensiona o canvas
  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
  }, []);

  // Handler de mouse
  const handleMouseMove = useCallback((e: MouseEvent) => {
    mouseRef.current = { x: e.clientX, y: e.clientY };
  }, []);

  // Efeito principal: inicializa canvas e animação
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;
    const visibility = new IntersectionObserver(([entry]) => {
      activeRef.current = entry.isIntersecting;
      if (activeRef.current && !animationRef.current) animate(ctx, canvas.clientWidth, canvas.clientHeight);
    });
    visibility.observe(canvas);
    resizeCanvas();
    const rect = canvas.getBoundingClientRect();
    initParticles(rect.width, rect.height);
    animate(ctx, rect.width, rect.height);
    window.addEventListener('resize', resizeCanvas);
    window.addEventListener('mousemove', handleMouseMove);
    return () => {
      cancelAnimationFrame(animationRef.current);
      window.removeEventListener('resize', resizeCanvas);
      window.removeEventListener('mousemove', handleMouseMove);
      visibility.disconnect();
      activeRef.current = false;
    };
  }, [density, speed, initParticles, animate, resizeCanvas, handleMouseMove]);

  // Efeito para detectar mudança de tema
  useEffect(() => {
    const html = document.documentElement;
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'data-theme') {
          const canvas = canvasRef.current;
          if (!canvas) return;
          const rect = canvas.getBoundingClientRect();
          initParticles(rect.width, rect.height);
        }
      });
    });
    observer.observe(html, { attributes: true });
    return () => observer.disconnect();
  }, [initParticles]);

  return (
    <canvas
      ref={canvasRef}
      className={`quantum-bg-canvas ${className}`}
      style={{
        position: 'fixed',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
      }}
      aria-hidden="true"
    />
  );
}
