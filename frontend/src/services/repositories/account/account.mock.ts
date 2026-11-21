import type { AccountRepository } from './account.repository';

export const accountMock: AccountRepository = {
  async getMe() {
    return { name: 'Zaeem', email: 'zaeem@example.com', initials: 'Z', onboarded: true };
  },
};
