import type { AccountUser } from '@/types/domain/account';

export interface AccountRepository {
  /** The signed-in user. */
  getMe(): Promise<AccountUser>;
}
