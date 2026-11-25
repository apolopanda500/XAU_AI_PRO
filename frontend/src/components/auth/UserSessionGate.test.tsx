import { describe, expect, it, vi } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';

vi.mock('../../lib/api', () => ({
  isMobileRuntime: () => true,
}));

import UserSessionGate from './UserSessionGate';

describe('UserSessionGate - acesso direto APK', () => {
  it('entra direto no app no mobile, sem login/wizard', () => {
    render(
      <UserSessionGate>
        <div data-testid="app">app</div>
      </UserSessionGate>,
    );
    expect(screen.getByTestId('app')).toBeTruthy();
  });
});
