/** The signed-in person, as shown in the account menu. */
export interface AccountUser {
  name: string;
  email: string;
  initials: string;
  /** False until the site has been set up in onboarding. */
  onboarded: boolean;
}
