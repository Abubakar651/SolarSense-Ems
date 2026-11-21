import { initials } from '@/lib/format';
import { apiGet } from '../../http/client';
import type { UserDto } from '../../http/dto';
import type { AccountRepository } from './account.repository';

export const accountHttp: AccountRepository = {
  async getMe() {
    const user = await apiGet<UserDto>('/api/me');
    return {
      name: user.name,
      email: user.email,
      initials: initials(user.name),
      onboarded: user.onboarded,
    };
  },
};
